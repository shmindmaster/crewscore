/*
 * Reproducible capture of the real static CrewScore checker using only the
 * public fictional fixture. This script deliberately uses a fresh browser
 * context per run: no personal profile, saved storage, accounts, or user
 * prompts can enter the footage.
 */
import { chromium } from "@playwright/test";
import { createHash } from "node:crypto";
import { copyFile, mkdir, readFile, rm, stat, writeFile } from "node:fs/promises";
import { execFileSync, spawn } from "node:child_process";
import { createRequire } from "node:module";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = resolve(fileURLToPath(new URL("../..", import.meta.url)));
const demoRoot = resolve(root, "demo/release-demo");
const scriptPath = resolve(demoRoot, "release-demo-script.json");
const workRoot = resolve(process.env.CREWSCORE_DEMO_WORK_DIR || resolve(root, "_production/demo-work"));
const runDirectory = resolve(workRoot, "capture/release-demo");
const port = Number(process.env.CREWSCORE_DEMO_PORT || "41741");
const baseUrl = `http://127.0.0.1:${port}`;
const viewport = { width: 1600, height: 900 };
const sourceRevision = execFileSync("git", ["rev-parse", "HEAD"], { cwd: root, encoding: "utf8" }).trim();

function assertGeneratedPath(path) {
  if (!path.startsWith(`${workRoot}\\`) && path !== workRoot) {
    throw new Error(`Refusing to modify a path outside the configured demo work directory: ${path}`);
  }
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function sleep(milliseconds) {
  return new Promise((resolveSleep) => setTimeout(resolveSleep, milliseconds));
}

async function waitForServer(url) {
  const deadline = Date.now() + 15_000;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(1_000) });
      if (response.ok) return;
    } catch (error) {
      lastError = error;
    }
    await sleep(250);
  }
  throw new Error(`The local CrewScore server did not become ready at ${url}: ${lastError?.message || "unknown error"}`);
}

function durationFor(timing, segment) {
  const measured = timing?.segments?.find((entry) => entry.id === segment.id)?.durationSeconds;
  return Number.isFinite(measured) ? measured + Number(segment.gapAfterSeconds || 0) : segment.fallbackDurationSeconds + Number(segment.gapAfterSeconds || 0);
}

function serializableError(error) {
  return { name: error?.name || "Error", message: error?.message || String(error) };
}

const narration = JSON.parse(await readFile(scriptPath, "utf8"));
const timingPath = resolve(workRoot, "narration/release-demo/narration-timing.json");
let timing;
try {
  timing = JSON.parse(await readFile(timingPath, "utf8"));
} catch {
  timing = null;
}

assertGeneratedPath(runDirectory);
await rm(runDirectory, { recursive: true, force: true });
await mkdir(resolve(runDirectory, "video"), { recursive: true });
await mkdir(resolve(runDirectory, "screens"), { recursive: true });

const server = spawn(process.execPath, ["scripts/serve-static.mjs"], {
  cwd: root,
  env: { ...process.env, CREWSCORE_STATIC_PORT: String(port) },
  stdio: ["ignore", "pipe", "pipe"],
  windowsHide: true,
});
let serverOutput = "";
server.stdout.on("data", (value) => { serverOutput += value.toString(); });
server.stderr.on("data", (value) => { serverOutput += value.toString(); });

