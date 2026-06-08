# Workspace Structure and Bootstrap

## Purpose

The repository should be useful after a fresh GitHub clone without carrying raw
private state. The tracked `workspace/` scaffold preserves the working map; local
private payloads are restored into ignored subdirectories when needed.

For the combined day-to-day rulebook covering version axes, workspace paths, and
commit boundaries, read `docs/operations/WORKING_RULES.md` first.

## Workspace Layers

| Layer | Paths | Git policy | Notes |
| --- | --- | --- | --- |
| Tracked source/control | `README.md`, `docs/`, `workspace/public/src/native-init/`, `workspace/public/src/scripts/revalidation/`, `workspace/public/src/harness/`, small README/index files | commit | Portable current project state. |
| Public project artifacts | `docs/artifacts/`, selected `docs/reports/` | commit redacted metadata | Final public summaries and reports. |
| Public workspace state | `workspace/public/` | commit after review | Recovery manifests, inventories, redacted summaries, config templates, and runbooks. |
| Private workspace state | `workspace/private/` | scaffold tracked, payload ignored | Default local working area for raw/private/large inputs, generated builds, and evidence. |
| Private build outputs | `workspace/private/builds/`, `workspace/private/inputs/boot_images/` | ignored payload | Current generated ramdisks/init/helper binaries and local boot images. |
| Legacy local artifacts | `tmp/`, restored root `stage3/boot_linux*.img`, restored root `stage3/ramdisk_v*`, compiled `init_v*`, helper binaries | ignored | Historical generated outputs only; active writers must use workspace private paths. |
| Runtime device scratch | `/tmp/a90-*`, `/cache/*`, `/mnt/sdext/a90/*` | not repo artifacts | Runtime paths mentioned in reports only. |

## Tracked Workspace Scaffold

The scaffold is committed, but private payloads are ignored by
`workspace/.gitignore`.

```text
workspace/
  README.md
  .gitignore
  private/
    README.md
    inputs/
      firmware/
      boot_images/
      toolchains/
      external_tools/
      kernel_source/
    builds/
      native-init/
      boot_images/
      ramdisks/
      helpers/
      wifi/
    secrets/
    raw-logs/
    device-dumps/
    archives/
    scratch/
  public/
    README.md
    src/
      native-init/
      harness/
      scripts/
        revalidation/
      third_party/
        mkbootimg/
    archive/
      scripts/
      stage3/
    manifests/
    summaries/
    inventories/
    redacted-logs/
    configs/
    runbooks/
```

Default workflow:

1. Work in `workspace/private/` first.
2. Promote only redacted, small, reproducible, or metadata-only state to
   `workspace/public/` or `docs/artifacts/`.
3. Never move raw/private payloads into public directories just for convenience.

## Local Artifact Layout

New harness output should use structured roots. Existing `tmp/wifi/v...` paths
and any restored root `stage3/` generated files are legacy provenance paths and
should not receive new active writers.

| Path | Use |
| --- | --- |
| `workspace/private/builds/native-init/` | Active native-init build intermediates: compiled init/helper binaries, ramdisks, cpio files, and build manifests. |
| `workspace/private/inputs/boot_images/` | Trusted seed/current boot images used as rollback or next-build inputs. |
| `tmp/wifi/runs/` | Live run evidence and result bundles. |
| `tmp/wifi/builds/` | Legacy/review-only build outputs and manifests. |
| `tmp/wifi/cache/` | Extracted vendor/kernel/userland caches. |
| `tmp/wifi/bench/` | NCM/file-transfer benchmark artifacts. |
| `tmp/wifi/scratch/` | Disposable work; safe to prune aggressively. |
| `tmp/wifi/archive/` | Local-only compressed evidence bundles and delete manifests. |
| `tmp/logs/{bridge,host,device,kernel,supplicant,net,archive}/` | Cross-run logs not tied to a single evidence directory. |

Use `workspace/public/src/harness/a90harness/evidence.py` helpers from new
scripts:

