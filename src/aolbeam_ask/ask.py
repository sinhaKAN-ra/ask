#!/usr/bin/env python3
"""
ask - a lightweight terminal AI CLI.

Zero idle footprint: no daemon, no server. It only runs for the duration of
one request. Points at any OpenAI-compatible chat API (Groq, Gemini via its
OpenAI-compat endpoint, OpenRouter, Cerebras, local Ollama, ...).

Features:
  - Fully configurable via ~/.ask-cli/config.json (see DEFAULT_CONFIG below).
  - Conversation memory in plain .txt (readable) + .json (structured).
  - Resume prompt when the last session is older than resume_threshold_hours.
  - Per-answer metrics: prompt/completion/total tokens, context-window usage %,
    latency, model, plus a warning as you approach the context limit.

Usage:
  ask "your question"              one-shot, continues the active session
  ask -f FILE "question"           ask about a file (repeatable: -f a.py -f b.py)
  ask -f big.py:50-120 "question"  include only lines 50-120 (also :50- / :-30 / :80)
  ask -f "src/*.py" "question"     globs are supported
  cat err.log | ask "what broke?"  piped stdin is added as context too
  ask -w "latest python version"   force a web search for this query
  ask --no-web "..."               disable web fallback for this query
  ask -n "fresh question"          force a brand-new conversation
  ask --new                        start a new conversation (then prompts)
  ask --resume                     resume the saved conversation
  ask --list                       list saved conversations (numbered, with titles)
  ask --select N                   switch to / resume saved conversation N
  ask --title "A good name"        rename the active conversation
  ask --info                       show current session stats and config
  ask --config                     print resolved config + where it lives
  ask --clear                      archive the active session and start clean
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config. Everything here can be overridden in ~/.ask-cli/config.json.
# The config file is created on first run; edit it to switch provider/model.
# ---------------------------------------------------------------------------
HOME = os.path.expanduser("~")
BASE_DIR = os.path.join(HOME, ".ask-cli")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
ACTIVE_TXT = os.path.join(SESSIONS_DIR, "active.txt")
ACTIVE_JSON = os.path.join(SESSIONS_DIR, "active.json")

DEFAULT_CONFIG = {
    # --- Provider / endpoint (OpenAI-compatible chat/completions) ----------
    "provider": "groq",
    "base_url": "https://api.groq.com/openai/v1",
    "model": "llama-3.3-70b-versatile",
    # API key: put it here, OR set the env var named by api_key_env.
    "api_key": "",
    "api_key_env": "GROQ_API_KEY",

    # --- Generation --------------------------------------------------------
    "system_prompt": "You are a concise, accurate terminal assistant. Answer directly. Use short code blocks when relevant.",
    "max_tokens": 1024,
    "temperature": 0.4,

    # --- Web fallback ------------------------------------------------------
    # When enabled, the model self-assesses whether its answer may be stale or
    # outside its knowledge. It appends a machine-readable line:
    #     NEEDS_WEB: yes|no  (reason)
    # If 'yes' (or you force it with -w/--web), the script runs a web search,
    # feeds the results back, and returns a grounded final answer.
    # The search only happens during that one invocation — zero idle cost.
    "web_fallback": True,
    # Search provider: "duckduckgo" (keyless, free, default), or one of
    # "tavily" / "serper" / "brave" — add a key below (or set the env var) to
    # use those. Skeleton is wired for all four; just fill in the key.
    "search_provider": "duckduckgo",
    "search_api_key": "",
    "search_api_key_env": "SEARCH_API_KEY",
    "search_results": 5,          # how many results to feed back
    "search_max_chars": 6000,     # cap on total search text sent to the model
    # Also search when YOUR question contains freshness cues (latest/today/2026...).
    "web_on_freshness_cues": True,

    # --- Context / memory --------------------------------------------------
    # The model's real context window (tokens). Used ONLY for the usage %
    # metric and the near-limit warning. Set it to match your model.
    "context_window": 128000,
    # How many past user+assistant exchanges to send back as context.
    "history_turns": 12,
    # Max characters read from EACH file passed via -f/--file (or stdin).
    # Larger files are truncated (with a notice) so one file can't blow the
    # context window. ~4 chars/token, so 48000 ≈ 12k tokens per file.
    "max_file_chars": 48000,
    # If the active session was last touched more than this many hours ago,
    # ask whether to resume or start new.
    "resume_threshold_hours": 2,

    # --- Display -----------------------------------------------------------
    "show_metrics": True,
    # Render clickable terminal hyperlinks (OSC 8) for sources + in-answer
    # citations. Set false if your terminal shows raw ']8;;' escape codes.
    "osc8_links": True,
    # Warn when a request's total tokens exceed this fraction of the window.
    "context_warn_fraction": 0.75,
    # Rough chars-per-token estimate, used only when the API omits usage.
    "chars_per_token_estimate": 4,
}

# Known-provider hints printed by --config to make switching easy.
PROVIDER_HINTS = {
    "groq": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile", "GROQ_API_KEY",
             "Free key: https://console.groq.com/keys"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-2.0-flash",
               "GEMINI_API_KEY", "Free key: https://aistudio.google.com/apikey"),
    "openrouter": ("https://openrouter.ai/api/v1", "meta-llama/llama-3.3-70b-instruct:free",
                   "OPENROUTER_API_KEY", "Free key: https://openrouter.ai/keys"),
    "cerebras": ("https://api.cerebras.ai/v1", "llama-3.3-70b", "CEREBRAS_API_KEY",
                 "Free key: https://cloud.cerebras.ai"),
    "ollama": ("http://localhost:11434/v1", "llama3.2", "OLLAMA_API_KEY",
               "Local Ollama; api_key can be any non-empty string"),
}


# ---------------------------------------------------------------------------
# Setup / config loading
# ---------------------------------------------------------------------------
def ensure_dirs():
    os.makedirs(SESSIONS_DIR, exist_ok=True)


def load_config():
    ensure_dirs()
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                user = json.load(f)
            cfg.update(user)
        except Exception as e:
            print(f"[ask] warning: could not read config ({e}); using defaults", file=sys.stderr)
    else:
        with open(CONFIG_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        print(f"[ask] created default config at {CONFIG_PATH}", file=sys.stderr)
        print("[ask] add your free API key there (or set the env var) and re-run.", file=sys.stderr)
    return cfg


def resolve_api_key(cfg):
    if cfg.get("api_key"):
        return cfg["api_key"]
    env_name = cfg.get("api_key_env", "")
    if env_name and os.environ.get(env_name):
        return os.environ[env_name]
    return ""


# ---------------------------------------------------------------------------
# Session storage
# ---------------------------------------------------------------------------
def now_iso():
    return datetime.now(timezone.utc).isoformat()


def new_session():
    return {"started": now_iso(), "last_active": now_iso(), "title": "", "messages": []}


def derive_title(session, max_words=6):
    """Title = first user message, trimmed to a few words. Falls back to date."""
    if session.get("title"):
        return session["title"]
    for m in session.get("messages", []):
        if m["role"] == "user":
            words = m["content"].strip().split()
            t = " ".join(words[:max_words])
            if len(words) > max_words:
                t += "…"
            return t or "(empty)"
    return "(no messages)"


def load_session():
    if os.path.exists(ACTIVE_JSON):
        try:
            with open(ACTIVE_JSON) as f:
                s = json.load(f)
            s.setdefault("title", "")
            return s
        except Exception:
            pass
    return new_session()


def save_session(session):
    session["last_active"] = now_iso()
    # Auto-title from the first question once we have one, unless user set it.
    if not session.get("title"):
        session["title"] = derive_title(session)
    with open(ACTIVE_JSON, "w") as f:
        json.dump(session, f, indent=2)
    # Human-readable transcript
    with open(ACTIVE_TXT, "w") as f:
        f.write(f"# conversation started {session['started']}\n")
        f.write(f"# last active   {session['last_active']}\n\n")
        for m in session["messages"]:
            role = m["role"].upper()
            ts = m.get("ts", "")
            f.write(f"[{role}] {ts}\n{m['content']}\n\n")


def slugify(text, maxlen=40):
    keep = "".join(c if c.isalnum() or c in " -_" else "" for c in text)
    slug = "-".join(keep.split()).strip("-").lower()
    return (slug[:maxlen] or "conversation")


def archive_session():
    if not os.path.exists(ACTIVE_JSON):
        return None
    try:
        with open(ACTIVE_JSON) as f:
            s = json.load(f)
    except Exception:
        s = {}
    title = s.get("title") or derive_title(s) if s else "conversation"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = f"conversation-{stamp}-{slugify(title)}"
    dst_json = os.path.join(SESSIONS_DIR, base + ".json")
    dst_txt = os.path.join(SESSIONS_DIR, base + ".txt")
    os.rename(ACTIVE_JSON, dst_json)
    if os.path.exists(ACTIVE_TXT):
        os.rename(ACTIVE_TXT, dst_txt)
    return dst_json


def hours_since(iso_str):
    try:
        then = datetime.fromisoformat(iso_str)
        if then.tzinfo is None:
            then = then.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - then).total_seconds() / 3600.0
    except Exception:
        return 1e9


# ---------------------------------------------------------------------------
# Web fallback: self-assessment + search
# ---------------------------------------------------------------------------
WEB_SENTINEL = "NEEDS_WEB:"

SELF_ASSESS_SUFFIX = (
    "\n\nAfter your answer, on a NEW final line, output exactly one of:\n"
    "  NEEDS_WEB: no\n"
    "  NEEDS_WEB: yes — <short reason>\n"
    "Say 'yes' only if answering well needs information that is newer than your "
    "training, changes frequently (prices, versions, news, current events, "
    "who-holds-a-role-now), or that you are genuinely unsure about. Otherwise 'no'. "
    "This line is a control signal; keep it as the very last line."
)

FRESHNESS_CUES = (
    "latest", "newest", "current", "today", "right now", "this week",
    "this year", "2024", "2025", "2026", "2027", "recent", "nowadays",
    "as of", "up to date", "up-to-date", "release", "released", "news",
)


def wants_web_from_question(query, cfg):
    if not cfg.get("web_on_freshness_cues"):
        return False
    q = query.lower()
    return any(cue in q for cue in FRESHNESS_CUES)


def normalize_citations(text):
    """Rewrite noisy model citation glyphs like 【3†L1-L4】 or [3†...] into
    plain [3]. Leaves already-plain [n] untouched."""
    import re
    text = re.sub(r"[【〔]\s*(\d+)\s*(?:†[^】〕]*)?[】〕]", r"[\1]", text)
    text = re.sub(r"\[(\d+)\s*†[^\]]*\]", r"[\1]", text)
    text = re.sub(r"(?<!\w)(\d+)†[\w\-]+", r"[\1]", text)
    return text


def osc8_link(url, label):
    """Wrap label in an OSC 8 terminal hyperlink (clickable in iTerm2,
    Terminal.app, kitty, WezTerm, VS Code terminal...). Degrades to plain
    text where unsupported."""
    if not url:
        return label
    esc = "\033"
    return f"{esc}]8;;{url}{esc}\\{label}{esc}]8;;{esc}\\"


def link_citations(text, sources):
    """Turn plain [n] citations in the answer into OSC 8 hyperlinks pointing
    to source n's URL. sources is a list of (title, url); [1] -> sources[0]."""
    import re

    def repl(m):
        n = int(m.group(1))
        if 1 <= n <= len(sources):
            url = sources[n - 1][1]
            if url:
                return osc8_link(url, f"[{n}]")
        return m.group(0)

    return re.sub(r"\[(\d+)\]", repl, text)


