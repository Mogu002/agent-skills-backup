#!/usr/bin/env node

import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

function parseArgs(argv) {
  const result = {
    mode: "preview",
    provider: "coconut",
    stateDir: path.join(os.homedir(), ".codex", "codex-router"),
    configPath: path.join(os.homedir(), ".codex", "config.toml"),
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--apply") result.mode = "apply";
    else if (arg === "--check") result.mode = "check";
    else if (arg === "--self-test") result.mode = "self-test";
    else if (["--provider", "--state-dir", "--config"].includes(arg)) {
      const value = argv[++index];
      if (!value || value.startsWith("--")) throw new Error(`${arg} requires a value.`);
      if (arg === "--provider") result.provider = value;
      if (arg === "--state-dir") result.stateDir = path.resolve(value);
      if (arg === "--config") result.configPath = path.resolve(value);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  if (!/^[a-z0-9][a-z0-9-]*$/.test(result.provider)) {
    throw new Error("Provider must contain only lowercase letters, digits, and hyphens.");
  }
  return result;
}

function readJson(filePath, required = true) {
  if (!fs.existsSync(filePath)) {
    if (required) throw new Error(`Missing file: ${filePath}`);
    return undefined;
  }
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    throw new Error(`Invalid JSON: ${filePath}`);
  }
}

function gatewaySafe(value) {
  return String(value)
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, "-")
    .replace(/-{2,}/g, "-")
    .replace(/^-|-$/g, "");
}

function providerLabel(provider) {
  return provider.charAt(0).toUpperCase() + provider.slice(1);
}

function normalizeModels(document, provider) {
  if (!document || document.version !== 1 || !Array.isArray(document.models)) {
    throw new Error("user-models.json must use version 1 with a models array.");
  }
  const prefix = `${provider}-`;
  const replacements = new Map();
  const changed = [];
  const models = document.models.map((model) => {
    if (model?.provider !== provider || typeof model.upstreamModel !== "string" || !model.upstreamModel.startsWith(prefix)) {
      return model;
    }
    const publicId = model.upstreamModel.slice(prefix.length);
    if (!publicId) throw new Error(`Empty public id for ${model.upstreamModel}.`);
    const desiredSlug = `${provider}/${publicId}`;
    const legacySlug = `${provider}/${model.upstreamModel}`;
    replacements.set(legacySlug, desiredSlug);
    if (typeof model.slug === "string" && model.slug !== desiredSlug) {
      replacements.set(model.slug, desiredSlug);
    }
    const gatewayModel = gatewaySafe(`${provider}-${publicId}`);
    const next = {
      ...model,
      slug: desiredSlug,
      gatewayModel,
      compHash: `${gatewayModel}-user-v1`,
      displayName: `${publicId} (${providerLabel(provider)})`,
    };
    if (JSON.stringify(next) !== JSON.stringify(model)) changed.push({ from: model.slug, to: desiredSlug });
    return next;
  });

  for (const field of ["slug", "gatewayModel", "compHash"]) {
    const values = models.map((model) => model?.[field]).filter(Boolean);
    if (new Set(values).size !== values.length) throw new Error(`Normalization would create duplicate ${field} values.`);
  }
  return { document: { ...document, models }, replacements, changed };
}

function migratePicker(document, replacements) {
  if (document === undefined) return undefined;
  if (!document || document.version !== 1 || !Array.isArray(document.hidden)) {
    throw new Error("model-picker.json must use version 1 with a hidden array.");
  }
  const hidden = new Set(document.hidden.map(String));
  const visible = new Set((Array.isArray(document.visible) ? document.visible : []).map(String));
  const seeded = new Set((Array.isArray(document.seeded) ? document.seeded : []).map(String));
  for (const [from, to] of replacements) {
    if (from === to) continue;
    const sourceVisible = visible.has(from);
    const sourceHidden = hidden.has(from);
    const sourceSeeded = seeded.has(from);
    hidden.delete(from);
    visible.delete(from);
    seeded.delete(from);
    if (sourceVisible) {
      hidden.delete(to);
      visible.add(to);
    } else if (sourceHidden) {
      visible.delete(to);
      hidden.add(to);
    }
    if (sourceVisible || sourceHidden || sourceSeeded) seeded.add(to);
  }
  for (const slug of hidden) visible.delete(slug);
  return {
    ...document,
    hidden: [...hidden].sort(),
    ...(Array.isArray(document.visible) ? { visible: [...visible].sort() } : {}),
    ...(Array.isArray(document.seeded) ? { seeded: [...seeded].sort() } : {}),
  };
}

function migrateAnnouncements(document, replacements) {
  if (document === undefined) return undefined;
  if (!document || document.version !== 1 || !document.models || typeof document.models !== "object" || Array.isArray(document.models)) {
    throw new Error("announced-models.json must use version 1 with a models object.");
  }
  const models = { ...document.models };
  for (const [from, to] of replacements) {
    if (from === to || !Object.hasOwn(models, from)) continue;
    const source = Number(models[from]) || 0;
    const destination = Number(models[to]) || 0;
    models[to] = Math.max(source, destination);
    delete models[from];
  }
  return { ...document, models };
}

