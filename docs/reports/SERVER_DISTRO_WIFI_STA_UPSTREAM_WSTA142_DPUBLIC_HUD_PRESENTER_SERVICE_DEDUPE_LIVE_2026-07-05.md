# WSTA142 D-public HUD Presenter Service Dedupe Live Pass

Date: 2026-07-05 09:45 KST

## Verdict

WSTA142 fixes and live-proves the stale-intent log-spam defect found in WSTA141.
The native presenter service now de-duplicates unchanged consumed intent content
and unchanged rejected intent content before re-running noisy validation.  New
stale content is still fail-closed rejected once, but the unchanged stale file no
longer emits `intent.reject=stale` every `100ms`.

The device is left resident on V3400 with the presenter service stopped and
final health clean.

## Source Change

- Added `A90WSTA142` live-visible dedupe markers.
- Added `same-content-consumed-or-rejected` policy marker.
- Added raw intent content cache for consumed intent bytes.
- Added raw intent content cache for rejected intent bytes.
- Skips repeated validation when the read intent bytes are identical to the last
  consumed or rejected content.
- Preserves fail-closed validation for new stale, forbidden, unknown, or invalid
  intent content.

## Build

- Cycle: `V3400`
- Init: `A90 Linux init 0.11.156 (v3400-dpublic-hud-presenter-service-dedupe)`
- Boot image:
  `workspace/private/inputs/boot_images/boot_linux_v3400_dpublic_hud_presenter_service_dedupe.img`
- Boot SHA256:
  `4bc7a216b4a370bae9c5d561e022d57cc2cfcfc42e0a50152ed5bd7d5a45e260`
- Candidate manifest:
  `workspace/private/builds/native-init/v3400-dpublic-hud-presenter-service-dedupe/dpublic-hud-presenter-service-dedupe.json`
- Native-init report:
  `docs/reports/NATIVE_INIT_V3400_DPUBLIC_HUD_PRESENTER_SERVICE_DEDUPE_SOURCE_BUILD_2026-07-05.md`

## Live Proof

Run dir:
`workspace/private/runs/server-distro/wsta142-dpublic-hud-presenter-service-dedupe-live-20260705T0940KST`

Checked flash:

- Local image SHA matched the pinned V3400 SHA.
- Recovery ADB came up before boot write.
- Remote pushed image SHA matched.
- Boot prefix readback SHA matched.
- Post-boot cmdv1 verify passed for `version` and `status`.

Post-boot health:

- `version`: `0.11.156`, build `v3400-dpublic-hud-presenter-service-dedupe`.
- `status`: `BOOT OK shell 5.1s`.
- `selftest`: `pass=12 warn=1 fail=0`.
- serial/NCM/tcpctl ready.

Service start:

- `A90WSTA140 start.pid=662`
- `A90WSTA140 start.done=1`
- `A90WSTA142 intent_dedupe=same-content-consumed-or-rejected`

Consumed-content dedupe:

- Fresh sequence `14201` presented:
  `dpublic-hud-presenter-service: presented framebuffer 1080x2400 on crtc=133`.
- Status file recorded `last_sequence=14201` and `present_rc=0`.
- After waiting beyond the `2000ms` stale window, service status still reported
  `status.state=running`, `status.drm_fd=1`, `status.debian_direct_kms=0`, and
  `A90WSTA142 status.intent_dedupe=same-content-consumed-or-rejected`.
- No `A90WSTA136 intent.reject=stale` appeared in the consumed stale-window
  status/readback transcripts.

Rejected-content dedupe:

- A new stale sequence `14202` with `monotonic_ms=1` emitted one fail-closed
  `A90WSTA136 intent.reject=stale ... stale_after_ms=2000`.
- After another stale window, service status again reported the dedupe marker and
  no repeated stale reject lines.

Stop and final health:

- `dpublic-hud-presenter-service stop --pid-file ... --release-drm` returned
  `A90WSTA140 stop.done=1`.
- Final `selftest` stayed `pass=12 warn=1 fail=0`.
- Final `status` stayed `BOOT OK`, V3400 resident, serial/NCM/tcpctl ready,
  and `autohud: stopped`.

No Wi-Fi association, DHCP, public tunnel/smoke, packet-filter mutation,
userdata mutation, Debian `switch_root`, forbidden partition write, PMIC,
regulator, GDSC, GPIO, backlight, or panel re-init action was performed.

## Validation

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_native_init_boot_v3400_dpublic_hud_presenter_service_dedupe.py \
  tests/test_build_native_init_boot_v3400_dpublic_hud_presenter_service_dedupe.py
```

Pass.

```sh
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_build_native_init_boot_v3399_dpublic_hud_presenter_service \
  tests.test_build_native_init_boot_v3400_dpublic_hud_presenter_service_dedupe
```

Pass, `10 tests`.

```sh
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  discover -s tests -p 'test_server_distro_wsta*.py'
```

Pass, `458 tests`.

## Next

WSTA143 can proceed to the Debian handoff survival proof: start the V3400 durable
native presenter, perform the bounded Debian handoff, prove the same native
presenter PID survives and remains the sole DRM owner, prove Debian/a90hud has no
DRM fd, then prove a fresh Debian-written intent is consumed after handoff.
