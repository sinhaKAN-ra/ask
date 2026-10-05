# Publish runbook — the steps YOU run (account-bound)

The repo is staged at `~/aolbeam-ask`. Everything below needs YOUR accounts/
tokens, so run these yourself. Order matters: GitHub → PyPI → Homebrew → posts.

---

## 0. One-time safety: rotate the exposed Groq key

Your old key was visible in chat. Regenerate it at
https://console.groq.com/keys , then update your shell:
```bash
# edit ~/.zshrc, replace the GROQ_API_KEY value with the new key, then:
source ~/.zshrc
```
(The repo contains NO keys — verified. This is just hygiene for the exposed one.)

---

## 1. Create the GitHub repo and push

```bash
cd ~/aolbeam-ask
git init -b main
git add .
git status           # CONFIRM: no config.json, no sessions/, no keys listed
git commit -m "Initial release: ask — stateless terminal AI with conditional web search"
```
Create an empty repo named `ask` under the `aolbeam` org (or your user) on
github.com — do NOT let GitHub add a README/License (we have them). Then:
```bash
git remote add origin https://github.com/sinhaKAN-ra/ask.git
git push -u origin main
```
On the repo page: add description, set homepage to https://ask.aolbeam.com ,
and add Topics: `cli llm ai terminal assistant groq web-search ollama`.

---

## 2. Publish to PyPI

### 2a. What credentials you need (and what the package does NOT ship)

Publishing requires **your own PyPI account + an API token**. These are
*maintainer* credentials — they let you upload to the index. They are
completely separate from the runtime API keys the tool uses.

> **The package ships NO API keys.** `aolbeam-ask` has zero embedded
> credentials. Every end user supplies their *own* provider key (Groq,
> Tavily, etc.) via an environment variable or their local
> `~/.ask-cli/config.json` — see the README "Setup" section. Nothing you do
> here puts a key into the published artifact; `twine check` + the secret
> scan already confirmed the tree is clean.

You need exactly one credential to publish: a **PyPI API token**.

1. Create/verify a PyPI account: https://pypi.org/account/register
2. Enable 2FA (PyPI requires it to upload).
3. Mint a token: https://pypi.org/manage/account/token/ → "Add API token" →
   scope **"Entire account"** for the first upload (narrow it to the
   `aolbeam-ask` project afterward). Copy it now — it starts with `pypi-`
   and is shown only once.
4. (Recommended) Do the same on https://test.pypi.org for a dry run — it has
   a **separate** account and a **separate** token.

### 2b. Install the build + upload tooling

```bash
python3 -m pip install --upgrade build twine
```
- `build` → produces the wheel (`.whl`) and source dist (`.tar.gz`).
- `twine` → validates and uploads them to PyPI.

### 2c. Build and validate

```bash
cd ~/aolbeam-ask
rm -rf dist/ build/ *.egg-info src/*.egg-info
python3 -m build                      # creates dist/*.whl and *.tar.gz
python3 -m twine check dist/*         # must say PASSED for both files
```
Smoke-test the built wheel in a throwaway venv before uploading:
```bash
python3 -m venv /tmp/ask-test
/tmp/ask-test/bin/pip install dist/aolbeam_ask-0.1.0-py3-none-any.whl
/tmp/ask-test/bin/ask --config        # confirms the `ask` command installed
rm -rf /tmp/ask-test
```

### 2d. (Recommended) dry run on TestPyPI first

```bash
python3 -m twine upload --repository testpypi dist/*
# username: __token__
# password: <your TestPyPI token, the whole pypi-... string>

# confirm it installs from TestPyPI:
python3 -m venv /tmp/ask-live && /tmp/ask-live/bin/pip install \
  --index-url https://test.pypi.org/simple/ aolbeam-ask
/tmp/ask-live/bin/ask --config && rm -rf /tmp/ask-live
```

### 2e. Upload to real PyPI

```bash
python3 -m twine upload dist/*
# username: __token__
# password: <your real PyPI token>
```
Live at https://pypi.org/project/aolbeam-ask . Verify:
```bash
pipx install aolbeam-ask && ask --config
```

> **Version numbers are permanent.** You cannot re-upload `0.1.0` once it is
> published (even after deleting it). To ship a fix, bump the `version` in
> `pyproject.toml` to `0.1.1` and rebuild.

### 2f. Store the token so you don't paste it every time (`~/.pypirc`)

`twine` reads credentials from `~/.pypirc`. With this file present you can run
`twine upload dist/*` with no username/password prompt. Put your real tokens
in place of the placeholders and keep the file private (`chmod 600`):
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-REPLACE_WITH_YOUR_REAL_PYPI_TOKEN

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-REPLACE_WITH_YOUR_REAL_TESTPYPI_TOKEN
```
A template has been created at `~/.pypirc` for you — edit the two
`REPLACE_WITH_...` lines with your actual tokens. The `username` stays the
literal string `__token__` for API-token auth.

---

## 3. Homebrew tap

```bash
# After the PyPI release exists, get the real sdist URL + sha256:
pip download aolbeam-ask --no-deps --no-binary :all: -d /tmp/askdl
shasum -a 256 /tmp/askdl/aolbeam_ask-0.1.0.tar.gz
```
- Create a repo `homebrew-tap` under `aolbeam` on GitHub.
- Put `Formula/ask.rb` (from this repo) in it, with the real `url` + `sha256`
  pasted in place of the two TODO placeholders.
- Push it. Users then install with:
```bash
brew install sinhaKAN-ra/tap/ask
```
Test locally first: `brew install --build-from-source ./Formula/ask.rb`

---

## 4. install.sh (curl path) — already works once step 1 is pushed

`curl -fsSL https://raw.githubusercontent.com/sinhaKAN-ra/ask/main/install.sh | bash`
No action needed beyond the push; just verify it on a clean machine/path.

---

## 5. Discoverability — posts & PRs (manual, your identity)

Drafts are in `docs/launch-posts.md` and `docs/awesome-list-submissions.md`.
Fill `<GITHUB_URL>` = https://github.com/sinhaKAN-ra/ask , then:
1. Open awesome-list PRs (awesome-cli-apps, awesome-shell, Awesome-LLM).
2. Submit to terminaltrove.com.
3. Post Show HN (Tue–Thu morning US time lands best), then r/commandline,
   r/LocalLLaMA, and your LinkedIn.

Do these spaced out over a few days, not all at once — a repo with a handful of
stars converts an HN visit far better than a zero-star one, so seed with the
awesome-list PRs + a couple of friends first.

---

## Checklist

- [ ] Rotated the exposed Groq key
- [ ] GitHub repo public, topics + homepage set
- [ ] `git status` showed no secrets before first commit
- [ ] PyPI: `pipx install aolbeam-ask` works, `ask` on PATH
- [ ] Homebrew tap formula has real url+sha256
- [ ] install.sh verified
- [ ] awesome-list PRs opened
- [ ] Launch posts sent (manually)
