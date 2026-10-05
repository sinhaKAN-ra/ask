# Awesome-list submissions — drafts

Open a PR against each repo adding the line under the most fitting section.
Match each list's existing entry format exactly (check a few neighboring lines
before committing — formats vary slightly per list). Fill <GITHUB_URL>.

Target lists (highest traffic first):
- agarrharr/awesome-cli-apps        → section "Productivity" or "Development"
- alebcay/awesome-shell             → section "Productivity" / "Terminal"
- sindresorhus/awesome-nodejs       → SKIP (Node only; this is Python)
- Hannibal046/Awesome-LLM           → "Tools" / "LLM Applications"
- learn-anything or terminals lists → optional

---

## Entry (markdown-link style — most lists)

```markdown
- [ask](<GITHUB_URL>) - Stateless terminal AI CLI that searches the web only when the model self-assesses its answer as stale. Any OpenAI-compatible API, file/stdin context, zero idle memory.
```

## Entry (shorter, for terse lists)

```markdown
- [ask](<GITHUB_URL>) - Terminal LLM that self-decides when to search the web. Single file, no deps.
```

## PR description template

```
Adds `ask`, an open-source (MIT) terminal AI CLI.

What makes it list-worthy: unlike other terminal LLM tools that either never
search or always search, `ask` has the model self-assess staleness and only
performs a web search + grounded re-ask when the answer is flagged uncertain.
Single-file, stdlib-only, zero idle footprint, works with any OpenAI-compatible
API (Groq/Gemini/OpenRouter/Ollama).

Repo: <GITHUB_URL>
Added under: <SECTION>
I checked the entry matches the list's existing format and alphabetical order.
```

---

## Also submit to directories (no PR, just a form/submit)

- https://terminaltrove.com/submit/   (terminal tool directory — good fit)
- https://www.libhunt.com/            (auto-indexes GitHub; just needs stars)
- https://pypi.org                    (automatic once published — see runbook)
