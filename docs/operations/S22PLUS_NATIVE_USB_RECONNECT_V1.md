# S22+ idle USB tty reconnect V1

Status: **Review-gated capability; no live grant or USB recovery proof.**
Target: **SM-S906N / g0q / S906NKSS7FYG8** only.
P392 / `v0.2.1` uses the rc.9 thermal V3 feature set as its code baseline.
This document does not admit a native baseline, grant a transfer or resolve
the existing device's unanswered D0 observation.

The distinct `thermal-v3-reconnect-v1` factory profile changes only the native
tty owner. After initial startup or the existing completed DETACH cleanup,
EOF, EIO, ENODEV or EPIPE **before any OPEN byte** closes the owned descriptor
once. The owner then services local work between one-second attempts to reopen
only `/dev/ttyGS0` with the existing nonblocking, no-controlling-terminal and
close-on-exec flags. Only absent/disconnected-node open errors are retriable.
Healthy EAGAIN/EINTR and ordinary idle deadlines retain the current descriptor.

Initial and reopened descriptors normalize and read back raw mode plus
VMIN=1/VTIME=0. The exact FYG8 n_tty reader can return zero for ordinary empty
reads with VMIN=0/VTIME=0; zero is not a disconnect discriminator until this
normalization succeeds. EIO/ENODEV/EPIPE from those pre-OPEN ioctls follows the
same close/reopen path, covering a drop during configuration. Other ioctl
errors, semantic readback mismatch or close faults latch terminal state.
Descriptor ownership is cleared before one close; close is never retried.
Open/configuration cleanup obeys the same ownership rule.

The boot ID, authentication ordinal, nonce history, boot-once preparation,
sampling state and terminal latch are preserved. Any consumed OPEN byte,
incomplete AUTH, active command failure or incomplete CONTROL/DETACH output
remains terminal. No command is automatically replayed. A fully submitted
native DETACH ACK does not prove host receipt: the host still requires complete
raw ACK evidence, descriptor close, current authority and journal ownership.
A later responsive tty cannot close an earlier uncertain operation.

No new worker, reset, gadget reconfiguration, partition write or recovery
mechanism is added. The exact kernel's gserial close may wait up to 15 seconds
for queued output if USB reconnects before close; uninterrupted PID1 HUD service
during that syscall is not promised. Existing workers may continue, and local
service resumes after close and during reopen waits. Thermal V3 provider,
collector, renderer and external authenticated wire remain unchanged.

H0 qualification must exercise actual PTY hangup/replacement, initial and
post-DETACH reopen, same-boot nonce/ordinal continuity, sampling progress,
partial-request and output failure latching, descriptor ownership faults and
real AArch64 termios/read behavior against exact target UAPI constants.
Both compiled ARM64 packages must agree and reopen through the existing audit.
Historical P387/P391 native artifacts and consumed records remain unchanged.
These checks do not prove Samsung USB recovery or long-duration reliability.

Live use remains subject to the selected baseline/research owner, current
source-bound independent review and an exact finite grant. Existing unresolved
health must be recovered and verified before any new candidate is installed.
Baseline promotion requires the chosen live qualification; this H0 profile
definition alone does not promote rc.9 or P392.
