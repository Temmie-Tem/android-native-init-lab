# V878 eSoC Engine Register Preflight Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| plan | `tmp/wifi/v878-esoc-engine-register-preflight-plan/manifest.json` | `v878-esoc-engine-register-preflight-plan-ready` |
| missing-flags negative | `tmp/wifi/v878-esoc-engine-register-preflight-missing-flags/manifest.json` | `v878-esoc-engine-register-preflight-approval-required` |
| live | `tmp/wifi/v878-esoc-engine-register-preflight-live/manifest.json` | `v878-esoc-engine-register-ioctl-review` |

V878 executed the bounded live helper `v137` eSoC engine registration preflight.
This was not an mdm3 power-on attempt and not a Wi-Fi bring-up attempt.

## Live Findings

| Item | Value |
| --- | --- |
| helper mode | `wifi-companion-esoc-engine-register-preflight` |
| CMD fd | `3` |
| REQ fd | `4` |
| `REG_CMD_ENG` | rc `-1`, errno `16` |
| `REG_REQ_ENG` | rc `0`, errno `0` |
| hold | `6s` |
| helper result | `engine-register-preflight-complete` |

Private node proof:

- `/dev/esoc-0`: present in helper namespace
- `/dev/subsys_esoc0`: present in helper namespace
- `/dev/subsys_modem`: present in helper namespace

Important interpretation:

- The critical REQ engine registration path is live and returned rc `0`.
- CMD engine registration returned `EBUSY`; this blocks any direct userspace
  `ESOC_CMD_EXE` plan until command-engine ownership is classified.
- The helper `v137` open errno fields are stale when fd is non-negative because
  errno was not cleared before successful `open()`. Interpret fd `3` and fd `4`
  as successful opens.

Postflight dmesg filter recorded:

```text
mdm-4x esoc0: Client hooks not registered for the device
```

## Cleanup and Health

| Check | Result |
| --- | --- |
| created nodes removed | pass |
| postflight bootstatus | pass |
| postflight selftest | `pass=11 warn=1 fail=0` |
| actor hits | `0` |
| Wi-Fi link hits | `0` |

## Guardrails

- Only `REG_CMD_ENG` and `REG_REQ_ENG` were attempted.
- No `CMD_EXE`, `PWR_ON`, `WAIT_FOR_REQ`, `NOTIFY`, or `/dev/subsys_esoc0`
  open occurred.
- No actor start, no `mdm_helper`, no `ks`, no `pm_proxy_helper`, no CNSS, no
  service-manager trio, and no Wi-Fi HAL.
- No scan/connect, credentials, DHCP/routes, external ping, module load/unload,
  boot image write, partition write, or firmware mutation occurred.

## Reference Notes

- Android msm `esoc_dev.c` registers request and command engines through
  `ESOC_REG_REQ_ENG` and `ESOC_REG_CMD_ENG`, and gates direct `ESOC_CMD_EXE`
  access on command-engine ownership:
  https://android.googlesource.com/kernel/msm/+/dd4275868d0fdb79752a8e7a8f1f51396263b9dd/drivers/esoc/esoc_dev.c
- Qualcomm mdm/esoc debug diff confirms `ESOC_REQ_ENG_ON` completes the request
  engine wait path and logs command/request registration failures:
  https://android.googlesource.com/kernel/msm/+/d210dd22d8bfbd55a320f57eaac861137dd3eca0%5E2..d210dd22d8bfbd55a320f57eaac861137dd3eca0/

## Interpretation

V878 narrowed the blocker. `/dev/esoc-0` can register the REQ engine, but the
CMD engine is already busy or otherwise unavailable to this helper. The next
safe unit is not a blind retry; it is a host-only classifier for CMD engine
ownership, the meaning of the `Client hooks not registered` dmesg line, and
whether the next live gate should use the subsystem powerup path after REQ
registration rather than direct userspace `ESOC_CMD_EXE`.

## Next

V879 should be host-only first:

1. classify `REG_CMD_ENG` `EBUSY` against public `esoc_dev.c` and local
   Samsung evidence,
2. repair helper stale successful-open errno reporting in a later helper build,
3. define the exact guardrails for any future `/dev/subsys_esoc0` hold or
   kernel-side powerup window.
