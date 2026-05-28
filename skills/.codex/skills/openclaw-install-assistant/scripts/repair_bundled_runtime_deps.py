#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ISOLATED_DIR_NAME = ".bundled-runtime-deps"

KNOWN_MANIFEST_FIXES: Dict[str, Dict[str, str]] = {
    "dist/extensions/diagnostics-otel/package.json": {
        '"@opentelemetry/api-logs": "^0.214.0"': '"@opentelemetry/api-logs": "^0.213.0"',
        '"@opentelemetry/exporter-logs-otlp-proto": "^0.214.0"': '"@opentelemetry/exporter-logs-otlp-proto": "^0.213.0"',
        '"@opentelemetry/exporter-metrics-otlp-proto": "^0.214.0"': '"@opentelemetry/exporter-metrics-otlp-proto": "^0.213.0"',
        '"@opentelemetry/exporter-trace-otlp-proto": "^0.214.0"': '"@opentelemetry/exporter-trace-otlp-proto": "^0.213.0"',
        '"@opentelemetry/sdk-logs": "^0.214.0"': '"@opentelemetry/sdk-logs": "^0.213.0"',
        '"@opentelemetry/sdk-metrics": "^2.6.1"': '"@opentelemetry/sdk-metrics": "^2.6.0"',
        '"@opentelemetry/sdk-node": "^0.214.0"': '"@opentelemetry/sdk-node": "^0.213.0"',
    }
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Repair bundled plugin runtime deps for an installed OpenClaw runtime root "
            "using an isolated npm prefix plus symlinks into the package root."
        ),
        epilog=(
            "Risk operations: this script may edit known-bad bundled plugin manifests, "
            "create or reuse an isolated dependency tree under the runtime root, and "
            "remove/recreate matching package directories or symlinks under node_modules "
            "for the targeted direct dependencies. Run with --dry-run first if unsure."
        ),
    )
    parser.add_argument("--runtime-root", required=True, help="Installed OpenClaw package root")
    parser.add_argument("--npm-bin", required=True, help="npm binary used for the target runtime")
    parser.add_argument(
        "--isolated-dir-name",
        default=ISOLATED_DIR_NAME,
        help=f"Directory name for the isolated dependency tree (default: {ISOLATED_DIR_NAME})",
    )
    parser.add_argument(
        "--skip-known-manifest-fixes",
        action="store_true",
        help="Do not apply built-in manifest version fixes before installing deps",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print actions without changing files")
    return parser.parse_args()


def print_risks(runtime_root: Path, isolated_prefix: Path) -> None:
    print(f"[risk] runtime root: {runtime_root}")
    print(f"[risk] isolated prefix: {isolated_prefix}")
    print("[risk] may patch known broken bundled manifests in dist/extensions/*/package.json")
    print("[risk] may install packages into the isolated prefix with npm")
    print("[risk] may replace matching entries under runtime_root/node_modules with symlinks")


def patch_known_manifests(runtime_root: Path, dry_run: bool) -> List[Path]:
    changed: List[Path] = []
    for relative_path, replacements in KNOWN_MANIFEST_FIXES.items():
        manifest = runtime_root / relative_path
        if not manifest.exists():
            continue
        original = manifest.read_text()
        updated = original
        for old, new in replacements.items():
            updated = updated.replace(old, new)
        if updated == original:
            continue
        changed.append(manifest)
        if not dry_run:
            manifest.write_text(updated)
    return changed


def discover_missing(runtime_root: Path) -> Tuple[List[str], List[str]]:
    extensions_dir = runtime_root / "dist" / "extensions"
    specs: List[str] = []
    dep_names: List[str] = []
    if not extensions_dir.exists():
        return specs, dep_names
    for entry in sorted(extensions_dir.iterdir()):
        manifest = entry / "package.json"
        if not manifest.exists():
            continue
        package_json = json.loads(manifest.read_text())
        deps = {}
        deps.update(package_json.get("dependencies", {}))
        deps.update(package_json.get("optionalDependencies", {}))
        for dep, version in deps.items():
            sentinel = runtime_root / "node_modules" / Path(*dep.split("/")) / "package.json"
            if sentinel.exists():
                continue
            specs.append(f"{dep}@{version}")
            dep_names.append(dep)
    # Preserve order while deduplicating.
    specs = list(dict.fromkeys(specs))
    dep_names = list(dict.fromkeys(dep_names))
    return specs, dep_names


def run_npm_install(npm_bin: Path, isolated_prefix: Path, specs: List[str], dry_run: bool) -> None:
    if not specs:
        return
    cmd = [
        str(npm_bin),
        "install",
        "--prefix",
        str(isolated_prefix),
        "--omit=dev",
        "--ignore-scripts",
        "--package-lock=false",
        *specs,
    ]
    print("[plan] npm install specs:")
    for spec in specs:
        print(f"  - {spec}")
    if dry_run:
        return
    subprocess.run(cmd, check=True)


def relink_direct_deps(runtime_root: Path, isolated_prefix: Path, dep_names: List[str], dry_run: bool) -> None:
    if not dep_names:
        return
    root_node_modules = runtime_root / "node_modules"
    isolated_node_modules = isolated_prefix / "node_modules"
    if not dry_run:
        root_node_modules.mkdir(parents=True, exist_ok=True)
    for dep in dep_names:
        source = isolated_node_modules / Path(*dep.split("/"))
        target = root_node_modules / Path(*dep.split("/"))
        print(f"[plan] link {target} -> {source}")
        if dry_run:
            continue
        if not source.exists():
            raise FileNotFoundError(f"isolated dependency is missing: {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.exists():
            shutil.rmtree(target)
        target.symlink_to(source, target_is_directory=True)


def verify_missing(runtime_root: Path) -> List[str]:
    missing_specs, _ = discover_missing(runtime_root)
    return missing_specs


def main() -> int:
    args = parse_args()
    runtime_root = Path(args.runtime_root).expanduser().resolve()
    npm_bin = Path(args.npm_bin).expanduser().resolve()
    isolated_prefix = runtime_root / args.isolated_dir_name

    if not runtime_root.exists():
        print(f"runtime root does not exist: {runtime_root}", file=sys.stderr)
        return 2
    if not npm_bin.exists():
        print(f"npm binary does not exist: {npm_bin}", file=sys.stderr)
        return 2

    print_risks(runtime_root, isolated_prefix)

    if not args.skip_known_manifest_fixes:
        changed = patch_known_manifests(runtime_root, args.dry_run)
        if changed:
            print("[info] patched known bundled manifests:")
            for manifest in changed:
                print(f"  - {manifest}")
        else:
            print("[info] no known manifest patch needed")

    missing_specs, dep_names = discover_missing(runtime_root)
    if not missing_specs:
        print("[info] bundled runtime deps already complete")
        return 0

    print("[info] missing direct deps:")
    for spec in missing_specs:
        print(f"  - {spec}")

    run_npm_install(npm_bin, isolated_prefix, missing_specs, args.dry_run)
    relink_direct_deps(runtime_root, isolated_prefix, dep_names, args.dry_run)

    if args.dry_run:
        print("[info] dry-run only; verification skipped")
        return 0

    remaining = verify_missing(runtime_root)
    if remaining:
        print("[error] bundled runtime deps still missing after repair:")
        for spec in remaining:
            print(f"  - {spec}")
        return 1

    print("[ok] bundled runtime deps are complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
