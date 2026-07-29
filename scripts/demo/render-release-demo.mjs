/* Packages the actual browser capture with local narration and deterministic captions. */
import { createHash } from "node:crypto";
import { cp, mkdir, readFile, writeFile } from "node:fs/promises";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(fileURLToPath(new URL("../..", import.meta.url)));
const demoRoot = resolve(root, "demo/release-demo");
const workRoot = resolve(process.env.CREWSCORE_DEMO_WORK_DIR || resolve(root, "_production/demo-work"));
const reviewRoot = resolve(process.env.CREWSCORE_DEMO_REVIEW_DIR || resolve(root, "_production/demo-review/release-demo"));
const sourceVideo = resolve(workRoot, "capture/release-demo/crewscore-written-controls-review.webm");
const captureManifestPath = resolve(workRoot, "capture/release-demo/capture-manifest.json");
const narrationRoot = resolve(workRoot, "narration/release-demo");
const narrationPath = resolve(narrationRoot, "narration.wav");
const timingPath = resolve(narrationRoot, "narration-timing.json");
const srtPath = resolve(narrationRoot, "captions.srt");
const sourceRevision = execFileSync("git", ["rev-parse", "HEAD"], { cwd: root, encoding: "utf8" }).trim();

function run(command, args) {
  execFileSync(command, args, { cwd: root, stdio: "inherit" });
}

function hashFile(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function filterPath(path) {
  return path.replaceAll("\\", "/").replace(":", "\\:").replaceAll("'", "\\'");
}

run("ffmpeg", ["-version"]);
await mkdir(reviewRoot, { recursive: true });
const cleanMaster = resolve(reviewRoot, "crewscore-written-controls-review-clean.mp4");
const captionedMaster = resolve(reviewRoot, "crewscore-written-controls-review-captioned.mp4");
const poster = resolve(reviewRoot, "crewscore-written-controls-review-poster.png");
const scaleFilter = "scale=1920:1080:flags=lanczos";
const subtitleFilter = `subtitles=filename='${filterPath(srtPath)}':force_style='FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BorderStyle=3,Outline=1,Shadow=0,MarginV=38,Alignment=2'`;
const common = ["-y", "-i", sourceVideo, "-i", narrationPath, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart"];
run("ffmpeg", [...common, "-vf", scaleFilter, cleanMaster]);
run("ffmpeg", [...common, "-vf", `${scaleFilter},${subtitleFilter}`, captionedMaster]);
run("ffmpeg", ["-y", "-ss", "00:00:32", "-i", captionedMaster, "-frames:v", "1", "-update", "1", poster]);

await cp(resolve(narrationRoot, "captions.srt"), resolve(reviewRoot, "captions.srt"));
await cp(resolve(narrationRoot, "captions.vtt"), resolve(reviewRoot, "captions.vtt"));
await cp(resolve(narrationRoot, "transcript.txt"), resolve(reviewRoot, "transcript.txt"));
await cp(timingPath, resolve(reviewRoot, "narration-timing.json"));
await cp(resolve(demoRoot, "release-demo-script.json"), resolve(reviewRoot, "release-demo-script.json"));
await cp(resolve(demoRoot, "storyboard.json"), resolve(reviewRoot, "storyboard.json"));
await cp(resolve(demoRoot, "product-claims.json"), resolve(reviewRoot, "product-claims.json"));
await cp(resolve(demoRoot, "truth-sheet.md"), resolve(reviewRoot, "truth-sheet.md"));
await cp(captureManifestPath, resolve(reviewRoot, "capture-manifest.json"));

const timing = JSON.parse((await readFile(timingPath, "utf8")).replace(/^\uFEFF/, ""));
const manifest = {
  version: 1,
  episodeId: "written-controls-review",
  sourceRevision,
  syntheticDataDisclosure: "All visible input is the public fictional fixture assets/demo-fixture.js. No user prompt or customer data was captured.",
  voice: timing.voice,
  renders: [
    { role: "clean-master", path: relative(root, cleanMaster), sha256: hashFile(cleanMaster), captionsBurned: false },
    { role: "captioned-master", path: relative(root, captionedMaster), sha256: hashFile(captionedMaster), captionsBurned: true },
    { role: "poster", path: relative(root, poster), sha256: hashFile(poster) }
  ],
  source: {
    captureManifest: relative(root, captureManifestPath),
    narrationTiming: relative(root, timingPath),
    storyboard: "demo/release-demo/storyboard.json",
    claims: "demo/release-demo/product-claims.json",
    truthSheet: "demo/release-demo/truth-sheet.md"
  },
  reproduction: ["npm run demo:narration", "npm run demo:capture", "npm run demo:render"],
  qaStatus: "pending technical and independent five-role review",
  humanApprovalStatus: "needs-human-review",
  renderedAt: new Date().toISOString()
};
await writeFile(resolve(reviewRoot, "render-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
const checksums = manifest.renders.map((item) => `${item.sha256}  ${item.path}`).join("\n");
await writeFile(resolve(reviewRoot, "checksums.txt"), `${checksums}\n`, "utf8");
const reviewTemplate = {
  assetPath: relative(root, captionedMaster),
  classification: "<human must select approved, needs-redaction, or rejected>",
  reviewedBy: "<reviewer name or handle>",
  reviewedAt: "<ISO timestamp after watch-through>",
  syntheticDataConfirmed: "<human confirmation>",
  watchThroughStatus: "<completed only after captions-on and captions-off review at delivery size>",
  redactionNotes: ""
};
await writeFile(resolve(reviewRoot, "evidence-review.template.json"), `${JSON.stringify(reviewTemplate, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ reviewRoot: relative(root, reviewRoot), cleanMaster: relative(root, cleanMaster), captionedMaster: relative(root, captionedMaster), poster: relative(root, poster) }, null, 2));
