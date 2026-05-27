# Native Init V1132 Subsys Nonblock Semantics Classifier Report

Date: `2026-05-27`

## Result

- Decision: `v1132-subsys-open-nonblock-unsupported-route-closed`
- Pass: `true`
- Evidence: `tmp/wifi/v1132-subsys-nonblock-semantics-classifier/manifest.json`
- Summary: `tmp/wifi/v1132-subsys-nonblock-semantics-classifier/summary.md`
- Classifier:
  `scripts/revalidation/native_wifi_subsys_nonblock_semantics_classifier_v1132.py`
- Source input:
  `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/subsystem_restart.c`

## Summary

V1132 is a host-only classifier for the V1131 `/dev/subsys_modem`
pre-holder result.

It confirms that another `O_NONBLOCK` `/dev/subsys_modem` pre-holder retry is
not meaningful.

The local Samsung OSRC source shows:

```text
subsys_device_open() lines 1625-1645
  -> subsystem_get_with_fwname()
  -> no file->f_flags check
  -> no O_NONBLOCK / FMODE_NONBLOCK branch

__subsystem_get()
  -> when count == 0, synchronously calls subsys_start()

subsys_start()
  -> synchronously calls desc->powerup()
```

V1131 runtime evidence already proved the matching behavior:

```text
helper v213 modem pre-holder requested/allowed/started
modem_pre_holder_plain_retry=0
modem_pre_holder_open_reported=false
modem_pre_holder_result_reported=false
modem_pre_holder_confirmed=false
pm-service Binder worker path=/dev/subsys_modem
pm-service Binder worker wchan=__subsystem_get
mss=OFFLINING
mdm3=OFFLINING
WLFW/service69/wlan0 absent
```

## Interpretation

The subsystem char-device open path is synchronous and does not implement
nonblocking behavior. `O_NONBLOCK` is ignored by this driver because
`subsys_device_open()` never inspects `file->f_flags`.

The V1131 result is therefore expected:

```text
open("/dev/subsys_modem", O_RDONLY | O_NONBLOCK | O_CLOEXEC)
  -> subsys_device_open()
  -> subsystem_get_with_fwname("modem", ...)
  -> __subsystem_get()
  -> subsys_start()
  -> desc->powerup()
  -> wait path / __subsystem_get blocker
```

This closes the synthetic `/dev/subsys_modem` first-opener route. The blocker is
not a host-side open flag or holder timing problem.

## Safety

V1132 did not perform:

```text
device_commands_executed=false
device_mutations=false
tracefs_write_executed=false
pm_actor_executed=false
cnss_daemon_start_executed=false
wifi_hal_start_executed=false
scan_connect_executed=false
credential_use_executed=false
dhcp_route_executed=false
external_ping_executed=false
partition_write_executed=false
flash_executed=false
```

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_subsys_nonblock_semantics_classifier_v1132.py
python3 scripts/revalidation/native_wifi_subsys_nonblock_semantics_classifier_v1132.py
```

Result:

```text
decision: v1132-subsys-open-nonblock-unsupported-route-closed
pass: True
```

## Next

Do not repeat `/dev/subsys_modem` plain/nonblocking pre-holder retries.

The next closest route to native Wi-Fi bring-up is lower eSoC/SDX50M
precondition classification:

1. compare Android-good `mdm_helper`/`pm_proxy_helper`/`pm-service` ordering
   against native V1131;
2. classify whether the missing piece is still eSoC request-engine/PWR_ON
   sequencing, PMIC GPIO9 soft-reset behavior, GPIO142 readiness, or a PM
   service transaction field;
3. keep the next unit host-only/read-only until a narrower live trigger is
   justified;
4. continue forbidding `/dev/subsys_esoc0`, Wi-Fi HAL, scan/connect,
   credentials, DHCP/route, external ping, partition writes, boot image writes,
   and flash.
