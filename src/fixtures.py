"""Known-buggy diffs with documented ground truth, for measuring recall.

Precision is easy to fake: an agent that never comments scores 1.0. These
fixtures answer the opposite question — given code with a bug you KNOW is
there, does the agent find it?

Each fixture is a realistic unified diff containing exactly one planted defect.
`expect` describes the bug in plain language; `signals` are substrings that a
correct comment would plausibly contain, used for a rough automatic score.
The automatic score is a convenience, not the truth — always read the output.

KEEP SIGNALS SPECIFIC TO THE MECHANISM. An early version of this file listed
"Promise" as a signal for the missing-await bug, and the harness happily scored
a HIT on a comment about "unhandled promise rejection" — a completely different
issue. Generic signals turn the recall number into a lie that flatters you.
"""

FIXTURES = [
    {
        "name": "off-by-one in retry loop",
        "file": "lib/core/retry.js",
        "expect": (
            "The loop runs `i < maxRetries - 1`, so it performs one fewer attempt "
            "than configured. maxRetries=1 means the request is never retried at all."
        ),
        "signals": ["off-by-one", "maxRetries", "one fewer", "- 1", "never retri"],
        "diff": """--- FILE: lib/core/retry.js (modified, +14/-2)
@@ -8,10 +8,22 @@ const DEFAULT_MAX_RETRIES = 3;

 async function withRetry(fn, options = {}) {
   const maxRetries = options.maxRetries ?? DEFAULT_MAX_RETRIES;
-  return fn();
+  let lastError;
+
+  for (let i = 0; i < maxRetries - 1; i++) {
+    try {
+      return await fn();
+    } catch (err) {
+      lastError = err;
+      await delay(options.backoffMs ?? 100);
+    }
+  }
+
+  throw lastError;
 }

 module.exports = { withRetry };
""",
    },
    {
        "name": "missing await returns a Promise",
        "file": "lib/adapters/cache.js",
        "expect": (
            "`serialize(response)` is async but is not awaited, so a Promise object "
            "is written to the cache instead of the serialized body. Every cache read "
            "afterwards returns '[object Promise]'."
        ),
        "signals": [
            "not awaited",
            "missing await",
            "without await",
            "await this.serialize",
            "await the serialize",
            "object promise",
            "promise instead",
            "stores a promise",
            "pending promise",
        ],
        "diff": """--- FILE: lib/adapters/cache.js (modified, +9/-1)
@@ -22,7 +22,15 @@ class ResponseCache {

   async set(key, response) {
-    this.store.set(key, response);
+    const entry = {
+      body: this.serialize(response),
+      status: response.status,
+      storedAt: Date.now(),
+    };
+
+    this.store.set(key, entry);
+    return entry;
   }

   async serialize(response) {
     return JSON.stringify(await response.json());
   }
""",
    },
    {
        "name": "user input compiled into a RegExp",
        "file": "lib/helpers/matchUrl.js",
        "expect": (
            "A caller-supplied string is passed straight to `new RegExp()` without "
            "escaping, allowing regex injection and catastrophic backtracking (ReDoS) "
            "from a crafted pattern."
        ),
        "signals": [
            "regexp",
            "regular expression",
            "redos",
            "backtrack",
            "escape",
            "regex injection",
        ],
        "diff": """--- FILE: lib/helpers/matchUrl.js (modified, +11/-3)
@@ -1,10 +1,18 @@
-function matchUrl(url, allowed) {
-  return allowed.some((entry) => url === entry);
+function matchUrl(url, allowed) {
+  return allowed.some((entry) => {
+    if (entry.includes('*')) {
+      const pattern = new RegExp('^' + entry.replace('*', '.*') + '$');
+      return pattern.test(url);
+    }
+
+    return url === entry;
+  });
 }

 module.exports = matchUrl;
""",
    },
    {
        "name": "shared mutable default leaks across calls",
        "file": "lib/core/mergeConfig.js",
        "expect": (
            "DEFAULT_HEADERS is a module-level object that is mutated in place, so "
            "headers set during one request persist into every later request that "
            "relies on the defaults."
        ),
        "signals": [
            "object.assign(default_headers",
            "mutates default_headers",
            "mutates the shared",
            "modifies default_headers",
            "shared object",
            "module-level",
            "leak",
            "persist across",
        ],
        "diff": """--- FILE: lib/core/mergeConfig.js (modified, +8/-2)
@@ -1,12 +1,18 @@
 const DEFAULT_HEADERS = { 'Accept': 'application/json' };

-function mergeConfig(config) {
-  return { ...config, headers: { ...DEFAULT_HEADERS, ...config.headers } };
+function mergeConfig(config) {
+  const headers = Object.assign(DEFAULT_HEADERS, config.headers);
+
+  if (config.auth) {
+    headers['Authorization'] = buildAuthHeader(config.auth);
+  }
+
+  return { ...config, headers };
 }

 module.exports = mergeConfig;
""",
    },
]
