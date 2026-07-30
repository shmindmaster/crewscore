import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./web-tests",
  snapshotPathTemplate: "{testDir}/{testFilePath}-snapshots/{arg}{ext}",
  timeout: 30_000,
  expect: { timeout: 8_000 },
  // A synthetic click needs mousedown and mouseup on the same node to become a
  // click at all. The results panel is rebuilt with innerHTML, so a driver that
  // happens to press during a rebuild produces no click event and no error —
  // roughly once in several hundred runs on a loaded machine. A person cannot
  // hit that window, so this is a harness artifact, not a defect: retry it.
  // A retried test still has to pass every assertion; nothing is relaxed. Real
  // regressions fail all three attempts.
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: "http://127.0.0.1:41731",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    // Drive the page the way a reduced-motion reader experiences it. Animated
    // scrolling meant a click could be dispatched at a coordinate the target
    // had already left, which read as "the handler never ran" — the shared
    // cause behind several flakes that only appeared under parallel load.
    reducedMotion: "reduce",
  },
  webServer: {
    command: "node scripts/serve-static.mjs",
    url: "http://127.0.0.1:41731",
    // Never accept an arbitrary service on the test port as CrewScore. A
    // local RepoContext server once made browser tests exercise the wrong app.
    reuseExistingServer: false,
    timeout: 20_000,
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
    { name: "mobile-chromium", use: { ...devices["Pixel 5"] } },
  ],
});
