# S22+ validation proportionality audit

Target: **SM-S906N / g0q / S906NKSS7FYG8** only.
Scope: assess the current P392 bootstrap, native observation and qualification
workflow against concrete hazards and the requested minimum useful capability.
This is an H0 assessment, not an implementation review or policy activation.
Source checkpoint: `c880544a98e1cca2c8d380dc9c22467a36de2cad`, with the existing
uncommitted other-target work and legacy review variants left untouched.

**Some current procedure is disproportionate. The clearest problems are host
authentication inside a short execution timeout and consuming the whole grant
on a proved pre-effect baseline rejection. The relevant transport tests,
effect-time target checks and exact recovery evidence remain necessary.**

## Observed cost and interpretation

The [P392 incident record](S22PLUS_NATIVE_USB_RECONNECT_H0_2026-09-14.md)
separates two different stops:

- The first bootstrap rejected one retained P387 carrier record during Android
  D0. It issued no Download request or partition transfer and closed
  `ABORTED_NO_DEVICE_EFFECT`. A normal reboot and new clean D0 followed. The
  next request had the same authorization digest but needed another returned
  authorization because the first grant was closed.
- The second bootstrap installed P392 once. Its first native phase accepted
  two authenticated sessions, native health and timely CONTROL/Download.
  Before the second native installation, host authentication did not complete
  within the guard's 30-second arm window. Exact original Android fallback and
  final health completed. Full bootstrap and physical cable-reconnect
  qualification did not complete.

Private guard captures were re-read for this audit: the first has 103 stdout
bytes; the second has zero stdout/stderr bytes and no second native transfer
record. Their SHA-256 values are respectively
`f824778f8cdc63a30f469bcd794b7aed43291c4164b6af1e7b402a3238dcdd99`
and `513c32c1334bd092071e6496d90dfe24089aab24c18aea18a8c21fc10a2808ea`.
The terminal re-read is `ANDROID_CLOSED`, `native_admitted=false`,
`research_stopped=true`, `recovery_required=false`, SHA-256
`a031b2481af276db4045279f6097941230587ec9a3a8cf31b1c62a78a0335261`.
The incident record retains the correlated polkit timing and private evidence
locations. Neither stop establishes a P392 USB hardware defect.

## Findings and smallest useful changes

| Item | Assessment | Recommended scope |
| --- | --- | --- |
| Per-phase privileged guard setup with a 30-second arm deadline | **Confirmed workflow defect.** Preventing another host process from probing the tty is useful; treating human password-entry time as native execution failure unnecessarily couples unrelated events. This caused the second stop after useful native proof. | Prepare host permission before the first effect. A narrowly scoped permanent ModemManager rule with explicit observer adoption is suitable. The smaller temporary option allows authentication within the original absolute grant deadline, with cancellation cleanup. Preserve device protocol/control deadlines. |
| Reservation/grant consumption before connected baseline acceptance | **Confirmed accounting/ordering problem.** Recording the failed read is necessary; a proved zero-effect rejection need not consume future device capacity or require the same approval again in a prospective design. | Move reusable readiness checks before effect-capacity consumption, or define explicit pre-effect rejection accounting in the existing owner. Recheck fresh target/health at dispatch. Preserve the failed record and original deadline; uncertain intent/write/control can never use this route. |
| Privileged tty holder census with a five-second timeout | **Source-confirmed recurrence risk; no new observed incident.** Detecting another tty opener has a concrete transport purpose, but `pkexec fuser` puts another human authorization inside a five-second command budget. Standalone D0 also starts its total observation clock before guard setup. | Include this privilege requirement in host readiness. Do not claim that a permanent udev rule removes every password prompt. Separate human authorization readiness from the bounded census and observation; do not discard the ownership check merely to avoid authentication. |
| Requiring absence of the whole retained evidence family | **Strong candidate for narrower scope, not yet a safe deletion.** The first stop was correct under the installed decoder, but the current native session has fresh authenticated identity while Carrier evidence is supplemental. Requiring a reboot merely to remove an identifiable old record can exceed that proof need. | For the native-primary path, establish whether retained-record classification and exclusion from current proof suffice. Preserve bounded raw evidence and reject ambiguity in evidence actually used. Avoid another candidate-specific exception or declaring the old snapshot clean. Other Carrier-dependent lanes retain their requirements. |
| Binding routine capability review to entire common/target documents | **Broad invalidation cost is confirmed; review is not automatically unnecessary.** The normal-reboot capability recently refreshed only two document receipts while its other seven inputs and eight actions stayed unchanged. Shared policy changes can still affect it. | Bind the selected authority and reachable machinery with explicit handling of higher-precedence changes. Reuse unchanged executable qualification; review actual authority/behavior changes. Do not blindly remove policy hashes or repin old consumed requests. |
| Two native boots and reauthentication during bootstrap | **Useful for reusable-baseline admission, excessive if presented as the threshold for every narrower feature observation.** First-boot acceptance and reusable admission answer different questions. | Keep the current admission verdict incomplete. Report first-boot proof separately. Any future narrower experimental lane needs its own stated success criterion and recovery semantics; do not rerun all admission work for routine experiments on an already admitted baseline. |

