# v221 Plan: Host Vendor ELF / Library Evidence Closure

## Summary

v221 follows v220 `no-go`. The goal is to close the v218 blocker
`elf-inspection-no-host-vendor-root` before any CNSS daemon experiment is
planned.

This version is read-only and host-side by default. It must not execute
`cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, supplicant, hostapd, rfkill,
link-up, scan, or connect.

- baseline native runtime: `A90 Linux init 0.9.59 (v159)`
- previous result: v220 PASS, decision `no-go`
- planned tool: `scripts/revalidation/wifi_vendor_elf_library_closure.py`
- evidence output: `tmp/wifi/v221-host-vendor-elf-library-evidence`
- report after execution:
  `docs/reports/NATIVE_INIT_V221_HOST_VENDOR_ELF_LIBRARY_EVIDENCE_2026-05-13.md`

## Why This Comes Before CNSS Start

v218 already proved that `cnss-daemon` and `cnss_diag` are represented in the
Android service graph and visible in vendor asset evidence, but it did not have
a host-visible vendor root for ELF inspection.

v220 then kept active Wi-Fi blocked because:

- `icnss_recovery` is blocked: reboot is the only proven recovery.
- `shim_policy` is blocked: property/QMI/recovery/security areas remain denied.
- `security_exposure` is blocked: pre-connect exposure review is not complete.
- `daemon_dryrun` is warning: ELF/library/recovery blockers remain.

Therefore v221 must close evidence, not start services.

## Reference Basis

- Linux dynamic loader behavior depends on the program interpreter and dynamic
  dependency entries. The loader uses `.interp`, `DT_NEEDED`, `DT_RPATH`,
  `DT_RUNPATH`, `LD_LIBRARY_PATH`, cache/default search paths, and dynamic
  string tokens such as `$ORIGIN` and `$LIB`:
  <https://man7.org/linux/man-pages/man8/ld.so.8.html>
- Android init service definitions include user, group, capabilities, sockets,
  class, disabled/oneshot flags, and other runtime context. CNSS service
  feasibility must therefore combine ELF evidence with init `.rc` policy:
  <https://android.googlesource.com/platform/system/core/+/master/init/README.md>
- Android services can request capabilities through init `.rc` service options.
  This matters for `cnss-daemon` because v218 mapped `NET_ADMIN` and Wi-Fi
  related group requirements:
  <https://source.android.com/docs/core/permissions/ambient>

## Inputs

Required manifests:

- `tmp/wifi/v210-vendor-asset-classifier/manifest.json`
- `tmp/wifi/v216-service-replay-model/manifest.json`
- `tmp/wifi/v218-cnss-daemon-dryrun/manifest.json`
- `tmp/wifi/v218-cnss-daemon-dryrun-native/manifest.json`
- `tmp/wifi/v219-native-android-env-shim/manifest.json`
- `tmp/wifi/v220-bringup-gate-v2/manifest.json`

Optional host input:

- `--vendor-root <path>`
  - extracted or mounted vendor filesystem root
  - expected to contain `bin/cnss-daemon`, `bin/cnss_diag`, and library
    directories

The tool must also work without `--vendor-root` and return a clear
`vendor-root-required` decision.

## Planned Tool Behavior

`wifi_vendor_elf_library_closure.py` should:

1. load v210/v216/v218/v219/v220 manifests;
2. verify no active Wi-Fi/device command is defined;
3. identify target binaries:
   - `cnss-daemon`
   - `cnss_diag`
4. if `--vendor-root` is absent:
   - emit `vendor-root-required`;
   - preserve v218 daemon model;
   - list exact paths needed from vendor evidence;
5. if `--vendor-root` is present:
   - validate it is a directory inside an allowed host path;
   - reject suspicious symlink traversal where output or input safety matters;
   - inspect target ELF headers with `readelf`;
   - extract interpreter, `DT_NEEDED`, `DT_RPATH`, `DT_RUNPATH`, and machine
     architecture;
   - recursively resolve direct vendor libraries where practical;
   - classify missing libraries and Android-only dependencies;
   - write private/no-follow evidence via `a90harness.evidence.EvidenceStore`.

## Output Model

The tool should write:

- `manifest.json`
- `elf-dependencies.json`
- `summary.md`

Manifest fields should include:

- `decision`
- `pass`
- `reason`
- input manifest paths
- host metadata
- target daemon models
- target binary path, exists, mode, size, sha256
- ELF interpreter
- `DT_NEEDED`
- `DT_RPATH`
- `DT_RUNPATH`
- resolved library path map
- unresolved library list
- Android init policy summary for user/group/capabilities/classes/flags
- blockers carried from v218-v220

## Decision Model

- `elf-evidence-ready`
  - vendor root exists
  - target binaries parse as ELF
  - interpreter and direct `DT_NEEDED` entries are captured
  - unresolved library list is empty or explicitly classified as Android-only
    but not a blocker for later dry-run planning
- `vendor-root-required`
  - no `--vendor-root` was provided
  - tool still produced a useful required-path checklist
- `daemon-native-blocked`
  - binaries or critical direct libraries are missing
  - ELF parse fails
  - host evidence indicates Android runtime dependency is too wide
- `manual-review-required`
  - evidence conflicts with v210/v216/v218/v220 manifests

`vendor-root-required` should be a PASS result for the tool because it is a
safe and expected planning outcome when no vendor root is available.

## Guardrails

The tool must not:

- run any device command by default;
- start `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, supplicant, or
  hostapd;
