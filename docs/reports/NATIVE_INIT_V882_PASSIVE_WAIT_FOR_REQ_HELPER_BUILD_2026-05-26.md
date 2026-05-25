# V882 Passive WAIT_FOR_REQ Observer Helper Build Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| helper build | `tmp/wifi/v882-execns-helper-v139-build/manifest.json` | `v882-helper-v139-build-pass` |

V882 was source/build-only. It did not contact the device, did not deploy the
helper, did not execute live eSoC ioctls, did not open `/dev/subsys_esoc0`, and
did not bring up Wi-Fi.

## Changes

- Updated `stage3/linux_init/helpers/a90_android_execns_probe.c` to helper
  marker `a90_android_execns_probe v139`.
- Extended `wifi-companion-esoc-req-registered-subsys-hold-preflight` with a
  passive `ESOC_WAIT_FOR_REQ` observer.
- The observer runs in a separate killable child under the hold-window process
  group and records request, rc, errno, value, elapsed time, and cleanup
  markers.
- Kept `ESOC_NOTIFY`, explicit userspace `PWR_ON`, direct userspace
  `CMD_EXE`, actor starts, Wi-Fi HAL, scan/connect, DHCP/routes, credentials,
  and external ping blocked.
- Tightened timeout cleanup so a surviving observer pipe/process turns into
  `reboot-required` evidence instead of an unbounded host wait.

## Build

```text
bash scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v882-execns-helper-v139-build/a90_android_execns_probe
```

Artifact:

- path: `tmp/wifi/v882-execns-helper-v139-build/a90_android_execns_probe`
- size: `1057232`
- sha256:
  `077ced65ae5b0b546ecdf3b1bb0c808d3ec34bfa2462516e6ceba170b18f23c5`
- type: static AArch64 ELF
- dynamic section: absent

String checks passed for:

- `a90_android_execns_probe v139`
- `wifi-companion-esoc-req-registered-subsys-hold-preflight`
- `--allow-esoc-req-registered-subsys-hold-preflight`
- `esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.begin=1`
- `esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.mode=passive`
- `esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.result=%s`
- `esoc_req_registered_subsys_hold_preflight.notify_attempted=0`
- `esoc_req_registered_subsys_hold_preflight.result=reboot-required`

## Interpretation

V882 implements the source support needed to classify whether SDX50M emits an
eSoC request during the future REQ-registered subsystem-hold window. If a later
live run observes no request while mdm3 progresses, that supports the
PCIe/self-boot path. If a request appears, the next gate must classify it before
any `ESOC_NOTIFY` implementation.

## Guardrails

- No helper deploy or device contact in V882.
- No live `REG_REQ_ENG`, `REG_CMD_ENG`, `CMD_EXE`, `PWR_ON`,
  `WAIT_FOR_REQ`, `NOTIFY`, or `/dev/subsys_esoc0` open.
- No actor start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external
  ping, boot image write, partition write, firmware mutation,
  GPIO/sysfs/debugfs write, module load/unload, or reboot.

## Next

V883 should deploy helper `v139` only and prove checksum/version/mode parity.
The bounded live REQ-registered subsystem-hold proof should wait until the
helper is deployed.
