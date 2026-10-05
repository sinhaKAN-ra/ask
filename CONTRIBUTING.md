# Contributing to ask

Thanks for your interest in improving `ask`! This is a small, focused tool and
contributions of all sizes are welcome — bug reports, docs, and code.

## Ground rules

- Be respectful. See the [Code of Conduct](CODE_OF_CONDUCT.md).
- Keep the tool **single-file, stdlib-only, zero idle footprint.** This is the
  core design constraint: no daemon, no resident process, and ideally **no third-party
  runtime dependencies.** A PR that adds a background process or a heavy dependency
  will likely be declined — propose it in an issue first.
- Prefer small, focused PRs over large sweeping ones.

## Reporting a bug

Open an issue using the **Bug report** template. Include:
- The command you ran and the full output (redact any API keys!).
- Your OS, terminal, and `python3 --version`.
- Your provider/model (from `ask --config`, with keys removed).

## Suggesting a feature

Open an issue using the **Feature request** template. Explain the use case, and
note whether it can be done without a daemon or new dependency (see Ground rules).

## Development setup

The entire tool is one readable file: `src/aolbeam_ask/ask.py`.

```bash
git clone https://github.com/sinhaKAN-ra/ask
cd ask
pip install -e .          # installs the `ask` command pointing at your checkout
ask "it works"
```

To run without installing:
```bash
python3 -m aolbeam_ask "your question"      # from the repo root, with src/ on PYTHONPATH
# or directly:
python3 src/aolbeam_ask/ask.py "your question"
```

Set a key first:
```bash
export GROQ_API_KEY="gsk_..."   # free at https://console.groq.com/keys
```

## Testing your change

There is no heavy test suite — this is a thin CLI over an HTTP API. Before
opening a PR, manually exercise the paths your change touches:

```bash
ask "explain recursion"                   # basic, no web
ask -w "latest python version"            # forced web search
ask -f src/aolbeam_ask/ask.py:1-40 "..."  # file context + line range
echo "hi" | ask "what did I say?"         # stdin
ask --config                              # config loads
```

If you add a new flag or behavior, update the module docstring in `ask.py`
**and** the README usage table.

## Pull request process

1. Fork the repo and create a branch: `git checkout -b feat/short-description`.
2. Make your change. Keep the style consistent with the surrounding code.
3. Update docs (README + the `ask.py` docstring) if behavior changed.
4. Open a PR against `main` with a clear description of what and why.
5. Confirm no secrets are in your diff.

## Security

Found a security issue (e.g. a way the tool could leak a key)? **Do not open a
public issue.** Email **nomore.report@gmail.com** directly. See
[SECURITY.md](SECURITY.md).

## Questions

Open a [Discussion](https://github.com/sinhaKAN-ra/ask/discussions) or email
**nomore.report@gmail.com**.
