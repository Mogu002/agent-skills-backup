#!/usr/bin/env node

import fs from "node:fs";
import process from "node:process";

function printHelp() {
  process.stdout.write(`Extract a real Feishu/Lark doc URL or token from ByteTech-related text.

Usage:
  node extract_feishu_doc.mjs --text "<raw text or iframe url>"
  node extract_feishu_doc.mjs --file page.html
  cat page.html | node extract_feishu_doc.mjs --stdin
  node extract_feishu_doc.mjs --url https://my.feishu.cn/docx/DrA2...

Options:
  --text <value>     Parse the provided text directly
  --file <path>      Read input text from a local file
  --stdin            Read input text from stdin
  --url <value>      Alias of --text for a suspected doc URL
  --pretty           Pretty-print JSON output
  --help             Show this help

The script prefers real Feishu/Lark doc URLs such as:
  https://my.feishu.cn/docx/<token>
  https://*.larkoffice.com/docx/<token>
  https://*.larkoffice.com/wiki/<token>

It intentionally does not treat ByteTech hash tokens like #doxcn... as a
confirmed fetchable doc token.
`);
}

function parseArgs(argv) {
  const args = {
    pretty: false,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--help") {
      args.help = true;
    } else if (arg === "--pretty") {
      args.pretty = true;
    } else if (arg === "--stdin") {
      args.stdin = true;
    } else if (arg === "--text" || arg === "--file" || arg === "--url") {
      const value = argv[i + 1];
      if (!value) {
        throw new Error(`Missing value for ${arg}`);
      }
      args[arg.slice(2)] = value;
      i += 1;
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  return args;
}

function readStdin() {
  return new Promise((resolve, reject) => {
    let buf = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => {
      buf += chunk;
    });
    process.stdin.on("end", () => resolve(buf));
    process.stdin.on("error", reject);
  });
}

function shellQuote(value) {
  return `'${String(value).replace(/'/g, `'\\''`)}'`;
}

function collectCandidates(input) {
  const candidates = [];

  const urlRegex =
    /https?:\/\/(?:my\.feishu\.cn|[\w-]+\.larkoffice\.com|[\w-]+\.sg\.larkoffice\.com)\/(?:docx|wiki)\/([A-Za-z0-9]+)(?:[^\s"'<>)]*)?/g;
  for (const match of input.matchAll(urlRegex)) {
    candidates.push({
      type: "doc_url",
      token: match[1],
      raw: match[0],
    });
  }

  const attrRegex =
    /(?:src|href|currentSrc|iframeSrc|iframeCurrentSrc)"?\s*[:=]\s*"([^"]*(?:my\.feishu\.cn|larkoffice\.com)\/(?:docx|wiki)\/[A-Za-z0-9][^"]*)"/g;
  for (const match of input.matchAll(attrRegex)) {
    const inner = match[1];
    const docMatch = inner.match(
      /https?:\/\/(?:my\.feishu\.cn|[\w-]+\.larkoffice\.com|[\w-]+\.sg\.larkoffice\.com)\/(?:docx|wiki)\/([A-Za-z0-9]+)(?:[^\s"'<>)]*)?/,
    );
    if (docMatch) {
      candidates.push({
        type: "doc_attr",
        token: docMatch[1],
        raw: docMatch[0],
      });
    }
  }

  return dedupeCandidates(candidates);
}

function dedupeCandidates(candidates) {
  const seen = new Set();
  return candidates.filter((candidate) => {
    const key = `${candidate.token}|${candidate.raw}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function buildResult(input) {
  const candidates = collectCandidates(input);
  const primary = candidates[0] || null;
  const suspiciousHashTokens = [...new Set(
    [...input.matchAll(/#(doxcn[A-Za-z0-9]+)/g)].map((match) => match[1]),
  )];

  return {
    ok: !!primary,
    primary,
    candidates,
    suspicious_hash_tokens: suspiciousHashTokens,
    fetch_command: primary
      ? `lark-cli docs +fetch --api-version v2 --doc ${shellQuote(primary.token)} --doc-format markdown`
      : null,
    notes: primary
      ? [
          "Prefer the real Feishu/Lark doc token over the ByteTech outer-shell hash token.",
          "Use the fetch command above as the canonical正文拉取路径.",
        ]
      : [
          "No real Feishu/Lark doc URL was found in the provided input.",
          "If this came from a ByteTech article, switch to Chrome and inspect the embedded iframe src.",
        ],
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    printHelp();
    return;
  }

  const sources = [args.text, args.url, args.file, args.stdin].filter(Boolean);
  if (sources.length === 0) {
    throw new Error("Provide one of --text, --url, --file, or --stdin");
  }
  if ((args.text ? 1 : 0) + (args.url ? 1 : 0) + (args.file ? 1 : 0) + (args.stdin ? 1 : 0) > 1) {
    throw new Error("Use exactly one input source at a time");
  }

  let input = "";
  if (args.text) {
    input = args.text;
  } else if (args.url) {
    input = args.url;
  } else if (args.file) {
    input = fs.readFileSync(args.file, "utf8");
  } else if (args.stdin) {
    input = await readStdin();
  }

  const result = buildResult(input);
  const out = args.pretty ? JSON.stringify(result, null, 2) : JSON.stringify(result);
  process.stdout.write(`${out}\n`);
  if (!result.ok) {
    process.exitCode = 2;
  }
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
