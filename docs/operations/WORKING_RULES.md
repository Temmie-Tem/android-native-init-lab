# A90 Working Rules

Updated: `2026-06-10`

This is the first document to check before changing native-init source,
revalidation scripts, boot artifacts, reports, or workspace layout. Detailed
policy remains in `docs/operations/VERSIONING_POLICY.md` and
`docs/operations/WORKSPACE_STRUCTURE_AND_BOOTSTRAP.md`.

The current active TODO map is
`docs/plans/NATIVE_INIT_CURRENT_TODO_2026-06-08.md`.
The standing boot/bridge/communication contract is
`docs/operations/NATIVE_INIT_BOOT_TRANSPORT_CONTRACT.md`.
Baseline QA and stability criteria are in
`docs/operations/NATIVE_INIT_QA_STABILITY_POLICY.md`.

## 1. Version Axes

Keep these axes separate.

| Axis | Format | Use |
| --- | --- | --- |
| Run ID | `VNNNN` | Project execution, source-build check, live handoff, classifier, baseline-promotion report. |
| Native init version | `MAJOR.MINOR.PATCH` | Device-visible `/init` version. Bump only when the boot artifact changes. |
| Build tag | `vNNNN-purpose` | Boot/init baseline identity embedded in the banner and usually boot image filename. |
| Helper version | `helper-vNNN` | Helper binary marker stream, e.g. `a90_android_execns_probe helper-v427`. |
| Artifact hash | SHA256 | Final identity for boot images, ramdisks, helpers, and evidence bundles. |

Rules:

- Do not use a build tag as a run ID. `v2169-transport-contract` is a boot/init
  baseline tag, not a `V2169` run ID.
- Do not use helper numbers as run IDs, boot filenames, or native-init build
  tags.
- The current promoted baseline uses build tag
  `v2187-screenapp-ui-validation`. Keep this as the rollback/test baseline until
  a newer boot image is intentionally promoted.
- If an existing artifact is only reproduced or documented, keep its build tag
  and record it as `Baseline tag`, not `Cycle`.
- If the boot image SHA changes and that image becomes a rollback/test
  baseline, promote it under a new run/build identity.

## 2. Source Locations

Use these paths for active work.

| Work type | Canonical path | Notes |
| --- | --- | --- |
| Current native-init source | `workspace/public/src/native-init/` | Edit active `a90_*`, `init_v724.c`, `init_v725_fasttransport.c`, `v319/`, `v724/`, and current helper source here. |
| Current revalidation entrypoints | `workspace/public/src/scripts/revalidation/` | New active entrypoint scripts should live here. |
| Shared harness code | `workspace/public/src/harness/a90harness/` | Current shared Python modules used by active revalidation entrypoints. |
| Historical script provenance | `workspace/public/archive/scripts/` | Historical scripts and compatibility symlinks only; do not add new active entrypoints here. |
| Historical native-init provenance | `workspace/public/archive/stage3/linux_init/` | Old source provenance and compatibility symlinks only; do not edit active source here. |
| Rules and runbooks | `docs/operations/` | Version, workspace, host setup, and repeatable operational rules. |
| Reports and decisions | `docs/reports/` | Redacted report output only; include all relevant version axes. |
| Public portable state | `workspace/public/` | Manifests, redacted summaries, inventories, config templates, and portable source. |

Active builders must not write generated binaries into tracked source
directories. If a legacy command still targets root `stage3/`, root
`scripts/revalidation/`, or flat `tmp/wifi/v...`,
migrate the active writer before relying on it for new baseline work.

## 3. Private And Generated Locations

Use these roots for local-only payloads.

| Payload | Path |
| --- | --- |
| Trusted boot image inputs/current rollback images | `workspace/private/inputs/boot_images/` |
| Firmware/vendor extracts | `workspace/private/inputs/firmware/` |
| External static tools | `workspace/private/inputs/external_tools/` |
| Toolchains/kernel source snapshots | `workspace/private/inputs/toolchains/`, `workspace/private/inputs/kernel_source/` |
| Native-init build intermediates | `workspace/private/builds/native-init/` |
| Secrets and Wi-Fi env files | `workspace/private/secrets/` |
| Raw logs/device dumps/archives | `workspace/private/raw-logs/`, `workspace/private/device-dumps/`, `workspace/private/archives/` |
| Structured live run evidence | `tmp/wifi/runs/` |
| Structured cross-run logs | `tmp/logs/` |

