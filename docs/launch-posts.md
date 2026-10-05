# Launch posts — drafts (send manually)

> You send these yourself. No automation (ToS/account safety). Fill the GitHub
> URL once the repo is live. The LinkedIn one uses the narrated-beat style.

---

## LinkedIn (narrated beats)

I built a terminal AI tool. The interesting part isn't that it answers questions — it's *when it decides to shut up and go look things up*.

The problem I kept hitting:
- Terminal LLM tools either never touch the web (fast, but confidently wrong on anything recent)
- or they search on every single query (accurate, but slow and heavy for "explain recursion")

Nobody did the obvious middle thing: search *only when the model itself knows it's out of date*.

So that's what I made it do.
- The model answers normally.
- It ends its reply with a hidden line: NEEDS_WEB: yes / no — and a reason.
- The tool reads that line, strips it from what you see, and only then goes to the web — fetches sources, re-asks the model grounded in them, cites them.

"explain git rebase" → instant, no search.
"current CEO of X" → the model flags itself stale → it searches → grounded answer with sources.

Other things I cared about:
- Zero idle memory. No daemon. It spawns, runs ~1s, prints, dies. Nothing resident.
- Reads files (`ask -f app.py "why slow?"`), even specific line ranges for big files.
- Pipes: `cat error.log | ask "what broke?"`
- Works with any OpenAI-compatible API — Groq, Gemini, OpenRouter, local Ollama.

It's open source, MIT, one readable Python file, zero dependencies.

Install: pipx install aolbeam-ask (command is `ask`)
Repo: <GITHUB_URL>
Docs: https://ask.aolbeam.com

Would love feedback from anyone who lives in the terminal.

#opensource #cli #llm #developertools

---

## Show HN

**Title:** Show HN: ask – a terminal LLM that searches the web only when it knows it's stale

**Body:**
I wanted a terminal AI that didn't make me choose between "fast but outdated" and "always searches and slow". So `ask` makes the model self-assess: it answers, then appends a machine-readable `NEEDS_WEB: yes/no` line with a reason. The tool reads that, strips it, and only runs a web search + grounded re-ask when the model flagged its own answer as stale or uncertain. Freshness words in your question ("latest", "2026") also trigger it; `-w` forces it.

It's deliberately a single file, stdlib-only, zero dependencies, and has zero idle footprint — no daemon, each call just spawns and exits. Works with any OpenAI-compatible API (Groq/Gemini/OpenRouter/Ollama). Keyless DuckDuckGo search by default; Tavily/Serper/Brave if you want better results.

Also does file context with line ranges (`ask -f big.py:50-120 "..."`), stdin piping, conversation memory, and per-answer token/latency metrics.

Repo: <GITHUB_URL>  ·  MIT.

Happy to answer questions about the self-assessment approach — curious if people think model self-reporting of staleness is reliable enough (it's been good in practice, with freshness-cue + `-w` as backstops).

---

## r/commandline

**Title:** I made `ask` — a terminal AI that only hits the web when the model admits it's out of date

**Body:**
Most terminal LLM CLIs either never search or always search. `ask` does the middle: the model self-assesses staleness (appends a hidden `NEEDS_WEB:` flag), and the tool only searches + re-grounds when it flags itself. Single file, stdlib only, zero idle memory (no daemon). Any OpenAI-compatible API. File context with line ranges, stdin piping, cited sources.

`pipx install aolbeam-ask` → command is `ask`.
Repo: <GITHUB_URL>  (MIT)

---

## r/LocalLLaMA (angle: works great with local Ollama)

**Title:** `ask` — stateless terminal CLI, points at local Ollama, self-decides when to augment with web search

**Body:**
Set `base_url` to your Ollama endpoint and `ask` runs fully local — except it'll self-assess when its answer is stale and (optionally) pull web results to ground a re-ask. Keyless DuckDuckGo or bring a Tavily key. One file, no deps, nothing resident between calls. Repo: <GITHUB_URL>