- write to `/sys`, `/proc/sys`, debugfs, tracefs, ICNSS controls, rfkill, or
  network interfaces;
- collect Wi-Fi credentials;
- read `/data/misc/wifi`;
- create world-readable evidence output.

## Validation

Static:

```bash
python3 -m py_compile scripts/revalidation/wifi_vendor_elf_library_closure.py
git diff --check
python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import wifi_vendor_elf_library_closure
wifi_vendor_elf_library_closure.validate_no_active_commands()
print('v221 command guard PASS')
PY
```

Manifest-only run:

```bash
python3 scripts/revalidation/wifi_vendor_elf_library_closure.py \
  --v210-manifest tmp/wifi/v210-vendor-asset-classifier/manifest.json \
  --v216-manifest tmp/wifi/v216-service-replay-model/manifest.json \
  --v218-manifest tmp/wifi/v218-cnss-daemon-dryrun/manifest.json \
  --v218-native-manifest tmp/wifi/v218-cnss-daemon-dryrun-native/manifest.json \
  --v219-manifest tmp/wifi/v219-native-android-env-shim/manifest.json \
  --v220-manifest tmp/wifi/v220-bringup-gate-v2/manifest.json \
  --out-dir tmp/wifi/v221-host-vendor-elf-library-evidence
```

Expected:

- PASS
- decision `vendor-root-required`
- no device command execution
- required vendor paths listed

Optional vendor-root run:

```bash
python3 scripts/revalidation/wifi_vendor_elf_library_closure.py \
  --vendor-root <extracted-or-mounted-vendor-root> \
  --out-dir tmp/wifi/v221-host-vendor-elf-library-evidence
```

Expected:

- PASS if target ELF/library graph is captured
- `elf-evidence-ready` or `daemon-native-blocked`
- no daemon execution

## Acceptance

- v218 `elf-inspection-no-host-vendor-root` is replaced by either real ELF
  evidence or a precise vendor-root-required checklist.
- `cnss-daemon` and `cnss_diag` execution remains blocked.
- v222 recovery/rollback policy can use v221 output without guessing binary
  dependencies.
- v220 `no-go` remains authoritative until a later integrated gate supersedes
  it.

## Next

If v221 returns `elf-evidence-ready`, plan v222 recovery/rollback policy
hardening. If v221 returns `vendor-root-required`, obtain or mount a host-visible
vendor root and re-run v221 before any active CNSS planning.