function migrateRootModel(config, replacements) {
  if (config === undefined) return undefined;
  const newline = config.includes("\r\n") ? "\r\n" : "\n";
  const trailing = config.endsWith("\n");
  const lines = config.split(/\r?\n/);
  let inRoot = true;
  for (let index = 0; index < lines.length; index += 1) {
    if (/^\s*\[/.test(lines[index])) inRoot = false;
    if (!inRoot) continue;
    const match = lines[index].match(/^(\s*model\s*=\s*)(["'])([^"']+)\2(\s*(?:#.*)?)$/);
    if (!match) continue;
    const replacement = replacements.get(match[3]);
    if (replacement) lines[index] = `${match[1]}${match[2]}${replacement}${match[2]}${match[4]}`;
  }
  if (trailing && lines.at(-1) !== "") lines.push("");
  return lines.join(newline);
}

function jsonText(value) {
  return `${JSON.stringify(value, null, 2)}\n`;
}

function changed(before, after) {
  return after !== undefined && before !== after;
}

function backupName(filePath, stamp) {
  return `${filePath}.backup-coconut-slugs-${stamp}`;
}

function atomicWrite(filePath, contents, stamp) {
  const stat = fs.statSync(filePath);
  const backup = backupName(filePath, stamp);
  fs.copyFileSync(filePath, backup, fs.constants.COPYFILE_EXCL);
  fs.chmodSync(backup, stat.mode & 0o777);
  const temporary = `${filePath}.tmp.${process.pid}`;
  fs.writeFileSync(temporary, contents, { mode: stat.mode & 0o777 });
  fs.renameSync(temporary, filePath);
  fs.chmodSync(filePath, stat.mode & 0o777);
  return backup;
}

function selfTest() {
  const oldSlug = "coconut/coconut-model-alpha";
  const newSlug = "coconut/model-alpha";
  const fixture = {
    version: 1,
    models: [{
      slug: oldSlug,
      gatewayModel: "coconut-coconut-model-alpha",
      compHash: "coconut-coconut-model-alpha-user-v1",
      upstreamModel: "coconut-model-alpha",
      provider: "coconut",
      displayName: "old",
    }],
  };
  const normalized = normalizeModels(fixture, "coconut");
  assert.equal(normalized.document.models[0].slug, newSlug);
  assert.equal(normalized.document.models[0].upstreamModel, "coconut-model-alpha");
  assert.equal(normalized.document.models[0].displayName, "model-alpha (Coconut)");
  const picker = migratePicker({ version: 1, hidden: [newSlug], visible: [oldSlug], seeded: [oldSlug, newSlug] }, normalized.replacements);
  assert.deepEqual(picker.hidden, []);
  assert.deepEqual(picker.visible, [newSlug]);
  assert.equal(migrateRootModel(`model = "${oldSlug}"\n[profile]\nmodel = "keep"\n`, normalized.replacements), `model = "${newSlug}"\n[profile]\nmodel = "keep"\n`);
  process.stdout.write("PASS normalize-coconut-slugs self-test\n");
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.mode === "self-test") return selfTest();

  const modelsPath = path.join(options.stateDir, "user-models.json");
  const pickerPath = path.join(options.stateDir, "model-picker.json");
  const announcementsPath = path.join(options.stateDir, "announced-models.json");
  const modelsBefore = fs.readFileSync(modelsPath, "utf8");
  const normalized = normalizeModels(readJson(modelsPath), options.provider);
  const modelsAfter = jsonText(normalized.document);

  const pickerRaw = fs.existsSync(pickerPath) ? fs.readFileSync(pickerPath, "utf8") : undefined;
  const pickerAfterDocument = migratePicker(readJson(pickerPath, false), normalized.replacements);
  const pickerAfter = pickerAfterDocument === undefined ? undefined : jsonText(pickerAfterDocument);

  const announcementsRaw = fs.existsSync(announcementsPath) ? fs.readFileSync(announcementsPath, "utf8") : undefined;
  const announcementsAfterDocument = migrateAnnouncements(readJson(announcementsPath, false), normalized.replacements);
  const announcementsAfter = announcementsAfterDocument === undefined ? undefined : jsonText(announcementsAfterDocument);

  const configRaw = fs.existsSync(options.configPath) ? fs.readFileSync(options.configPath, "utf8") : undefined;
  const configAfter = migrateRootModel(configRaw, normalized.replacements);
  const writes = [
    { path: modelsPath, before: modelsBefore, after: modelsAfter },
    { path: pickerPath, before: pickerRaw, after: pickerAfter },
    { path: announcementsPath, before: announcementsRaw, after: announcementsAfter },
    { path: options.configPath, before: configRaw, after: configAfter },
  ].filter((entry) => entry.before !== undefined && changed(entry.before, entry.after));

  const summary = {
    mode: options.mode,
    provider: options.provider,
    models: normalized.changed,
    files: writes.map((entry) => entry.path),
  };
  process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);

  if (options.mode === "check") {
    if (writes.length) process.exitCode = 1;
    return;
  }
  if (options.mode !== "apply" || writes.length === 0) return;

  const stamp = `${new Date().toISOString().replace(/[^0-9]/g, "").slice(0, 14)}-${process.pid}`;
  const backups = writes.map((entry) => ({
    path: entry.path,
    backup: atomicWrite(entry.path, entry.after, stamp),
  }));
  process.stdout.write(`${JSON.stringify({ applied: writes.length, backups }, null, 2)}\n`);
}

try {
  main();
} catch (error) {
  process.stderr.write(`normalize-coconut-slugs: ${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 2;
}
