# V1050 PM Modem Pre-Holder Private Root Repair Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| source patch | `stage3/linux_init/helpers/a90_android_execns_probe.c` | `v1050-private-root-repair-source-pass` |
| build artifact | `tmp/wifi/v1050-execns-helper-v179-build/a90_android_execns_probe` | `v1050-helper-v179-build-pass` |

V1050 fixes the V1049 implementation error. The modem pre-holder now enters the
helper private root before opening `/dev/subsys_modem`, matching the namespace
where V1049 proved the node exists.

## Changes

- Helper marker bumped to `a90_android_execns_probe v179`.
- Usage output now includes:
  - `--allow-pm-full-contract-with-modem-holder`
  - `after-mdm-helper-esoc-fd-with-pm-full-contract-with-modem-holder`
- Modem pre-holder child now executes:
  - `setsid()`
  - `chroot(paths->root)`
  - `chdir("/")`
  - `open("/dev/subsys_modem", ...)`
- Confirmation is stricter: `modem_pre_holder_confirmed=1` requires an explicit
  child open-success report and a still-live holder child.
- Cleanup avoids a blocking wait on the holder after `SIGKILL`.

## Build Artifact

```text
path:   tmp/wifi/v1050-execns-helper-v179-build/a90_android_execns_probe
sha256: 9cb6d49849af181a87a5619e7b3ed7f0f513223ef97ce8b0599ce43694453a7b
size:   1188336 bytes
arch:   ELF 64-bit LSB executable, ARM aarch64, statically linked
```

Contract strings verified:

```text
a90_android_execns_probe v179
--allow-pm-full-contract-with-modem-holder
after-mdm-helper-esoc-fd-with-pm-full-contract-with-modem-holder
cnss_before_esoc.modem_pre_holder_child_chroot=1
cnss_before_esoc.modem_pre_holder_path=/dev/subsys_modem
cnss_before_esoc.modem_pre_holder_open_reported=%d
```

## Validation

```bash
scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v1050-execns-helper-v179-build/a90_android_execns_probe
sha256sum tmp/wifi/v1050-execns-helper-v179-build/a90_android_execns_probe
stat -c 'size=%s mode=%a' tmp/wifi/v1050-execns-helper-v179-build/a90_android_execns_probe
strings tmp/wifi/v1050-execns-helper-v179-build/a90_android_execns_probe | \
  rg 'a90_android_execns_probe v179|--allow-pm-full-contract-with-modem-holder|after-mdm-helper-esoc-fd-with-pm-full-contract-with-modem-holder|modem_pre_holder_child_chroot|modem_pre_holder_open_reported|modem_pre_holder_path'
```

## Guardrails

No device contact, helper deploy, daemon start, subsystem open, Wi-Fi HAL,
scan/connect, credentials, DHCP/routes, external ping, sysfs write, GPIO write,
partition write, boot image write, or firmware mutation occurred in V1050.

## Next

V1051 should be deploy-only for helper `v179`. V1052 should rerun the bounded
live gate and require:

```text
modem_pre_holder_child_chroot=1
modem_pre_holder_open_reported=1
modem_pre_holder_confirmed=1
pm_full_contract_seen=1
```

If `modem_pre_holder_open_reported=0` or `result_reported=0`, stop and classify
whether `/dev/subsys_modem` open is blocking in PIL rather than retrying
service-manager, HAL, scan/connect, or Wi-Fi bring-up.
