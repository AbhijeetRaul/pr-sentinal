"""Cross-file fixtures: bugs that are invisible in the diff alone.

Every fixture in `fixtures.py` is self-contained — all the evidence needed to
find the bug is inside the diff. Those cannot measure whether codebase
retrieval helps, because there is nothing to retrieve.

Each fixture here plants a defect that is genuinely undecidable from the diff.
The changed file looks correct in isolation; it is only wrong given how it is
used somewhere else in the repo. `context_files` holds that elsewhere.

Use this to answer the question BEFORE building a retrieval pipeline:
if handing the agent perfect context (the oracle) does not raise recall, then
retrieval — which only ever approximates the oracle — cannot help either, and
pgvector would be infrastructure you added for the roadmap's sake.

MEASURED RESULT: recall was 3/3 both blind and with context. A capable model
guesses "callers may expect the old shape" from the diff alone. So detection is
NOT where retrieval pays off.

Which is why XFIXTURES_SAFE below exists. Each safe fixture pairs the SAME diff
with context proving the change is fine — every caller was already updated. A
blind agent still emits its speculative warning, and that warning is now a false
positive. Context is what lets the agent stay quiet.

The real question is therefore not "does context find more bugs" but "does
context stop the agent from crying wolf". Compare false positives on the safe
set, not hits on the unsafe set.
"""

XFIXTURES = [
    {
        "name": "return shape changed, caller not updated",
        "expect": (
            "parseConfig now returns {config, warnings} instead of the config object. "
            "dispatchRequest still does `cfg.url`, which is now undefined — every "
            "request goes to undefined. The diff alone looks like a clean refactor."
        ),
        "signals": [
            "dispatchrequest",
            "caller",
            "callers",
            "return shape",
            "cfg.url",
            "cfg.config",
            "undefined",
            "no longer returns",
            "returns an object",
        ],
        "diff": """--- FILE: lib/core/parseConfig.js (modified, +8/-2)
@@ -1,14 +1,20 @@
 function parseConfig(raw) {
   const config = { ...DEFAULTS, ...raw };
+  const warnings = [];

   if (!config.url) {
     throw new TypeError('url is required');
   }

+  if (config.timeout && config.timeout < 0) {
+    warnings.push('negative timeout coerced to 0');
+    config.timeout = 0;
+  }
+
-  return config;
+  return { config, warnings };
 }

 module.exports = parseConfig;
""",
        "context_files": [
            {
                "path": "lib/core/dispatchRequest.js",
                "content": """const parseConfig = require('./parseConfig');

async function dispatchRequest(raw) {
  const cfg = parseConfig(raw);

  const response = await adapter({
    url: cfg.url,
    method: cfg.method || 'get',
    timeout: cfg.timeout,
    headers: cfg.headers,
  });

  return response;
}

module.exports = dispatchRequest;
""",
            }
        ],
    },
    {
        "name": "null guard removed, a live caller depends on it",
        "expect": (
            "The `if (!headers) return {}` guard is deleted as apparently dead code, "
            "but httpAdapter calls normalizeHeaders(config.headers) and config.headers "
            "is undefined whenever the caller omits headers. Object.keys(undefined) "
            "throws."
        ),
        "signals": [
            "httpadapter",
            "http.js",
            "caller",
            "undefined",
            "object.keys",
            "guard",
            "throws",
            "omits headers",
        ],
        "diff": """--- FILE: lib/helpers/normalizeHeaders.js (modified, +3/-5)
@@ -1,12 +1,10 @@
 function normalizeHeaders(headers) {
-  if (!headers) {
-    return {};
-  }
-
   return Object.keys(headers).reduce((acc, key) => {
     acc[key.toLowerCase()] = headers[key];
     return acc;
   }, {});
 }

 module.exports = normalizeHeaders;
""",
        "context_files": [
            {
                "path": "lib/adapters/http.js",
                "content": """const normalizeHeaders = require('../helpers/normalizeHeaders');

function httpAdapter(config) {
  // config.headers is optional throughout the public API - axios.get(url)
  // reaches this line with config.headers === undefined.
  const headers = normalizeHeaders(config.headers);

  return request({
    hostname: config.hostname,
    headers,
    method: config.method,
  });
}

module.exports = httpAdapter;
""",
            }
        ],
    },
    {
        "name": "error code changed, retry logic keys off the old one",
        "expect": (
            "The timeout path now throws a TimeoutError with code 'ETIMEDOUT' instead "
            "of code 'ECONNABORTED'. shouldRetry() tests for 'ECONNABORTED', so timed-out "
            "requests silently stop being retried. Nothing in the diff hints at this."
        ),
        "signals": [
            "shouldretry",
            "retry",
            "econnaborted",
            "etimedout",
            "no longer",
            "silently",
            "err.code",
        ],
        "diff": """--- FILE: lib/adapters/timeout.js (modified, +9/-3)
@@ -1,16 +1,22 @@
+class TimeoutError extends Error {
+  constructor(ms) {
+    super(`timeout of ${ms}ms exceeded`);
+    this.name = 'TimeoutError';
+    this.code = 'ETIMEDOUT';
+  }
+}
+
 function withTimeout(promise, ms) {
   return Promise.race([
     promise,
     new Promise((_, reject) =>
-      setTimeout(() => {
-        const err = new Error('timeout');
-        err.code = 'ECONNABORTED';
-        reject(err);
-      }, ms)
+      setTimeout(() => reject(new TimeoutError(ms)), ms)
     ),
   ]);
 }

-module.exports = { withTimeout };
+module.exports = { withTimeout, TimeoutError };
""",
        "context_files": [
            {
                "path": "lib/core/shouldRetry.js",
                "content": """const RETRYABLE_CODES = ['ECONNABORTED', 'ECONNRESET', 'EAI_AGAIN'];

function shouldRetry(err, attempt, maxRetries) {
  if (attempt >= maxRetries) {
    return false;
  }

  return RETRYABLE_CODES.includes(err.code);
}

module.exports = shouldRetry;
""",
            }
        ],
    },
]


