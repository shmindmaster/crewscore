/**
 * CrewScore hero screencast — Sabhi-style continuous Playwright recording.
 *
 * Records the REAL static product (local index.html + score-engine.js), not mocks:
 *   landing → Weak demo prompt → score (hero: ~0/100) → Inspect → Plan fix → Apply → Export
 *
 * Usage (from repo root):
 *   node scripts/record-hero-demo.mjs
 *   node scripts/record-hero-demo.mjs --public-gif
 *   BASE_URL=https://crewscore.ai node scripts/record-hero-demo.mjs
 *
 * Outputs (gitignored under _production/):
 *   _production/screencast/desktop/CrewScore-01-Hero-Preflight-Desktop.webm
 *   _production/screencast/desktop/CrewScore-01-Hero-Preflight-Desktop.mp4
 *   _production/screencast/desktop/CrewScore-01-Hero-Preflight-Desktop.gif
 *   _production/screencast/desktop/timeline.hero.desktop.json
 * Public optional: docs/hero-demo.gif  (--public-gif)
 */
import { createRequire } from "node:module";
import { spawnSync } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import http from "node:http";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, "..");
const OUT_DIR = path.join(REPO, "_production", "screencast", "desktop");
const STEM = "CrewScore-01-Hero-Preflight-Desktop";
const VIEWPORT = { width: 1440, height: 900 };
const PUBLIC_GIF = process.argv.includes("--public-gif");
const BASE_ENV = process.env.BASE_URL || "";

const require = createRequire(import.meta.url);

