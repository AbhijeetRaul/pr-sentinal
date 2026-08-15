"""A synthetic repo for the cross-file fixtures to retrieve from.

The oracle experiment handed the agent the correct file directly. Real retrieval
has to FIND it, which is only a meaningful test if there are plausible wrong
answers to pick instead. These distractors are deliberately adversarial:

  - `xhr.js` and `settle.js` both mention 'ECONNABORTED', the exact literal the
    timeout fixture keys on, so naive string matching has competition.
  - `AxiosHeaders.js` is full of header-normalising talk, competing with the
    normalizeHeaders fixture's true context file.
  - `buildFullPath.js` and `defaults/index.js` both handle config objects,
    competing with the parseConfig fixture.

If retrieval still wins against these, the number means something.
"""

DISTRACTORS = [
    {
        "path": "lib/helpers/buildURL.js",
        "content": """const isAbsoluteURL = require('./isAbsoluteURL');

function buildURL(url, params) {
  if (!params) {
    return url;
  }

  const serialized = Object.entries(params)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&');

  return url + (url.includes('?') ? '&' : '?') + serialized;
}

module.exports = buildURL;
""",
    },
    {
        "path": "lib/core/AxiosHeaders.js",
        "content": """class AxiosHeaders {
  constructor(headers) {
    this.store = new Map();
    if (headers) {
      this.merge(headers);
    }
  }

  merge(headers) {
    for (const [key, value] of Object.entries(headers)) {
      this.store.set(String(key).toLowerCase().trim(), value);
    }
    return this;
  }

  get(key) {
    return this.store.get(String(key).toLowerCase());
  }

  toJSON() {
    return Object.fromEntries(this.store);
  }
}

module.exports = AxiosHeaders;
""",
    },
    {
        "path": "lib/adapters/xhr.js",
        "content": """const settle = require('../core/settle');

function xhrAdapter(config) {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open(config.method.toUpperCase(), config.url, true);
    request.timeout = config.timeout;

    request.ontimeout = function handleTimeout() {
      const err = new Error('timeout exceeded');
      err.code = 'ECONNABORTED';
      reject(err);
    };

    request.onerror = function handleError() {
      const err = new Error('Network Error');
      err.code = 'ERR_NETWORK';
      reject(err);
    };

    request.send(config.data || null);
  });
}

module.exports = xhrAdapter;
""",
    },
    {
        "path": "lib/core/settle.js",
        "content": """function settle(resolve, reject, response) {
  const validateStatus = response.config.validateStatus;

  if (!response.status || !validateStatus || validateStatus(response.status)) {
    resolve(response);
    return;
  }

  const err = new Error('Request failed with status code ' + response.status);
  err.code = response.status >= 500 ? 'ECONNRESET' : 'ERR_BAD_RESPONSE';
  err.response = response;
  reject(err);
}

module.exports = settle;
""",
    },
    {
        "path": "lib/core/buildFullPath.js",
        "content": """const isAbsoluteURL = require('../helpers/isAbsoluteURL');
const combineURLs = require('../helpers/combineURLs');

function buildFullPath(baseURL, requestedURL) {
  if (baseURL && !isAbsoluteURL(requestedURL)) {
    return combineURLs(baseURL, requestedURL);
  }
  return requestedURL;
}

module.exports = buildFullPath;
""",
    },
    {
        "path": "lib/defaults/index.js",
        "content": """const DEFAULTS = {
  method: 'get',
  timeout: 0,
  maxRedirects: 21,
  validateStatus(status) {
    return status >= 200 && status < 300;
  },
  transformRequest: [function transformRequest(data, headers) {
    if (typeof data === 'object') {
      headers['content-type'] = 'application/json';
      return JSON.stringify(data);
    }
    return data;
  }],
};

module.exports = DEFAULTS;
""",
    },
    {
        "path": "lib/cancel/CanceledError.js",
        "content": """class CanceledError extends Error {
  constructor(message, config) {
    super(message || 'canceled');
    this.name = 'CanceledError';
    this.code = 'ERR_CANCELED';
    this.config = config;
  }
}

module.exports = CanceledError;
""",
    },
    {
        "path": "lib/helpers/isAbsoluteURL.js",
        "content": """function isAbsoluteURL(url) {
  return /^([a-z][a-z\\d+\\-.]*:)?\\/\\//i.test(url);
}

module.exports = isAbsoluteURL;
""",
    },
    {
        "path": "lib/helpers/combineURLs.js",
        "content": """function combineURLs(baseURL, relativeURL) {
  return relativeURL
    ? baseURL.replace(/\\/+$/, '') + '/' + relativeURL.replace(/^\\/+/, '')
    : baseURL;
}

module.exports = combineURLs;
""",
    },
    {
        "path": "lib/core/InterceptorManager.js",
        "content": """class InterceptorManager {
  constructor() {
    this.handlers = [];
  }

  use(fulfilled, rejected) {
    this.handlers.push({ fulfilled, rejected });
    return this.handlers.length - 1;
  }

  eject(id) {
    if (this.handlers[id]) {
      this.handlers[id] = null;
    }
  }

  forEach(fn) {
    this.handlers.forEach((h) => {
      if (h !== null) {
        fn(h);
      }
    });
  }
}

module.exports = InterceptorManager;
""",
    },
    {
        "path": "lib/helpers/toFormData.js",
        "content": """function toFormData(obj, formData) {
  formData = formData || new FormData();

  Object.entries(obj).forEach(([key, value]) => {
    if (value === undefined || value === null) {
      return;
    }
    formData.append(key, value);
  });

  return formData;
}

module.exports = toFormData;
""",
    },
    {
        "path": "test/unit/adapters/http.test.js",
        "content": """const httpAdapter = require('../../../lib/adapters/http');

describe('httpAdapter', () => {
  it('sends a GET request', async () => {
    const res = await httpAdapter({ hostname: 'example.com', method: 'GET' });
    expect(res.status).toBe(200);
  });

  it('propagates a timeout', async () => {
    await expect(
      httpAdapter({ hostname: 'example.com', method: 'GET', timeout: 1 })
    ).rejects.toThrow();
  });
});
""",
    },
]


def build_corpus(fixture):
    """The fixture's true context file(s) plus every distractor.

    Order is deterministic (true files last) so nothing can accidentally win by
    sitting at the front of the list.
    """
    return list(DISTRACTORS) + [
        {"path": cf["path"], "content": cf["content"]}
        for cf in fixture["context_files"]
    ]


def true_paths(fixture):
    return {cf["path"] for cf in fixture["context_files"]}