let browser;
let context;
let page;
try {
  await waitForServer(baseUrl);
  browser = await chromium.launch({ headless: true });
  context = await browser.newContext({
    viewport,
    deviceScaleFactor: 1,
    locale: "en-US",
    timezoneId: "America/Chicago",
    recordVideo: { dir: resolve(runDirectory, "video"), size: viewport },
  });
  page = await context.newPage();
  const consoleErrors = [];
  const failedRequests = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("requestfailed", (request) => failedRequests.push({ url: request.url(), failure: request.failure()?.errorText || "unknown" }));
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.addStyleTag({ content: "*, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; }" });

  const fixture = await page.evaluate(() => window.CrewScoreDemoFixture);
  if (!fixture || fixture.id !== "fictional-clinic-support-v1") throw new Error("The public fictional demo fixture did not load.");
  if (fixture.expected?.found !== 20 || fixture.expected?.missing?.length !== 3) throw new Error("The demo fixture no longer has the declared 20/23 starting state.");

  const screenshots = [];
  async function shot(id) {
    const path = resolve(runDirectory, "screens", `${id}.png`);
    await page.screenshot({ path });
    screenshots.push({ id, path: relative(root, path) });
  }
  async function hold(id) {
    await page.waitForTimeout(Math.round(durationFor(timing, narration.segments.find((segment) => segment.id === id)) * 1000));
  }

  await page.locator("#checker-workspace").scrollIntoViewIfNeeded();
  await page.locator("#agent-prompt").fill(fixture.prompt);
  await page.locator("#agent-prompt").evaluate((element) => { element.scrollTop = 0; });
  await shot("01-before-state");
  await hold("before-state");

  await page.locator("#check-instructions").click();
  await page.getByRole("heading", { name: "20 of 23 written guardrails found" }).waitFor();
  await page.locator("#results").scrollIntoViewIfNeeded();
  await shot("02-controls-result");
  await hold("local-check");
  await hold("missing-controls");

  await page.getByRole("button", { name: "Review suggested guardrails" }).click();
  const approval = page.locator('[data-select="human_gate.approval_required"]');
  await approval.waitFor();
  await approval.click();
  await page.getByLabel("Full before and after diff").waitFor();
  await page.locator("#fix-diff").scrollIntoViewIfNeeded();
  await shot("03-editable-control-review");
  await hold("review-control");

  const approvalBox = await approval.boundingBox();
  if (!approvalBox) throw new Error("The selected control had no measurable focus box.");
  await page.getByRole("button", { name: "Add selected guardrails" }).click();
  await page.getByRole("heading", { name: "21 of 23 written guardrails found" }).waitFor();
  await page.locator("#results").scrollIntoViewIfNeeded();
  await shot("04-local-rescan-hero");
  await hold("local-rescan");

  await page.getByText("A result link includes ruleset and control IDs only; prompt text is never included.").scrollIntoViewIfNeeded();
  await shot("05-prompt-free-share");
  await hold("prompt-free-share");
  // Keep an explicit tail so the measured narration always lands before the
  // recorded product state ends, even if a browser drops initial frames.
  await page.waitForTimeout(2_000);

  if (consoleErrors.length || failedRequests.length) {
    throw new Error(`Capture browser faults: ${JSON.stringify({ consoleErrors, failedRequests })}`);
  }
  const video = page.video();
  const resultHeading = await page.getByRole("heading", { name: "21 of 23 written guardrails found" }).textContent();
  await context.close();
  context = null;
  const capturedVideo = resolve(runDirectory, "crewscore-written-controls-review.webm");
  await copyFile(await video.path(), capturedVideo);
  const fileInfo = await stat(capturedVideo);
  const manifest = {
    version: 1,
    scenario: "written-controls-review",
    beat: "full-episode",
    route: "/",
    environment: "local static server",
    deployment: { identity: baseUrl, verification: "Started by scripts/serve-static.mjs for this capture run", sourceRevision },
    persona: fixture.persona,
    fixture: { id: fixture.id, source: "assets/demo-fixture.js", sha256: sha256(fixture.prompt), expectedFound: fixture.expected.found, expectedMissing: fixture.expected.missing },
    viewport: { ...viewport, deviceScaleFactor: 1 },
    locale: "en-US",
    timezone: "America/Chicago",
    reducedMotion: true,
    actions: [
      "Fill the public fictional fixture in the real checker",
      "Run the local checker and assert 20 of 23 written controls",
      "Select the real human approval suggestion and show its diff",
      "Apply the selected wording and assert 21 of 23 written controls",
      "Show the prompt-free result-sharing explanation"
    ],
    focus: { x: Math.round(approvalBox.x), y: Math.round(approvalBox.y), width: Math.round(approvalBox.width), height: Math.round(approvalBox.height) },
    protectedRegions: [{ x: 800, y: 120, width: 700, height: 640 }],
    cursor: { from: [760, 400], to: [Math.round(approvalBox.x), Math.round(approvalBox.y)] },
    screenshotPaths: screenshots,
    videoPath: relative(root, capturedVideo),
    videoBytes: fileInfo.size,
    consoleErrors,
    failedRequests,
    reset: { command: "Fresh Playwright context plus localStorage/sessionStorage clear", result: "pass" },
    narrationTimingPath: timing ? relative(root, timingPath) : null,
    expectedResult: resultHeading,
    readinessState: "PASS pending independent product-experience handoff validation",
    verdict: "pass",
    capturedAt: new Date().toISOString()
  };
  const manifestPath = resolve(runDirectory, "capture-manifest.json");
  await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  console.log(JSON.stringify({ capturedVideo: relative(root, capturedVideo), manifest: relative(root, manifestPath), screenshots, bytes: fileInfo.size }, null, 2));
} catch (error) {
  const failurePath = resolve(runDirectory, "capture-failure.json");
  await writeFile(failurePath, `${JSON.stringify({ error: serializableError(error), serverOutput, capturedAt: new Date().toISOString() }, null, 2)}\n`, "utf8");
  throw error;
} finally {
  if (context) await context.close().catch(() => {});
  if (browser) await browser.close().catch(() => {});
  if (!server.killed) server.kill();
}