function loadChromium() {
  const candidates = [
    "playwright",
    "@playwright/test",
    path.resolve(REPO, "..", "sabhi", "studio", "node_modules", "playwright"),
    path.resolve(REPO, "..", "sabhi", "studio", "node_modules", "@playwright", "test"),
  ];
  for (const id of candidates) {
    try {
      const mod = require(id);
      if (mod?.chromium) return mod.chromium;
    } catch {
      /* try next */
    }
  }
  throw new Error(
    "Playwright not found. Install with: npm i -D playwright  (or ensure sabhi/studio deps exist)",
  );
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function findFfmpeg() {
  const which = spawnSync(process.platform === "win32" ? "where" : "which", ["ffmpeg"], {
    encoding: "utf8",
  });
  const line = (which.stdout || "")
    .split(/\r?\n/)
    .map((s) => s.trim())
    .find(Boolean);
  return line || "ffmpeg";
}

async function startStaticServer(root) {
  const mime = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".json": "application/json",
    ".png": "image/png",
    ".woff2": "font/woff2",
  };
  const server = http.createServer(async (req, res) => {
    try {
      let urlPath = decodeURIComponent((req.url || "/").split("?")[0]);
      if (urlPath === "/") urlPath = "/index.html";
      const filePath = path.normalize(path.join(root, urlPath.replace(/^\//, "")));
      if (!filePath.startsWith(root)) {
        res.writeHead(403);
        res.end("forbidden");
        return;
      }
      const data = await fs.readFile(filePath);
      const ext = path.extname(filePath).toLowerCase();
      res.writeHead(200, { "Content-Type": mime[ext] || "application/octet-stream" });
      res.end(data);
    } catch {
      res.writeHead(404);
      res.end("not found");
    }
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  return {
    baseUrl: `http://127.0.0.1:${port}`,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}

async function moveCursor(page, x, y, steps = 14) {
  await page.mouse.move(x, y, { steps });
}

async function clickCenter(page, selector, { waitMs = 400 } = {}) {
  const loc = page.locator(selector).first();
  await loc.waitFor({ state: "visible", timeout: 15000 });
  const box = await loc.boundingBox();
  if (!box) throw new Error(`no box for ${selector}`);
  const x = box.x + box.width / 2;
  const y = box.y + box.height / 2;
  await moveCursor(page, x, y);
  await sleep(waitMs);
  await page.mouse.click(x, y);
  return { selector, x, y };
}

async function run() {
  const chromium = loadChromium();
  await fs.mkdir(OUT_DIR, { recursive: true });

  let closer = async () => {};
  let baseUrl = BASE_ENV;
  if (!baseUrl) {
    const srv = await startStaticServer(REPO);
    baseUrl = srv.baseUrl;
    closer = srv.close;
    console.log(`serving local product at ${baseUrl}`);
  } else {
    console.log(`recording remote ${baseUrl}`);
  }

  const recordDir = path.join(OUT_DIR, "_raw");
  await fs.rm(recordDir, { recursive: true, force: true });
  await fs.mkdir(recordDir, { recursive: true });

  const browser = await chromium.launch({
    headless: true,
    args: ["--disable-dev-shm-usage"],
  });

  const context = await browser.newContext({
    viewport: VIEWPORT,
    deviceScaleFactor: 1,
    locale: "en-US",
    timezoneId: "America/Chicago",
    recordVideo: {
      dir: recordDir,
      size: VIEWPORT,
    },
    reducedMotion: "reduce",
  });

  const page = await context.newPage();
  const timeline = {
    product: "CrewScore",
    episode: "hero-preflight",
    baseUrl,
    viewport: VIEWPORT,
    startedAt: new Date().toISOString(),
    acts: [],
  };
  const mark = (id, detail = {}) => {
    timeline.acts.push({ id, t: Date.now(), ...detail });
    console.log(`act: ${id}`);
  };

  try {
    await page.goto(baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`, {
      waitUntil: "networkidle",
      timeout: 60000,
    });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.waitForFunction(
      () => window.CrewScoreEngine && document.getElementById("btn-score-agent"),
      { timeout: 20000 },
    );
    mark("cold-open-landing");
    await sleep(1800);

    mark("before-state-empty-invite");
    await page.locator("#empty-invite").waitFor({ state: "visible" });
    await sleep(2200);

    const weak = page.locator("#template-chips button", { hasText: "Weak demo prompt" });
    await weak.waitFor({ state: "visible" });
    const weakBox = await weak.boundingBox();
    await moveCursor(page, weakBox.x + weakBox.width / 2, weakBox.y + weakBox.height / 2);
    await sleep(350);
    await weak.click();
    mark("select-weak-demo");

    await page.locator("#agent-scorecard").waitFor({ state: "visible", timeout: 15000 });
    const inspectOpen = await page.locator("#deck-inspect:not(.hidden)").count();
    if (!inspectOpen) {
      await clickCenter(page, "#btn-score-agent");
      await page.locator("#deck-inspect:not(.hidden)").waitFor({ timeout: 15000 });
    }
    mark("hero-score-reveal");
    await sleep(2800);

    await page.locator("#agent-scorecard").scrollIntoViewIfNeeded();
    await sleep(2200);
    mark("inspect-hold");

    await clickCenter(page, "#btn-plan-fix");
    await page.locator("#deck-act:not(.hidden)").waitFor({ timeout: 15000 });
    await page.locator("#btn-apply-fix").waitFor({ state: "visible" });
    mark("plan-preview");
    await sleep(2200);

    await clickCenter(page, "#btn-apply-fix");
    await sleep(1200);
    await page.locator("#agent-scorecard, #deck-export:not(.hidden)").first().waitFor({
      state: "visible",
      timeout: 15000,
    });
    mark("apply-and-rescore");
    await sleep(2500);

    const exportPill = page.locator("#stg-export:not([disabled])");
    if (await exportPill.count()) {
      await exportPill.click();
      await page
        .locator("#deck-export:not(.hidden)")
        .waitFor({ timeout: 10000 })
        .catch(() => {});
      mark("export-stage");
      await sleep(2200);
    }

    await page
      .locator("#stg-inspect:not([disabled])")
      .click()
      .catch(() => {});
    await sleep(1800);
    mark("end-hold");
  } finally {
    await context.close();
    await browser.close();
    await closer();
  }

  const files = await fs.readdir(recordDir);
  const webmRaw = files.find((f) => f.endsWith(".webm"));
  if (!webmRaw) throw new Error("Playwright did not produce a .webm recording");

  const webmOut = path.join(OUT_DIR, `${STEM}.webm`);
  const mp4Out = path.join(OUT_DIR, `${STEM}.mp4`);
  const gifOut = path.join(OUT_DIR, `${STEM}.gif`);
  await fs.rename(path.join(recordDir, webmRaw), webmOut);
  await fs.rm(recordDir, { recursive: true, force: true });

  const ffmpeg = findFfmpeg();
  console.log(`ffmpeg: ${ffmpeg}`);

  const mp4 = spawnSync(
    ffmpeg,
    [
      "-y",
      "-i",
      webmOut,
      "-c:v",
      "libx264",
      "-pix_fmt",
      "yuv420p",
      "-movflags",
      "+faststart",
      "-an",
      mp4Out,
    ],
    { encoding: "utf8" },
  );
  if (mp4.status !== 0) {
    console.error(mp4.stderr);
    throw new Error("ffmpeg mp4 failed");
  }

  // Full-res gif for delivery folder
  const gif = spawnSync(
    ffmpeg,
    [
      "-y",
      "-i",
      webmOut,
      "-vf",
      "fps=12,scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer",
      "-loop",
      "0",
      gifOut,
    ],
    { encoding: "utf8" },
  );
  if (gif.status !== 0) {
    console.error(gif.stderr);
    throw new Error("ffmpeg gif failed");
  }

  if (PUBLIC_GIF) {
    // Compact README/HN loop (720w) — keep under ~4MB
    const publicPath = path.join(REPO, "docs", "hero-demo.gif");
    const pub = spawnSync(
      ffmpeg,
      [
        "-y",
        "-i",
        webmOut,
        "-vf",
        "fps=10,scale=720:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=96:stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3",
        "-loop",
        "0",
        publicPath,
      ],
      { encoding: "utf8" },
    );
    if (pub.status !== 0) {
      console.error(pub.stderr);
      throw new Error("ffmpeg public gif failed");
    }
    console.log(`public gif: ${publicPath}`);
  }

  timeline.finishedAt = new Date().toISOString();
  timeline.outputs = {
    webm: path.relative(REPO, webmOut).replace(/\\/g, "/"),
    mp4: path.relative(REPO, mp4Out).replace(/\\/g, "/"),
    gif: path.relative(REPO, gifOut).replace(/\\/g, "/"),
  };
  const timelinePath = path.join(OUT_DIR, "timeline.hero.desktop.json");
  await fs.writeFile(timelinePath, JSON.stringify(timeline, null, 2));

  const sizes = {};
  for (const p of [webmOut, mp4Out, gifOut]) {
    const st = await fs.stat(p);
    sizes[path.basename(p)] = `${(st.size / 1024 / 1024).toFixed(2)} MB`;
  }
  console.log(JSON.stringify({ ok: true, sizes, timeline: path.relative(REPO, timelinePath) }, null, 2));
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
