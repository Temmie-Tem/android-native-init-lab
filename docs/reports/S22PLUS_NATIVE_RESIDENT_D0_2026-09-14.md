# S22+ resident D0 response check and operator observation

## Result and evidence limits

The operator requested a command-response check after prolonged P387 resident
operation. The one native checkpoint stopped as
`NO_PROOF_NATIVE_RESPONSE_UNRESOLVED`. Its host intent began at
2026-09-14 01:22:44 KST and its stop was recorded at 01:23:45 KST.
The host wrote one valid 32-byte OPEN to the exact native tty and captured
**zero response bytes** during the approximately 59-second banner wait.
The complete capture interval, including admission work, was 60.465 seconds;
this is not a successful within-60-second checkpoint.

The existing frame decoder independently accepts the retained OPEN's framing,
CRC, sequence zero and P387 run payload. That proves the host transcript,
not delivery or acceptance by the device. AUTH, EXEC, CONTROL and DETACH
frame counts are all zero. No current kernel boot identity, uptime, command
health or clean native DETACH was authenticated by this USB observation.

The later operator photo provides separate positive evidence. It displays
`v0.2.0-rc.5`, `WAITING FOR AUTH`, uptime **0 D 18:49:06**, `SYSTEM: FRESH`,
`SENSORS: FRESH`, system sample sequence **67,676** and sensor sequence
**67,262**. The operator explicitly confirmed that the UPTIME seconds and
SYSTEM SAMPLE sequence continue increasing. This supports current local
monitoring and display activity, and meaningful long-duration resident
operation. The failed USB check does not establish device-wide stoppage.
A complete uninterrupted healthy interval and the failing USB-path component
remain unproved.

The frozen resident renderer prints the accepted system/hardware sample
sequences and derives freshness from sample age. The collector increments its
sequence on each collection iteration. Sequence values are not a count of
all successfully delivered samples: dropped sends can leave gaps. The
operator observation remains distinct from the unchanged machine raw verdict.
The original P387 temperature limitations are unchanged.

## Bounded action and host preparation

This was a directly requested, fixed D0 observation of only
SM-S906N/g0q/S906NKSS7FYG8. The planned command set reused the existing native
health command, STATUS, optional bounded resident HUD export and clean DETACH.
It did not reopen the closed F1 grant or authorize a transfer/reboot.

Earlier preparation attempts stopped before any native intent or descriptor
open. A host guard lifetime argument was rejected by the existing validator;
the corrected caller uses its reviewed default while retaining a 60-second
native checkpoint bound. A subsequent current-tty property read found both
ModemManager ignore flags absent. Neither result was a native response test.
Their original source snapshots, review receipts and failure records remain
private and unchanged.

The independently reviewed host repair applied **one** change event to the
exact resolved tty, under the existing transient guard. It selected no USB
ancestor, reset/rebind operation, other tty or global ModemManager change.
The host rule audit covered 132 files across the four installed rule roots,
including the absent local root and root-readable netplan rule. No applicable
rule dispatched a device-control command for that tty change event.

The event completed with return code zero and the exact selected tty line
followed by `settle` for the same tty. A parser expecting only the first line
stopped before native authentication. H0 reconciliation reopened those exact
immutable bytes and classified the completed event; the event was never
replayed. The final checkpoint caller contains no host-event dispatch path.
Other host-tool preparation errors are retained in the private H0 logs and
did not reach native authentication.

Before the sole OPEN, both fresh tty ignore-property observations passed.
After TIOCEXCL, a bounded privileged opener census found only the checkpoint
process holding that tty. This is an admission snapshot, not a guarantee
against every future privileged opener. Exact endpoint, current native inputs,
key identity, shared target lease and no-F1-owner checks also passed.

The caller preserved received chunks before parsing and finalized the raw
transcript on failure. Failure handling called descriptor close before
releasing the host guard, and the process exited. Guard release succeeded. There is no
normal native DETACH/close receipt and no healthy native terminal. These host
cleanup facts do not establish native responsiveness or the cause of silence.

## Retention, validation and continuation

The final private evidence group is
`workspace/private/outputs/s22plus-native-resident-d0-20260914-4/`.
Earlier host-only preparations and the completed event are retained in the
three preceding numbered groups. The operator photo and advancing-counter
confirmation are separate private records; no image or raw device evidence
is published here.

The final caller and plan were independently reviewed `PASS_GO`, with all
212 execution-source receipts matching. Eight focused tests passed, including
actual resident C/PTY reentry after a simulated 17-hour interval, pre-AUTH
fresh-boot rejection, wrong boot/ordinal rejection before EXEC, raw preservation,
close-before-guard-release on interruption, actual privileged opener checks,
and exact retained-event rederivation. Clock-accelerated fixtures do not prove
a real-device soak. Native code and its numeric ABI flags were unchanged;
no firmware was rebuilt or transferred for this check.

Final caller SHA-256:
`7f5b63e5d85f7d2f597965cc4f2c434b0d639a547229bd454d0a219f2b245abb`.
Final plan SHA-256:
`eb9d3ccbaf033ba35007f9fe8c36cd4c26628e7623dcbdd68853743577ea9c00`.
Raw capture receipt SHA-256:
`6c84848bd2ec0c09dc86d5913022f6bbf0eb87d7344a36223e165eb9de43d66a`.
The raw receipt records `producer_error_type=TimeoutError`; its generic
subprocess `timed_out` field is false because the protocol raised the timeout.

The historical P391 native terminal remains byte-identical at SHA-256
`3baf937274fcf3965956dfa7bc4384296dcc6819dd928a7dd623d9ccdac3ecaf`.
A no-clobber D0 successor intent was published before the first OPEN, so the
existing F1 reader rejects reuse of that stale predecessor before effects.
This failed D0 result cannot replace it with a healthy terminal or authorize
native reauthentication. The checkpoint is consumed and new native effects
remain stopped; H0 diagnosis and otherwise allowed observation remain separate.
No recovery, candidate replay, reboot or partition transfer occurred. A90 and
S20+ received no command.
