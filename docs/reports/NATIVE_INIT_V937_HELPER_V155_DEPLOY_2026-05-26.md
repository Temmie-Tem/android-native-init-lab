# Native Init V937 Helper v155 Deploy Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| deploy-only wrapper | `scripts/revalidation/native_wifi_helper_v155_deploy_v937.py` | static validation pass |
| live deploy | `tmp/wifi/v937-execns-helper-v155-deploy/manifest.json` | `execns-helper-v155-deploy-pass` |

V937 deployed helper `a90_android_execns_probe v155` to
`/cache/bin/a90_android_execns_probe` over the serial bridge. No daemon,
service-manager, Wi-Fi HAL, scan/connect, credential use, DHCP/route, external
ping, eSoC ioctl, subsystem open, GPIO/sysfs/debugfs write, boot image write, or
partition write was executed.

## Artifact

- Local artifact:
  `tmp/wifi/v936-execns-helper-v155-build/a90_android_execns_probe`.
- Remote path:
  `/cache/bin/a90_android_execns_probe`.
- SHA-256:
  `44d7820e7bc33ab9886ea4f5f39248b1902c404c694c48fcd00a3ecc0fb76063`.
- Marker:
  `a90_android_execns_probe v155`.

## Transfer

- Method: serial appendfile + uudecode.
- Chunk size: `1850`.
- Chunks written: `837`.
- Encoded bytes: `1547035`.
- Line-safety check: pass.
- `cmdv1x` path: used.

NCM was not active on the host at deploy time, so HTTP transfer was not used.
The bridge on `127.0.0.1:54321` was active and serial deploy completed.

## Postflight

Post-deploy wrapper checks passed:

- native health: `BOOT OK`, `selftest fail=0`;
- service-manager processes: clean;
- Wi-Fi link surface: clean;
- remote helper SHA and usage contract: pass;
- approval gate: pass.

Manual postflight after deploy also passed:

```bash
python3 scripts/revalidation/a90ctl.py bootstatus
python3 scripts/revalidation/a90ctl.py selftest
python3 scripts/revalidation/a90ctl.py netservice status
```

Observed:

- `bootstatus`: `BOOT OK shell 4.2s`;
- `selftest`: `pass=11 warn=1 fail=0`;
- `netservice`: flag disabled, `ncm0` present, `tcpctl` stopped.

## Guardrails

- Deploy-only mutation under `/cache/bin`.
- No live actor start.
- No Wi-Fi bring-up.
- No eSoC/subsystem trigger.
- No credentials used.

## Next

Run a bounded `wifi-companion-mdm-helper-runtime-contract-capture` live capture
with helper `v155` to collect the new `mdm_helper_lower_contract` evidence. Do
that before any eSoC trigger retry or Wi-Fi HAL bring-up attempt.
