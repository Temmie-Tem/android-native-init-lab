# Native Init V855 eSoC Node Parity Preflight Plan

## Goal

Verify that native init can safely materialize Android-equivalent eSoC/subsys
device nodes without opening them or starting actors.

## Inputs

- V854 classifier:
  `tmp/wifi/v854-esoc-actor-parity-classifier/manifest.json`
- Android node contract from V853:
  - `/dev/esoc-0` char `484:0`, mode `0660`, owner `root:radio`
  - `/dev/subsys_esoc0` char `236:9`, mode `0640`, owner `system:system`
  - `/dev/subsys_modem` char `236:0`, mode `0640`, owner `system:system`

## Method

1. Confirm native health with `bootstatus` and `selftest`.
2. Read `/proc/devices`, `/sys/class/subsys/*/dev`, and
   `/sys/bus/esoc/devices/esoc0` metadata.
3. Materialize only the Android-equivalent device nodes.
4. Scan `/proc/*/fd` symlinks to confirm no process holds the nodes.
5. Remove only nodes created by this run.
6. Confirm native health again.

## Guardrails

- No eSoC/subsys node open or ioctl.
- No actor service start: no `pm-service`, `mdm_helper`, `ks`, CNSS retry, or
  Wi-Fi HAL.
- No Wi-Fi scan/connect/link-up, credential use, DHCP/routes, or external ping.
- No GPIO/sysfs/debugfs write, subsystem state write, module load/unload, boot
  image write, or partition write.

## Success Criteria

- Native exposes `subsys` major `236` and `esoc` major `484`.
- Native sysfs exposes `subsys_esoc0`, `subsys_modem`, and `esoc0` metadata.
- All three Android-equivalent nodes are created with expected char major/minor,
  mode, and owner.
- No holder appears for those nodes.
- Cleanup removes all nodes created by the run.
- Native postflight remains `BOOT OK` with selftest `fail=0`.

## Commands

```bash
python3 scripts/revalidation/native_wifi_esoc_node_parity_preflight_v855.py \
  --out-dir tmp/wifi/v855-esoc-node-parity-preflight \
  --allow-node-materialization \
  --allow-node-cleanup \
  --assume-yes \
  run
```
