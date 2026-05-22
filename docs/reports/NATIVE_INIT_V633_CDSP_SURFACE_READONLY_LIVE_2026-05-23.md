# Native Init V633 CDSP Read-Only Surface Report

- date: `2026-05-23 KST`
- status: `captured/live-readonly`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_cdsp_surface_collect_v633.py`
- evidence: `/home/temmie/dev/A90_5G_rooting/tmp/wifi/v633-cdsp-surface-readonly-20260523-051845`
- decision: `v633-cdsp-firmware-surface-missing`
- pass: `True`
- reason: native read-only evidence has firmware_class.path set to a vendor firmware path but no matching firmware mount is visible
- next: mount/verify firmware surfaces read-only before any CDSP write proof

## Scope

V633 contacts the current native device only through read-only shell
commands. It collects CDSP boot-node metadata, subsystem state, firmware
surface visibility, CDSP-related kernel threads, and CDSP-related dmesg
markers.

It does not write sysfs, boot ADSP/CDSP/SLPI, start daemons, start
service-manager, start Wi-Fi HAL, scan/connect/link-up, use credentials,
run DHCP, change routes, or ping externally.

## Command Results

| name | ok | rc | status | raw |
| --- | --- | --- | --- | --- |
| bootstatus | True | 0 | ok | /home/temmie/dev/A90_5G_rooting/tmp/wifi/v633-cdsp-surface-readonly-20260523-051845/bootstatus.txt |
| initial-hide | True | 0 | ok | /home/temmie/dev/A90_5G_rooting/tmp/wifi/v633-cdsp-surface-readonly-20260523-051845/initial-hide.txt |
| boot-cdsp-surface | True | 0 | ok | /home/temmie/dev/A90_5G_rooting/tmp/wifi/v633-cdsp-surface-readonly-20260523-051845/boot-cdsp-surface.txt |
| subsys-state | True | 0 | ok | /home/temmie/dev/A90_5G_rooting/tmp/wifi/v633-cdsp-surface-readonly-20260523-051845/subsys-state.txt |
| firmware-surface | True | 0 | ok | /home/temmie/dev/A90_5G_rooting/tmp/wifi/v633-cdsp-surface-readonly-20260523-051845/firmware-surface.txt |
| threads-cdsp | True | 0 | ok | /home/temmie/dev/A90_5G_rooting/tmp/wifi/v633-cdsp-surface-readonly-20260523-051845/threads-cdsp.txt |
| dmesg-cdsp | True | 0 | ok | /home/temmie/dev/A90_5G_rooting/tmp/wifi/v633-cdsp-surface-readonly-20260523-051845/dmesg-cdsp.txt |

## Marker Counts

| marker | count |
| --- | --- |
| boot_cdsp_dir | 2 |
| boot_cdsp_not_readable | 0 |
| subsys_cdsp | 22 |
| subsys_offline | 10 |
| subsys_online | 0 |
| firmware_path_vendor | 1 |
| firmware_mount | 0 |
| firmware_dir_missing | 5 |
| cdsp_firmware_name | 22 |
| sysmon_cdsp | 0 |
| service_notifier | 0 |
| fastrpc | 29 |
| direct_firmware_fail | 0 |

## Key Lines

| key | line |
| --- | --- |
| firmware_class_path | firmware_class.path=/vendor/firmware_mnt/image |
| boot_cdsp_line | --- /sys/kernel/boot_cdsp/boot |
| cdsp_subsys_line | name=cdsp |
| cdsp_state_line | state=OFFLINING |
| cdsp_firmware_line | firmware_name=cdsp |
| sysmon_cdsp_line | missing |
| direct_firmware_fail_line | missing |

## Guardrails

- sysfs write
- ADSP/CDSP/SLPI boot-node write
- boot_wlan/qcwlanstate write
- boot image build/flash
- daemon start
- service-manager start
- Wi-Fi HAL start
- scan/connect/link-up
- credential/DHCP/routing/external ping
