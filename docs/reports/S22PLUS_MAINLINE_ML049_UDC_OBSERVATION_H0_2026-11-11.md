# ML049 preparation for a continuously connected USB cable

ML048 produced 88 host observations of an absent endpoint and returned to
Android healthy. It supplied no device-side bind return or UDC state.
[ML048 physical results](S22PLUS_MAINLINE_ML048_NO_REPLUG_RUN_2026-11-11.md)
and the [comparison with S22 r0q](S22PLUS_MAINLINE_ML048_USB_ATTACH_REFERENCES_2026-11-11.md)
identify the question for ML049. Can the S22+ bind the RAM gadget and still
report an unattached controller while the cable remains connected?

The prepared boot-v4/AP contains a freshly keyed Debian RAM SysVinit
observer, the existing g0q USB setup, and the ML048 board configuration and
DTB. Its kernel adds a bounded observer around the original configfs store
and reads the UDC core state used by sysfs. The Linux UFS host driver is
disabled and there is no UFS module in the archive. The packaged observer
can answer its usual single authenticated base request. The original-A owner
uses the ordinary **attended physical Download** path, including when USB
stays absent. ML048's timed Download child belonged to its UFS profile.

## What the observer measured in QEMU

These are separate boots of the actual candidate kernel on an emulated
ARM64 board. The VM-only fixtures supplied a missing controller, a dummy
controller with its virtual cable disconnected, and a connected dummy
controller. Each case executed the real configfs store and the same kernel
worker, wrote the emulated reserved log, and used the FYG8 stock rotation
model and production decoder on the complete returned bytes.

| VM condition | Original configfs return | States sampled after the callback |
| --- | --- | --- |
| Controller absent | EBUSY, with the target UDC absent from the list | UDC absent |
| Controller accepted, no virtual peer | 11 bytes | not attached |
| Controller accepted, virtual peer enumerated | 11 bytes | configured |

The last three measurements were at guest times of 60.384, 91.104 and
119.776 seconds in each fixture. The first two reported a missing controller
before the test program's write. The early 7-second slot was missed at
startup and stayed empty. Each of the three final raw regions preserved
the four header words and all bytes outside the 256-byte window. Both
authenticated cumulative records were decoded separately. The once-only
bind hooks and sampling worker serialize the state and bind metadata;
a timestamp tie is inconclusive. A second clock check excludes reads
completed at or after the deadline.

The initial VM harness waited for six populated slots, including the missed
one. Offline inspection of those runs recovered the actual five measurements.
The final harness waits for the last sampled slot and all three cases were
repeated on the final kernel. The Debian positive and wrong-key VM cases,
two byte-identical boot/AP packages, and actual loader EL1/EL2 entry and EL3
rejection were checked separately. The physical image excludes the VM dummy
controller and fixture init. Private raw evidence, build inputs and review
packet are under
`workspace/private/outputs/s22plus-ml049-udc-observation-h0-20261111-1/`.

## Physical observation plan

Leave the cable and buttons untouched throughout the initial host window.
If the original owner calls for physical Download early, wait for the
operator cue at or after N+180 seconds, within its recovery deadline.
Urgent recovery takes precedence. Capture actual handling separately. After
one original A and full healthy closure, the fixed D0 reader brackets one
returned log with health checks on that same Android boot.

A fully authenticated record can show that the kernel accepted the bind
and what it sampled on that candidate boot. A record with no completed
callback, an error return, and a missing record have different meanings.
Guest timestamps do not align themselves to host N. Separate records can
come from different boot attempts and the samples cannot rule out brief
intermediate states. Firmware retention through the physical Download and
Android return is still unproved for ML049.

[Target scope](../operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md#mainline-ramusb-first-boot-v1)
and [runtime and recovery conditions](../operations/S22PLUS_MAINLINE_RAM_V1.md#ml049-retained-udc-observation).

The independent review verified 203 pins and decompressed the sole boot
member, matching its Image, DTB and CPIO to the actual loader. It covered
the fixed physical return, reader and v49 ordinary-terminal backend.
Integrated no-cue and raw collector tests passed. The terminal worker
selected the reviewed backend. The named foreground D0 completed all seven
original-Android health reads. At preparation close there was no grant,
candidate operation or partition transfer.
