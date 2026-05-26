# V1003 Helper v170 Deploy Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| deploy final parity | `tmp/wifi/v1003-execns-helper-v170-deploy-final/manifest.json` | `execns-helper-v170-deploy-pass` |

V1003 confirms `/cache/bin/a90_android_execns_probe` is helper `v170` with the
V1002 service-window subsystem trigger contract. No daemon or Wi-Fi bring-up ran.

## Deploy Notes

- A first `--serial-chunk-size 3000` attempt failed closed before transfer:
  `chunks_written=0`, line limit check failed.
- The stable serial path with chunk size `1850` transferred the helper:
  `chunks=886`, `chunks_written=886`, `line_check_ok=True`.
- The first postflight after transfer was blocked by a V1003 wrapper verifier
  bug: it required result strings that are present in `strings` output but not
  in no-argument usage output.
- The wrapper was corrected to use usage-visible contract tokens, and final
  parity passed without retransmission because the remote helper was already
  current.

## Results

| Item | Result |
| --- | --- |
| local helper v170 | PASS |
| native health | PASS |
| service-manager process surface | clean |
| Wi-Fi link surface | clean |
| remote helper sha | PASS |
| remote helper contract | PASS |
| approval gate | PASS |

Remote helper sha256:

```text
edbccfef2fd117c5264c140ff5b2f4cec5424c917151607cecc309268cd9c254  /cache/bin/a90_android_execns_probe
```

Post-check health:

```text
boot: BOOT OK shell 4.2s
selftest: pass=11 warn=1 fail=0
exposure: ncm=absent tcpctl=stopped rshell=stopped boundary=usb-local
```

## Guardrails

- helper deploy/parity only;
- no SELinux policy load;
- no service-manager start;
- no Wi-Fi HAL start;
- no `wificond` start;
- no CNSS daemon start;
- no `/dev/subsys_esoc0` open;
- no eSoC ioctl;
- no scan/connect/link-up;
- no credential use;
- no DHCP, route mutation, external ping, boot image write, or partition write.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_helper_v170_deploy_v1003.py
python3 scripts/revalidation/native_wifi_helper_v170_deploy_v1003.py plan
python3 scripts/revalidation/native_wifi_helper_v170_deploy_v1003.py preflight
python3 scripts/revalidation/native_wifi_helper_v170_deploy_v1003.py \
  --approval-phrase "approve v1003 deploy execns helper v170 only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

Final result:

```text
decision: execns-helper-v170-deploy-pass
pass: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Next

V1004 should run current-boot SELinux refresh plus the new service-window scoped
subsystem trigger capture. It must not perform Wi-Fi scan/connect, use
credentials, mutate DHCP/routes, or ping externally.