Rules:

- Work in `workspace/private/` first when data could be private, large,
  generated, proprietary, or device-specific.
- Do not create new root-level payload directories such as `firmware/`,
  `kernel_build/`, `toolchains/`, `external_tools/`, `backups/`, or `out/`.
  Restore those inputs and outputs under `workspace/private/` instead.
- Promote only redacted, small, reproducible, or metadata-only output to
  `workspace/public/`, `docs/artifacts/`, or `docs/reports/`.
- Do not commit boot images, firmware, ramdisks, compiled init/helper binaries,
  raw archives, Wi-Fi credentials, generated supplicant configs, DHCP leases, or
  unredacted MAC/BSSID/IP traces.
- `tmp/` is allowed only as structured evidence/log scratch. Do not make new
  unstructured top-level `tmp` conventions.

## 4. Script And Builder Rules

- New scripts should prefer `workspace/public/src/harness/a90harness/evidence.py`
  helpers for workspace paths and evidence directories.
- Builders should read private inputs from `workspace/private/inputs/` and write
  generated outputs to `workspace/private/builds/`.
- Final boot images used as rollback or next-build inputs should be placed under
  `workspace/private/inputs/boot_images/` with SHA recorded in a report or
  manifest.
- Compatibility symlinks may remain under `workspace/public/archive/scripts/`,
  but canonical active entrypoints must be documented under
  `workspace/public/src/scripts/revalidation/`.
- If a source move leaves compatibility symlinks under
  `workspace/public/archive/stage3/`, keep the symlink target under
  `workspace/public/src/` or `workspace/private/builds/`, not an ad-hoc local
  path.

## 5. Report Header Rules

Every non-trivial source-build, live handoff, classifier, or promotion report
should state the relevant axes explicitly.

For a new artifact:

```text
Run ID: V2176
Native init: A90 Linux init 0.9.252
Build tag: v2176-<purpose>
Helper: a90_android_execns_probe helper-v427
Boot image: workspace/private/inputs/boot_images/boot_linux_v2176_<purpose>.img
Boot SHA256: <sha256>
Device flash: yes|no
Host commit: <git-sha-or-uncommitted>
```

For an unchanged existing artifact:

```text
Run ID: <current validation run>
Native init: A90 Linux init 0.9.255 (v2182-hud-menu-cleanup)
Build tag: unchanged
Baseline tag: v2182-hud-menu-cleanup
Helper: unchanged
Device flash: no
Host commit: <git-sha-or-uncommitted>
```

## 6. Validation Rules

Before committing source or builder changes:

```bash
git diff HEAD --check
python3 -m py_compile <changed-python-files>
bash -n <changed-shell-files>
```

When native-init source, ramdisk layout, helper inclusion, boot packaging, or
boot-image input changes, also run the relevant build script and record:

- init SHA256
- helper SHA256 when embedded
- ramdisk SHA256
- boot SHA256
- source root used by the builder
- output paths under `workspace/private/`

For the current V726 artifact reproduction:

```bash
python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v726_wifi_lifecycle.py
```

Expected current boot SHA:

```text
6b34aac93d4fa6d5b40355b9e13b2c1ae847c24a3685d84b0d1cd78751351d40
```

## 7. Live Test Safety Rules

Live device tests remain bounded and rollbackable.

- Use approved test-boot and rollback images only.
- Verify `selftest fail=0` after rollback or baseline flash.
- Keep Wi-Fi credentials in environment files under `workspace/private/secrets/`
  or another ignored path.
- Redact SSID/PSK/BSSID/full MAC/full IP before public reports.
- Do not move raw live captures into public paths unless explicitly redacted.
- Do not mix unrelated subsystem experiments into a Wi-Fi lifecycle run.

## 8. Commit Rules

- Commit source, scripts, docs, manifests, redacted reports, and compatibility
  symlinks when they are part of the intended project state.
- Do not commit ignored private payloads or generated binaries.
- Keep migration commits focused: source/workspace moves, version-policy
  changes, and live-test behavior changes should be separate unless a single
  baseline promotion requires them together.
- Before commit, check `git status --short`, `git diff --cached --check`, and
  confirm no private path payload is staged.
