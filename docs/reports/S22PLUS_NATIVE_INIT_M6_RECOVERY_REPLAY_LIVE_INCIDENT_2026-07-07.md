# S22+ Native-Init M6 Recovery-Replay Live Incident - 2026-07-07

## Verdict

M6 did not expose the recovery-replay USB-ACM control channel.

The M5B incident was first recovered cleanly to the rooted Magisk Android
baseline. M6 preflight then passed: the SHA-pinned `AGENTS.md` exception was
present, Android was stable, Magisk root was available, and the current boot
hash matched the known-good Magisk boot baseline. The M6 boot-only candidate AP
flashed successfully, but no ACM, Odin/download, ADB, or Samsung USB endpoint
appeared during the bounded M6 observation window.

Current status: **rollback clean**. The operator later entered download mode,
Codex ran the checked rollback helper, Android returned, Magisk root was
available, and the expected boot hash was verified again.

## Candidate

```text
AP.tar.md5             a12bd8f067375cb14ab9043da5bae37d1f93f82c1d70bccd8fa9cef2f616bee9
boot.img               7fe85c5973b930d777a670ac5997b0f26a51fa5b97705f5e467b0cecf501ffd2
M6 /init               7aecdf7a2c936b0785d20f5124667a8d682e9eb9678e77d20893889312860295
base boot              2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                 bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
vendor_ramdisk00       41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193
runtime                freestanding-raw-syscall
glibc_static_startup   false
```

The AP contained exactly one Odin member:

```text
boot.img.lz4
```

## Preflight

Dry-run passed before live flashing:

```text
dry-run ok: M6 candidate, rollback APs, AGENTS exception, Android stability, and boot hash verified
```

Relevant preflight facts from the live log:

```text
agents_exception_missing=[]
android_stability_result=ok samples=4
current_boot_hash_rc=0
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e  -
```

The M6 manifest parser-bound gates were also present:

```text
modules.load.recovery count       446
modules.load.recovery bytes       7239
runtime recovery-list buffer      32768
runtime module-name buffer        128
modules.load.recovery max name    30
modules.load.recovery all .ko     true
inline whitespace                 false
```

## Live Timeline

Private run log:

```text
workspace/private/runs/s22plus_m6_recovery_replay_live_gate_20260707T043949Z/s22plus_m6_recovery_replay_live_gate.txt
```

Key events:

```text
04:39:49Z  live helper start
04:39:59Z  preflight snapshot complete
04:39:59Z  adb reboot download requested
04:40:10Z  Odin/download device appeared for candidate flash
04:40:10Z  M6 candidate AP flash started
04:40:12Z  candidate Odin flash rc=0
04:40:12Z  M6 ACM/Odin/ADB observation started
04:42:12Z  m6_acm_seen=0
```

Observed during the M6 window:

```text
ACM devices           none
ADB transports        none
Odin transports       none
Samsung USB endpoint  none observed by host checks after helper exit
```

The helper exited with rc `4` and printed:

```text
M6 ACM did not appear. Enter download mode manually and run --rollback-from-download.
```

## Post-Helper State

After helper exit, host checks still showed no transport:

```text
adb devices -l       no devices
odin4 -l             no devices
lsusb Samsung/04e8   no devices
```

Codex then ran a bounded Odin polling loop for 180 iterations at 2 seconds per
iteration. It ended at `2026-07-07T04:48:40Z` with:

```text
odin-not-detected-after-wait
```

The operator later entered Samsung download mode. At
`2026-07-07T09:37:33Z`, the host saw exactly one Odin endpoint:

```text
/dev/bus/usb/002/098
```

Codex then ran the checked rollback helper:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m6_recovery_replay_live_gate.py \
  --rollback-from-download \
  --ack S22PLUS-M6-ROLLBACK-FROM-DOWNLOAD
```

Result:

```text
M6 rollback-from-download completed rc=0
log=workspace/private/runs/s22plus_m6_recovery_replay_live_gate_20260707T093733Z/s22plus_m6_recovery_replay_live_gate.txt
```

Post-rollback Android verification:

```text
adb device             SM-S906N/g0q
sys.boot_completed     1
init.svc.bootanim      stopped
verifiedbootstate      orange
Magisk root            uid=0(root) context=u:r:magisk:s0
boot hash              2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Retained evidence was absent:

```text
post_rollback_pstore_files=[]
post_rollback_pstore_marker_found=0
post_rollback_last_kmsg_marker_found=0
post_rollback_retained_marker_found=0
```

## Interpretation

This is a live NO-GO for M6. It proves that the host-side package, AGENTS gate,
Android baseline, and Odin candidate flash path were valid, but it does not
prove whether M6 `/init` reached the module replay, role-switch, configfs, or
UDC binding phases. Post-rollback pstore/last_kmsg retained no M6 marker.

The failure is still compatible with at least these possibilities:

```text
early boot rejection or crash before /init marker
module replay hang/crash before configfs
UDC/role/configfs failure before ACM enumeration
candidate parked without any host-visible transport
```

Do not infer a specific M6 root cause from the empty host transport alone.
The operator later characterized the device behavior as a boot loop; the
separate host-only operator postmortem
`docs/reports/S22PLUS_NATIVE_INIT_M6_BOOTLOOP_POSTMORTEM_OPERATOR_2026-07-07.md`
narrows the next hypothesis to "USB subset minus watchdog/reset-prone modules"
rather than repeating the full 446-module recovery replay.

## Required Recovery

Manual operator action was completed:

1. Force the phone into Samsung download mode.
2. Confirm the screen is in the final `Downloading...` state, not only the
   warning/continue screen.
3. Once `/usr/bin/odin4 -l` shows exactly one device, run the checked rollback
   helper:

   ```text
   PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
     workspace/public/src/scripts/revalidation/s22plus_m6_recovery_replay_live_gate.py \
     --rollback-from-download \
     --ack S22PLUS-M6-ROLLBACK-FROM-DOWNLOAD
   ```

4. After Android returns, verify:

   ```text
   sys.boot_completed=1
   init.svc.bootanim=stopped
   Magisk root available
   boot hash = 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
   ```

5. Collect retained pstore/last_kmsg through the rollback helper and record
   whether `S22_NATIVE_INIT_USB_ACM_M6` appears.

## Stop Rule

The M6 no-transport incident is recovered. Do not repeat M6 without a new
postmortem narrowing the next target; same-shape S22+ native-init boot flashes
are stopped until the next candidate has a fresh SHA-pinned `AGENTS.md`
exception and a specific hypothesis stronger than "replay more modules."
