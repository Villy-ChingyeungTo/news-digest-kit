# Changelog

## 1.1.0

- Use the absolute Windows PowerShell executable path.
- Discover and validate Python interpreters; skip Microsoft Store aliases and support custom paths.
- Validate Gmail app password format locally; remove formatting spaces without showing the password.
- Check network connectivity before asking for credentials.
- Add configurable HTTP CONNECT SMTP and HTTP RSS proxy support without changing global settings.
- Use ASCII-only Message-ID domains to support Chinese Windows computer names.
- Serialize MIME messages before connecting; preserve non-English subjects, content and attachments.
- Replace console tracebacks with actionable errors while keeping local diagnostic logs.
- Separate safe pre-transmission retries from uncertain delivery that requires reconciliation.
- Add resume, preview, connection-check, status and uninstall entry points.
- Preserve English-default, three-language HTML readers and section filtering.
- Keep account configuration, credentials and real news/history out of distribution packages.
- Document setup, scheduling constraints, public RSS limitations and recovery in English.
