# ask

**A lightweight, stateless terminal AI CLI that knows when it needs to search the web.**

Ask any question from your terminal and get a fast, grounded answer. `ask` points at any OpenAI-compatible API (Groq, Gemini, OpenRouter, Cerebras, or a local Ollama), reads files and piped input as context, and — this is the part most tools get wrong — **only searches the web when the model itself admits its answer might be stale.** No daemon, no background process, zero idle memory.

🔗 **Homepage:** [ask.aolbeam.com](https://ask.aolbeam.com) · **Package:** `aolbeam-ask` · **Command:** `ask`

```console
$ ask "explain git rebase vs merge in 3 lines"
Git merge joins two histories with a new merge commit, preserving both branches.
Git rebase replays your commits onto another branch for a linear history.
Use merge to keep context; use rebase for a clean, linear log.

$ ask "latest stable version of Rust"
[ask] searching the web (tavily) — model self-assessed: version may have changed since training
Rust 1.98.1 [1]

Sources:
  [1] Announcing Rust 1.98.1 | Rust Blog   https://blog.rust-lang.org/...
```

---

## Why it's different

Most terminal AI tools fall into one of two camps:

- **Never search** (`llm`, `qqqa`, `fastask`) — fast, but confidently wrong on anything after the model's training cutoff.
- **Always search** (Perplexity-style CLIs) — accurate on fresh facts, but slow and heavy on every single query.

`ask` sits in the empty middle: **the model self-assesses whether its answer is stale or uncertain, and the tool reads that assessment and searches only when needed.** You get instant answers for stable questions ("explain recursion") and grounded, cited answers for fresh ones ("current CEO of X") — automatically, no flags required.

It does this with a simple, reliable mechanism: the system prompt asks the model to end its answer with a machine-readable line (`NEEDS_WEB: yes — reason` / `NEEDS_WEB: no`). The tool parses that line, strips it from your view, and triggers a web search + grounded re-ask when the model flagged itself. No fragile phrase-matching on prose.

---

## Features

- 🧠 **Conditional web fallback** — searches only when the model self-assesses staleness, or when your question contains freshness cues (`latest`, `current`, `2026`, `today`, `release`…), or when you force it with `-w`.
- 🔌 **Any OpenAI-compatible API** — Groq, Gemini (OpenAI-compat endpoint), OpenRouter, Cerebras, local Ollama. Just set `base_url` + `model`.
- 🔎 **Pluggable search** — keyless **DuckDuckGo** by default (zero setup); drop in **Tavily**, **Serper**, or **Brave** for higher-quality results with your own key.
- 📄 **File context** — `ask -f app.py "why is this slow?"`, repeatable, with glob support.
- ✂️ **Line selection** — `ask -f big.py:50-120 "..."` sends only the lines you want, so large files never overload the context window.
- 📥 **Stdin piping** — `cat error.log | ask "what broke?"` or `ls -la | ask "which is largest?"`.
- 💬 **Conversation memory** — sessions saved as readable `.txt` + structured `.json`; resume, list, rename, switch.
- 📊 **Per-answer metrics** — tokens, context-window usage %, latency, model, with a warning as you approach the limit.
- 🔗 **Cited sources** — web answers print a numbered Sources block with clickable links (OSC 8, in terminals that support it).
- 🪶 **Zero idle footprint** — no server, no daemon. Each call spawns, runs ~1–2s, prints, and exits. Nothing stays resident.

---

## Install

The published package is **`aolbeam-ask`**; it installs a command named **`ask`**.

### pipx (recommended — isolated, always on PATH)
```bash
pipx install aolbeam-ask
```

### pip
```bash
pip install aolbeam-ask
```

### Homebrew (macOS / Linux)
```bash
brew install sinhaKAN-ra/tap/ask
```

### From GitHub (no PyPI needed)
```bash
pipx install git+https://github.com/sinhaKAN-ra/ask
```

### One-line script install (single-file, no packaging)
```bash
curl -fsSL https://raw.githubusercontent.com/sinhaKAN-ra/ask/main/install.sh | bash
```

### Run without installing
```bash
uvx aolbeam-ask "your question"
```

---

## Setup

`ask` needs one thing: an API key for an OpenAI-compatible provider. The default is **Groq** (free key, very fast).

1. Get a free key at [console.groq.com/keys](https://console.groq.com/keys).
2. Set it as an environment variable (recommended — keeps the secret out of any file):
   ```bash
   export GROQ_API_KEY="gsk_your_key_here"
   # add that line to ~/.zshrc or ~/.bashrc to make it permanent
   ```
3. Run it:
   ```bash
   ask "hello, are you working?"
   ```

On first run, `ask` creates `~/.ask-cli/config.json`. Edit it to switch provider/model or tune behavior (see [Configuration](#configuration)).

**Optional — better web search:** DuckDuckGo works with no key. For more reliable results, get a free [Tavily](https://app.tavily.com) key, set `search_provider` to `tavily` in the config, and `export SEARCH_API_KEY="tvly-..."`.

---

## Usage

```bash
# Basic
ask "write a bash one-liner to find files over 100MB"

# Web search (auto when the model flags staleness, or forced)
ask "who is the current CEO of OpenAI?"     # auto-searches
ask -w "best Python HTTP library"           # force a search
ask --no-web "explain recursion"            # never search this one

# File context
ask -f app.py "why is this slow?"            # one file
ask -f main.py -f utils.py "do these clash?" # multiple files
ask -f "src/*.py" "summarize this module"    # globs
ask -f big.py:50-120 "explain this function" # lines 50–120 only
ask -f log.txt:-100 "what's at the top?"     # first 100 lines
ask -f app.py:200- "review from here down"   # line 200 to end
ask -f config.py:42 "what does this do?"     # single line

# Pipe anything in
cat error.log | ask "what caused this?"
git diff | ask "write a commit message"

# Conversations
ask -n "fresh topic"      # start a new conversation
ask --list                # list saved conversations
ask --select 2            # resume conversation #2
ask --title "A good name" # rename the active conversation
ask --info                # session stats + token usage
ask --config              # show resolved config and where it lives
ask --clear               # archive current and start clean
```

---

## Configuration

Config lives at `~/.ask-cli/config.json` (created on first run). See [`config.json.example`](config.json.example) for an annotated template.

| Key | Default | Description |
|---|---|---|
| `provider` / `base_url` / `model` | `groq` / Groq URL / llama-3.3-70b | OpenAI-compatible endpoint + model |
| `api_key` / `api_key_env` | `""` / `GROQ_API_KEY` | Key in file, or name of env var holding it |
| `system_prompt` | concise assistant | Base instruction prepended to every chat |
| `max_tokens` / `temperature` | `1024` / `0.4` | Generation controls |
| `web_fallback` | `true` | Master switch for conditional web search |
| `search_provider` | `duckduckgo` | `duckduckgo` (keyless) \| `tavily` \| `serper` \| `brave` |
| `search_api_key` / `search_api_key_env` | `""` / `SEARCH_API_KEY` | Key for the chosen provider |
| `search_results` | `5` | How many results to fetch and feed the model |
| `web_on_freshness_cues` | `true` | Also search when the question has words like "latest"/"2026" |
| `history_turns` | `12` | How many prior exchanges to send as context |
| `max_file_chars` | `48000` | Safety cap per attached file (truncates with a warning) |
| `show_metrics` | `true` | Print the per-answer metrics footer |

**Switching provider** (example — local Ollama):
```json
{ "provider": "ollama", "base_url": "http://localhost:11434/v1", "model": "llama3.1", "api_key": "ollama" }
```

---

## How it works (architecture)

```
your question ─► build prompt (+ files, +stdin, +history, +date)
              ─► call the LLM once
              ─► read the NEEDS_WEB line the model appended
                   ├─ no  ─► strip the line, print the answer
                   └─ yes ─► web search ─► re-ask grounded in results ─► print + Sources
```

Everything happens inside a single process invocation. There is no server to start, no port to bind, nothing resident between calls — the design goal is **zero idle memory**. Web search, when it fires, runs only during that one call.

---

## Contributing

PRs welcome. The whole tool is one readable file: [`src/aolbeam_ask/ask.py`](src/aolbeam_ask/ask.py) (stdlib only, no dependencies).

```bash
git clone https://github.com/sinhaKAN-ra/ask
cd ask
pip install -e .
ask "it works"
```

---

## License

[MIT](LICENSE) © Aolbeam
