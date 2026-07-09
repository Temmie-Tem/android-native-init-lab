# S22+ M34 S8B1 Live Consumed: B1 Miss (2026-07-09)

## Verdict

S8B1 live was executed once under the active AGENTS exception and is now
consumed. The one-bit download-beacon probe returned MISS:

```text
download-beacon-miss-parked-manual-download-required
```

This proves B1 was observed and false in native-init under the S7A2 module
recipe. Do not proceed to B2/B3/B4 or descriptor/composition work from this
result.

## Live Run

Run directory:

```text
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T042547Z_live/
```

Pinned candidate:

```text
AP.tar.md5 SHA256: 0bf313cdf24a5f5babc3d0073a1e90686f1b734b6dafdfa548154ef3eac6c2c8
boot.img SHA256:   4e599087f242fdf2ae6bee1465e0725b60057bad893b665a178bcf87b88b9a20
/init SHA256:      a1cbc9828a24a7e302bd569de93b4f41e2ceb159130ea373d2ea9c9572f5a20d
```

Result summary:

```text
result=download-beacon-miss-parked-manual-download-required
rc=0
rollback_target=magisk
android_serial=<S22_SERIAL_REDACTED>
```

Timeline events were ordered and monotonic:

```text
live_session_start
candidate_flash_start
candidate_flash_done
candidate_boot_ready
manual_after_miss_rollback_flash_start
rollback_flash_start
manual_after_miss_rollback_flash_done
rollback_flash_done
rollback_boot_ready
manual_after_miss_rollback_boot_ready
live_session_end
```

The operator observed no bootloop during the candidate window. The helper did
not observe a new Odin Download endpoint during the bounded 90 second beacon
window, then waited for manual Download rollback. Manual Download appeared as:

```text
/dev/bus/usb/002/108
```

## Analyzer

Analyzer output:

```text
decision=s22plus-m34-s8b1-b1-miss-stop-at-typec-or-i2c
b1_observed=true
b1_state=false
ok_to_advance=false
ok_to_live_next_stage=false
magisk_baseline_restored=true
timeline_errors=[]
errors=[]
```

Fail-closed gates behaved correctly:

```text
--require-advance: nonzero, s22plus-m34-s8b1-b1-miss-stop-at-typec-or-i2c
--require-live-next-stage: nonzero, s22plus-m34-s8b1-b1-miss-stop-at-typec-or-i2c
```

## Post-Rollback Baseline

Post-rollback Android returned cleanly:

```text
adb serial: <S22_SERIAL_REDACTED>
sys.boot_completed=1
ro.boot.verifiedbootstate=orange
ro.boot.bootreason=reboot,download
ro.build.version.incremental=S906NKSS7FYG8
su id: uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
boot SHA256: 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

The S8B1 AGENTS exception is retired after this run. The consumed live and
rollback ack tokens are no longer active authorization.

## Interpretation

On Android, the same preflight sees:

```text
/sys/bus/i2c/devices/57-0066 exists
/sys/class/typec/port0 absent
/sys/devices/platform/soc/994000.i2c/i2c-57/57-0066/max77705-usbc/typec/port0 exists
/sys/devices/platform/soc/994000.i2c/i2c-57/57-0066/max77705-usbc/typec/port0/port0-partner exists
```

S8B1 in native-init did not hit even the OR predicate
`/sys/class/typec/port0 OR /sys/bus/i2c/devices/57-0066`. The immediate
host-only follow-up is S8B1A, which keeps the same recipe but widens the I2C
predicate to `/sys/bus/i2c/devices/*-0066` so the Android bus-number assumption
is tested before touching downstream USB behavior.

S8B1A host-build report:

```text
docs/reports/S22PLUS_NATIVE_INIT_M34_S8B1A_WIDE_I2C_BEACON_HOST_BUILD_2026-07-09.md
```