def parse_needs_web(answer):
    """Split the model's reply into (visible_answer, needs_web_bool, reason).
    The sentinel line is removed from what the user sees."""
    lines = answer.splitlines()
    needs, reason = False, ""
    kept = []
    for ln in lines:
        s = ln.strip()
        if s.upper().startswith(WEB_SENTINEL):
            val = s[len(WEB_SENTINEL):].strip()
            low = val.lower()
            needs = low.startswith("yes") or low.startswith("y ")
            # reason after a dash/colon if present
            for sep in ("—", "-", ":"):
                if sep in val:
                    reason = val.split(sep, 1)[1].strip()
                    break
        else:
            kept.append(ln)
    visible = "\n".join(kept).strip()
    return visible, needs, reason


def resolve_search_key(cfg):
    if cfg.get("search_api_key"):
        return cfg["search_api_key"]
    env = cfg.get("search_api_key_env", "")
    if env and os.environ.get(env):
        return os.environ[env]
    return ""


def web_search(query, cfg):
    """Return (results_text, source_list). Default keyless DuckDuckGo;
    tavily/serper/brave used if configured + keyed. Called only during a
    single invocation — nothing stays resident. On failure, results_text
    begins with '[web search failed:' so the caller can report it."""
    provider = cfg.get("search_provider", "duckduckgo").lower()
    n = int(cfg.get("search_results", 5))
    cap = int(cfg.get("search_max_chars", 6000))
    key = resolve_search_key(cfg)

    try:
        if provider == "tavily" and key:
            return _search_tavily(query, n, key, cap)
        if provider == "serper" and key:
            return _search_serper(query, n, key)
        if provider == "brave" and key:
            return _search_brave(query, n, key)
        if provider in ("tavily", "serper", "brave") and not key:
            # Configured for a keyed provider but no key found -> fall back.
            print(f"[ask] {provider} selected but no key found "
                  f"(${cfg.get('search_api_key_env','SEARCH_API_KEY')}); "
                  "falling back to DuckDuckGo.", file=sys.stderr)
        return _search_duckduckgo(query, n, cap)
    except Exception as e:
        return (f"[web search failed: {e}]", [])