```python
wifi_artifact_dir("runs", label)
wifi_artifact_dir("builds", label)
wifi_artifact_dir("bench", label, timestamp=True)
tmp_log_dir("host", label, timestamp=True)
workspace_private_build_path("native-init", label)
workspace_private_input_path("boot_images", "boot_linux_vNNN.img")
EvidenceStore.write_log("host", "step", text)
docs_artifact_path(label)
```

## Fresh Clone Bootstrap

Run these steps after cloning into a new checkout.

### 1. Verify Source State

```bash
git status --short
git log -1 --oneline
```

Expected: clean worktree before restoring local-only inputs.

### 2. Initialize Generated Artifact Layout

```bash
python3 workspace/public/src/scripts/revalidation/cleanup_tmp_wifi_artifacts.py --init-layout
```

The tracked `workspace/` scaffold already exists after clone. The command above
creates ignored `tmp/wifi/*` and `tmp/logs/*` run/log directories for live
evidence. Build intermediates should go to `workspace/private/builds/`.

### 3. Restore Private Inputs

Restore private inputs under `workspace/private/inputs/` from local backup,
vendor downloads, or external storage:

- `workspace/private/inputs/firmware/` — proprietary firmware/vendor extracts.
- `workspace/private/inputs/boot_images/` — trusted seed/current boot images and
  SHA sidecars.
- `workspace/private/inputs/toolchains/` — local toolchains when system packages
  are insufficient.
- `workspace/private/inputs/external_tools/` — static userland helpers such as
  busybox, toybox, a90_tcpctl, and a90_usbnet.
- `workspace/private/inputs/kernel_source/` — Samsung/open-source kernel source
  or build tree snapshots.

Public SHA/checklist metadata belongs under `workspace/public/manifests/` or
`docs/artifacts/`. Restored payloads stay private.

Generated build outputs belong under `workspace/private/builds/`. Current boot
images that become rollback or next-build inputs belong under
`workspace/private/inputs/boot_images/`.

### 3a. Legacy Path Compatibility

Migrated harness defaults resolve these legacy local roots through
`workspace/private/inputs/` first, then falls back to the old root when present:

These legacy roots are not scaffolded anymore. Do not recreate them for new
work; they are read-only compatibility fallbacks for old checkouts or old local
scripts only.

| Legacy root | Workspace root | Override env |
| --- | --- | --- |
| `firmware/` | `workspace/private/inputs/firmware/` | `A90_FIRMWARE_ROOT` |
| restored root `stage3/boot_linux*.img` | `workspace/private/inputs/boot_images/` | `A90_BOOT_IMAGE_ROOT` |
| `toolchains/` | `workspace/private/inputs/toolchains/` | `A90_TOOLCHAIN_ROOT` |
| `external_tools/` | `workspace/private/inputs/external_tools/` | `A90_EXTERNAL_TOOLS_ROOT` |
| `kernel_build/` | `workspace/private/inputs/kernel_source/` | `A90_KERNEL_SOURCE_ROOT` |
| active build outputs | `workspace/private/builds/` | `A90_BUILD_ROOT` |

Current source/script entrypoints live under `workspace/public/src/`. Historical
source/script paths stay under `workspace/public/archive/` as provenance files
or compatibility symlinks. Private payloads, toolchains, restored firmware,
downloaded source archives, and static helper binaries belong under the
workspace private roots above.

`workspace/public/src/native-init/` is the canonical source root for the current
native-init baseline. Only the latest/current source closure is migrated there;
historical `init_v*` files remain under
`workspace/public/archive/stage3/linux_init/` as provenance.
Generated boot images, ramdisks, cpio files, compiled init binaries, and
generated helper binaries should not be written to tracked source directories by
active builders.

Current revalidation script entrypoints live under
`workspace/public/src/scripts/revalidation/`. Historical revalidation scripts
and compatibility symlinks live under
`workspace/public/archive/scripts/revalidation/`.

### 4. Rebuild Ignored Boot Images

