# ask

**A lightweight terminal AI for quick questions, file context, and live web search.**

Ask any question from your terminal and get a fast, grounded answer. `ask` points at any OpenAI-compatible API (Groq, Gemini, OpenRouter, Cerebras, or a local Ollama), reads files and piped input as context, and searches when you request it, when the question has freshness cues, or when the model flags uncertainty. No daemon, no background process, zero idle memory.

🔗 **Homepage:** [ask.aolbeam.com](https://ask.aolbeam.com) · **Package:** `aolbeam-ask` · **Command:** `ask`

```console
$ ask "explain git rebase vs merge in 3 lines"
Git merge joins two histories with a new merge commit, preserving both branches.
Git rebase replays your commits onto another branch for a linear history.
Use merge to keep context; use rebase for a clean, linear log.

$ ask -w "what changed in the latest Python release? Cite sources."
[ask] searching the web (brave) — forced (-w)
...answer using retrieved sources [1]...

Sources:
  [1] Python release notes — https://www.python.org/downloads/
# Illustrative output; actual answers and sources depend on the search results.
```

---

## Why I built this

I wanted **lightweight LLM access from the terminal** — the place I already live as a developer.

Every existing option made me stop and open something heavy first: a browser tab for ChatGPT/Claude, a desktop app idling in the background, an Electron client eating hundreds of MB of RAM, or an IDE assistant that only works inside the editor. Just to ask one quick question — *"what's the flag for this?"*, *"explain this stack trace"* — I had to break focus, launch a resource-hungry tool, and leave it running.

That felt backwards. A quick question should cost a quick command, not a running process.

So `ask` is built on one rule: **spawn, answer, exit.** Each call starts a process, prints the answer, and exits — **zero idle memory, no daemon, no background app.** It's a single stdlib-only Python file. Nothing stays resident between questions. You get the answer in your terminal, in your flow, and your machine goes right back to doing nothing.

---

## Search when you need it

Stable questions usually take one model call. Freshness cues (such as “latest”)
and explicit `-w` requests search **before** the model call. Other questions use a
model self-assessment; if it flags uncertainty, ask retrieves search results and
makes a second, grounded request.

This is a heuristic, not a guarantee of accuracy. Use `-w` when freshness matters,
and verify important claims against the source URLs. An explicit web search that
fails returns exit code 4 rather than silently substituting model knowledge.
Automatic search failure is clearly reported and can fall back to a model answer.

---

## Features

- 🧠 **Conditional web fallback** — searches only when the model self-assesses staleness, or when your question contains freshness cues (`latest`, `current`, `2026`, `today`, `release`…), or when you force it with `-w`.
- 🔌 **Any OpenAI-compatible API** — Groq, Gemini (OpenAI-compat endpoint), OpenRouter, Cerebras, local Ollama. Just set `base_url` + `model`.
- 🔎 **Pluggable search** — keyless **DuckDuckGo** by default (zero setup); drop in **Tavily**, **Serper**, or **Brave** for higher-quality results with your own key. Use `ask --setup-search brave` or `tavily` to configure it.
- 📄 **File context** — `ask -f app.py "why is this slow?"`, repeatable, with glob support.
- ✂️ **Line selection** — `ask -f big.py:50-120 "..."` sends only the lines you want, to keep the context focused.
- 📥 **Stdin piping** — `cat error.log | ask "what broke?"` or `ls -la | ask "which is largest?"`.
- 💬 **Conversation memory** — sessions saved as readable `.txt` + structured `.json`; resume, list, rename, switch.
- 🎨 **Terminal-native formatting** — output dynamically wraps to your terminal width, with rich ANSI rendering for headings, code blocks, tables, lists, and blockquotes.
- 🎛️ **Controlled output format** — choose `--format rich` (ANSI styled), `--format plain` (clean text, no colors), or `--format md` (raw Markdown for piping). Set defaults in config.
- 🪟 **Cross-platform** — runs seamlessly on **macOS**, **Linux**, and **Windows** (Command Prompt, PowerShell, Windows Terminal, WSL, Git Bash) with auto-enabled VT processing and UTF-8 encoding.
- 📊 **Visual metrics** — per-answer token breakdown, latency, model info, and visual context-window bar chart `[████░░░░░░░░]` with approaching-limit warnings.
- 🔗 **Cited sources** — web answers print a numbered Sources block with clickable links (OSC 8, in terminals that support it).
- 🪶 **Zero idle footprint** — no server or daemon; each call answers and exits. Response time depends on the model and network.
- 🩺 **Setup diagnostics** — `--doctor` checks local key presence; `--doctor --check-web` tests the search connection without calling a model.
- 🕶️ **Standalone requests** — `--no-history` skips reading and saving conversations.
- 🧰 **Script-friendly** — strict flag validation, useful exit codes, `--quiet`, and source URLs preserved in redirected output.

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

### One-line script install (macOS / Linux — bash / zsh)
```bash
curl -fsSL https://raw.githubusercontent.com/sinhaKAN-ra/ask/main/install.sh | bash
```

### One-line script install (Windows — PowerShell)
```powershell
irm https://raw.githubusercontent.com/sinhaKAN-ra/ask/main/install.ps1 | iex
```

### Run without installing
```bash
uvx aolbeam-ask "your question"
```

---

## Setup

`ask` needs one thing: an API key for an OpenAI-compatible provider. The default is **Groq** (free key, very fast).

> **You bring your own keys.** `aolbeam-ask` ships with **no API keys of any
> kind** — not for the LLM provider, not for web search. You create your own
> free key(s) and supply them via an environment variable or your local
> `~/.ask-cli/config.json`. Keys live only on your machine; nothing is sent
> anywhere except directly to the provider you configured.


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

### Add web access: Brave or Tavily

Web access here means **search results**, not browser control. You still need your
model key (e.g. `GROQ_API_KEY`) to generate answers. Choose **one** search provider.
Never paste a real key into a Git commit or issue.

> The setup, doctor, provider-override, and no-history flags are new source features.
> Until the updated package is published, install from this updated checkout with
> `pipx install --force .`. On older releases, use the manual config below.

**Brave Search — bash / zsh (macOS, Linux, WSL)**

1. Open the [Brave API dashboard](https://api-dashboard.search.brave.com), choose
   a plan, and create an API key. A Brave browser installation is not an API key.
2. Replace the placeholder and run:

```bash
export BRAVE_API_KEY="YOUR_BRAVE_KEY"
ask --setup-search brave
ask --doctor
ask --doctor --check-web
ask -w "What changed in the latest Python release? Cite sources."
```

**Tavily — bash / zsh**

1. Create an account and a key in the [Tavily dashboard](https://app.tavily.com).
2. Replace the placeholder and run:

```bash
export TAVILY_API_KEY="YOUR_TAVILY_KEY"
ask --setup-search tavily
ask --doctor
ask --doctor --check-web
ask -w "What changed in the latest Python release? Cite sources."
```

**Windows PowerShell** — connect the model, then choose Brave:

```powershell
$env:GROQ_API_KEY="YOUR_GROQ_KEY"
$env:BRAVE_API_KEY="YOUR_BRAVE_KEY"
ask --setup-search brave
ask --doctor --check-web
ask -w "What changed in the latest Python release? Cite sources."
```

Or use Tavily in PowerShell:

```powershell
$env:TAVILY_API_KEY="YOUR_TAVILY_KEY"
ask --setup-search tavily
ask --doctor --check-web
ask -w "What changed in the latest Python release? Cite sources."
```

The local doctor checks key **presence**, not validity. `--check-web` sends a test
search and reports the result count; it may consume search credits. A successful
`-w` answer includes numbered source URLs. Provider plans and limits vary.

To persist environment variables, add the export lines to `~/.zshrc` or
`~/.bashrc`, or add User variables in Windows Environment Variables settings.
Reopen your terminal afterward. Keep files containing keys private.

**Manual config (also works with older releases):** run `ask --config` to create
`~/.ask-cli/config.json`, then merge these fields with your existing model settings:

```json
{
  "search_provider": "brave",
  "search_api_key": "",
  "search_api_key_env": "BRAVE_API_KEY",
  "web_fallback": true
}
```

For Tavily, use `"tavily"` and `"TAVILY_API_KEY"`. Set the matching variable before
running `ask -w "latest Python release; cite sources"`. Older versions may expose
saved keys in `--config` output; keep it private.

**Other options:** `ask --setup-search duckduckgo` needs no search key;
`ask --setup-search serper` uses `SERPER_API_KEY` from [Serper](https://serper.dev).
DuckDuckGo's HTML endpoint can rate-limit or return no results.

`--setup-search` persists the provider and its environment-variable name, enables
web fallback, and clears any inline search key from the previous provider. It
preserves model settings. Existing custom `search_api_key_env` and inline search
keys still work; configured keys take precedence over provider-specific defaults.
Use `--search-provider tavily` for a single request; when switching providers,
it uses the matching environment variable rather than reusing another provider's key.

**Troubleshooting:** `ask` not found → run `pipx ensurepath` and reopen the shell.
Missing key → check the variable in the same terminal. HTTP 401/403 → verify key
and plan in the provider dashboard. HTTP 429 → check quota or retry later. Unknown
flag → install the updated source or use manual config.

Provider API references: [Brave quickstart](https://api-dashboard.search.brave.com/documentation/quickstart)
and [Tavily Search](https://docs.tavily.com/documentation/api-reference/endpoint/search).

---

## Usage

```bash
# Basic
ask "write a bash one-liner to find files over 100MB"

# Web search (auto when the model flags staleness, or forced)
ask "who is the current CEO of OpenAI?"     # auto-searches
ask -w "best Python HTTP library"           # force a search
ask --no-web "explain recursion"            # never search this one
ask --search-provider tavily -w "latest Python release" # one-request override
ask --no-history "explain this command"     # no prior context or saved transcript
ask --quiet "explain DNS"                   # hide metrics and routine progress

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

# Terminal output formatting
ask --format rich "explain DNS"        # styled ANSI (bold headers, code borders, tables)
ask --format plain "explain DNS"       # clean text, no ANSI codes (great for dumb terminals)
ask --format md "write a Dockerfile"   # raw Markdown (pipe to files/editors)
ask "generate a README" > README.md    # auto-detect defaults to md when piped!

# Conversations
ask -n "fresh topic"      # start a new conversation
ask --list                # list saved conversations
ask --select 2            # resume conversation #2
ask --title "A good name" # rename the active conversation
ask --info                # session stats + token usage + terminal width
ask --config              # show config with secrets redacted
ask --doctor              # check local configuration
ask --doctor --check-web  # also send a real search request
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
| `search_api_key` / `search_api_key_env` | `""` / `SEARCH_API_KEY` | Configured key first; also recognizes BRAVE_API_KEY, TAVILY_API_KEY, SERPER_API_KEY for the selected provider |
| `search_results` | `5` | How many results to fetch and feed the model |
| `web_on_freshness_cues` | `true` | Also search when the question has words like "latest"/"2026" |
| `history_turns` | `12` | How many prior exchanges to send as context |
| `max_file_chars` | `48000` | Safety cap per attached file (truncates with a warning) |
| `output_format` | `auto` | `auto` (rich in TTY, md when piped) \| `rich` \| `plain` \| `md` |
| `show_metrics` | `true` | Print the per-answer metrics footer |
| `osc8_links` | `true` | Clickable terminal hyperlinks (OSC 8) |

**Switching provider** (example — local Ollama):
```json
{ "provider": "ollama", "base_url": "http://localhost:11434/v1", "model": "llama3.1", "api_key": "ollama" }
```

---

## How it works (architecture)

```
your question (+ files, stdin, optional history)
  ├─ -w / freshness cue → search → one grounded model call → answer + source URLs
  └─ stable question → model answer + hidden self-check
       ├─ no search needed → answer
       └─ uncertain → search → grounded model call → answer + source URLs
```

Everything happens inside a single process invocation. There is no server to start, no port to bind, nothing resident between calls — the design goal is **zero idle memory**. Web search, when it fires, runs only during that one call.

### Data and automation

Questions, attached files, stdin, and recent history go to your configured model
provider. Web search sends the question to the selected search provider. Sessions
are stored under `~/.ask-cli/sessions`; `--no-history` skips reading and saving them.
This does not prevent network requests. `ask` does not execute generated commands
or edit attached files.

Answers and source URLs go to stdout; progress, errors, and metrics go to stderr.
Exit codes: `0` success, `1` session/usage error, `2` arguments or configuration,
`3` model failure, `4` forced search or live search check failure.

---

## Contributing

PRs welcome. The whole tool is one readable file: [`src/aolbeam_ask/ask.py`](src/aolbeam_ask/ask.py) (stdlib only, no dependencies).

```bash
git clone https://github.com/sinhaKAN-ra/ask
cd ask
pip install -e .
python -m unittest discover -s tests -v
ask "it works"
```

---

## License

[MIT](LICENSE) © Aolbeam
