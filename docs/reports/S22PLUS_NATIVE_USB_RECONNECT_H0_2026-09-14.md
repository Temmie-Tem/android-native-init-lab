# S22+ P392 / v0.2.1 idle USB reconnect

Target: **SM-S906N / g0q / S906NKSS7FYG8** only.
Scope: use rc.9's thermal V3 features as the code baseline, repair idle USB tty
reacquisition, and qualify a fresh v0.2.1 package before live baseline promotion.
No physical device command, new grant or transfer is part of this H0 work.

Latest live outcome: **first P392 native phase accepted; full bootstrap
incomplete after a host authentication wait; original Android restored healthy.**
P392 is consumed and not admitted. No second native transfer or physical USB
cable-reconnect qualification occurred.

## Result and limits

P392 / `v0.2.1` is implemented and its ARM64 A/B boot packages agree exactly.
All 31 selected tests pass. Independent review returned **PASS_GO**, findings
`[]`, for frozen source set SHA-256
`7914ba422e99c455b81334018d9511055642095dcc0c5e3602f03948916b31e3`.
The research, V2 and deferred capability receipts bind that reviewed closure,
including both legacy working/publication variants. At H0 close, the device
was last recorded at P387 / rc.5 with unanswered D0 observations. Neither rc.9
nor P392 was promoted by that H0 change; the later live outcomes follow below.

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
At that H0 checkpoint there was no unresolved F1 owner, but current
authenticated device health was unverified. H0 success did not clear the old
observation failure; later Android recovery established a new healthy state.

## Next live boundary

The Android recovery described below has completed. P392's first installation
is now consumed and its bootstrap is incomplete; its closed grants do not
permit replay. Resolve the host permission setup before qualifying a fresh
successor under its own current authority.
Same-boot live USB disconnect/reconnect evidence is required before calling
this repair demonstrated on Samsung hardware. Long-duration reliability is
still unproved. A90 and S20+ were untouched; old consumed images and journals
remain unchanged.

## Separate live recovery and bootstrap preflight

The operator entered physical Download and returned the exact separate Android
exit and P392 bootstrap approvals. Passive endpoint/retained-lane binding and
the original A artifact passed. The stale P387 H0 preparation was rejected
before a grant; refreshing its host source receipts preserved every native
artifact and its admitted native identity.

The new Android-exit owner transferred the original boot-only A exactly once.
Android USB appeared with ADB initially offline. After the operator unlocked
Android, exact rooted FYG8 health, boot/supporting hashes and Download absence
passed. It closed `ANDROID_CLOSED`, terminal SHA-256
`486b43ead7991f83325eff65db5b9976404a158e83791aaa49c24abce788f0b3`.
Its grant is closed; no native role ran during recovery.

The separately opened P392 bootstrap passed initial Android health but its D0
clean-baseline classification stopped before any Download request, Odin
invocation or partition transfer. The complete 2,097,136-byte `/proc/last_kmsg`
capture, SHA-256
`abc87b4b9066386fa8061e7e6cdabde133187bb9f32d3ef4bdff6f211e18a731`,
contains one valid P387 `S22E1L2|` carrier record and no P392 binary identity.
H0 replay reproduces the existing decoder's current/legacy-family rejection.
This is an expected negative baseline, not a P392 execution failure.

The bootstrap reservation closed `ABORTED_NO_DEVICE_EFFECT`, terminal SHA-256
`20753bd47749b3bb63d665b2c6831ea7c367b63792c9ae3bacc940d3fca3634f`.
Its one-reservation grant is closed, both F1 owners are released, and P392
remains globally unconsumed. Its rejected D0 result is not reusable. All raw
records and the replay remain under
`workspace/private/outputs/s22plus-v021-live-prepare-20260914-1/` and the named
private owner runs. Normal reboot and fresh baseline observation were selected
as the next bounded preparation; no parser exception or old-record relabelling
was introduced.

