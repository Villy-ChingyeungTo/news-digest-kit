---
name: news-digest-kit
description: Configure and maintain a shareable Windows RSS news digest with scheduled HTML email delivery, source provenance, deduplication, and overnight catch-up. Use for personal headline subscriptions and reusable email digest setup.
---

# News digest kit

This folder is both an executable Python 3.10+ application and a Codex skill. Read [README.md](README.md) for setup, limitations, and recovery commands. No Python packages required.

- Ask for recipient, sender, time zone, times, and source scope only when missing. Recipients are user-configured; never copy the original owner's settings into a shared kit.
- Start from `config.example.json`. `setup.ps1` stores an SMTP application password with Windows DPAPI via Export-Clixml. Have the user enter it locally; do not ask for it in chat. The encrypted credential is only usable by that Windows account on that machine.
- Default the interface and outgoing email to English. Browser previews and full HTML attachments support en, zh-Hans, and zh-Hant via an offline language selector, plus filtering by original RSS section; email uses the config `language` field. Keep original news titles and source section names unchanged. Never embed the browser selector JavaScript into outgoing email.
- Run `digest.py preview` before activation. Report actual source status and article counts. RSS channel names are provenance, not guaranteed article-page taxonomy. Preserve original titles and links. Never guess a section from keywords. Do not claim complete Bloomberg coverage.
- Scheduler uses Windows Task Scheduler, not Codex automation. `setup.ps1` checks transport before requesting credentials and tests SMTP before enabling scheduling. Gmail credentials require exactly 16 ASCII letters after whitespace removal. The resume entry point reuses the locally encrypted credential. Authorization for a personal subscription does not authorize sending to other people.
- An `ok` feed with articles is necessary, but not proof of comprehensive coverage. Keep unavailable sections visible; do not silently remove failures. No access-barrier bypasses.
- `sections: []` means all sources; selected channel names restrict the delivery set before marking sent. Browser filters only change the view. Each email attaches full interactive HTML; keep its message body script-free with section anchor links.
- Preserve `private/state.sqlite3`: sent URLs prevent repeats. SMTP acknowledgement failures leave a `sending` batch, which pauses delivery until inbox/Sent-mail verification. Use `resolve` only after checking that evidence; `retry` may duplicate mail if a previous SMTP transmission actually succeeded.
- For distribution, include only code, this skill, user guide, example config, runtime/setup helpers, ui.py, and synthetic sample preview. Exclude `config.json`, `private/`, real previews, logs, credentials, recipient addresses, and collected news. ZIP packaging must use an explicit allowlist.
- Validate with `python -m unittest discover -s tests`, the skill-creator validator if available, and a live RSS probe. Browser preview is not Gmail/Outlook rendering verification. Never report scheduled delivery as active without confirming task registration and enabled config.
