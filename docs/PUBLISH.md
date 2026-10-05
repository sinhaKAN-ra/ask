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

```bash
cd ~/aolbeam-ask
python3 -m pip install --upgrade build twine
python3 -m build                      # creates dist/*.whl and *.tar.gz
python3 -m twine check dist/*         # sanity check metadata
```
Get a token at https://pypi.org/manage/account/token/ (scope: entire account
for the first upload). Then:
```bash
python3 -m twine upload dist/*
# username: __token__
# password: pypi-<your-token>
```
Verify: `pipx install aolbeam-ask && ask --config`

> Tip: test on TestPyPI first with
> `twine upload --repository testpypi dist/*` if you want a dry run.

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
