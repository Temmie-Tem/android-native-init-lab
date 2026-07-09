# V3409 S22+ O1.1 Live Pass

## Verdict

`PASS`. The single authorized O1.1 boot-only candidate completed the framed
stock-USB control proof and the checked helper completed mandatory Magisk
boot-only rollback. The one-shot exception is consumed.

Private run evidence:

```text
workspace/private/runs/s22plus_o11_stock_first_stage_control_live_gate_20260709T193558Z
```

## Candidate Identity

- Target: `SM-S906N/g0q/S906NKSS7FYG8`
- Candidate AP SHA256:
  `c43eeb83cedb2db3e0758de71050ef2960765740face7378fcc285a5b8188730`
- Candidate padded boot SHA256:
  `1e59b172edda0d2c717a93021c9084af1393c0c4db7d28eeb10e06c0b1787b0d`
- AP members: exactly `boot.img.lz4`
- Candidate boot readback: exact match
- Kernel and Magisk `/init`: preserved
- Executable behavior delta from failed O1: exactly
  `seclabel u:r:magisk:s0`

No recovery, vendor_boot, dtbo, vbmeta, BL, CP, CSC, super, userdata, EFS,
sec_efs, RPMB, keymaster, modem, bootloader, or other partition payload was
present or written.

## Runtime Proof

Before host tty open, the helper observed:

```text
marker=1
phase=daemon-running
o1_service_state=running
o1_daemon_pid=3211
DR-daemon=stopped
stock_ddexe_present=false
ttyGS0_stock_owner_count=0
```

The framed protocol then passed:

```text
requested=128
completed=128
payload_equality=true
sequence_continuity=true
host_reopen_requested_at=64
host_reopen_completed=true
payload_bytes_each_direction=7383
latency_ms_min=0.140080
latency_ms_p50=0.286844
latency_ms_p95=1.855466
latency_ms_p99=4.058925
latency_ms_max=4.872837
```

After the protocol, the candidate reported:

```text
result=pass
daemon_rc=0
restore_rc=0
o1_service_state=stopped
o1_daemon_pid=
DR-daemon=running
stock_ddexe_present=true
ttyGS0_stock_owner_count=1
```

Both the candidate and rollback `adb reboot download` requests returned success
on the first bounded attempt. The retry branch was not needed.

## Retained Evidence

Automatic postrollback collection found no pstore file and successfully read
2,097,136 bytes from `/proc/last_kmsg`. The O1 marker was present. Relevant
retained init evidence shows:

- the `sys.usb.configured=configured` action was processed;
- service `s22plus_o1_control` was started with a real PID;
- the service exited status 0 after 9.059 seconds;
- the prior O1 `no domain transition from u:r:init:s0` rejection did not recur.

The short-lived service process ended before a separate live `ps -Z` context
snapshot was captured. Therefore the SELinux conclusion is scoped to the exact
single-delta candidate plus accepted service execution and complete protocol
behavior; this report does not claim an independent process-context readback.

## Rollback And Final State

The helper flashed the pinned Magisk boot-only rollback AP SHA256:

```text
d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
```

Final boot readback matched the known baseline:

```text
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Postrollback checks passed for Android boot completion, stopped boot animation,
Magisk root in `u:r:magisk:s0`, three stability samples, stock `DR-daemon`
running, one ttyGS0 owner fd, one host ACM endpoint, and no Odin endpoint.

## Timeline

`timeline.json` uses the canonical `events:[{name,timestamp_utc}]` schema and
contains every required phase:

```text
live_session_start      2026-07-09T19:36:02.147785Z
candidate_flash_start   2026-07-09T19:36:13.119092Z
candidate_flash_done    2026-07-09T19:36:14.666951Z
candidate_boot_ready    2026-07-09T19:36:49.756082Z
rollback_flash_start    2026-07-09T19:37:02.771488Z
rollback_flash_done     2026-07-09T19:37:04.300025Z
rollback_boot_ready     2026-07-09T19:37:43.508712Z
live_session_end        2026-07-09T19:37:50.177917Z
```

The two additional protocol start/done events preserve finer timing without
changing the schema.

## Interpretation And Next Rung

O1 is closed. The run proves that the known-good stock first-stage/module load
and stock Samsung gadget can carry a reliable framed boot-time host control
plane through a Magisk overlay service. It does not prove direct native-PID1
USB bring-up.

The next rung is O2 host-only loader parity: hard dependency recursion,
`modules.softdep` pre/post ordering, stock-order tie-breaks, explicit alias/
blocklist/options treatment, and EOF-complete `/proc/modules` reads. Promotion
still requires functional bind gates in dependency order before O3 direct-PID1
minimal ACM is considered.
