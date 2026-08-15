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
        # Widened after a real miss: the model wrote "DEFAULT_HEADERS is being
        # mutated ... will retain the changes made in previous calls", which is
        # a textbook description of the bug, and the scorer marked it MISS
        # because it wanted the phrase "persist across". The list had been
        # tightened to fix an earlier over-report and overshot.
        "signals": [
            "default_headers is being mutated",
            "mutates default_headers",
            "mutating default_headers",
            "object.assign(default_headers",
            "mutates the shared",
            "modifies default_headers",
            "shared object",
            "module-level",
            "leak",
            "persist across",
            "retain the changes",
            "retains the changes",
            "previous calls",
            "across function calls",
            "subsequent calls",
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


# ---------------------------------------------------------------------------
# Round 2: bug classes the first four did not cover.
#
# The original set was one arithmetic slip, one async slip, one injection and
# one shared-state slip. Real defects also hide in error handling, cleanup,
# authorisation and concurrency, and an agent can be good at one family and
# blind to another. Signals here list several phrasings on purpose - the
# scorer has already produced both a false hit and a false miss by being too
# loose and then too strict.
# ---------------------------------------------------------------------------

FIXTURES += [
    {
        "name": "error swallowed, corrupt result returned as success",
        "file": "lib/core/loadProfile.js",
        "expect": (
            "The catch block logs and returns `partial`, so a failed fetch is "
            "indistinguishable from a successful one. Callers receive an object "
            "missing its permissions and treat it as valid."
        ),
        "signals": [
            "swallow", "swallowed", "silently", "silent",
            "returns partial", "partial data", "incomplete",
            "treated as success", "looks like a success",
            "caller cannot tell", "callers cannot tell",
            "hides the error", "hiding the failure", "masks the error",
            "empty permissions", "missing permissions",
        ],
        "diff": """--- FILE: lib/core/loadProfile.js (modified, +12/-3)
@@ -1,14 +1,23 @@
 async function loadProfile(userId) {
   const partial = { id: userId, name: null, permissions: [] };

-  const user = await api.getUser(userId);
-  const perms = await api.getPermissions(userId);
-  return { ...partial, name: user.name, permissions: perms };
+  try {
+    const user = await api.getUser(userId);
+    partial.name = user.name;
+
+    const perms = await api.getPermissions(userId);
+    partial.permissions = perms;
+  } catch (err) {
+    logger.warn('profile load failed', err);
+  }
+
+  return partial;
 }

 module.exports = loadProfile;
""",
    },
    {
        "name": "interval never cleared on the error path",
        "file": "lib/core/pollJob.js",
        "expect": (
            "clearInterval only runs on the success path. If the job errors, the "
            "interval keeps firing forever, holding the callback and its closure "
            "alive - a leak that grows with every failed job."
        ),
        "signals": [
            "clearinterval", "clear interval", "never cleared", "not cleared",
            "leak", "leaks", "keeps running", "keeps firing", "runs forever",
            "error path", "on failure", "if it throws", "when it rejects",
            "finally",
        ],
        "diff": """--- FILE: lib/core/pollJob.js (modified, +16/-4)
@@ -1,12 +1,26 @@
 function pollJob(jobId, onDone) {
-  return api.getJob(jobId).then(onDone);
+  const timer = setInterval(async () => {
+    const job = await api.getJob(jobId);
+
+    if (job.status === 'running') {
+      return;
+    }
+
+    if (job.status === 'failed') {
+      onDone(new Error(`job ${jobId} failed`));
+      return;
+    }
+
+    clearInterval(timer);
+    onDone(null, job);
+  }, 1000);
+
+  return timer;
 }

 module.exports = pollJob;
""",
    },
    {
        "name": "ownership checked against the wrong id",
        "file": "lib/routes/documents.js",
        "expect": (
            "The handler verifies the requester owns `req.params.id`, then loads "
            "and returns `req.query.docId` instead. Any authenticated user can "
            "read any document by passing an id they own plus someone else's "
            "docId."
        ),
        "signals": [
            "wrong id", "different id", "params.id", "query.docid",
            "checks one", "checked against", "mismatch",
            "any user", "another user", "other users",
            "idor", "authorization", "authorisation", "access control",
            "bypass", "not the document being returned",
        ],
        "diff": """--- FILE: lib/routes/documents.js (modified, +11/-2)
@@ -1,13 +1,22 @@
 router.get('/documents/:id', requireAuth, async (req, res) => {
-  const doc = await Document.findById(req.params.id);
-
-  if (doc.ownerId !== req.user.id) {
-    return res.status(403).json({ error: 'forbidden' });
-  }
-
-  return res.json(doc);
+  const owned = await Document.findById(req.params.id);
+
+  if (!owned || owned.ownerId !== req.user.id) {
+    return res.status(403).json({ error: 'forbidden' });
+  }
+
+  // support ?docId= for the new bulk viewer
+  const target = req.query.docId || req.params.id;
+  const doc = await Document.findById(target);
+
+  return res.json(doc);
 });
""",
    },
    {
        "name": "check-then-act across an await",
        "file": "lib/core/reserveSeat.js",
        "expect": (
            "The seat count is read, awaited on, then written. Two concurrent "
            "calls both read the same count before either writes, so the seat is "
            "handed to both and capacity is exceeded."
        ),
        "signals": [
            "race", "race condition", "concurrent", "concurrently",
            "two requests", "both requests", "simultaneous",
            "check-then-act", "read.*then.*write", "between the read and the write",
            "stale", "overbook", "oversell", "exceed capacity",
            "atomic", "not atomic", "transaction", "lock",
        ],
        "diff": """--- FILE: lib/core/reserveSeat.js (modified, +14/-3)
@@ -1,12 +1,23 @@
 async function reserveSeat(eventId, userId) {
-  return db.reservations.create({ eventId, userId });
+  const event = await db.events.findById(eventId);
+  const taken = await db.reservations.countFor(eventId);
+
+  if (taken >= event.capacity) {
+    throw new Error('sold out');
+  }
+
+  const reservation = await db.reservations.create({ eventId, userId });
+
+  await db.events.update(eventId, { remaining: event.capacity - taken - 1 });
+
+  return reservation;
 }

 module.exports = reserveSeat;
""",
    },
]
