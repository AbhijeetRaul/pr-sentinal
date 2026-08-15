"""Two retrievers, one interface, so they can be measured against each other.

SymbolRetriever  — lexical. Pulls identifiers and string literals out of the
                   diff and scores files by exact occurrence. No API, no model,
                   no index. For "who calls this function", exact symbols are a
                   very strong signal and this is the honest baseline that a
                   vector store has to beat.

EmbeddingRetriever — semantic. Embeds each file and the diff, ranks by cosine
                   similarity. Catches conceptual relationships that share no
                   tokens, which is exactly where lexical search goes blind.

Cosine is computed in pure Python. At corpus scale (tens of files) a vector
database buys nothing but setup risk; pgvector only starts paying off when the
corpus is a whole repo, and that is a persistence decision, not a retrieval-
quality one. Swapping the store later does not change these numbers.
"""
import math
import re
from typing import Dict, List, Sequence

# function foo(...)  |  class Foo  |  const foo = ...  |  let/var foo = ...
_DECL_RE = re.compile(
    r"\b(?:function|class)\s+([A-Za-z_$][\w$]*)"
    r"|\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*="
)
# Any quoted literal: 'ECONNABORTED', "application/json", ...
_LITERAL_RE = re.compile(r"['\"]([A-Za-z_][\w.\-/]{2,})['\"]")
# Bare identifiers, used as a weak fallback signal.
_IDENT_RE = re.compile(r"\b([A-Za-z_$][\w$]{2,})\b")

_STOPWORDS = {
    "const", "let", "var", "function", "class", "return", "this", "new",
    "require", "module", "exports", "true", "false", "null", "undefined",
    "async", "await", "throw", "catch", "try", "else", "for", "while",
    "typeof", "instanceof", "constructor", "super", "length", "string",
    "number", "object", "error", "value", "key", "config", "options",
}


def changed_lines(diff: str) -> str:
    """Only the +/- lines. Context lines are already visible to the model."""
    return "\n".join(
        line[1:]
        for line in diff.splitlines()
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    )


def changed_file_paths(diff: str) -> List[str]:
    return re.findall(r"--- FILE: (\S+)", diff)


def extract_symbols(diff: str) -> List[str]:
    """Identifiers and literals worth searching the repo for."""
    body = changed_lines(diff)
    symbols: List[str] = []

    for m in _DECL_RE.finditer(body):
        symbols.append(m.group(1) or m.group(2))

    # String literals matter more than they look: the timeout fixture's only
    # link to its caller is the literal 'ECONNABORTED', which appears in no
    # declaration anywhere.
    symbols.extend(_LITERAL_RE.findall(body))

    # The module's own basename catches `require('./parseConfig')` importers.
    for path in changed_file_paths(diff):
        stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        symbols.append(stem)

    seen, out = set(), []
    for s in symbols:
        if not s or s.lower() in _STOPWORDS or len(s) < 3:
            continue
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


class SymbolRetriever:
    name = "symbol"

    def retrieve(self, diff: str, corpus: Sequence[Dict], k: int = 2) -> List[Dict]:
        symbols = extract_symbols(diff)
        changed = set(changed_file_paths(diff))
        stems = [
            p.rsplit("/", 1)[-1].rsplit(".", 1)[0] for p in changed_file_paths(diff)
        ]
        scored = []

        for f in corpus:
            if f["path"] in changed:
                continue  # never retrieve the file being reviewed
            text = f["content"]

            # A file that actually imports the changed module is a caller, which
            # is the single strongest signal available. Note this must test for
            # an import OF THE CHANGED MODULE — an earlier version credited any
            # file merely containing the substring "require(", which handed the
            # bonus to every module in the repo.
            imports_changed = any(
                re.search(rf"require\(['\"][^'\"]*{re.escape(stem)}['\"]\)", text)
                for stem in stems
            )

            score = 8.0 if imports_changed else 0.0
            for sym in symbols:
                hits = len(re.findall(rf"\b{re.escape(sym)}\b", text))
                if hits:
                    score += min(hits, 3)

            if score > 0:
                scored.append((score, f))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [f for _, f in scored[:k]]


class EmbeddingRetriever:
    name = "embed"

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is empty. Set it in .env to benchmark the "
                "embedding retriever, or run with --skip-embed."
            )
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._cache: Dict[str, List[float]] = {}

    def _embed(self, text: str) -> List[float]:
        key = text[:200] + str(len(text))
        if key not in self._cache:
            resp = self._client.embeddings.create(
                model=self._model, input=text[:8000]
            )
            self._cache[key] = resp.data[0].embedding
        return self._cache[key]

    @staticmethod
    def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else 0.0

    def retrieve(self, diff: str, corpus: Sequence[Dict], k: int = 2) -> List[Dict]:
        changed = set(changed_file_paths(diff))
        query = self._embed(changed_lines(diff))

        scored = []
        for f in corpus:
            if f["path"] in changed:
                continue
            scored.append((self._cosine(query, self._embed(f["content"])), f))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [f for _, f in scored[:k]]


def format_context(files: Sequence[Dict]) -> str:
    return "\n\n".join(f"--- FILE: {f['path']}\n{f['content']}" for f in files)