The ordinary-Android goal capability's executable inputs and eight actions
were unchanged. Independent `PASS_GO`, findings `[]`, approved refreshing only
its common/target source receipts, reusing the retained 25-test PASS and review
evidence. The nine-source map has canonical sorted compact JSON plus LF SHA-256
`10faa3674cd67fdd947374e0e2dd14e01e9c9d58aaba1d0a3b4c7d3ab45a51b1`.
The already authorized foreground profile then dispatched one normal reboot.
Its exact changed-boot health passed, with zero other-target commands, result
SHA-256 `30fd60a5458679a695b41d26786816bcf145bacbc6c85b53c6c809a7bd405f52`.
Its goal grant closed and the pending-reboot marker was retired normally.

Fresh complete D0 now returns `PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`:
the new 2,097,136-byte observer has zero family and exact markers, a clean
baseline, and SHA-256
`a8e5c9ad23f2ee6d9e85aaec7f6a92e1d16434632684c0f04a5afa0d735e777c`.
Current target/boot/Android health and the prepared target binding agree.
The structured D0 result has SHA-256
`7ee4ca938738816db37cf7ebdb628c1d9e27c2ec68b9c4edbe6167c386a97ff7`.
The rejected old snapshot and closed first bootstrap grant remain unchanged.

Request `p392-bootstrap-20260914-2` was freshly prepared for one operation and
600 seconds. Its unchanged scope/artifacts produced the same request digest as
the first proposal, but required a new returned authorization for that separate
request. No old grant or budget was reopened. The operator subsequently
returned that authorization and the following live attempt consumed P392.

## Accepted first native boot, host guard wait and healthy fallback

The second request completed one P392 boot-only installation. Its first native
observer returned `accepted`, with two authenticated sessions, three commands,
native-health proof, one host descriptor close/reopen and accepted CONTROL.
The owner also proved timely Download return. These are first-boot capability
observations; descriptor reopening is not physical USB cable-reconnect proof.

Before the second native transfer, the next temporary ModemManager guard
invocation produced no ARM receipt during its 30-second arm window. It produced
zero stdout/stderr bytes and was still running at capture finalization. The
raw capture's generic `timed_out` flag remains false; the outer guard owner
enforces the separate arm deadline. It raised `ObserverError` at this host
pre-transfer step. No `native-final` transfer intent exists.

Timestamp-correlated local polkit evidence shows the first password dialog
completed successfully before its guard armed at 11.409 seconds. The second
dialog requested a password but had no authentication-completion event before
the 30.064-second cutoff. This explains the host wait; it is not evidence of a
P392 USB-serial failure or an invalid password.

The already authorized original A fallback transferred once and verified
exact rooted FYG8 health and Download absence. The result is `ANDROID_CLOSED`,
`research_stopped=true`, `native_admitted=false`, terminal SHA-256
`a031b2481af276db4045279f6097941230587ec9a3a8cf31b1c62a78a0335261`.
The grant is closed, F1 and pending-D1 owners are absent, and the temporary
runtime udev rule is absent. Candidate qualification and healthy rollback
remain separate. The concise close record is
`workspace/private/outputs/s22plus-v021-live-prepare-20260914-1/p392-consumed-close-summary.json`.

## Host permission design assessment

ModemManager is active on this PC. The current guard installs a scoped runtime
udev rule using `pkexec`, then removes it after each observation phase. The
second phase therefore requires another host authentication. Its 30-second arm
window is distinct from the installed rule's 360-second default lifetime.

Independent design assessment identifies two bounded alternatives. Allowing
authentication to wait within the original BOOTTIME grant is the smallest
temporary-guard code change; it must preserve legacy defaults, cancellation
cleanup and all effect-time authority/target checks. A permanent rule limited
to the S22+ native gadget and bound lab port is a suitable host configuration
alternative, but needs explicit observer verification of root-owned rule bytes
and effective device/port-ignore properties. The current helper rejects a
same-name permanent override, so installing a file alone does not adopt it.
No temporary-child or rule-removal receipt may be fabricated for external
configuration. Separate privileged checks, such as a holder census, remain
separate from guard-install authentication.

A private permanent-rule draft matches the bound native port, VID/PID,
interface and `S22E3` plus exactly 32 hexadecimal build-ID characters. It passes
`udevadm verify`, SHA-256
`37e00aa041d95e6d02000d245bd8b8f991233b9334fdbce4b571ab60d171bd29`.
This is a syntax-checked proposal, not an installed or activated policy. No
host service, security policy or execution code was changed by this assessment.
