# ML026: bind the interface name immediately before profile creation

Status: **H0 QUALIFIED / INDEPENDENT PASS_GO; PHYSICAL RUN CONSUMED /
PASS_DEBIAN_SSH_RAM / ANDROID_CLOSED_HEALTHY**.
The [run report](S22PLUS_MAINLINE_ML026_RUN_2026-11-05.md) records same-boot
authenticated base/SSH success and normal original-A return. The physical
anchor and final names were equal; the name-change branch's proof remains H0.

## Proportionality finding and selected correction

The operator asked whether the conditions were excessively strict.
[ML025's complete raw evidence](S22PLUS_MAINLINE_ML025_RUN_2026-11-05.md)
identifies one unnecessarily early restriction: the first observed interface
name was frozen before a host profile or socket needed that name. The later
snapshot differed only in that string. Once the profile had already been
created with the old name, the actual stop was appropriate: subsequent commands
would use that bound name. The useful repair moves the binding point.

ML026 keeps the first valid endpoint as an identity anchor. Configuration
performs its existing address and UUID-absence reads, then its existing full
guard. One fresh fixed USB census must match every anchor field except the
interface name. Only then are `endpoint.json` and `network-intent.json`
published with the same current name, and the single owned profile is created.
The returned endpoint is used by later configuration, socket and SSH paths.

The address-conflict check excludes only a row whose integer ifindex equals
the anchored ifindex. A changed label therefore does not falsely classify its
own addresses as foreign, and a different interface using the old label is
not excluded. Missing or noninteger indices, including booleans, are not
excluded. Preapproval checks without an own index still inspect every interface.

| Phase | Treatment | Reason |
| --- | --- | --- |
| First observation to profile binding | Name may differ; all other endpoint fields must match | No profile or socket is yet bound to the provisional label |
| Address-conflict exclusion | Own integer ifindex, rather than name | Names can change or be reused by another interface |
| After profile binding | Existing full endpoint/name, profile, socket, route and SSH checks remain strict | The name is now an actual command argument and profile constraint |
| Capture/publication to profile creation | Existing full guard plus a cheap original-deadline check after publication | Preserve the prior time-check position without repeating the full guard |

There is no fixed sleep, two-identical-snapshot requirement, extra full guard,
new naming daemon, host naming-policy dependency, postbinding reconfiguration,
additional connection or retry. The original 120-second observation and
one-base-request/one-SSH bounds remain. The policy records the concrete
prebinding hazard, scope and review/retirement trigger for the fresh capture.
It adds no separate human readiness question or approval layer.

The final census, durable publications and process creation are not atomic.
A later rename can still cause the existing fail-stop. Individual host commands
retain their existing eight-second timeout, without a new absolute acquisition
deadline; the cheap pre-create check and subsequent original-window checks do
not promise that every host command finishes within 120 seconds. No measured
physical improvement, fixed settling time or hard real-time guarantee is claimed.

The observed final name is consistent with the current host's USB MAC naming
rule. Neither that rule nor two matching endpoint projections proves the
historical rename actor/mechanism, exact timing, uninterrupted physical identity
or globally unique ifindex/device numbers. Those causal questions do not block
this narrowly identified ordering repair. No global host naming rule is changed.

## Focused producer and consumer validation

The original `configure()` reproduces ML025's exact preactivation stop using its
retained raw inputs with command acquisition, processes and sockets blocked.
The original source bytes are preserved separately; an append-only mapping
joins the old source pin to that immutable copy after the development file
changes. Old evidence and consumed records are not rewritten.

The initial regression failed with `NCM changed before activation` on the old
implementation. The changed path passes a clean focused suite of **53 tests**,
including real local socket acquisition and complete offline proof. Touched
Python compiles. The tests exercise:

- a name change before binding, with the final name used for publication,
  profile creation/activation and one actual socket;
- changed ifindex, USB generation/speed, MAC, driver or device path, absence
  and ambiguity, all rejecting before profile intent or creation;
- semantic/expired guard failure before binding, and expiry during durable
  publication preventing profile creation while preserving the intent;
- a name change after creation retaining the old fail-stop, with exact owned
  profile cleanup and no second deletion;
- a renamed own interface excluded by ifindex, a foreign interface reusing the
  old name still checked, and noninteger indices not excluded;
- existing request/raw/SSH failure, owner recovery, deadline and no-replay cases.

A separate H0 reproduction combines ML025's actual name-change snapshots with
an explicitly synthetic successful configuration tail. It binds the new name
and simulates one create/up without acquiring any command or socket. This is
ordering evidence, not a new physical run or physical network proof.

The first regression log predates the test API's explicit deadline argument;
it remains historical evidence, not a reused current test result. Current test
bytes and the clean final suite are bound separately. Unrelated readiness
fixture timing and historical activation counts are not new gates on this fix.

Past-failure checklist: HOST/SEMANTIC concern the name's role and binding time;
ROUTE/WIRE concern the actual command arguments and complete raw-to-proof path;
PERSIST concerns publication before effects and cleanup when no profile was
created; ARTIFACT/AUDIT preserve consumed inputs and current checker provenance.
These checks address the changed path without a diagnostic device ladder.

## Fresh candidate, review and readiness

The changed host source is part of both capability and backend review closures.
V30 receipts cannot authorize the changed code. The selected policy/profile
reference now selects the new interface-binding receipt, after coherent
independent review and V31 backend publication. The stable worker's actual two
source pins remain unchanged. No old receipt was repinned.

The fresh ML026 candidate keeps ML025's functional kernel/configuration, DT,
PHY and packaged Debian SSH workload. Only candidate/authentication/SSH keys
and V1 marker literals change. Consumed ML025 image bytes are not reused for a
new operation. Both fresh observer binaries reproduce byte-for-byte as static
ARM64 executables. The new Image/loader passes twenty loader cases and three
actual exception-level runs. V1 marker qualification passes 342 cases and six
actual exception-level runs. Repeated boot-only AP packages match. The exact
same-kernel VM base/SSH positive, wrong-HMAC rejection, six constrained SSH cases
and complete offline raw rederivation pass. These are H0 results, separate from
physical Debian PID1/USB and SSH proof.

The five previous CPIO negative cases retain their original ML024 manifest and
raw inputs, with the relevant archive-checker source hashes unchanged. They
are reused for that unchanged checker; the new valid archive and its runtime
have their own exact qualification. No isolated comparison helper is
adopted as review or execution authority.

Final independent source/artifact review is **PASS_GO**, with no findings,
against ninety-six public sources, 408 artifact/raw/advisory pins, forty-two
capability sources, forty-five backend sources and two stable worker inputs.
It verifies the exact signed 22-package/27-ELF/CPIO closure, complete observer/
key/Image/DTB/loader/AP joins and VM/SSH raw evidence. The actual image, task
and current terminal consumers pass with acquisition/USB/socket/process/
readiness/grant/start calls blocked, with zero calls and missing approval rejected.

The reviewed capability and backend V31 receipts are published. Real production
preparation passes using those receipts and ML025's closed healthy predecessor.
Eight honestly rebound mode, identity, qualification and SSH-proof mutations
reject through the actual image consumer. The connected worker reports V31.
No extra settling gate or retry was required by review.

One fixed preapproval D0 completed. All seven Android health raw captures
rederive with successful producer status and empty stderr, proving the current
exact target, original-A identity and healthy Android state. No grant, candidate
control, partition transfer or attendance assertion was created in preparation.
The operator subsequently returned the exact one-operation, 1800-second approval
and confirmed current attendance with usable Download recovery. The expired
readiness was refreshed before arming; the original freshness and effect-time
checks remained binding. One conditional replug was reported complete. ML026 is
now consumed and closed healthy; no successor is armed.

Source freezes, actual current capability/backend bindings, local links/privacy,
the 798-line goal, unchanged unrelated-file hashes and scoped diff checks close
this preparation. No candidate or artifact bytes change after final review.

## Advisory review and usage accounting

Two critique/challenge rounds each with Claude Opus 5.5 High and Gemini 4 Argon
High support this minimal ordering change. The challenge rejected an extra full
guard and corrected claims about rename actor/timing, identifier uniqueness,
atomic identity, absent IPv4 configuration, V30 reuse and consumed-image reuse.
Their advice is not independent artifact qualification or device authority.

All four calls completed without fallback. Private before/after quota snapshots
and per-call token records are appended to the usage ledger. Claude reported
4 uncached input, 14,690 cache-creation and 16,793 output tokens, including
10,502 thinking tokens. Its USD 0.453396 list-price equivalent is not actual
subscription billing. Five-hour account snapshots were 11%, 12%, 14% and 14%.
Argon reported 35,044 input and 15,377 output tokens, including 10,848 thinking
tokens, for 50,421 total. Fresh-process weekly remaining snapshots were 82.44%,
82.51% and 81.50%. The observed increase is not negative per-call consumption;
these account-wide readings cannot isolate the calls' usage. Actual subscription
charges were unavailable.

Private evidence is under
`workspace/private/outputs/s22plus-mainline-ml026-interface-binding-h0-20261105-1/`
and sibling `s22plus-ml025-next-discussion-20261105-1/`.
A90 and S20+ are untouched; unrelated dirty work remains preserved.