Boot images are not tracked. Restore trusted images from private backup or
rebuild in dependency order:

```bash
python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v724.py
python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v725_fasttransport.py
python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v726_wifi_lifecycle.py
python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v2169_transport_contract.py
python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v2174_wifi_urandom_connect.py
sha256sum workspace/private/inputs/boot_images/boot_linux_v2174_wifi_urandom_connect.img
```

The active builders write ramdisk/init/helper intermediates under
`workspace/private/builds/native-init/` and final baseline boot images under
`workspace/private/inputs/boot_images/`. The current V2174 baseline SHA is
recorded in the source-build, live-validation, and V2175 promotion reports.
Verify SHA before using an image for any flash/handoff cycle.

### 5. Create Private Wi-Fi Test Env Only When Needed

The connect runner loads this file first:

```bash
workspace/private/secrets/a90-wifi-test.env
```

Legacy fallback remains:

```bash
tmp/wifi/.wifi-test.env
```

An explicit override is also supported:

```bash
A90_WIFI_ENV_FILE=/path/to/env \
python3 workspace/public/src/scripts/revalidation/native_wifi_dhcp_ping_handoff_v2176.py
```

Template:

```bash
umask 077
cat > workspace/private/secrets/a90-wifi-test.env <<'ENV'
A90_WIFI_SSID=<ssid>
A90_WIFI_PSK=<passphrase>
ENV
chmod 600 workspace/private/secrets/a90-wifi-test.env
```

This file is local-only. It must not appear in logs, archives, commits, or public
artifact summaries.

### 6. Host NCM Setup

Use `docs/operations/A90_NCM_HOST_AUTOCONFIG.md` for host-side NetworkManager,
IPv6 link-local, and USB NCM readiness configuration. Do not encode host sudo
state into repository files.

### 7. Seal Check

```bash
python3 workspace/public/src/scripts/revalidation/inventory_tmp_artifacts.py --write-public --write-full-private

python3 workspace/public/src/scripts/revalidation/cleanup_tmp_wifi_artifacts.py \
  --legacy-build-products-only \
  --legacy-build-product-days 0 \
  --json

python3 workspace/public/src/scripts/revalidation/cleanup_tmp_classified_artifacts.py --all-safe --json

python3 workspace/public/src/scripts/revalidation/cleanup_stage3_artifacts.py
```

Expected after a clean bootstrap: no unexpected flat `tmp/wifi/v...` writers, no
review bucket, and no root `stage3/` scratch tree unless explicitly restored for
legacy inspection.

## Legacy Evidence Policy

Historical reports intentionally cite old `tmp/wifi/v...` paths. Do not bulk
rewrite those paths. They are provenance references, not active output
destinations.

For long-term cleanup of old local evidence:

1. Create a full private manifest under `workspace/private/archives/` or
   `tmp/logs/archive/`.
2. Create a redacted public index under `workspace/public/manifests/` or
   `docs/artifacts/`.
3. Compress the expanded evidence directory into `workspace/private/archives/`,
   `tmp/wifi/archive/`, or external private storage.
4. Verify archive SHA and redaction.
5. Delete the expanded local directory only after the manifest and archive are
   validated.

## Folder Reduction Priority

1. Safe generated outputs: use cleanup tools first.
2. `stage3` generated ramdisks/init/helper binaries: active writers should move
   to `workspace/private/builds/`; delete reproducible old products when space
   matters.
3. Legacy `tmp/wifi` evidence: bundle/archive before deleting expanded folders.
4. Large local inputs: keep under `workspace/private/inputs/` or external private
   storage and restore as needed.

## Do Not Commit

- Raw `tmp/` evidence or raw archives.
- Boot images, firmware, kernel build outputs, and extracted vendor files.
- Wi-Fi credentials, generated supplicant configs, DHCP leases, routes, ping
  transcripts, full MAC/BSSID/IP, or private allowlists.
- Host-specific NetworkManager/systemd/sudo files except redacted templates.
