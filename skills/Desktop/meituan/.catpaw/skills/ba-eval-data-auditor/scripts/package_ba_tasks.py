#!/usr/bin/env python3
import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Iterable

TASK_NAME_RE = re.compile(r"^ba-(\d{3})$")
DEFAULT_START = 43
DEFAULT_END = 81
DEFAULT_SOURCE_ROOTS = [Path("BA/43-53"), Path("BA/54-81")]
DEFAULT_TEMPLATE_ROOT = Path("ba-0xx")
DEFAULT_OUTPUT_ROOT = Path("packaged-ba-043-081")
SKILL_REL_PATH = Path("environment/ride-hailing-ba-skill")


class PackagingError(Exception):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy BA tasks into the ba-0xx folder layout and build one zip file per task "
            "without modifying the original BA directories."
        )
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Workspace root. Relative paths are resolved from here.",
    )
    parser.add_argument(
        "--source-root",
        dest="source_roots",
        action="append",
        default=[],
        type=Path,
        help=(
            "Source BA root to scan. Repeat this flag to provide multiple roots. "
            "Defaults to BA/43-53 and BA/54-81 under the workspace root."
        ),
    )
    parser.add_argument(
        "--template-root",
        type=Path,
        default=DEFAULT_TEMPLATE_ROOT,
        help="Template folder that contains environment/ride-hailing-ba-skill.",
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Output root for copied task folders and generated zip files.",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=DEFAULT_START,
        help="Start task number, inclusive.",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=DEFAULT_END,
        help="End task number, inclusive.",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Only package the given task name(s), for example: --only ba-043 --only ba-081",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Remove the existing output root before packaging.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the packaging plan without writing files.",
    )
    return parser.parse_args()


def resolve_path(workspace: Path, candidate: Path) -> Path:
    return candidate if candidate.is_absolute() else workspace / candidate


def task_name_to_number(task_name: str) -> int:
    match = TASK_NAME_RE.fullmatch(task_name)
    if not match:
        raise PackagingError(f"Invalid task name: {task_name}")
    return int(match.group(1))


def normalize_only(values: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        task_name = value.strip()
        task_name_to_number(task_name)
        normalized.append(task_name)
    return sorted(set(normalized))


def collect_tasks(source_roots: list[Path], start: int, end: int, only: list[str]) -> dict[str, Path]:
    selected = set(only) if only else {f"ba-{number:03d}" for number in range(start, end + 1)}
    found: dict[str, Path] = {}

    for source_root in source_roots:
        if not source_root.exists():
            raise PackagingError(f"Source root does not exist: {source_root}")
        for child in sorted(source_root.iterdir()):
            if not child.is_dir():
                continue
            match = TASK_NAME_RE.fullmatch(child.name)
            if not match:
                continue
            task_number = int(match.group(1))
            if child.name not in selected:
                continue
            if not (start <= task_number <= end):
                continue
            if child.name in found:
                raise PackagingError(f"Duplicate task found in multiple roots: {child.name}")
            found[child.name] = child

    missing = sorted(selected - set(found))
    if missing:
        raise PackagingError("Missing task directories: " + ", ".join(missing))
    return dict(sorted(found.items()))


def ensure_source_files(task_name: str, task_dir: Path) -> tuple[Path, Path]:
    instruction_path = task_dir / "instruction.md"
    rubrics_path = task_dir / "solution" / "rubrics.md"
    missing: list[str] = []
    if not instruction_path.is_file():
        missing.append(str(instruction_path))
    if not rubrics_path.is_file():
        missing.append(str(rubrics_path))
    if missing:
        raise PackagingError(f"{task_name} is missing required files: {', '.join(missing)}")
    return instruction_path, rubrics_path


def prepare_output_root(out_root: Path, force: bool, dry_run: bool) -> None:
    if not out_root.exists():
        return
    if not force:
        raise PackagingError(f"Output root already exists, use --force to overwrite: {out_root}")
    if dry_run:
        return
    shutil.rmtree(out_root)


def ensure_template_skill(template_root: Path) -> Path:
    skill_dir = template_root / SKILL_REL_PATH
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        raise PackagingError(f"Template skill file not found: {skill_file}")
    return skill_dir


def copy_task(task_name: str, instruction_path: Path, rubrics_path: Path, skill_dir: Path, out_root: Path) -> Path:
    task_out_dir = out_root / task_name
    (task_out_dir / "solution").mkdir(parents=True, exist_ok=True)
    (task_out_dir / "input").mkdir(parents=True, exist_ok=True)
    (task_out_dir / "environment").mkdir(parents=True, exist_ok=True)

    shutil.copy2(instruction_path, task_out_dir / "instruction.md")
    shutil.copy2(rubrics_path, task_out_dir / "solution" / "rubrics.md")
    shutil.copytree(skill_dir, task_out_dir / SKILL_REL_PATH, dirs_exist_ok=True)
    return task_out_dir


def write_zip(task_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        base_dir = task_dir.parent
        add_directory_entry(archive, task_dir, base_dir)
        for path in sorted(task_dir.rglob("*")):
            if path.is_dir():
                add_directory_entry(archive, path, base_dir)
                continue
            archive.write(path, path.relative_to(base_dir))


def add_directory_entry(archive: zipfile.ZipFile, directory: Path, base_dir: Path) -> None:
    arcname = directory.relative_to(base_dir).as_posix().rstrip("/") + "/"
    info = zipfile.ZipInfo(arcname)
    archive.writestr(info, "")


def main() -> int:
    args = parse_args()
    workspace = args.workspace.resolve()
    template_root = resolve_path(workspace, args.template_root).resolve()
    out_root = resolve_path(workspace, args.out_root).resolve()
    source_roots = [resolve_path(workspace, root).resolve() for root in (args.source_roots or DEFAULT_SOURCE_ROOTS)]
    only = normalize_only(args.only)

    if args.start > args.end:
        raise PackagingError(f"Invalid range: start={args.start} is greater than end={args.end}")
    if only:
        for task_name in only:
            task_number = task_name_to_number(task_name)
            if not (args.start <= task_number <= args.end):
                raise PackagingError(
                    f"Task {task_name} is outside the selected range {args.start}-{args.end}"
                )

    skill_dir = ensure_template_skill(template_root)
    tasks = collect_tasks(source_roots, args.start, args.end, only)
    task_files = {
        task_name: ensure_source_files(task_name, task_dir)
        for task_name, task_dir in tasks.items()
    }

    print(f"Workspace: {workspace}")
    print(f"Template: {template_root}")
    print("Source roots:")
    for source_root in source_roots:
        print(f"  - {source_root}")
    print(f"Output root: {out_root}")
    print(f"Tasks: {', '.join(tasks.keys())}")

    if args.dry_run:
        print("Dry run only, no files were written.")
        return 0

    prepare_output_root(out_root, args.force, args.dry_run)
    out_root.mkdir(parents=True, exist_ok=True)

    for task_name, _task_dir in tasks.items():
        instruction_path, rubrics_path = task_files[task_name]
        copied_task_dir = copy_task(task_name, instruction_path, rubrics_path, skill_dir, out_root)
        write_zip(copied_task_dir, out_root / f"{task_name}.zip")
        print(f"Packaged {task_name} -> {copied_task_dir} and {out_root / f'{task_name}.zip'}")

    print(f"Done. Generated {len(tasks)} task folders and {len(tasks)} zip files.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PackagingError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
