# S22+ P453: P452 early capture and missing runtime in a dirty home-block view

P453 consumed its returned one-operation, 1800-second attended approval on
2026-10-23 KST and closed **ANDROID_CLOSED_HEALTHY**. One reader N and one
original A were transferred. Native CONTROL and the normal return succeeded;
no recovery continuation or additional transfer was needed. No F1 owner remains.
A90, S20+ and the 46 preexisting unrelated change paths were untouched.
The [H0 qualification](S22PLUS_MOUNTKERNFS_P453_H0_2026-10-23.md) and
[mountkernfs analysis](S22PLUS_MOUNTKERNFS_P453_ANALYSIS_H0_2026-10-23.md)
retain the independent review, exact sources and actual artifact/VM checks.

## Acquisition and authenticated result

The fixed mountless acquisition completed **PASS_ROOT_EVIDENCE_OBSERVED**.
The child settled after 22 bounded reads totalling 181,248 bytes, with
partition RO and no mount, journal replay or filesystem write. The protected
superblock view was state 1, RECOVER 1, orphan head 0.

| Selected P452 file | Result | Captured bytes | Authentication |
| --- | --- | ---: | --- |
| Early | READ | 10,972 | All 14 records through EARLY_PRE_UNMOUNT |
| Runtime | ABSENT_IN_HOME_VIEW | 0 | No captured bytes; no pair join |

The early file has the required root-owned regular 0600, single-link metadata.
Its raw bytes were saved before decoding. The original source-bound collector
returned **PASS_AUTHENTICATED_LOCAL_PROGRESS**, with no trailing parse or
authentication error. The preparation contains 76 module completions; six
client calls have attempt/return records. Durable records span device elapsed
6,435–6,593 ms, through the pre-unmount record. That record is not an unmount
return, installed-init, rcS completion, service, SSH or clean-shutdown proof.

The early boot identity matches only the first of P452's three authenticated
retained spans. Its kernel header was already outside the retained fragment.
This join was rederived from the original raw retained bytes and unchanged
primary/script-channel decoders; the other two boot identities do not match.
The operator's accidental additional boot and the remaining reset causes are
still not assigned to those spans.

Runtime absence describes the checkpointed home-block view. RECOVER=1 means
journal recovery is pending; this view may omit committed journal-only updates.
It does not prove that runtime was never created, deleted, or never executed.
The capture does not extend P452's existing authenticated hostname completion
and separate mountkernfs BEGIN into a mountkernfs return or a failure location.
Complete current-root consistency and later-boot filesystem effects remain
unproved. P452's original evidence and consumed actions are unchanged.

## Closure and next step

The reviewed ordinary-terminal entry checked the exact returned approval,
source snapshots and preceding P452 healthy closure before the original V3
grant opener and CLI. Fresh Android checks, original-A transfer and changed-boot
rooted Android32/GPT/statfs final health passed. The terminal has recovered=false.

H0 closure rederived **643 raw captures**, the unchanged **18-row journal**,
terminal, consumption and exact N/A counts with process/device acquisition
blocked. No failed raw capture occurred. The task and grant are consumed.

Canonical timeline, seconds from the original grant:

| Event | Seconds |
| --- | ---: |
| Live session start | 0.000 |
| Candidate transfer start / complete | 15.262 / 16.778 |
| Native ready and fixed read intent | 41.977 |
| Fixed read complete | 45.520 |
| Original-A transfer start / complete | 53.701 / 55.269 |
| Original-A final health proved | 102.495 |
| H0 audit and task close | 168.630 |

The next bounded unit is H0 qualification of a fresh native_data-only strict
journal-recovery candidate. Eligibility and the current data accounting must
be checked; this observation alone grants no replay or repair. Any qualified
recovery requires its own returned attended grant. After healthy closure, a
separately qualified fresh reader can inspect the P452 pair again. Do not
repeat P453 or start another writable Debian boot on this evidence.

Private evidence:
`workspace/private/outputs/s22plus-mountkernfs-p453-h0-20261023-1/`.
`offline-prepared-1/task/closed.json` binds the consumption and `closure-audit.json`;
`retrieval-1/` preserves the complete acquisition and early bytes;
`p452-file-interpretation.json` binds authentication and the retained boot join.
Frozen host/runtime/collector sources preserve execution provenance.
