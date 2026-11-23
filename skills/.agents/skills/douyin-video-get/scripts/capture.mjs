// capture.mjs — run via: ego-browser nodejs (script read from stdin)
// Inputs arrive on globalThis.__IN = { url, outDir } (injected by get-douyin.sh).
// Opens the Douyin video page in the user's real logged-in browser, lets the
// page compute its own request signatures, harvests the DASH media stream URLs
// from Resource Timing, and downloads them through the same page session.
// Emits one line on stdout: RESULT {json}. Diagnostics go to stderr so they
// survive a non-zero exit.

const { url, outDir } = globalThis.__IN;
const log = (m) => process.stderr.write(String(m) + "\n");
const emit = (obj) => process.stdout.write("RESULT " + JSON.stringify(obj) + "\n");

// Unique name avoids resuming a stale space whose p1 was closed by a prior run.
const task = await taskSpace("douyin-video-get-" + Date.now());

// A fresh space normally has p1; be robust if it does not.
let page;
const existing = await task.pages();
page = existing[0] || (await task.newPage());

try {
  await page.cdp("Network.enable", {});
  await page.goto(url, { timeout: 60000 });
  await page.waitForTimeout(3000);

  const title = (await page.title()) || "";
  const curUrl = await page.url();
  if (/\/(login|verify)/i.test(curUrl)) {
    emit({ ok: false, reason: "login_or_verify_required" });
    await task.finish({ keep: [page.label] });
    process.exit(0);
  }

  // Nudge playback so the player requests media segments, then let them flow.
  try { await page.click("xpath=//video", { timeout: 5000 }); } catch (e) {}
  await page.waitForTimeout(6000);

  const picked = await page.evaluate(() => {
    const uniq = [...new Set(performance.getEntriesByType("resource").map((e) => e.name))];
    const bt = (u) => { const m = /[?&]bt=(\d+)/.exec(u); return m ? +m[1] : 0; };
    const byBitrate = (list) => list.sort((a, b) => bt(b) - bt(a));
    const video = byBitrate(uniq.filter((u) => /media-video/.test(u)));
    const audio = byBitrate(uniq.filter((u) => /media-audio/.test(u)));
    // Fallback: some videos expose a single progressive mp4 instead of split DASH.
    const progressive = uniq.filter((u) => /douyinvod\.com/.test(u) && /mime_type=video_mp4/.test(u) && !/media-(video|audio)/.test(u));
    return { video: video[0] || null, audio: audio[0] || null, progressive: progressive[0] || null };
  });

  if (!picked.video && !picked.progressive) {
    emit({ ok: false, reason: "no_stream_captured", title });
    await task.finish({ keep: [page.label] });
    process.exit(0);
  }

  const result = { ok: true, title };
  const idm = /\/video\/(\d+)/.exec(curUrl);
  if (idm) result.id = idm[1];
  const src = picked.video || picked.progressive;
  log("downloading video stream...");
  const rv = await page.fetch(src, { saveAs: `${outDir}/video.mp4`, timeout: 180000 });
  if (rv.status !== 200) throw new Error("video fetch status " + rv.status);
  result.video = `${outDir}/video.mp4`;
  result.progressive = !picked.video; // progressive mp4 is already muxed

  if (picked.video && picked.audio) {
    log("downloading audio stream...");
    const ra = await page.fetch(picked.audio, { saveAs: `${outDir}/audio.mp4`, timeout: 180000 });
    if (ra.status === 200) result.audio = `${outDir}/audio.mp4`;
  }

  emit(result);
  await task.finish({ keep: [] });
} catch (err) {
  log("CAPTURE ERROR: " + (err && err.stack || err));
  emit({ ok: false, reason: String(err && err.message || err) });
  try { await task.finish({ keep: [page.label] }); } catch (e) {}
  process.exit(1);
}