def _http_json(url, headers=None, data=None, method="GET", timeout=25):
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("User-Agent", "ask-cli/1.0")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode(errors="replace"))


def _trim(text, cap):
    return text if len(text) <= cap else text[:cap] + "\n...[search text truncated]..."


def _search_duckduckgo(query, n, cap):
    """Keyless. Uses DuckDuckGo's HTML endpoint and strips tags crudely —
    no third-party package needed."""
    import re
    import html as _html
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, method="POST",
                                 data=urllib.parse.urlencode({"q": query}).encode())
    req.add_header("User-Agent",
                   "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
    with urllib.request.urlopen(req, timeout=20) as resp:
        page = resp.read().decode(errors="replace")
    # Each result: <a class="result__a" href="...">title</a> + snippet
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', page, re.S)
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', page, re.S)
    links = re.findall(r'class="result__a"[^>]*href="(.*?)"', page, re.S)

    def clean(x):
        return _html.unescape(re.sub(r"<[^>]+>", "", x)).strip()

    def real_url(href):
        # DuckDuckGo wraps links as //duckduckgo.com/l/?uddg=<encoded>&...
        href = _html.unescape(href)
        m2 = re.search(r"[?&]uddg=([^&]+)", href)
        if m2:
            return urllib.parse.unquote(m2.group(1))
        if href.startswith("//"):
            return "https:" + href
        return href

    out, sources = [], []
    for i in range(min(n, len(titles))):
        t = clean(titles[i])
        s = clean(snippets[i]) if i < len(snippets) else ""
        link = real_url(links[i]) if i < len(links) else ""
        out.append(f"[{i+1}] {t}\n{s}\n{link}")
        sources.append((t or link, link))
    text = "\n\n".join(out) if out else "[no results]"
    return _trim(text, cap), sources


def _search_tavily(query, n, key, cap=6000):
    body = json.dumps({
        "query": query,
        "max_results": n,
        "search_depth": "advanced",   # richer snippet content
        "include_answer": "advanced", # Tavily's own synthesized answer
    }).encode()
    data = _http_json(
        "https://api.tavily.com/search",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"},   # current Tavily auth
        data=body, method="POST")
    out, sources = [], []
    tav_answer = (data.get("answer") or "").strip()
    if tav_answer:
        out.append(f"[Tavily summary] {tav_answer}")
    for i, r in enumerate(data.get("results", [])[:n], 1):
        content = (r.get("content") or "")[:1500]
        out.append(f"[{i}] {r.get('title','')}\n{content}\n{r.get('url','')}")
        sources.append((r.get("title") or r.get("url", ""), r.get("url", "")))
    text = "\n\n".join(out) or "[no results]"
    return _trim(text, cap), sources


def _search_serper(query, n, key):
    body = json.dumps({"q": query, "num": n}).encode()
    data = _http_json("https://google.serper.dev/search",
                      headers={"X-API-KEY": key, "Content-Type": "application/json"},
                      data=body, method="POST")
    out, sources = [], []
    for i, r in enumerate(data.get("organic", [])[:n], 1):
        out.append(f"[{i}] {r.get('title','')}\n{r.get('snippet','')}\n{r.get('link','')}")
        sources.append((r.get("title") or r.get("link", ""), r.get("link", "")))
    return "\n\n".join(out) or "[no results]", sources


def _search_brave(query, n, key):
    url = "https://api.search.brave.com/res/v1/web/search?q=" + urllib.parse.quote(query)
    data = _http_json(url, headers={"X-Subscription-Token": key,
                                    "Accept": "application/json"})
    out, sources = [], []
    for i, r in enumerate((data.get("web", {}).get("results") or [])[:n], 1):
        out.append(f"[{i}] {r.get('title','')}\n{r.get('description','')}\n{r.get('url','')}")
        sources.append((r.get("title") or r.get("url", ""), r.get("url", "")))
    return "\n\n".join(out) or "[no results]", sources


# ---------------------------------------------------------------------------
# File / stdin context
# ---------------------------------------------------------------------------
def split_line_range(arg):
    """Split a '-f' argument into (path, range_or_None).
    Supported range suffixes (only when they are clearly numeric):
        file.py:50-120   lines 50..120 inclusive
        file.py:50-      line 50 to end
        file.py:-30      first 30 lines
        file.py:80       just line 80
    A trailing ':<non-numeric>' (e.g. a Windows drive, or a URL) is left alone."""
    import re
    m = re.search(r":(\d*-?\d*)$", arg)
    if not m:
        return arg, None
    spec = m.group(1)
    if spec in ("", "-"):
        return arg, None
    # Must contain at least one digit and only digits/one dash.
    if not re.fullmatch(r"\d+|\d*-\d*", spec):
        return arg, None
    path = arg[: m.start()]
    if "-" in spec:
        a, b = spec.split("-", 1)
        start = int(a) if a else 1
        end = int(b) if b else None
    else:
        start = end = int(spec)
    return path, (start, end)


def apply_line_range(text, rng):
    """Keep only lines[start..end] (1-indexed, inclusive). end=None -> to EOF."""
    if rng is None:
        return text, None
    start, end = rng
    lines = text.splitlines()
    total = len(lines)
    s = max(1, start)
    e = total if end is None else min(end, total)
    if s > total:
        return "", f"lines {start}-{end if end else '∞'} (file only has {total})"
    selected = lines[s - 1 : e]
    return "\n".join(selected), f"lines {s}-{e} of {total}"


def gather_file_context(file_args, cfg):
    """Turn -f paths (with glob + optional :line-range) + piped stdin into
    labeled context blocks. Returns (context_str, meta). Reads at call time
    only; nothing stays resident after the process exits."""
    import glob as _glob

    blocks = []
    meta = []  # (label, chars, truncated)
    cap = int(cfg.get("max_file_chars", 48000))

    # Each -f arg may carry a :range suffix; split it off before globbing.
    specs = []  # (path, range)
    for a in file_args:
        raw, rng = split_line_range(a)
        matched = _glob.glob(os.path.expanduser(raw))
        if matched:
            for mp in sorted(matched):
                specs.append((mp, rng))
        else:
            specs.append((os.path.expanduser(raw), rng))

    for p, rng in specs:
        if not os.path.isfile(p):
            print(f"[ask] warning: file not found, skipping: {p}", file=sys.stderr)
            continue
        try:
            with open(p, "r", errors="replace") as fh:
                text = fh.read()
        except Exception as e:
            print(f"[ask] warning: could not read {p} ({e}); skipping", file=sys.stderr)
            continue
        range_note = ""
        if rng is not None:
            text, info = apply_line_range(text, rng)
            if not text:
                print(f"[ask] warning: {p}: {info}; skipping", file=sys.stderr)
                continue
            range_note = f"  [{info}]"
        truncated = False
        if len(text) > cap:
            text = text[:cap] + f"\n...[truncated at {cap} chars]..."
            truncated = True
        lines = text.count("\n") + 1
        label = f"{p}{range_note}"
        blocks.append(f"--- FILE: {label} ({lines} lines shown) ---\n{text}\n--- END FILE: {p} ---")
        meta.append((label, len(text), truncated))

    # Piped stdin (e.g. `cat err.log | ask "..."`). Only when not a tty.
    if not sys.stdin.isatty():
        try:
            piped = sys.stdin.read()
        except Exception:
            piped = ""
        if piped.strip():
            truncated = False
            if len(piped) > cap:
                piped = piped[:cap] + f"\n...[truncated at {cap} chars]..."
                truncated = True
            blocks.append(f"--- PIPED INPUT (stdin) ---\n{piped}\n--- END PIPED INPUT ---")
            meta.append(("<stdin>", len(piped), truncated))

    return ("\n\n".join(blocks), meta)


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------
def build_messages(session, cfg, user_query, file_context="", assess=False):
    sys_prompt = cfg["system_prompt"]
    if assess:
        sys_prompt = sys_prompt + SELF_ASSESS_SUFFIX
    msgs = [{"role": "system", "content": sys_prompt}]
    turns = cfg["history_turns"] * 2  # user+assistant pairs
    history = session["messages"][-turns:] if turns > 0 else []
    for m in history:
        msgs.append({"role": m["role"], "content": m["content"]})
    if file_context:
        content = (
            "Use the following file(s) as context for my question. "
            "Refer to them by their FILE path when relevant.\n\n"
            f"{file_context}\n\nQUESTION: {user_query}"
        )
    else:
        content = user_query
    msgs.append({"role": "user", "content": content})
    return msgs


def estimate_tokens(messages, cfg):
    chars = sum(len(m["content"]) for m in messages)
    return max(1, chars // cfg["chars_per_token_estimate"])


def call_api(cfg, api_key, messages):
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    payload = {
        "model": cfg["model"],
        "messages": messages,
        "max_tokens": cfg["max_tokens"],
        "temperature": cfg["temperature"],
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("User-Agent", "ask-cli/1.0")
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} from {cfg['provider']}: {detail}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"network error reaching {url}: {e.reason}")
    latency = time.time() - start
    return body, latency


# ---------------------------------------------------------------------------
# Output / metrics
# ---------------------------------------------------------------------------
def print_metrics(cfg, body, latency, est_prompt, file_meta=None, web_status=None):
    if not cfg.get("show_metrics", True):
        return
    usage = body.get("usage") or {}
    pt = usage.get("prompt_tokens")
    ct = usage.get("completion_tokens")
    tt = usage.get("total_tokens")
    estimated = False
    if pt is None:
        pt, estimated = est_prompt, True
    if ct is None:
        ct = 0
    if tt is None:
        tt = (pt or 0) + (ct or 0)

    win = cfg["context_window"]
    used_frac = tt / win if win else 0
    finish = (body.get("choices") or [{}])[0].get("finish_reason", "?")

    bar_tag = " (estimated)" if estimated else ""
    print("\n\033[2m" + "-" * 48, file=sys.stderr)
    print(f"model      : {cfg['model']}  ({cfg['provider']})", file=sys.stderr)
    if web_status:
        provider, n, trigger = web_status
        print(f"web search : {provider} — {n} results  [{trigger}]", file=sys.stderr)
    if file_meta:
        for path, chars, truncated in file_meta:
            name = os.path.basename(path) if path != "<stdin>" else "<stdin>"
            flag = "  [TRUNCATED]" if truncated else ""
            print(f"context in : {name}  (~{chars} chars, ~{chars//cfg['chars_per_token_estimate']} tok){flag}",
                  file=sys.stderr)
    print(f"tokens     : prompt {pt} + completion {ct} = {tt}{bar_tag}", file=sys.stderr)
    print(f"context    : {tt}/{win}  ({used_frac*100:.1f}% of window used)", file=sys.stderr)
    print(f"latency    : {latency:.2f}s   finish: {finish}", file=sys.stderr)
    if finish == "length":
        print("warning    : response hit max_tokens and was CUT OFF. "
              "Raise max_tokens in config for complete answers.", file=sys.stderr)
    if used_frac >= cfg["context_warn_fraction"]:
        print(f"warning    : using {used_frac*100:.0f}% of the context window. "
              "Older turns may be dropped and answer quality can degrade. "
              "Consider `ask --new` or lowering history_turns.", file=sys.stderr)
    print("\033[0m", end="", file=sys.stderr)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------
def cmd_info(cfg):
    s = load_session()
    n = len(s["messages"])
    print(f"active session : {ACTIVE_JSON}")
    print(f"title          : {derive_title(s)}")
    print(f"started        : {s['started']}")
    print(f"last active    : {s['last_active']}  ({hours_since(s['last_active']):.1f}h ago)")
    print(f"messages       : {n} ({n//2} exchanges)")
    print(f"model          : {cfg['model']} ({cfg['provider']})")
    print(f"context window : {cfg['context_window']} tokens")
    print(f"history sent   : last {cfg['history_turns']} exchanges")
    if n:
        est = estimate_tokens([{"content": m["content"]} for m in s["messages"]], cfg)
        print(f"stored size    : ~{est} tokens of transcript")


def list_archives():
    """Return sorted list of (number, path, session_dict) for saved conversations."""
    ensure_dirs()
    files = sorted(
        (f for f in os.listdir(SESSIONS_DIR)
         if f.endswith(".json") and f != "active.json"),
        reverse=True,  # newest first
    )
    out = []
    for i, f in enumerate(files, 1):
        p = os.path.join(SESSIONS_DIR, f)
        try:
            with open(p) as fh:
                s = json.load(fh)
        except Exception:
            s = None
        out.append((i, p, s))
    return out


def cmd_list():
    archives = list_archives()
    # Show the active session as entry 0 if it has content.
    active = load_session()
    if active["messages"]:
        print(f"  0  {derive_title(active):42s} [ACTIVE] "
              f"{len(active['messages'])//2} exch  {hours_since(active['last_active']):.1f}h ago")
    if not archives:
        if not active["messages"]:
            print("no saved conversations yet.")
        else:
            print("\n(no archived conversations; use `ask --select N` after you have some)")
        return
    print("\nsaved conversations (newest first):")
    for num, path, s in archives:
        if s is None:
            print(f"  {num:2d}  (unreadable: {os.path.basename(path)})")
            continue
        title = s.get("title") or derive_title(s)
        exch = len(s.get("messages", [])) // 2
        when = s.get("last_active", "?")[:16].replace("T", " ")
        print(f"  {num:2d}  {title:42s} {exch:3d} exch  {when}")
    print("\nresume one with:  ask --select N   (archives your current one first)")


def cmd_select(n):
    archives = list_archives()
    match = next((a for a in archives if a[0] == n), None)
    if not match:
        print(f"[ask] no conversation #{n}. Run `ask --list`.", file=sys.stderr)
        return 1
    _, path, s = match
    if s is None:
        print(f"[ask] conversation #{n} is unreadable.", file=sys.stderr)
        return 1
    # Archive whatever is currently active, then promote the chosen one.
    active = load_session()
    if active["messages"]:
        archive_session()
    with open(path) as f:
        chosen = json.load(f)
    chosen.setdefault("title", derive_title(chosen))
    save_session(chosen)
    # Remove the old archive copy so it isn't duplicated.
    try:
        os.remove(path)
        txt = path[:-5] + ".txt"
        if os.path.exists(txt):
            os.remove(txt)
    except OSError:
        pass
    print(f"[ask] resumed \"{chosen['title']}\" ({len(chosen['messages'])//2} exchanges). "
          f"Your next `ask` continues it.")
    return 0


def cmd_rename(title):
    s = load_session()
    s["title"] = title.strip()
    save_session(s)
    print(f"[ask] active conversation titled: \"{s['title']}\"")
    return 0


def cmd_config(cfg):
    print(f"config file: {CONFIG_PATH}")
    print(f"sessions   : {SESSIONS_DIR}")
    print(json.dumps(cfg, indent=2))
    hint = PROVIDER_HINTS.get(cfg["provider"])
    if hint:
        print(f"\nprovider hint: base_url={hint[0]}  model={hint[1]}  env={hint[2]}\n{hint[3]}")
    print("\nTo switch provider, edit base_url/model/api_key_env in the config.")
    print("Known providers:", ", ".join(PROVIDER_HINTS))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    cfg = load_config()
    args = sys.argv[1:]

    if not args:
        print(__doc__.strip())
        return 0

    flag = args[0]
    if flag in ("-h", "--help"):
        print(__doc__.strip()); return 0
    if flag == "--info":
        cmd_info(cfg); return 0
    if flag == "--list":
        cmd_list(); return 0
    if flag in ("--select", "--open", "--use"):
        if len(args) < 2 or not args[1].lstrip("-").isdigit():
            print("[ask] usage: ask --select N   (see numbers with `ask --list`)", file=sys.stderr)
            return 1
        return cmd_select(int(args[1]))
    if flag in ("--title", "--rename"):
        if len(args) < 2:
            print("[ask] usage: ask --title \"My conversation name\"", file=sys.stderr)
            return 1
        return cmd_rename(" ".join(args[1:]))
    if flag == "--config":
        cmd_config(cfg); return 0
    if flag == "--clear":
        dst = archive_session()
        print(f"archived to {dst}" if dst else "nothing to archive.")
        return 0

    force_new = False
    force_resume = False
    if flag in ("-n", "--new"):
        force_new = True
        args = args[1:]
    elif flag == "--resume":
        force_resume = True
        args = args[1:]

    query = " ".join(args).strip()

    # Pull out -f/--file FILE pairs from anywhere in the remaining args.
    file_args = []
    rest = []
    i = 0
    force_web = False
    disable_web = False
    while i < len(args):
        a = args[i]
        if a in ("-f", "--file"):
            if i + 1 < len(args):
                file_args.append(args[i + 1])
                i += 2
                continue
            else:
                print("[ask] -f/--file needs a path argument", file=sys.stderr)
                return 1
        elif a.startswith("--file="):
            file_args.append(a.split("=", 1)[1])
        elif a.startswith("-f") and len(a) > 2:
            file_args.append(a[2:])  # -fFILE
        elif a in ("-w", "--web"):
            force_web = True
        elif a == "--no-web":
            disable_web = True
        else:
            rest.append(a)
        i += 1
    query = " ".join(rest).strip()

    api_key = resolve_api_key(cfg)
    if not api_key:
        print(f"[ask] no API key. Put it in {CONFIG_PATH} (api_key) "
              f"or set ${cfg['api_key_env']}.", file=sys.stderr)
        hint = PROVIDER_HINTS.get(cfg["provider"])
        if hint:
            print(f"[ask] {hint[3]}", file=sys.stderr)
        return 2

    # Resume / new decision
    session = load_session()
    has_history = bool(session["messages"])
    if force_new:
        if has_history:
            archive_session()
        session = new_session()
    elif force_resume:
        pass  # keep active session as-is
    elif has_history:
        gap = hours_since(session["last_active"])
        if gap >= cfg["resume_threshold_hours"]:
            # interactive prompt only if we have a tty
            if sys.stdin.isatty() and sys.stdout.isatty():
                last = session["messages"][-1]["content"][:70].replace("\n", " ")
                print(f"[ask] last conversation was {gap:.1f}h ago "
                      f"({len(session['messages'])//2} exchanges).", file=sys.stderr)
                print(f"[ask] last message: \"{last}...\"", file=sys.stderr)
                try:
                    ans = input("[ask] resume it? [Y/n] ").strip().lower()
                except EOFError:
                    ans = "y"
                if ans in ("n", "no", "new"):
                    archive_session()
                    session = new_session()

    if not query and not file_args and sys.stdin.isatty():
        print("[ask] no query given.", file=sys.stderr)
        return 1

    file_context, file_meta = gather_file_context(file_args, cfg)

    if not query:
        # Files/stdin but no question -> sensible default.
        query = "Explain and summarize the provided context."

    web_enabled = cfg.get("web_fallback", True) and not disable_web
    # Ask the model to self-assess only when web is a possibility and the user
    # didn't already force it (forcing skips the assessment round-trip).
    assess = web_enabled and not force_web

    messages = build_messages(session, cfg, query, file_context, assess=assess)
    est_prompt = estimate_tokens(messages, cfg)

    try:
        body, latency = call_api(cfg, api_key, messages)
    except RuntimeError as e:
        print(f"[ask] {e}", file=sys.stderr)
        return 3

    choice = (body.get("choices") or [{}])[0]
    raw = (choice.get("message") or {}).get("content", "").strip()
    if not raw:
        print("[ask] empty response from provider.", file=sys.stderr)
        return 3

    # Decide whether to go to the web.
    answer, needs_web, reason = parse_needs_web(raw) if assess else (raw, False, "")
    do_web = web_enabled and (
        force_web
        or needs_web
        or wants_web_from_question(query, cfg)
    )

    web_status = None     # for metrics
    web_sources = []      # (title, url) pairs for the Sources block
    total_latency = latency
    if do_web:
        trigger = ("forced (-w)" if force_web
                   else "model self-assessed" if needs_web
                   else "freshness cue in question")
        print(f"[ask] searching the web ({cfg.get('search_provider','duckduckgo')}) — "
              f"{trigger}{(': ' + reason) if reason else ''}", file=sys.stderr)
        results_text, sources = web_search(query, cfg)
        if results_text.startswith("[web search failed:") or results_text == "[no results]":
            print(f"[ask] web search returned nothing usable "
                  f"({results_text.strip('[]')}). Answering from model knowledge only.",
                  file=sys.stderr)
        # Re-ask, grounded in the search results.
        today = datetime.now().strftime("%Y-%m-%d")
        grounded_sys = (cfg["system_prompt"] +
                        f"\n\nToday's date is {today}. Answer using the WEB RESULTS below as the "
                        "primary source for anything time-sensitive, and prefer the most recent "
                        "information. CITATION FORMAT: cite sources ONLY as plain bracketed "
                        "numbers like [1] or [2][3]. Do NOT use any other citation notation "
                        "(no '†', no 'L1-L4', no footnote glyphs). If the results don't cover "
                        "the question, say so plainly.")
        gmsgs = [{"role": "system", "content": grounded_sys}]
        turns = cfg["history_turns"] * 2
        for m in session["messages"][-turns:]:
            gmsgs.append({"role": m["role"], "content": m["content"]})
        ctx = ""
        if file_context:
            ctx = f"FILE CONTEXT:\n{file_context}\n\n"
        gmsgs.append({"role": "user", "content":
                      f"{ctx}WEB RESULTS (fetched just now):\n{results_text}\n\n"
                      f"QUESTION: {query}"})
        try:
            body2, latency2 = call_api(cfg, api_key, gmsgs)
            total_latency += latency2
            a2 = ((body2.get("choices") or [{}])[0].get("message") or {}).get("content", "").strip()
            if a2:
                answer = a2
                body = body2  # metrics reflect the final (grounded) call
            web_status = (cfg.get("search_provider", "duckduckgo"), len(sources), trigger)
            web_sources = sources
        except RuntimeError as e:
            print(f"[ask] web re-ask failed ({e}); showing the original answer.", file=sys.stderr)
            web_status = (cfg.get("search_provider", "duckduckgo"), 0, trigger + " [failed]")

    use_links = cfg.get("osc8_links", True)
    if web_sources:
        answer = normalize_citations(answer)
        if use_links:
            answer = link_citations(answer, web_sources)

    print(answer)

    # Show the web references the grounded answer was based on, as clickable
    # OSC 8 terminal hyperlinks (plain text where the terminal lacks support).
    if web_sources:
        print("\n\033[2mSources:", file=sys.stderr)
        for i, (title, url) in enumerate(web_sources, 1):
            label = (title.strip() or url)
            if url and use_links:
                print(f"  [{i}] {osc8_link(url, label)}", file=sys.stderr)
                print(f"      \033[2m{url}\033[0m\033[2m", file=sys.stderr)
            elif url:
                print(f"  [{i}] {label}\n      {url}", file=sys.stderr)
            else:
                print(f"  [{i}] {label}", file=sys.stderr)
        print("\033[0m", end="", file=sys.stderr)

    # Persist both sides. Store the user's QUESTION plus short notes (attached
    # files, whether web was used) — NOT the full file blob or search text, so
    # future turns don't re-send everything as history.
    stored_q = query
    notes = []
    if file_meta:
        # Label may carry a "  [lines ..]" suffix; keep just the filename part.
        names = [os.path.basename(m[0].split("  [")[0]) for m in file_meta]
        notes.append("attached: " + ", ".join(names))
    if web_status:
        notes.append(f"web: {web_status[0]} ({web_status[1]} results)")
    if notes:
        stored_q = query + "\n[" + " | ".join(notes) + "]"
    session["messages"].append({"role": "user", "content": stored_q, "ts": now_iso()})
    session["messages"].append({"role": "assistant", "content": answer, "ts": now_iso()})
    save_session(session)

    print_metrics(cfg, body, total_latency, est_prompt, file_meta, web_status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
