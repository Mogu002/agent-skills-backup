import fs from "node:fs";
import path from "node:path";

function versionParts(name) {
  return name.split(".").map((part) => Number.parseInt(part, 10) || 0);
}

function compareVersions(a, b) {
  const aa = versionParts(a);
  const bb = versionParts(b);
  const len = Math.max(aa.length, bb.length);
  for (let i = 0; i < len; i += 1) {
    const diff = (aa[i] || 0) - (bb[i] || 0);
    if (diff !== 0) return diff;
  }
  return 0;
}

export function findChromePluginRoot(homeDir) {
  const base = path.join(
    homeDir,
    ".codex",
    "plugins",
    "cache",
    "openai-bundled",
    "chrome",
  );
  if (!fs.existsSync(base)) {
    throw new Error(`Chrome plugin cache not found: ${base}`);
  }

  const versions = fs
    .readdirSync(base, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .filter((name) => /^\d+\.\d+\.\d+$/.test(name))
    .sort(compareVersions);

  if (versions.length === 0) {
    throw new Error(`No versioned Chrome plugin directories found under ${base}`);
  }

  return path.join(base, versions.at(-1));
}

export async function bootstrapChromeBrowser({ homeDir, globals = globalThis, sessionName }) {
  const root = findChromePluginRoot(homeDir);
  const modulePath = path.join(root, "scripts", "browser-client.mjs");
  const { setupBrowserRuntime } = await import(modulePath);
  await setupBrowserRuntime({ globals });
  const browser = await agent.browsers.get("extension");
  if (sessionName) {
    await browser.nameSession(sessionName);
  }
  return { browser, root };
}

export async function findMatchingOpenTab(browser, { urlIncludes, titleIncludes }) {
  const tabs = await browser.user.openTabs();
  return (
    tabs.find((tab) => {
      const urlMatch = !urlIncludes || (tab.url && tab.url.includes(urlIncludes));
      const titleMatch = !titleIncludes || (tab.title && tab.title.includes(titleIncludes));
      return urlMatch && titleMatch;
    }) || null
  );
}

export async function claimMatchingTab(browser, opts) {
  const match = await findMatchingOpenTab(browser, opts);
  if (!match) {
    throw new Error(`No open tab matched ${JSON.stringify(opts)}`);
  }
  const tab = await browser.user.claimTab(match);
  return { match, tab };
}

export async function extractTextWindow(tab, { needle, before = 1200, after = 5000 }) {
  return tab.playwright.evaluate(
    ({ needle: target, before: pre, after: post }) => {
      const txt = document.body?.innerText || "";
      const idx = txt.indexOf(target);
      return {
        idx,
        excerpt:
          idx >= 0
            ? txt.slice(Math.max(0, idx - pre), idx + post)
            : "",
      };
    },
    { needle, before, after },
  );
}
