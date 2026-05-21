# Native Init V585 Private Firmware Mount Gate

- date: `2026-05-22 KST`
- objective: move V584 firmware/modem mount parity from a global proof into the helper-owned private Android namespace used by bounded companion start-only tests
- status: `implemented/preflight-ready`; live companion start has **not** run in V585 yet

## Scope

- Helper:
  - `stage3/linux_init/helpers/a90_android_execns_probe.c`
  - version marker: `a90_android_execns_probe v97`
- Host tooling:
  - `scripts/revalidation/wifi_execns_helper_v97_deploy_preflight.py`
  - `scripts/revalidation/native_wifi_companion_firmware_mount_start_only_v585.py`
- Built artifact:
  - `tmp/wifi/v585-a90_android_execns_probe-v97/a90_android_execns_probe`

## Guardrails

- Deploy wrapper does not start daemons.
- V585 live runner starts only bounded companion services.
- No service-manager.
- No Wi-Fi HAL or `IWifi.start()`.
- No qcwlanstate write.
- No scan/connect/link-up/DHCP/routing.
- No external ping.
- Firmware/modem mounts are read-only.

## Implementation

Helper v97 adds private namespace firmware mounts after the private vendor mount:

```text
apnhlos -> /vendor/firmware_mnt
modem   -> /vendor/firmware-modem
```

The helper resolves partitions through `/sys/class/block/*/uevent`, creates temporary block nodes under its helper-owned temp directory, mounts both partitions read-only as `vfat`, and unmounts/removes temp nodes during helper cleanup.

The helper now emits:

```text
firmware_mnt_mount_source=<temp-node-or-not-mounted>
firmware_modem_mount_source=<temp-node-or-not-mounted>
```

## Static Verification

Commands:

```text
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v97_deploy_preflight.py scripts/revalidation/native_wifi_companion_firmware_mount_start_only_v585.py
bash scripts/revalidation/build_android_execns_probe_helper.sh tmp/wifi/v585-a90_android_execns_probe-v97/a90_android_execns_probe
strings tmp/wifi/v585-a90_android_execns_probe-v97/a90_android_execns_probe | rg "a90_android_execns_probe v97|firmware_mnt_mount_source|firmware_modem_mount_source|mount firmware partition"
```

Result:

```text
sha256=82ef904d6fdadbd0954b0fdc016d64f733f802cbca954b143970f86a044bf812
marker=a90_android_execns_probe v97
required strings present
```

## Deploy Preflight

Command:

```text
python3 scripts/revalidation/wifi_execns_helper_v97_deploy_preflight.py --transfer-method serial preflight
```

Result:

```text
decision: execns-helper-v97-deploy-preflight-ready
pass: True
reason: preflight complete; helper v97 deploy still requires exact approval
next: deploy helper v97, then run V585 companion firmware mount proof
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Evidence:

- `tmp/wifi/v585-execns-helper-v97-deploy-preflight/`

## Interpretation

- V584 proved the firmware/modem partitions can be mounted read-only and cleaned up.
- V585 fixes the namespace mismatch: the companion daemons run in the helper-owned private Android namespace, so the firmware/modem mounts must exist there, not only in the global native root.
- The next live step is v97 deployment, then bounded companion start-only using the V585 runner.

## Next Gate

1. Deploy helper v97 to `/cache/bin/a90_android_execns_probe`.
2. Run `native_wifi_companion_firmware_mount_start_only_v585.py preflight`.
3. Run bounded V585 live only if preflight passes.
4. If readiness markers still do not appear, inspect companion stderr/stdout and QRTR deltas before any qcwlanstate or Wi-Fi HAL retry.
