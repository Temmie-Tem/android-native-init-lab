# WSTA136 D-public Native HUD Presenter Source Proof

- Status: `PASS`
- Timestamp: `2026-07-05 08:32 KST`
- Decision: `wsta136-dpublic-native-presenter-source-pass`
- Source proof: `workspace/private/runs/server-distro/wsta136-dpublic-native-presenter-source-20260705T0830KST/wsta136_dpublic_native_presenter_source.json`
- Build report: `docs/reports/NATIVE_INIT_V3398_DPUBLIC_HUD_PRESENTER_SOURCE_BUILD_2026-07-05.md`

## Purpose

WSTA135 proved the Debian userdata appliance can write a bounded HUD intent while
leaving direct display presentation unstarted. WSTA136 adds the native/root-owned
consumer side: native-init now has a display command that reads the bounded intent,
rejects unsafe or stale content, and presents the HUD through native KMS ownership.

## Source Change

- Added native-init command `dpublic-hud-presenter [validate|present] [intent-path]`.
- Default intent path is `/run/a90-dpublic/hud-intent.json`.
- Accepted schema is `a90-dpublic-hud-intent-v1`.
- Intent reads are bounded to `4096` bytes and use `O_NOFOLLOW` plus regular-file checks.
- Stale intents are rejected after `2000ms`; future monotonic timestamps are rejected.
- Forbidden top-level fields such as command, argv, shell, URL, SSID, PSK, token, and secret are rejected.
- Unknown top-level fields are rejected fail-closed.
- `validate` mode performs parse/policy validation without opening or presenting KMS.
- `present` mode draws a minimal native HUD and calls the existing native KMS path.
- Debian remains an intent producer; the source markers record `presenter.owner=native-init-root` and `presenter.debian_direct_kms=0`.

## Build

V3398 source-built successfully:

- Init: `A90 Linux init 0.11.154 (v3398-dpublic-hud-presenter)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3398_dpublic_hud_presenter.img`
- Boot SHA256: `b18be6a39eb41fb71a5256db3b23d5c648631fb164061b98b35a35ffba9f3a0c`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3397_wsta_execute_gate_screen.img`

No flash, native reboot, switch-root, public tunnel, Wi-Fi connect, DHCP, packet-filter mutation,
DRM open, or KMS SETCRTC was performed by this WSTA136 source unit.

## Validation

Host/source validation passed:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta136_dpublic_native_presenter_source.py \
  workspace/public/src/scripts/revalidation/build_native_init_boot_v3398_dpublic_hud_presenter.py \
  workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py

bash -n workspace/public/src/scripts/server-distro/a90_dpublic_firstboot.sh

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_dpublic_smoke_helpers tests.test_prepare_wsta3_sta_rootfs

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta136_dpublic_native_presenter_source.py \
  --run-id wsta136-dpublic-native-presenter-source-20260705T0830KST \
  --run-dir workspace/private/runs/server-distro/wsta136-dpublic-native-presenter-source-20260705T0830KST

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_native_init_boot_v3398_dpublic_hud_presenter.py
```

The focused unittest run reported `Ran 48 tests` and `OK`. The WSTA136 source proof
reported all required presenter contract checks passing.

## Next

WSTA137 should live-gate this through native execution: boot or hot-reload V3398 under
the normal rollback gates, feed a fresh bounded intent, run `dpublic-hud-presenter validate`,
then run `dpublic-hud-presenter present` and verify the native KMS HUD appears while Debian
still has no direct DRM/KMS presenter.
