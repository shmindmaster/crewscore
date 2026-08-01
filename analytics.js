(function () {
  "use strict";

  const PROJECT_TOKEN = "phc_z36vRZVmYzw9NBJmY83QKwaAKREemEsGR7mxxZd2b92m";
  const CAPTURE_URL = "https://us.i.posthog.com/capture/";
  const SESSION_KEY = "crewscore_web_analytics_id";
  const OPT_OUT_KEY = "crewscore_analytics_opt_out_v1";
  const SCHEMA_VERSION = "2026-07-31";
  const MAX_STRING_LENGTH = 80;

  const RULESET_RE = /^crewscore-hygiene@\d+\.\d+\.\d+$/;
  const BUCKETS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100];
  const SOURCES = ["direct", "internal", "github", "search", "social", "referral", "paste", "file_upload", "github_import", "example", "demo", "profile_change", "mobile", "fix_apply"];
  const MODES = ["simple", "developer"];
  const PROFILES = ["system_prompt", "coding_agent_config"];
  const PRODUCT_PATHS = ["chatgpt", "claude", "cursor", "other"];
  const KINDS = [
    "copy_result",
    "copy_share_text",
    "copy_team",
    "native",
    "copy_badge",
    "x",
    "linkedin",
    "facebook",
    "reddit",
    "svg_linkedin",
    "svg_x",
    "svg_facebook",
    "svg_reddit",
    "svg_square",
    "svg_badge",
    "png_linkedin",
    "png_x",
    "png_facebook",
    "png_square",
    "png_badge",
  ];
  const PATHS = ["chatgpt", "claude", "cursor", "other", "feedback"];
  const TRAFFIC_CLASSES = ["production", "synthetic_qa"];

    const EVENT_SCHEMAS = {
    cs_site_view: {
      required: ["source"],
      properties: {
        source: { type: "string", enum: SOURCES, max_length: 24 },
      },
    },
    cs_rules_expand: { required: [], properties: {} },
    cs_fix_plan: { required: [], properties: {} },
    cs_fix_cancel: { required: [], properties: {} },
    cs_export: { required: [], properties: {} },
    cs_score: {
      required: ["source", "profile", "ruleset", "overall_bucket", "controls_found"],
      properties: {
        source: { type: "string", enum: SOURCES, max_length: 24 },
        profile: { type: "string", enum: PROFILES, max_length: 24 },
        ruleset: { type: "string", pattern: RULESET_RE, max_length: 40 },
        overall_bucket: { type: "integer", enum: BUCKETS, min: 0, max: 100 },
        controls_found: { type: "integer", min: 0, max: 23 },
        product_path: { type: "string", enum: PRODUCT_PATHS, max_length: 24 },
        smell_count: { type: "integer", min: 0, max: 23 },
        delta_bucket: { type: "integer", enum: BUCKETS, min: 0, max: 100 },
      },
    },
    cs_vendor_open: {
      required: ["kind"],
      properties: { kind: { type: "string", enum: ["summary"], max_length: 20 } },
    },
    cs_demo_started: { required: [], properties: {} },
    cs_check_completed: {
      required: ["source", "profile", "ruleset"],
      properties: {
        source: { type: "string", enum: SOURCES, max_length: 24 },
        profile: { type: "string", enum: PROFILES, max_length: 24 },
        ruleset: { type: "string", pattern: RULESET_RE, max_length: 40 },
      },
    },
    cs_fix_review: {
      required: ["dims_to_fix_count"],
      properties: { dims_to_fix_count: { type: "integer", min: 0, max: 23 } },
    },
    cs_mode_change: {
      required: ["mode"],
      properties: { mode: { type: "string", enum: MODES, max_length: 12 } },
    },
    cs_share: {
      required: ["kind"],
      properties: { kind: { type: "string", enum: KINDS, max_length: 40 } },
    },
    cs_product_path: {
      required: ["path"],
      properties: { path: { type: "string", enum: PATHS, max_length: 24 } },
    },
    cs_fix_apply: {
      required: ["controls_found"],
      properties: { controls_found: { type: "integer", min: 0, max: 23 } },
    },
};

  const ALLOWED_EVENTS = new Set([
  "cs_site_view",
  "cs_rules_expand",
  "cs_fix_plan",
  "cs_fix_cancel",
  "cs_export",
  "cs_score",
  "cs_vendor_open",
  "cs_demo_started",
  "cs_check_completed",
  "cs_fix_review",
  "cs_mode_change",
  "cs_share",
  "cs_product_path",
  "cs_fix_apply",
]);

  const ALLOWED_PROPERTIES = new Set([
  "source",
  "profile",
  "overall_bucket",
  "ruleset",
  "dims_to_fix_count",
  "delta_bucket",
  "kind",
  "mode",
  "path",
  "product_path",
  "controls_found",
  "smell_count",
  "traffic_class",
]);
  const FORBIDDEN_PROPERTIES = [
    "prompt",
    "text",
    "body",
    "system_prompt",
    "content",
    "snippet",
    "input",
    "source_text",
  ];

  const EVENT_OPTIONAL_PROPERTIES = {};
  Object.keys(EVENT_SCHEMAS).forEach((event) => {
    const schema = EVENT_SCHEMAS[event];
    schema.properties.traffic_class = {
      type: "string",
      enum: TRAFFIC_CLASSES,
      max_length: 16,
    };
    EVENT_OPTIONAL_PROPERTIES[event] = Object.keys(schema.properties).filter(
      (name) => !schema.required.includes(name)
    );
  });

  let sessionOptOut = false;
  let lastCaptureError = null;

  function isOptedOut() {
    if (sessionOptOut) return true;
    try {
      return localStorage.getItem(OPT_OUT_KEY) === "1";
    } catch (_error) {
      return false;
    }
  }

  function setOptOut(value) {
    sessionOptOut = Boolean(value);
    try {
      localStorage.setItem(OPT_OUT_KEY, value ? "1" : "0");
    } catch (_error) {
      // Preferences are optional; blocked storage must not break scoring.
    }
  }

  function newAnonymousId() {
    try {
      if (crypto && typeof crypto.randomUUID === "function") return crypto.randomUUID();
    } catch (_error) {
      // Fall through to a non-identifying random session value.
    }
    return "session-" + Date.now() + "-" + Math.random().toString(36).slice(2);
  }

  function anonymousId() {
    try {
      const current = sessionStorage.getItem(SESSION_KEY);
      if (current) return current;
      const next = newAnonymousId();
      sessionStorage.setItem(SESSION_KEY, next);
      return next;
    } catch (_error) {
      return newAnonymousId();
    }
  }

  function sanitizeValue(type, spec, value) {
    if (type === "string") {
      if (typeof value !== "string") return null;
      const trimmed = value.trim();
      if (!trimmed || trimmed.length > (spec.max_length || MAX_STRING_LENGTH)) return null;
      if (spec.enum && Array.isArray(spec.enum) && !spec.enum.includes(trimmed)) return null;
      if (spec.pattern && !(spec.pattern instanceof RegExp ? spec.pattern : new RegExp(spec.pattern)).test(trimmed)) return null;
      return trimmed;
    }
    if (type === "integer") {
      if (!Number.isInteger(value)) return null;
      if (spec.min != null && value < spec.min) return null;
      if (spec.max != null && value > spec.max) return null;
      if (spec.enum && !spec.enum.includes(value)) return null;
      return value;
    }
    return null;
  }

  function safeProperties(event, properties) {
    if (!ALLOWED_EVENTS.has(event)) return null;
    if (typeof properties !== "object" || properties === null || Array.isArray(properties)) return null;

    const schema = EVENT_SCHEMAS[event];
    const raw = properties || {};
    const required = schema.required || [];
    const schemaKeys = Object.keys(schema.properties);
    for (const key of Object.keys(raw)) {
      if (!schemaKeys.includes(key)) return null;
      if (!ALLOWED_PROPERTIES.has(key)) return null;
    }
    for (const key of required) {
      if (!(key in raw)) return null;
    }
    const output = {};
    for (const key of schemaKeys) {
      if (!(key in raw)) continue;
      const spec = schema.properties[key];
      const value = sanitizeValue(spec.type, spec, raw[key]);
      if (value === null) return null;
      output[key] = value;
    }
    return output;
  }

  function serializeSchema() {
    const events = {};
    for (const [event, schema] of Object.entries(EVENT_SCHEMAS)) {
      events[event] = {
        required: (schema.required || []).slice(),
        properties: {},
      };
      Object.keys(schema.properties || {}).forEach((name) => {
        const spec = schema.properties[name];
        const next = Object.assign({}, spec);
        if (next.pattern instanceof RegExp) next.pattern = next.pattern.source;
        if (Array.isArray(next.enum)) {
          next.enum = next.enum.slice().sort(function (left, right) {
            if (typeof left === "number" && typeof right === "number") return left - right;
            return String(left).localeCompare(String(right), undefined, { numeric: true, sensitivity: "base" });
          });
        }
        events[event].properties[name] = next;
      });
    }
    return {
      schema_version: SCHEMA_VERSION,
      allowed_events: Array.from(ALLOWED_EVENTS).sort(),
      allowed_properties: Array.from(ALLOWED_PROPERTIES).sort(),
      forbidden_prop_keys: FORBIDDEN_PROPERTIES.slice(),
      score_buckets: BUCKETS.slice(),
      optional_properties: EVENT_OPTIONAL_PROPERTIES,
      prompt_text: "never stored in event props",
      event_schemas: events,
    };
  }

  function classifyReferrer(referrer) {
    if (!referrer) return "direct";
    try {
      const url = new URL(referrer);
      if (url.protocol !== "http:" && url.protocol !== "https:") return "direct";
      const host = url.hostname.toLowerCase();
      const matches = (domain) => host === domain || host.endsWith("." + domain);
      if (matches("crewscore.ai")) return "internal";
      if (matches("github.com")) return "github";
      if (["google.com", "bing.com", "duckduckgo.com", "search.brave.com", "search.yahoo.com"].some(matches)) return "search";
      if (["linkedin.com", "x.com", "twitter.com", "facebook.com", "reddit.com", "bsky.app"].some(matches)) return "social";
      return "referral";
    } catch (_error) {
      return "direct";
    }
  }

  function capture(event, properties) {
    if (!ALLOWED_EVENTS.has(event)) return;
    if (location.hostname !== "crewscore.ai" || isOptedOut()) return;

    const safe = safeProperties(event, properties);
    if (!safe) return;
    safe.traffic_class = isHumanQaTraffic() ? "synthetic_qa" : "production";

    const body = JSON.stringify({
      api_key: PROJECT_TOKEN,
      event,
      properties: {
        distinct_id: anonymousId(),
        $process_person_profile: false,
        product: "crewscore",
        schema_version: SCHEMA_VERSION,
        ...safe,
      },
    });

    return fetch(CAPTURE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
    }).catch(function (error) {
      lastCaptureError = error;
    });
  }

  function isHumanQaTraffic() {
    try {
      return new URLSearchParams(location.search || "").get("crewscore_test_traffic") === "true";
    } catch (_error) {
      return false;
    }
  }

  function shareUrl() {
    try {
      const url = new URL(location.href);
      url.searchParams.delete("crewscore_test_traffic");
      return url.toString();
    } catch (_error) {
      const raw = String(location.href || "");
      const [withoutHash, hash = ""] = raw.split("#", 2);
      const [path, query = ""] = withoutHash.split("?", 2);
      const kept = query.split("&").filter((part) => part.split("=", 1)[0] !== "crewscore_test_traffic");
      return `${path}${kept.length ? `?${kept.join("&")}` : ""}${hash ? `#${hash}` : ""}`;
    }
  }

  window.CrewScoreAnalytics = Object.freeze({
    capture,
    isOptedOut,
    setOptOut,
    safeProperties,
    shareUrl,
    get lastCaptureError() {
      return lastCaptureError;
    },
    schemaPayload: serializeSchema,
    schemaVersion: SCHEMA_VERSION,
  });

  if (typeof document !== "undefined") {
    const referrer = document.referrer;
    capture("cs_site_view", { source: classifyReferrer(referrer) });
  }
})();