# ---------------------------------------------------------------------------
# SAFE variants: identical diffs, but the context proves nothing is broken.
# The correct number of comments on each of these is ZERO.
# A blind agent cannot know that, and will warn anyway — those are the false
# positives retrieval is supposed to eliminate.
# ---------------------------------------------------------------------------

XFIXTURES_SAFE = [
    {
        "name": "return shape changed — caller ALREADY updated",
        "expect": "No defect. dispatchRequest destructures { config } correctly.",
        "diff": XFIXTURES[0]["diff"],
        "context_files": [
            {
                "path": "lib/core/dispatchRequest.js",
                "content": """const parseConfig = require('./parseConfig');

async function dispatchRequest(raw) {
  const { config: cfg, warnings } = parseConfig(raw);

  if (warnings.length) {
    logger.debug('config warnings', warnings);
  }

  const response = await adapter({
    url: cfg.url,
    method: cfg.method || 'get',
    timeout: cfg.timeout,
    headers: cfg.headers,
  });

  return response;
}

module.exports = dispatchRequest;
""",
            }
        ],
    },
    {
        "name": "null guard removed — caller ALREADY defaults the value",
        "expect": "No defect. httpAdapter passes `config.headers || {}`, never undefined.",
        "diff": XFIXTURES[1]["diff"],
        "context_files": [
            {
                "path": "lib/adapters/http.js",
                "content": """const normalizeHeaders = require('../helpers/normalizeHeaders');

function httpAdapter(config) {
  // Defaulted here since v1.4 - normalizeHeaders never receives undefined.
  const headers = normalizeHeaders(config.headers || {});

  return request({
    hostname: config.hostname,
    headers,
    method: config.method,
  });
}

module.exports = httpAdapter;
""",
            }
        ],
    },
    {
        "name": "error code changed — retry list ALREADY includes the new code",
        "expect": "No defect. RETRYABLE_CODES contains 'ETIMEDOUT'.",
        "diff": XFIXTURES[2]["diff"],
        "context_files": [
            {
                "path": "lib/core/shouldRetry.js",
                "content": """const RETRYABLE_CODES = [
  'ECONNABORTED',
  'ETIMEDOUT',
  'ECONNRESET',
  'EAI_AGAIN',
];

function shouldRetry(err, attempt, maxRetries) {
  if (attempt >= maxRetries) {
    return false;
  }

  return RETRYABLE_CODES.includes(err.code);
}

module.exports = shouldRetry;
""",
            }
        ],
    },
]
