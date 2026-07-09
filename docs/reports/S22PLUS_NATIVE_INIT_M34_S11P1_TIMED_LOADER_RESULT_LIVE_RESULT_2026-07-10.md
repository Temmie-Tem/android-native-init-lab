# S22+ M34 S11P1 Timed Loader-Result Live Result

Date: 2026-07-10 KST / 2026-07-09 UTC

## Verdict

S11P1 live result is a timed-beacon MISS, not a loader-result HIT.

The candidate flashed and left the original Odin Download endpoint, but no new
Download endpoint appeared during the bounded 180s observation window. Because
S11P1 encodes its loader result only by delaying before `reboot(download)`, the
absence of a timed Download beacon means none of the delay buckets were proven:

```text
6s    modules open/read failure
12s   cmd-db was not attempted
18s   cmd-db rc was not accepted
20s+N first failing module index N
116s  no first failure, watchdog absent from /proc/modules
122s  watchdog visible, cmd_db absent from /proc/modules
128s  watchdog and cmd_db visible in /proc/modules
```

The S11P1 one-shot live exception is consumed and must not be reused for another
S11P1/S11P0/S10 repeat or any other boot candidate.

## Evidence

Primary live run:

```text
run_dir=workspace/private/runs/s22plus_m34_s11p1_timed_loader_result_live_gate_20260709T173415Z
result=download-beacon-miss-manual-download-required
rc=0
stage=S11P1
target=SM-S906N/g0q/S906NKSS7FYG8
schema=s22plus_m34_s11p1_timed_result_v1
module_load_probe=timed_first_failure_or_proc_modules_result
probe_module=cmd-db.ko
probe_proc_name=cmd_db
positive_control_proc_names=qcom_wdt_core,gh_virt_wdt
candidate_ap_sha256=1bc209674aa6b496bcc4132eae4343c1311de06143164771994cc8b1df945b56
candidate_boot_sha256=874c312b4ce1b95388c158a686f22e56d7a5278dd09cfab13c0c853ab688c61e
candidate_init_sha256=af4eb75a8bcdcbbe8bd4fe81e1100cbc34ef786c1c2e64b09b111582c727c3d1
base_boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

The result JSON had no `candidate_timed_download_elapsed_sec` field because no
timed self-Download endpoint was observed.

Timeline:

```text
live_session_start     2026-07-09T17:34:19.087216Z
candidate_flash_start  2026-07-09T17:34:30.649503Z
candidate_flash_done   2026-07-09T17:34:32.185626Z
candidate_boot_ready   2026-07-09T17:34:32.462931Z
rollback_flash_start   2026-07-09T17:40:00.213570Z
rollback_flash_done    2026-07-09T17:40:01.550660Z
rollback_boot_ready    2026-07-09T17:40:46.352029Z
live_session_end       2026-07-09T17:40:46.721525Z
```

The operator observed no bootloop during the candidate window. After the beacon
miss, manual Download entry was required for recovery.

## Rollback State

Manual Download rollback restored the pinned Magisk boot-only AP:

```text
rollback_target=magisk
rollback_device=/dev/bus/usb/002/015
rollback_odin_rc=0
```

Post-rollback verification:

```text
adb device=RFCT519XWGK usb:2-1.3 product:g0qksx model=SM_S906N device=g0q
boot_completed=1
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
incremental=S906NKSS7FYG8
vbstate=orange
boot_recovery=0
su_root_rc=0
su_root_out=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Current host checks after the helper returned also confirmed:

```text
adb devices -l -> RFCT519XWGK device
sys.boot_completed=1
ro.boot.verifiedbootstate=orange
su -c id -> uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
sha256sum /dev/block/by-name/boot -> 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

## Retained Evidence

Retained evidence did not contain the S11P1 marker:

```text
grep -a S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S11P1 /proc/last_kmsg -> no match
/sys/fs/pstore -> empty
```

That means this run cannot prove whether the direct native `/init` reached the
S11P1 marker, reached the module loop, slept, or failed before the timed
`reboot(download)` request. The only host-visible candidate result is the
bounded absence of the timed Download beacon.

## Interpretation

S11P1 was designed to turn the S11P0 one-bit parked MISS into a timed result.
The miss means the current observation channel is still too late in the
candidate flow: if native-init dies, resets, parks, or cannot execute
`reboot(download)`, all those states collapse into the same host observation.

This does not contradict S10/S11's module-loading hypothesis. It means the next
unit should first improve observability around early native-init progress and
the reboot/download request path, then return to per-module result decoding.

## Next Step

Next work should be host-only design before another live boot candidate. The
strongest follow-up is an earlier, more reliable observation path that does not
depend solely on the candidate reaching a delayed `reboot(download)` after the
module loop. Any new live run needs a fresh narrow `AGENTS.md` exception and new
explicit operator approval.
