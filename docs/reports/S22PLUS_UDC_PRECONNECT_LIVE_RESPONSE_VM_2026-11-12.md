# Pre-connect UDC state and retained-write failure over virtual USB

An ARM64 guest returned its pre-connect UDC sample and the first retained-log
write failure over CDC-NCM after virtual connection. Two different header
failures left the entire 2 MiB region untouched and produced different
authenticated responses. This is an offline H0 result for the instrumented
kernel. [ML050's physical return](S22PLUS_MAINLINE_ML050_RETENTION_ANALYSIS_2026-11-12.md)
has no equivalent same-boot evidence.

| Initial retained header | Publication at guest time | Pre-connect sample | Authenticated at the responder | Independent RAM inspection at exit |
| --- | --- | --- | --- | --- |
| Invalid LOGM magic | Magic check failed at 17.120 s | Not attached at 60.384 s | Configured at 61.243 s | Entire region unchanged, zero frames |
| Valid magic, cursor 127 (minimum 256) | Cursor check failed at 17.120 s | Not attached at 60.384 s | Configured at 61.247 s | Entire region unchanged, zero frames |
| Valid header and sufficient cursor | Slot read back at 60.384 s | Not attached at 60.384 s | Configured at 61.247 s | Two authenticated frames, matching sample, only the permitted slot window changed |

The original configfs callback returned 11 bytes once at guest 46.858 s in
all three boots. In both failure cases, the failure preceded binding. The
worker preserved that first reason in ordinary RAM, stopped issuing retained
writes, and continued to sample. In the control, it read back all 128 slot
bytes and rechecked the four header words before reporting success.

The fixture froze the first available post-bind RAM sample before enabling
the dummy host controller's virtual cable at 60.400–60.401 s. After
enumeration, it moved the CDC-NCM host interface into a separate network
namespace. The client bound its TCP socket to that interface. The gadget
checked the challenge and read the current UDC state before returning the
frozen fields. The guest client and the offline reader each checked the
response HMAC, identity and fresh nonce. The serial capture contains the
bytes received by the client. QEMU ran with no emulated network adapter or
host forwarding. Wrong keys, substituted nonces and modified status bytes
were rejected for each saved response.

An initial fixture used the UDC soft-disconnect and soft-connect controls.
The virtual host failed to enumerate and received no response. The final
fixture exposes the dummy controller's cable event directly and keeps the
gadget driver running. That failure and the final runs are retained
separately. The experiment exercises Linux's virtual USB link. It does not
exercise the S22+ Type-C hardware, bootloader, Android return, or the
production Debian response format.

## Reproduction

The [fixture sources](../../workspace/public/src/mainline/s22plus_udc_observation_h0/live_vm)
contain two kernel patches, the guest peer and the host runner. Apply the
patches to a private copy of the ML050 instrumented kernel source, use fresh
observation credentials, and build the ARM64 Image with the dummy HCD, MII,
usbnet, CDC Ethernet and CDC-NCM built in. The base copies of `retained-udc.h`
and `dummy_hcd.c` have SHA-256 digests
`a59ad399193fe0623a8a70e50ea8b1f2fc7319ad9918fe97579d44b193509673` and
`7dd400f2b1723e23ec38721ab76787b0250c597b4401adeeb3e0e9ee4b239e57`.
Both patches reproduced the actual build inputs byte-for-byte.

Run `run.py` once for each of `bad-magic`, `short-cursor` and `readback`
using the ML050 reserved-memory VM DTB, QEMU 10.2.1, that kernel build, its
observation ID/key, and a fresh private output directory for each case. The
three completed boots used kernel SHA-256
`59e77662bb6db25c3594977f26bed3d59cde707170d992a6cdd74f113526ee93`.
Build logs, ELF identity, command lines, client wire frames, full retained
regions and their digest index are under
`workspace/private/outputs/s22plus-udc-live-readback-vm-h0-20261112-1/`
(`bad-magic-4`, `short-cursor-1`, `readback-1`, and `audit.json`).
