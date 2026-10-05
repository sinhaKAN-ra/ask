# Security Policy

## Reporting a Vulnerability

If you discover a security issue — for example, a way `ask` could leak an API
key, execute untrusted input, or expose session data — please report it
**privately**:

**Email: nomore.report@gmail.com**

Do **not** open a public GitHub issue for security problems.

Please include:
- A description of the issue and its impact.
- Steps to reproduce.
- Any suggested fix, if you have one.

You'll get an acknowledgment as soon as possible, and we'll work with you on a
fix and coordinated disclosure.

## Scope

`ask` is a thin, stateless CLI over an HTTP API. The most relevant security
considerations are:
- **API keys** — stored in `~/.ask-cli/config.json` or environment variables.
  The tool never transmits them anywhere except the configured provider's
  endpoint. Never commit your `config.json`.
- **File / stdin context** — content you pass with `-f` or a pipe is sent to the
  configured LLM provider. Don't pass secrets you don't want sent to that API.
- **Web search** — your query is sent to the configured search provider when a
  web search triggers.

## Supported Versions

The latest released version on PyPI receives fixes. This is an early-stage tool;
please stay current.
