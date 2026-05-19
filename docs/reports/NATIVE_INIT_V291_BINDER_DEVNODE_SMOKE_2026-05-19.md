# Native Init v291 Binder Devnode Create/Cleanup Smoke

- date: `2026-05-19`
- scope: temporary Binder devnode create/stat/cleanup smoke
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- plan: `docs/plans/NATIVE_INIT_V291_BINDER_DEVNODE_SMOKE_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/wifi_binder_devnode_smoke.py`
- evidence:
  - plan mode: `tmp/wifi/v291-binder-devnode-smoke-plan/`
  - live mode: `tmp/wifi/v291-binder-devnode-smoke-live-20260519-140937/`

## Result

- decision: `binder-devnode-create-cleanup-pass`
- pass: `True`
- reason: temporary Binder devnodes were created, verified, and removed.

## Validation

Static validation passed:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_binder_devnode_smoke.py \
  scripts/revalidation/wifi_binder_devnode_feasibility.py \
  scripts/revalidation/a90ctl.py
git diff --check
```

Plan mode passed:

```bash
python3 scripts/revalidation/wifi_binder_devnode_smoke.py \
  --out-dir tmp/wifi/v291-binder-devnode-smoke-plan \
  plan
```

Live apply passed:

```bash
python3 scripts/revalidation/wifi_binder_devnode_smoke.py \
  --out-dir tmp/wifi/v291-binder-devnode-smoke-live-20260519-140937 \
  run --apply
```

## Live Steps

| Step | Result |
| --- | --- |
| pre `stat /dev/binder` | absent |
| pre `stat /dev/hwbinder` | absent |
| pre `stat /dev/vndbinder` | absent |
| `mknodc /dev/binder 10 81` | PASS |
| `mknodc /dev/hwbinder 10 80` | PASS |
| `mknodc /dev/vndbinder 10 79` | PASS |
| created `stat /dev/binder` | PASS |
| created `stat /dev/hwbinder` | PASS |
| created `stat /dev/vndbinder` | PASS |
| cleanup `run /cache/bin/toybox rm -f ...` | PASS |
| post `stat /dev/binder` | absent |
| post `stat /dev/hwbinder` | absent |
| post `stat /dev/vndbinder` | absent |

## Interpretation

The native shell can create the three Binder character nodes with the exact
major/minor values derived in v290, and the nodes can be removed cleanly. This
proves the missing Binder `/dev` surface can be repaired transiently in the
native init environment.

This does not prove Binder protocol usability. v291 deliberately did not open
the Binder devices, issue Binder ioctls, start service managers, or run Wi-Fi
HAL/`wificond`.

## Guardrails Kept

- no Binder device open
- no Binder ioctl
- no binderfs mount
- no service-manager execution
- no Wi-Fi daemon execution
- no QMI/QRTR packet
- no Wi-Fi scan/connect/link-up/credential/DHCP/routing
- no rfkill/ICNSS writes
- no Android partition write
- cleanup completed in the same tool run

## Next

- v292 should plan a Binder open-only static helper smoke.
- The helper should open and close `/dev/binder`, `/dev/hwbinder`, and
  `/dev/vndbinder` after temporary node creation.
- v292 must still avoid Binder ioctls, service-manager execution, HAL start,
  `wificond`, supplicant, hostapd, Wi-Fi scan, Wi-Fi connect, DHCP, and routing.