Source anchors:

- [Guard implementation](../../workspace/public/src/scripts/revalidation/device_action_cdc_acm_observer_v1.py):
  `GUARD_ARM_SEC`, `ModemManagerGuard.arm` and `_bound_observer_session`.
  [Native owner](../../workspace/public/src/scripts/revalidation/s22plus_native_baseline_owner_v1.py):
  `execute` enters a separate observer session for `bootstrap-first` and
  `native-final`; `reserve` precedes `collect_android`; `stop` closes the grant.
- [Native D0](../../workspace/public/src/scripts/revalidation/s22plus_native_reobservation_v1.py):
  `own_descriptor_only`, `Backend.connection` and `observe` establish the
  five-second privileged census and observation-clock ordering.
- [Connected D0](../../workspace/public/src/scripts/revalidation/device_action_d0_v2.py):
  `collect_connected` and `_inspect_clean_baseline` enforce the current retained
  baseline gate. [Typed evidence](../../workspace/public/src/scripts/revalidation/device_action_f1_evidence_v2.py)
  selects the decoder in `classify_clean_baseline`.
- [Ordinary Android capability](../../workspace/public/src/scripts/revalidation/s22plus_goal_research_v1.py):
  `SOURCES`, `source_identity` and `reviewed` bind whole common/target documents.
  [V2 policy](../operations/S22PLUS_NATIVE_BASELINE_V2.md) specifies bootstrap
  admission and the legacy finite approval. The
  [proportional scope](../operations/S22PLUS_PROPORTIONAL_RESEARCH_V1.md)
  already reuses candidate-independent capability review and permits scoped
  prospective repeats; it starts experiments from admitted N and does not
  replace the Android-origin bootstrap used here.

## Checks to retain and work not justified by this audit

Keep exact target/topology and current health before effects; boot-only archive
and actual payload/rollback identity; an available authorized recovery route;
durable intent/result ownership; authenticated fresh boot/nonce/ordinal evidence;
bounded raw acquisition; and independent verification of terminal health.
These prevent wrong-target writes, stale proof, duplicate effects and incomplete
recovery. Recovery success must remain separate from feature qualification.

The changed USB code justifies actual C/PTY hangup/reopen and partial-request
tests, relevant ARM64 termios/read syscall checks, and representative owner
failure/close paths. These test the behavior being changed. Cross-compilation
and source hashes alone cannot replace them. The 31 selected tests are not
evidence of excess merely because of their count. The earlier normal-reboot
refresh reused its 25-test evidence; it did not rerun that suite.

Do not add broad new daemons, global privilege exemptions, arbitrary repetition
counts, long soaks or full hardware-cause diagnosis as prerequisites for the
bounded reconnect claim. One successful live same-boot physical reconnect is
still needed before claiming that specific hardware behavior; it would not
establish long-duration reliability. Optional HUD/thermal export and causal
diagnostics should remain separate from transport acceptance unless that
experiment explicitly depends on them.

