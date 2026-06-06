# Public Workspace

This tree stores public/recoverable workspace state that can be committed after
review. Treat it as staging for `docs/artifacts/` and operational docs.

Allowed by default:

- SHA manifests and file inventories.
- Redacted summaries and small JSON/Markdown reports.
- Non-secret config templates and runbooks.
- Current tracked source/script entrypoints under `src/`.
- Redacted log excerpts with no credentials, full MAC/BSSID/IP, DHCP leases,
  routes, or ping transcripts.

The local `.gitignore` blocks common raw/binary/private patterns even under this
public tree. If a file is blocked, either keep it private or convert it to a
redacted text/JSON/Markdown summary.
