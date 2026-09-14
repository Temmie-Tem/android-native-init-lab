# S22+ P392 / v0.2.1 idle USB reconnect

Target: **SM-S906N / g0q / S906NKSS7FYG8** only.
Scope: use rc.9's thermal V3 features as the code baseline, repair idle USB tty
reacquisition, and qualify a fresh v0.2.1 package before live baseline promotion.
No physical device command, new grant or transfer is part of this H0 work.

## Result and limits

P392 / `v0.2.1` is implemented and its ARM64 A/B boot packages agree exactly.
All 31 selected tests pass. Independent review returned **PASS_GO**, findings
`[]`, for frozen source set SHA-256
`7914ba422e99c455b81334018d9511055642095dcc0c5e3602f03948916b31e3`.
The research, V2 and deferred capability receipts bind that reviewed closure,
including both legacy working/publication variants. The existing device
remains at its last recorded P387 / rc.5 native installation with unanswered
D0 observations. Neither rc.9 nor P392 has been promoted to the operational
baseline by this change.

The [new profile](../operations/S22PLUS_NATIVE_USB_RECONNECT_V1.md) closes a
hung-up descriptor once and reopens the fixed tty only before any OPEN byte,
initially or after the existing clean DETACH cleanup. It normalizes and reads
back VMIN=1/VTIME=0, keeps healthy EAGAIN/EINTR waits on the same descriptor,
and services local work between one-second retry attempts. Recognized link
loss during initial/reopen termios setup uses the same path; semantic readback
mismatch, other configuration failures and close faults remain terminal.

Boot identity, nonce/ordinal progression, boot-once preparation, sampling and
failure latches persist. Partial OPEN/AUTH, command failure and incomplete ACK
transmission never restart authentication or replay a command. Host receipt,
descriptor close and journal ownership remain independently required. The
exact gserial close can wait up to 15 seconds for queued output; uninterrupted
PID1 service during that call is not claimed.

## H0 evidence

Actual C/PTY tests exercise initial and post-DETACH physical PTY hangup,
replacement, raw-mode normalization, empty/deadline waits, transient node
absence, configuration-time link loss, readback and close faults, descriptor
reuse, partial OPEN/AUTH, active command interruption and a partial DETACH ACK.
The real thermal collector/renderer continue advancing across retry waits;
same-boot sessions retain ordinal progression and one boot preparation.

The AArch64 probe uses real ioctl/open/read/close syscalls under qemu-user and
checks exact FYG8 UAPI operands. It observes ordinary zero-byte empty reads at
VMIN=0, EAGAIN after normalization, zero/EIO after hangup, and a successful
fixed-path reopen. This is target-architecture syscall evidence on a host PTY,
not Samsung gadget-driver or live recovery proof.

The new profile also traverses the existing raw N/E/N owner with real C/IPC,
thermal decoding, unavailable sensors, battery faults, old IPC rejection and
grant expiry. USB, Android and partition transfers in those tests are fixtures.
The shared research-scope, D0 reobservation and capability identity regressions
are checked separately. Thermal V3 provider and renderer generation remain
byte-identical for the same identity. The data catalog adds a distinct reviewed
runtime profile; a data addition cannot silently deduplicate its new transport
code under the older thermal profile.

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| ARM64 static init | 150248 | `205621e856bd1abee342f377c0791f8b2abb67a23b0b6c52a7440ab3d5c9a618` |
| Boot-only AP, both A/B | 31303721 | `9e029f43e361aa63e516261060c69640be78851f51b03a18ac35e8eaf93038f2` |
| Identity-only Image | 41490944 | `00f76144f871f2596f8f67bb75bd2842b80067afe877c86cb7bec1b7301a2956` |

The fresh Image reverses exactly to the sealed P383 platform outside its two
declared identity spans. Existing package readers verify both boot-only APs,
the ARM64 ELF, modules, source identities and rollback artifact. Artifacts stay
under `workspace/private/outputs/s22plus-native-reconnect-v1/p392/build-1/`;
test logs, static preparation and qualification records stay under
`workspace/private/outputs/s22plus-v021-reconnect-h0-20260914-1/`.

The retained P391 native terminal and P387 admission rederive; all 121 P387
and 140 P391 native inputs, and both P391 APs, remain unchanged.
The latest D0 stop retains SHA-256
`b0641be6354a3fb63f7744ed8817330fbeec2c0256581ee109a43884181eaad2`.
There is no unresolved F1 owner, but current authenticated device health is
still unverified. H0 success cannot clear that observation failure.

## Next live boundary

The device must first return through the applicable attended exact Android
recovery path and pass health verification. A fresh finite grant and the
normal native-baseline qualification then govern any P392 installation.
Same-boot live USB disconnect/reconnect evidence is required before calling
this repair demonstrated on Samsung hardware. Long-duration reliability is
still unproved. A90 and S20+ were untouched; old consumed images and journals
remain unchanged.