Repeated full source/artifact rederivation is an optimization candidate, but
this audit did not measure its critical-path cost. The native owner already
caches retained proof within a read transaction; the proportional scope's
`review_sources` caches unchanged input identities. A blanket claim that every
frame rehashes/rebuilds everything would be false. Preserve effect-time checks;
optimize a demonstrated duplicate computation only when it causes material
delay, without adding a new benchmarking gate to the current task.

## N -> E -> N follow-up

The initial audit followed shared owner machinery but concentrated on the
Android-origin P392 bootstrap incident. This follow-up explicitly checks the
normal native-origin experiment. N is the admitted reference image; E is the
experimental image. The owner's `PHASES` and `execute`, the observer's
`mode_sessions`/`qualify`, and the protocol's `qualify_one` implement:

| Phase | Actual work | Proportionality assessment |
| --- | --- | --- |
| Starting N | One fresh authenticated health session, then CONTROL and measured Download return | Retain current health and exact transition proof. The old native terminal alone is insufficient. |
| E | One boot-only E transfer, two authenticated health sessions with DETACH/close/reopen between them, then CONTROL and measured Download return | New E identity/boot, health and safe departure are necessary. The second session directly tests reentry; retain it when reentry/USB behavior is the experiment, and assess reuse of prior capability evidence for unrelated routine changes. |
| Returned N | One boot-only N transfer, two fresh authenticated health sessions with DETACH/close/reopen, then final DETACH/close | Exact restoration, new-boot health and clean closure are necessary. Repeating the whole reentry qualification on unchanged admitted N after every E is a narrowing candidate, not a demonstrated universal requirement. |

Thus a normal N/E/N operation has **two image transfers, five authenticated
health sessions, two CONTROL/Download transitions and three temporary guard
lifecycles**. These counts exclude bootstrap. The three guard setups each use
the privileged helper; whether each displays a password prompt depends on host
authorization. The actual P388 roundtrip's retained report records the same
1/2/2 authentication layout. It is historical execution evidence, not a new
live measurement.

Returning to N has a concrete purpose: it closes each experiment on a known
reference image and gives the next experiment that same baseline. It does not
require bootstrapping N again. Restoring N after every E is the current chosen
experiment model, not a hardware law. Remaining on E, promoting E to N or
chaining E images changes state ownership and recovery semantics and is absent
from the current operation set. Such a different goal deserves a separate
scoped design; this audit does not assume it is safer or necessary here.

There is an additional coupling to remove from routine N/E/N where unnecessary:
`qualify` automatically enables optional HUD export for the second session of
each pair, including the restored N. `qualify_one` dispatches it when enough
time remains. It tolerates a terminal negative/rejection without requiring a
positive scientific result, but a dispatched HUD command that hangs consumes
the observation deadline; export decoding can also raise during projection.
Consequently optional diagnostics can obstruct otherwise completed core health
and normal closure. Prefer requesting export only when the experiment needs it,
and avoid it on routine restored-N health. Once a command has actually been
sent, its uncertain execution cannot be ignored or replayed.

The native-origin branch does **not** call the Android `collect_android`
clean-baseline path. The P392 retained-log rejection therefore is not a normal
N/E/N gate. Conversely, repeated privileged guard setup and mandatory pair
sessions are directly present. The proportional scope already avoids a new
human approval for each in-scope E and permits qualified prospective repeats;
it retains this same N/E/N phase workload. Existing failed/consumed legacy
operations do not gain new authority from this assessment.

## Disposition

Prioritize host permission readiness and pre-effect reservation accounting.
Then narrow retained-log and authority invalidation only where their consumers
prove the broader restriction unnecessary. Use the existing owner and evidence
records rather than another approval framework.

These recommendations change no current grant, consumed result, policy or host
setting. P392 remains consumed and unadmitted; this audit grants no replay.
No device command was run for the audit. Android health above is the retained
completed recovery result, not a new live measurement. A90 and S20+ were not
contacted. Validation of this document requires only content, link, privacy and
diff checks; another build, device run or independent safety review of an
unimplemented recommendation would not answer the user's audit question.
