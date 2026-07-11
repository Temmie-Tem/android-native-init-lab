# V3440 S22+ RDX USB Viability Live Controlled Negative

## Verdict

`CONTROLLED_NEGATIVE_SBOOT_NEGATIVE_ACK_PROBE_NOT_SENT`.

V3440 proved that the FYG8 S22+ kernel-panic RDX state exposes a host-visible
Samsung S-Boot USB endpoint and accepts the transport-level preamble request,
but the device returned the exact protocol response `NeGaTiVeAcKmNt\0` before
the probe-table command. The fail-closed contract stopped immediately:
`PrObE`, `DaTaXfEr`, address/range requests, qdl, Sahara, and RAM transfer were
not executed. No dump bytes were retrieved.

The result is stronger than `NO_ENDPOINT` and narrower than “RDX dumping is
impossible.” It shows that this retail state reaches the S-Boot command gate
and is rejected there. The same retained frame contains `RDX is locked`, so
the result is consistent with the expected token/locked authorization wall,
but V3440 does not prove which internal S-Boot check generated the negative
acknowledgement.

## Run Identity

```text
run_dir=workspace/private/runs/s22plus_v3440_rdx_20260711T000711Z
source_commit=e9356a17
policy_commit=172340f3
helper_sha256=cab62dcc89cb7f39d16e99b3d19106f1e5a418436d05a6d5fa7076aab136e4f8
run_id=9ab2fb480429abf280f59583560d2d29
candidate_flash=false
rollback_flash=false
```

## Preflight

The live helper passed all mandatory gates before the single panic attempt:

```text
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
boot_completed=1
root=uid=0
boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
dtbo_sha256=97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
baseline_usb=04e8:6860
PyUSB=1.2.1
libusb_backend=true
```

## Panic And RDX Proof

The helper emitted the run-bound marker and attempted SysRq once. Its initial
trigger classifier returned `sysrq command returned cleanly`, causing the main
helper to stop before USB observation. That classification was false: the
operator immediately observed the RDX kernel-panic screen, ADB disappeared,
and host kernel USB events recorded:

```text
00:07:25Z Android 04e8:6860 disconnect
00:07:37Z Samsung RDX 04e8:685d enumerate
00:08:02Z Samsung RDX 04e8:685d re-enumerate
00:09:13Z Android 04e8:6860 return after physical RDX EXIT
```

The retained `/proc/last_kmsg` independently closes the ambiguity:

```text
S22_V3440_RDX_BEGIN run=<current run id>         present
Kernel panic - not syncing: sysrq triggered crash present
sec_upload_cause ... sysrq triggered crash       present
RDX is locked.                                   present
collect_rr_data ... upload_cause = KERNEL PANIC  present
```

This was one panic, not a retry. The trigger bug is host classification only:
future helpers must not reject clean command rc immediately; they must poll for
delayed ADB transport loss before deciding that panic failed.

## S-Boot Probe Result

After exact helper SHA, active policy, both acknowledgement identities, private
PyUSB runtime, current run state, and exact `04e8:685d` were rechecked, the
checked helper's `sboot_two_command_probe()` was resumed for the same run.

```text
command_sent=PrEaMbLe\0
response=NeGaTiVeAcKmNt\0
response_bytes=15
response_sha256=3a4a3980e7835ebb77c927b99863e01847086171bdb81773e81e06f2192ab60c
PrObE_sent=false
DaTaXfEr_sent=false
memory_transfer_requested=false
qdl_invoked=false
```

The raw 15-byte response is private evidence. It exactly matches the negative
acknowledgement recognized by the pinned `sboot_dump` source. V3440 intentionally
uses the stricter interpretation: negative acknowledgement is a stop, not a
connected state.

## Recovery

After the host reported observation complete, the operator used physical RDX
EXIT. Android returned without any flash or rollback transfer:

```text
ADB=device
boot_completed=1
bootanim=stopped
root=uid=0
USB=04e8:6860
boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
dtbo_sha256=97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
```

## Evidence Pins

```text
result.json=62a6d12adb5ab33f39d9d44078de09f6180a39980b417dadf1fe9a598acd7dbe
timeline.json=50c514ef91d09a8701bf4d9459cd893134ba9e04a55376efda46bb57021ba0c4
sboot_preamble_response.bin=3a4a3980e7835ebb77c927b99863e01847086171bdb81773e81e06f2192ab60c
post_recovery_last_kmsg.bin=a397d9688e740bc03bead8c4fd2fcc667910cfe98d2f92252a36b474e66a5b04
host_kernel_usb_window.log=0ac5702517af3ad28bb181c52143581c9a07998a6ad870538f6e399f434d707b
```

The helper exited before completing its timeline because of the trigger false
negative. The final private timeline retains the single `events` schema and
records reconstructed phase timestamps from durable file mtimes and host kernel
USB events. It explicitly marks no candidate flash and no rollback flash.

## Decision

Retire this exact V3440 gate. Do not repeat the preamble under the same retail
RDX state, and do not imitate upstream behavior by sending `PrObE` after
`NegativeAck`. RDX direct dump is not promoted as the next observation path.
It can be reopened only by a materially different, host-supported hypothesis
for the token/locked gate or by evidence of a Qualcomm `05c6:900e` Sahara
endpoint. Blind protocol mutation, authentication bypass, full dump, and qdl
remain outside this result.

The practical frontier returns to stock-global-PID1 service-supervisor bring-up
for hardware ownership and to UART when an early real-time console is available.
The already-controlled-negative EUD software-enable path remains lower priority.

## Validation

```text
one SysRq panic                         proven
RDX operator screen                    proven
Samsung RDX USB 04e8:685d              proven
exact S-Boot NegativeAck               proven
PrObE/DataXfer/qdl/RAM transfer         not executed
post-run Android/root/boot/DTBO health  pass
```
