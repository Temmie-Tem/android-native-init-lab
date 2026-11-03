# ML021: one physical USB attach change on the existing RAM baseline

Status: **H0 qualified, independently reviewed and fixed preapproval D0 healthy;
exact attended approval pending; no grant or device control**.

ML021 is a fresh prospective candidate after consumed, healthy-closed
[ML020](S22PLUS_MAINLINE_ML020_RUN_2026-11-04.md). Its bounded question is whether
the existing functional RAM/USB baseline can produce authenticated access with
one attended physical cable detach/reattach during observation. The kernel
configuration, DT, PHY correction, CPUidle exclusion and PID1 logic are unchanged.
Fresh identity, key and V1 frame literals require newly built and qualified
Image, initramfs, loader and AP bytes; the consumed ML020 package is not replayed.

## Source basis and selected scope

The working r0q port's [boot log](https://github.com/cammo1997/SM-S901E-Linux-Part-Working/blob/main/docs/boot-log.md)
reports functioning Linux/userspace without USB until a physical replug in
attempts 4/4b; software reconnect did not help. Its later attempt 23 reports
access without replug after a bundle including MAX77705 Type-C and role changes.
Those are another board's reported results and a multivariable change, not
g0q evidence or isolation of a single fix.

The current g0q source already asserts the Qualcomm VBUS override before core
probe and in its run-stop callback. This does not establish the external
connection state. Conversely, the full MAX77705 patch also changes PD mailbox,
charger and VBUS-source behavior. A single physical-condition test answers a
useful functional question before such an implementation is selected.

The actual PID1 brings up its NCM interface without waiting for carrier and
listens until its existing absolute boot-time deadline. DWC3 disconnect/reset
and `gether_disconnect()` update link state and queues without unregistering
the underlying network device or requiring a second configfs UDC bind. This
is static support for the experiment, not physical re-enumeration proof.

Two rounds each with Claude Opus 5.5 High and Gemini 4 Argon High selected this
unit. Initial suggestions of fixed HOLD windows, zero races, literal binary
reuse and causal success labels were corrected against the actual consumer.
Both final discussions accept the unchanged observer and its fail-stop behavior.
These are advisory discussions, distinct from independent artifact review.

## Bounded attended procedure

The existing [mainline policy](../operations/S22PLUS_MAINLINE_RAM_V1.md) governs
the operation, exact returned approval, attendance, deadlines and original-A
recovery. This report adds no standing authority, runner mode or acceptance gate.
The prospective task's private physical-condition plan records:

1. Issue a replug instruction only after the exact N raw transfer result and
   completed installation step, with the original observation window published.
   Launch/progress output is insufficient. More than 60 seconds of that original
   window must remain when the instruction is issued.
2. The latest complete sealed USB census must show `ENOENT` with no children.
   No selected endpoint, request attempt, selected stop, return transition or
   terminal may be present, and no N/A transfer may be active. A parser result
   of `None` alone is insufficient because it can include partial enumeration.
3. If instructed, the operator removes the cable at the **phone end** once,
   waits approximately three seconds and reinserts it into the same phone with
   the same cable, host port and orientation, without holding buttons. No second
   reseat or request retry is part of this condition. Actual completion and
   timing are retained privately rather than inferred from USB absence.
4. The issuance check does not freeze device state. A spontaneous arrival may
   race the human action and invalidate the observation. Existing generation,
   route, single-socket and one-request checks remain intact; failure preserves
   raw evidence and proceeds only through original-owner recovery.
5. When observation ends, explicitly resolve any outstanding replug instruction
   as completed or cancelled before separately confirming physical Download
   and dispatching A. A replug answer is never a Download confirmation.

No replug is requested if a candidate endpoint or request is already selected,
or the issuance conditions are no longer met. The original 120-second host
observation and PID1 limit are unchanged; human delay does not extend either.
Their different clock origins are not treated as a measured boot-time guarantee.
An omitted, late or unconfirmed physical action limits interpretation; it does
not permit restarting the observation or candidate.

## Qualification and interpretation

The existing 16 USB, connection, owner and complete-observer tests pass. Four
additional H0 fixtures use the unchanged production consumers with synthetic
sysfs and socket inputs: disappearance and generation change before network-up,
generation loss after one connection but before sending, and partial-response
disconnect after one request. They verify owned-profile cleanup, descriptor
closure, retained failed raw bytes and absence of socket/request retry. The
first fixture omitted the endpoint record that real `observe()` publishes;
that fixture prerequisite was corrected and its failed evidence retained.

Fresh kernel/loader/package and actual-EL/VM qualification pass: the real RAM
PID1 and raw-evidence recheck, 342 actual marker cases with six exception-level
VM cases, 20 loader cases and 1,051 aligned-copy checks with three
exception-level VM cases, and two
matching boot/AP packages. Configuration and DT bytes are identical to ML020;
the kernel source difference is limited to fresh V1 frame literals, and seven
relevant functional objects are identical. The unchanged PHY and CPUidle
checks retain their original artifact provenance and complete raw evidence,
joined to new source/config/object equality. Independent exact-artifact and
procedure review is `PASS_GO` with no findings, binding 100 source pins and 480
artifact/raw pins. The unchanged mainline capability, V27 backend and stable
worker reviews are reused. Fixed preapproval D0 completed: seven successful,
complete raw captures rederive current exact original-A health. No unresolved
F1 owner, operator approval, grant or candidate dispatch exists. Fresh effect-time
checks and the exact finite attended approval remain required before transfer.

Applicable past-failure checks are ARTIFACT and ROUTE — confirmed for H0 by
actual package/loader/init identity joins and the unchanged real observer;
WIRE and IO — confirmed for the tested partial-response and disconnect paths,
with sealed failed raw bytes and no retry; SEMANTIC — confirmed by separating
USB absence, physical-action timing, authenticated evidence and recovery;
PERSIST — confirmed for the exercised raw publication/reopen paths, with
failed fixtures retained; RETURN — unchanged original-owner recovery, with
physical return and final health still unconfirmed for this candidate. ABI and
DISPLAY changes are inapplicable: no new syscall/register or display behavior.
HOST — confirmed for the reviewed V27 worker and current preapproval checks.

An authenticated response establishes this candidate's RAM PID1/USB function;
the complete F1 result also requires original Android recovery and final health.
It does not prove that a replug was necessary, identify a CCIC mechanism or
explain previous resets. A descriptor alone is not authenticated PID1 proof.
No accepted response remains `NO_PROOF`, without identifying the failed stage.
Recovered original A and the research result remain separate claims.

There is no kernel/observer logic change, new Type-C/PD/charger driver, storage
access, watchdog call, new marker ladder, or automatic-recovery claim. A90 and
S20+ are untouched. Private artifacts and raw qualification evidence are under
`workspace/private/outputs/s22plus-mainline-ml021-h0-20261104-1/`; discussion and
before/after external-model accounting are under
`workspace/private/outputs/s22plus-usb-attach-discussion-20261104-1/`.

All four external discussion calls completed without retries, fallback or tool
invocation. Claude reported four uncached input, 14,745 cache-creation input
and 11,891 output tokens; its five-hour account meter moved from 0% to 2% used,
and weekly used stayed 3%. Argon reported 34,058 input and 14,164 output tokens
(48,222 total, including 10,086 thinking tokens already in output); weekly
remaining moved from 89.68% to 88.80%. These are account-wide quota changes,
not exact per-call attribution. Claude's reported list-price equivalent was
USD 0.355796; actual subscription charges are unavailable for both providers.
