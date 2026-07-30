(function () {
  "use strict";

  const PROJECT_TOKEN = "phc_z36vRZVmYzw9NBJmY83QKwaAKREemEsGR7mxxZd2b92m";
  const CAPTURE_URL = "https://us.i.posthog.com/capture/";
  const SESSION_KEY = "crewscore_web_analytics_id";
  const OPT_OUT_KEY = "crewscore_analytics_opt_out_v1";
  let sessionOptOut = false;
  const ALLOWED_EVENTS = new Set([
    "cs_site_view",
    "cs_rules_expand",
    "cs_fix_plan",
    "cs_fix_cancel",
    "cs_fix_apply",
    "cs_export",
    "cs_score",
    "cs_vendor_open",
    "cs_demo_started",
    "cs_check_completed",
    "cs_fix_review",
    "cs_mode_change",
    "cs_share",
    "cs_product_path",
  ]);
  const ALLOWED_PROPERTIES = new Set([
    "source",
    "profile",
    "overall_bucket",
    "smell_count",
    "ruleset",
    "dims_to_fix_count",
    "delta_bucket",
    "kind",
    "controls_found",
    "mode",
    "path",
    "product_path",
  ]);

  function isOptedOut() {
    if (sessionOptOut) return true;
    try {
      return localStorage.getItem(OPT_OUT_KEY) === "1";
    } catch (error) {
      return false;
    }
  }

  function setOptOut(value) {
    sessionOptOut = Boolean(value);
    try {
      localStorage.setItem(OPT_OUT_KEY, value ? "1" : "0");
    } catch (error) {
      // Preferences are optional; blocked storage must not break scoring.
    }
  }

  function newAnonymousId() {
    try {
      if (crypto && typeof crypto.randomUUID === "function") return crypto.randomUUID();
    } catch (error) {
      // Fall through to a non-identifying random session value.
    }
    return `session-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }

  function anonymousId() {
    try {
      const current = sessionStorage.getItem(SESSION_KEY);
      if (current) return current;
      const next = newAnonymousId();
      sessionStorage.setItem(SESSION_KEY, next);
      return next;
    } catch (error) {
      return newAnonymousId();
    }
  }

  function safeProperties(input) {
    const output = {};
    Object.entries(input || {}).forEach(([key, value]) => {
      if (!ALLOWED_PROPERTIES.has(key)) return;
      if (typeof value === "string") output[key] = value.slice(0, 80);
      if (typeof value === "number" && Number.isFinite(value)) output[key] = value;
      if (typeof value === "boolean" || value === null) output[key] = value;
    });
    return output;
  }

  function capture(event, properties) {
    if (!ALLOWED_EVENTS.has(event) || location.hostname !== "crewscore.ai" || isOptedOut()) return;
    const body = JSON.stringify({
      api_key: PROJECT_TOKEN,
      event,
      properties: {
        distinct_id: anonymousId(),
        $process_person_profile: false,
        product: "crewscore",
        schema_version: "2026-07-30",
        ...safeProperties(properties),
      },
    });
    void fetch(CAPTURE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
    }).catch(function () {
      // Analytics must never affect the offline scoring experience.
    });
  }

  window.CrewScoreAnalytics = Object.freeze({ capture, isOptedOut, setOptOut });
  capture("cs_site_view");
})();
