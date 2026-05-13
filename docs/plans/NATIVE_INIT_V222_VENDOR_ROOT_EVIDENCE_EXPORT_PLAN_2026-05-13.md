# v222 Plan: Vendor Root Evidence Export / Extraction

## Summary

v222 follows v221 `vendor-root-required`. The goal is to produce a safe
host-visible vendor evidence root that can be passed back into v221
`--vendor-root`.

This version is read-only by policy. It must not execute Wi-Fi daemons, mutate
ICNSS controls, write firmware paths, use Wi-Fi credentials, or perform scan and
connect operations.

- baseline native runtime: `A90 Linux init 0.9.59 (v159)`
- previous result: v221 PASS, decision `vendor-root-required`
- planned tool: `scripts/revalidation/wifi_vendor_root_evidence_export.py`
- evidence output: `tmp/wifi/v222-vendor-root-evidence-export`
- report after execution:
  `docs/reports/NATIVE_INIT_V222_VENDOR_ROOT_EVIDENCE_EXPORT_2026-05-13.md`

## Goal

Create or validate a host-visible vendor evidence bundle containing at least:

- `bin/cnss-daemon`
- `bin/cnss_diag`
- enough related `lib`/`lib64` files for v221 ELF/library inspection

The output should look like a minimal vendor root:

```text
vendor-root/
├── bin/
│   ├── cnss-daemon
│   └── cnss_diag
├── lib/
└── lib64/
```

## Why This Is Separate From v221

v221 can parse ELF/library dependencies only when a host-visible vendor root is
available. v221 intentionally does not pull files from the device. Keeping file
export/extraction in v222 isolates:

- host filesystem safety;
- private/no-follow evidence output;
- source trust validation;
- future optional device export paths;
- v221's pure analysis role.

## Source Modes

### Mode A. Operator-Provided Vendor Root

Default implementation target.

Input:

```text
--source-vendor-root <path>
```

The tool validates the source root and copies an allowlisted subset into private
evidence output. This is the safest initial mode because it does not need live
device access.

Expected decision:

- `vendor-root-ready` if required files are copied
- `export-source-required` if no source root is provided
- `vendor-export-blocked` if source is unsafe or incomplete

### Mode B. Existing Native Mount Evidence

Future extension, not required for first implementation.

Use v209/v210 temporary `ro,noload` vendor mount logic as a read-only source,
but do not stream arbitrary binary data over the serial shell unless a safe
binary transfer helper is introduced.

### Mode C. TWRP / Android ADB Pull

Future extension, operator-assisted.

Use TWRP or rooted Android ADB to pull the needed files into a private host
directory, then run Mode A against that directory. This is often safer than
serial `cat` for binary files.

## Planned Tool Behavior

`wifi_vendor_root_evidence_export.py` should:

1. load v210, v221, and optionally v218 manifests;
2. verify no live device command list is present;
3. define an allowlist:
   - `bin/cnss-daemon`
   - `bin/cnss_diag`
   - `lib/**`
   - `lib64/**`
   - optional init/config text files needed for context
4. if `--source-vendor-root` is absent:
   - emit `export-source-required`;
   - write exact source paths required;
5. if `--source-vendor-root` is present:
   - reject symlink root;
   - reject non-directory source;
   - copy allowlisted files into private output using no-follow destination
     writes;
   - avoid preserving unsafe modes;
   - cap file count and total copied bytes;
   - hash every copied file;
   - write `vendor-root/` evidence tree;
   - optionally print the command to run v221 with `--vendor-root`.

## Output Model

The tool should write:

- `manifest.json`
- `export-plan.json`
- `summary.md`
- `vendor-root/` when a source root is provided and accepted

Manifest fields should include:

- `decision`
- `pass`
- `reason`
- source root status
- copied file count and total bytes
- missing required paths
- skipped files with reason
- hashes for copied files
- output vendor root path
- v221 rerun command
- guardrails
- host metadata

## Decision Model

- `vendor-root-ready`
  - required binaries are copied
  - at least one of `lib` or `lib64` exists or is explicitly absent with
    evidence
  - copied output is private
  - v221 rerun path is available
- `export-source-required`
  - no `--source-vendor-root` provided
  - required path checklist is produced
  - result is PASS because this is a safe planning outcome
- `vendor-export-blocked`
  - source root is missing, symlinked, not a directory, too large, or missing
    required binaries
- `manual-review-required`
  - source evidence conflicts with v210/v221 manifests

## Guardrails

The tool must not:

- run live device commands by default;
- dump full partitions by default;
- write to the device;
- execute any copied file;
- follow destination symlinks;
- create group/world-readable evidence output;
- copy `/data/misc/wifi` or credentials;
- start `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, supplicant, or
  hostapd;
- perform rfkill, link-up, scan, connect, or DHCP operations.

## Validation

Static:

```bash
python3 -m py_compile scripts/revalidation/wifi_vendor_root_evidence_export.py
git diff --check
python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import wifi_vendor_root_evidence_export
wifi_vendor_root_evidence_export.validate_no_active_commands()
print('v222 command guard PASS')
PY
```

Plan-only run:

```bash
python3 scripts/revalidation/wifi_vendor_root_evidence_export.py \
  --v210-manifest tmp/wifi/v210-vendor-asset-classifier/manifest.json \
  --v221-manifest tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json \
  --out-dir tmp/wifi/v222-vendor-root-evidence-export
```

Expected:

- PASS
- decision `export-source-required`
- required source paths listed

Source-root run:

```bash
python3 scripts/revalidation/wifi_vendor_root_evidence_export.py \
  --source-vendor-root <vendor-root> \
  --out-dir tmp/wifi/v222-vendor-root-evidence-export
```

Expected:

- PASS if required files are copied
- decision `vendor-root-ready`
- output path:
  `tmp/wifi/v222-vendor-root-evidence-export/vendor-root`

Then rerun v221:

```bash
python3 scripts/revalidation/wifi_vendor_elf_library_closure.py \
  --vendor-root tmp/wifi/v222-vendor-root-evidence-export/vendor-root \
  --out-dir tmp/wifi/v221-host-vendor-elf-library-evidence-rerun
```

## Acceptance

- The project has either a private host-visible vendor evidence root or an exact
  source-required checklist.
- Required CNSS binaries are never executed.
- Evidence output is private and no-follow safe.
- v221 can be rerun with `--vendor-root` when source evidence is available.
- Active Wi-Fi remains blocked.

## Next

If v222 returns `vendor-root-ready`, rerun v221 with the exported root. If v222
returns `export-source-required`, collect a vendor root using TWRP/Android ADB or
another reviewed read-only source before moving to recovery policy hardening.
