# The Brief — News Digest Kit

A Windows tool that collects Bloomberg RSS headlines and emails a readable digest at **09:00, 12:00 and 17:00 Beijing time (UTC+8)**. Runs with Python and Windows Task Scheduler; Codex is optional.

**Coverage is limited to available public RSS feeds. This is not a complete Bloomberg news feed, an official Bloomberg product, or a paywall bypass.** Source sections are the original RSS channel names, not guaranteed article-page taxonomy. Titles and source section names stay in their original language.

## What you get

- Original headline, original source section and original article link.
- English by default; Simplified Chinese and Traditional Chinese interface options.
- Section navigation in the email and an attached HTML reader with language and section selectors. Download the attachment and open it in a browser; email clients generally do not execute its interactive controls inside the message.
- URL deduplication across feeds and delivery times.
- Overnight stories included in the morning edition; older unsent stories labeled as catch-up.
- An optional HTTP CONNECT proxy for SMTP, plus HTTP proxy support for RSS. Works with a compatible FlClash mixed/HTTP port; the port is configurable.
- Local Windows-encrypted credentials. No passwords are included in the repository.

Open **sample-preview.html** for a fictional design sample. News is not translated or summarized by AI.

## Requirements

- Windows 10 or 11 and **Python 3.10 or newer** from [python.org](https://www.python.org/downloads/windows/) or an existing Anaconda installation. No pip packages required.
- An SMTP account that supports **implicit TLS/SSL**, usually port **465**. STARTTLS on port 587 is not implemented.
- An internet connection that can reach both Bloomberg RSS and your SMTP server. If a proxy is configured, it must remain running.
- Your Windows user must remain signed in. Locking the screen is fine; signing out, shutting down or sleeping may interrupt collection. Wake timers depend on hardware and Windows power settings.

## Quick start

1. On GitHub, click **Code → Download ZIP**. Extract it to a permanent folder. Do not run from inside the ZIP or move the folder after installing the task.
2. Double-click **start-setup.cmd**. If Windows blocks a downloaded script, review the files and use the file's Properties → Unblock option if you trust it; the tool does not disable machine-wide security policies.
3. Enter your own **recipient** and **sender** email addresses. They can be different. Nothing is prefilled with the author's accounts.
4. Choose email language (`en`, `zh-Hans`, `zh-Hant`), sections (`ALL` or comma-separated exact channel names), SMTP SSL host/port and delivery times. Times always use Beijing time, independent of your Windows time zone.
5. For the proxy setting, choose `DIRECT` or enter a local HTTP/mixed proxy endpoint such as `127.0.0.1:7890`. Check your proxy application's actual listening port; do not assume the example is yours. This setting applies only to this application and does not change global proxy settings.
6. The installer tests the network **before asking for a password**. Enter the sender's SMTP app password locally. Gmail passwords are checked for 16 letters; formatting spaces are removed automatically. A malformed password is rejected before it is saved.
7. A clearly labeled test email is sent. Check the recipient's inbox and spam folder. Review source availability in the generated preview.
8. Only after receiving the test email, type **YES**. A scheduled task is installed and its state is displayed. Close the setup window; the task runs independently.

The task collects every five minutes and sends at the next configured slot. Expect minute-level timing, not exact second delivery. The first scheduled edition starts after activation; setup sends only a test message.

## Gmail app password: step by step

1. Sign in to the **sender's** Google account, not the recipient's account.
2. Enable **2-Step Verification** in [Google Account Security](https://myaccount.google.com/security).
3. Open [App passwords](https://myaccount.google.com/apppasswords). Enter a label such as `News Digest` and create one.
4. Copy the complete **16-letter app password** into setup. Do not use your normal Google account password. Never paste the app password into a GitHub issue, chat, screenshot or config.json.

Google may not offer this feature for some organization accounts, security-key-only configurations or Advanced Protection accounts. Changing your Google password revokes app passwords. See [Google's official instructions](https://support.google.com/accounts/answer/185833). Do not weaken your account protection to use this tool; choose a supported sender account instead if needed. OAuth is not implemented.

## Everyday controls

| File | Purpose |
| --- | --- |
| `start-setup.cmd` | Configure accounts, language, sections, proxy and password. Editing configuration pauses delivery until reactivated. |
| `resume-setup.cmd` | Retry the test and activation using saved configuration and credentials. |
| `check.cmd` | Test SMTP TLS connectivity, without logging in or sending mail. |
| `preview.cmd` | Collect RSS and open a local HTML preview. Does not send mail. |
| `status.cmd` | Show enabled state, feed status and recent delivery batches. |
| `uninstall.cmd` | Remove the scheduled task and disable delivery. Preserve configuration/history. |

The browser's language/section selectors only change the reading view. They do not change future email subscriptions. To change those, rerun setup. You may also edit `config.json` while delivery is disabled; `language` controls email language, `sections: []` means all sources.

## Troubleshooting

| Symptom | Meaning and action |
| --- | --- |
| PowerShell not found | Launchers use `%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe` directly and do not depend on PATH. Check that Windows PowerShell exists. |
| Python not found | Store aliases are skipped. The tool probes installed interpreters and allows a full path to python.exe. For a custom installation, set `NEWS_DIGEST_PYTHON` or enter the full path when asked. |
| Gmail password has 15 characters | One character was missed. Setup now rejects it locally. Copy all 16 letters; do not guess the missing character. |
| `535` / login rejected | The server was reached, but it rejected the credentials. Verify the sender account, use a current app password belonging to that account, and rerun setup. Correct length alone does not prove validity. |
| Timeout / `10060` | Network connection failed before login. A browser working through a proxy does not mean Python SMTP uses it. Configure the actual HTTP/mixed proxy port and run `check.cmd`. |
| Proxy refused tunnel | The selected proxy route may block SMTP. Try a permitted route or supported sender service. Do not disable TLS certificate verification. |
| Chinese Windows computer name | Supported: Message-ID uses an ASCII domain instead of the machine hostname. Chinese UI/body text is MIME-encoded. |
| Cannot read credentials | Run under the same Windows account on the same PC. Copying `private/smtp.xml` to another account or machine will not work. Rerun setup locally. |
| No news / unavailable source | RSS may be empty, selective or unavailable. Check source status. A failed feed is not treated as proof that no news exists. |
| Task exists but no email | Check `status.cmd`, Windows Task Scheduler's last result, `private/run.log`, login state, proxy and network. No independent failure notification service is included. |

Pre-transmission connection/authentication failures do not mark stories as sent; the next tick can retry. If an SMTP transmission fails after sending begins, delivery can be ambiguous. The tool pauses that batch to avoid duplicates. Check your Sent folder and recipient inbox, then use the batch ID shown by `status.cmd`:

```powershell
python digest.py resolve --batch "BATCH_ID" --result sent
# Only if you have confirmed the message was NOT sent:
python digest.py resolve --batch "BATCH_ID" --result retry
```

This is not a guarantee of exactly-once email delivery. A crash or lost server acknowledgement still requires reconciliation. If retries repeatedly fail, disable the task while fixing the configuration.

## Coverage, storage and privacy

The example configuration includes working and candidate RSS URLs. Availability changes; some return 404 or empty lists. The software keeps their status visible. Frequent polling cannot guarantee full coverage, and articles that disappear from RSS while the PC is offline cannot be recovered.

At first collection, the window starts at 17:00 on the previous day. Later collections retain unsent stories from that initial window onward. Missed slots are consolidated into the latest due edition when the PC resumes. Changing sections may expose older unsent stories as catch-up; headline changes on an already-sent URL do not trigger a resend.

`private/` stores Windows-encrypted credentials, a SQLite history, logs and archives. These are local and may grow over time. `config.json` contains addresses and preferences, but not the password. Both are ignored by Git. **Share the source ZIP, never your configured application folder.** Do not remove the database unless you accept resetting deduplication history. Moving the installed folder requires uninstalling the old task and activating again at the new location.

TLS certificate verification remains enabled, including through proxies. Proxies can see destination metadata but the SMTP session is encrypted to the server. Only unauthenticated HTTP CONNECT proxies are supported; SOCKS-only endpoints are not supported.

## Optional Codex skill

Copy the source folder to `%USERPROFILE%\.codex\skills\news-digest-kit`, reload skills and invoke `$news-digest-kit`. Review [SKILL.md](SKILL.md). Codex helps configure and maintain the application; Python and Task Scheduler perform delivery. No Codex subscription or session is needed for the standalone program.

## Development and verification

To share your copy safely after using it, run `python package_release.py`. It creates `dist/news-digest-kit-share.zip` from an explicit source-file allowlist, excluding your addresses, credentials, history, logs and generated news previews. Do not manually ZIP the configured folder.

```powershell
python -m unittest discover -s tests -v
```

Tests use synthetic data and mocked mail transport. They do not send real email or certify every email client's rendering. A real inbox test is part of setup. The original installation's troubleshooting informed regression cases for Chinese hostnames, proxy connections, cross-section deduplication and interrupted delivery.

The HTML is inspired by [Mailchimp's email design guidance](https://templates.mailchimp.com/design/) and [responsive email documentation](https://templates.mailchimp.com/development/responsive-email/). Email body layout uses inline styles and tables; the downloaded reader adds local JavaScript. Some mail providers may block or quarantine interactive HTML attachments.
