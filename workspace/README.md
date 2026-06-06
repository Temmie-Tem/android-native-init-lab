# Local Workspace

This directory is a tracked scaffold for local work. The goal is that a fresh
GitHub clone keeps the same working map, while private/raw inputs can be restored
locally without being committed.

## Layout

| Path | Git policy | Purpose |
| --- | --- | --- |
| `private/` | scaffold tracked, contents ignored | Default working area for raw logs, firmware, boot images, generated builds, secrets, caches, and temporary files. |
| `public/` | tracked by default with guardrails | Public/recoverable state: manifests, summaries, inventories, redacted logs, config templates, runbooks. |

## Default Rule

Work in `workspace/private/` first. Promote only redacted, small, reproducible, or
metadata-only results into `workspace/public/` or `docs/artifacts/`.

The full working rulebook is `docs/operations/WORKING_RULES.md`.

## Restore Flow

1. Clone the repository.
2. Read `workspace/public/manifests/` and `workspace/private/inputs/README.md`.
3. Restore private inputs into `workspace/private/inputs/` from local backup or vendor sources.
4. Rebuild or restore generated outputs under `workspace/private/builds/`.
5. Verify restored inputs with public SHA manifests before using them.
6. Keep generated raw evidence under `workspace/private/` unless it has been redacted and summarized.

## Do Not Commit

- Firmware, boot images, ramdisks, compiled helper/init binaries, vendor extracts, kernel build outputs, or raw archives.
- Wi-Fi credentials, generated supplicant configs, DHCP leases, routes, ping transcripts, full MAC/BSSID/IP, or private allowlists.
- Raw dmesg/logcat/kmsg/diag captures unless explicitly redacted and moved to `public/` as text/JSON/Markdown.
