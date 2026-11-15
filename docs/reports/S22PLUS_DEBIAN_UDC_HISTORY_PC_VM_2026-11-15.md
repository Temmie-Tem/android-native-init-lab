# Debian UDC history verified by the PC collector on ARM64

The S22+ Debian RAM observer now has an H0 variant that includes UDC history
and the retained writer's result in its authenticated base response. The
implementation is commit `385c1c224d` on `codex/s22-debian-udc-pc-h0`.
Three ARM64 boots delivered complete 35,846-byte responses to the existing
PC socket collector after the virtual cable connected.

| Retained header | Sample before connection | Sample after connection | Reported publication | Independent inspection of 2 MiB |
| --- | --- | --- | --- | --- |
| Invalid LOGM magic | Not attached at 7.136 s | Configured at 17.120 s | Magic check failed on the 7.136 s sample | All bytes unchanged |
| Valid magic, cursor 127 | Not attached at 7.136 s | Configured at 17.120 s | Cursor below 256 on the 7.136 s sample | All bytes unchanged |
| Valid magic and cursor | Not attached at 7.136 s | Configured at 17.120 s | Latest slot readback verified on the 17.120 s sample | Two authenticated slots. The full 128-byte USB record matched one slot byte for byte |

All times use the guest boot clock. In each boot, the kernel saw one completed
gadget bind before the first sample. An independent VM fixture timestamped
both sides of enabling the dummy controller's cable. Even the earliest
pre-action timestamp (7.137 s) followed the first sample. Publication times
identify the sample for which the writer acted. The capture does not measure
the instant the final readback completed.

## What crossed the link

Debian SysVinit ran as PID 1 and started the packaged observer directly in
runlevel 2. The observer read one coherent kernel history containing the
boot tag, bind result, sampled states and the first publication failure or
latest successful readback. A failed publication stopped further writes
while later UDC observations continued in RAM.

On the Linux PC, `s22plus_mainline_access_v1.capture_connection` generated
a fresh nonce, bound its socket to a TAP inside a fresh network namespace,
sent one request, and sealed the response through EOF. QEMU carried the
Ethernet frames to a guest bridge between virtio and the emulated host's
CDC-NCM interface. The Debian program served the gadget side. The VM-only
bridge exchanged no application messages and held no protocol credentials.
The PC checked the Debian HMAC, nonce, PID 1, observer and inittab
identities, boot ID, and live device tree. The UDC decoder also verified
the nested record and matched its boot tag and sample to the retained bytes
in the successful control.

A fourth boot rejected a request with the wrong key and returned zero bytes.
In a fifth boot the cable stayed disconnected, the observer timed out and
QMP recorded a guest-initiated reset. This verifies the timer through the
VM reboot call. Physical Download arrival and restoration of Android were
outside this experiment.

## Artifacts and verification

The isolated worktree contains the opt-in producer, wire decoder and VM
fixture. The current v50 terminal pins the checksum of the previous verifier.
The primary checkout retains those reviewed bytes. The ordinary device image
validator still excludes the new schema. The board kernel and Debian
initramfs were built and inspected on the host. Only the VM variant ran.

For reproduction, prepare independent board and VM kernel trees with fresh
observation credentials. Apply `retained-udc-history.patch` to the
instrumented retained writer in both trees. Add the existing dummy-controller
cable fixture and built-in CDC-NCM host/bridge drivers only to the VM tree.
Build each Debian initramfs with `--udc-timer-return --udc-history` and select
`--vm` for the VM build. The VM runner is
`workspace/public/src/mainline/s22plus_udc_observation_h0/debian_vm/collect.py`
in the implementation commit. Run one case per fresh user, mount and network
namespace with sysfs mounted for that namespace. The exact invocations,
package manifests, kernel Images, request/response receipts, ring bytes and
QMP evidence are retained privately under
`workspace/private/outputs/s22plus-debian-udc-pc-vm-h0-20261115-1/`.
The selected packages are `debian-vm` and `debian-board`, with the board
kernel under `board/kernel-build`. Each final boot has a `*-final` directory.

Independent review passed for the H0 implementation and five VM cases.
Thirty-six focused existing tests passed. Wrong credentials, altered
authentication, invalid publication fields and future sample references
were rejected in saved-response checks. The retained ML050 base response
reproduced all 21 original proof fields with the new codec. The committed
isolated source reproduced the evidence index in `validation-isolated.json`.
[Earlier VM observer](S22PLUS_UDC_PRECONNECT_LIVE_RESPONSE_VM_2026-11-12.md) ·
[ML050 physical evidence](S22PLUS_MAINLINE_ML050_RETENTION_ANALYSIS_2026-11-12.md)
