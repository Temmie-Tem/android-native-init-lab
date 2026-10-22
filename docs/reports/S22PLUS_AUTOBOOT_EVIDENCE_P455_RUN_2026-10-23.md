# S22+ P455: authenticated P452 file pair after P454 replay

P455 consumed its returned one-operation, 1,800-second attended approval on
2026-10-23 KST and closed **ANDROID_CLOSED_HEALTHY**. One reader N and one
original A were transferred. Native CONTROL and the normal original-A transfer
succeeded. One post-A ADB read returned `error: closed`; the original owner
continued only final health, with no additional transfer or physical recovery.
The terminal has recovered=true and final step `recovery-health`. No F1 owner
remains. A90, S20+ and the 46 preexisting unrelated change paths were untouched.
The [H0 qualification](S22PLUS_AUTOBOOT_EVIDENCE_P455_H0_2026-10-23.md) preserves
the original actual artifacts, independent reviews and frozen sources.

## Acquisition and file authentication

The fixed acquisition completed **PASS_ROOT_EVIDENCE_OBSERVED**. The settled
reader made 24 bounded reads totalling 189,440 bytes under partition RO, with
no mount, journal replay or filesystem write. The protected superblock view
was state 1, RECOVER 0, orphan 0. This is not a complete current-root comparison.

| Selected P452 file | Result | Captured bytes | Authentication |
| --- | --- | ---: | --- |
| Early | READ | 10,972 | All 14 records through EARLY_PRE_UNMOUNT |
| Runtime | READ | 1,024 | All 6 available records, through rcS child-fork boundary |

Both files have root-owned regular 0600, single-link metadata. Raw bytes were
saved before decoding. The source-bound collector returned
**PASS_AUTHENTICATED_LOCAL_PROGRESS** without a trailing parse or authentication
error. The early file is byte-identical to P453's pre-replay capture. Runtime,
which P453 reported absent in the dirty home-block view, is now visible.

The two authenticated headers match in boot identity and derived nonce. The
original P452 retained raw spans and unchanged decoders independently rederive
a match only with the first of its three authenticated boots; that span's
kernel header is outside the retained fragment. These files do not establish
the later boots' filesystem effects or assign the operator's accidental boot
and remaining resets to particular spans.

Early retains 76 module completions, six client attempt/return pairs and device
elapsed records 6,435–6,593 ms. Runtime records cover 15,404–15,463 ms and prove
installed Debian PID1, automatic-start recording, rcS phase entry and child
fork. The one platform sample reports CPU0 and watchdog-enabled state; it
does not prove continuous CPU state or hardware watchdog renewal. There is no
child completion, rcS/runlevel completion, 120-second service, SSH or clean
shutdown proof. The persistent format does not contain per-script packets;
it does not add a mountkernfs return or identify a stall/reset location.
P452's existing retained hostname completion and separate mountkernfs BEGIN
evidence keep their original meanings.

## Closure and remaining boundary

The reviewed terminal tool dispatched the exact approved entry once after
current source, artifact and preceding P454 closure checks. Fresh Android
preflight passed. After the completed original-A transfer, the one transient
read failure was preserved; the existing health-only branch rechecked changed-
boot rooted Android, boot/supporting partitions, full GPT and Android32 statfs.
Final health passed at 105.138 seconds without another mode change or transfer.

H0 closure rederived **679 raw captures**, the unchanged **20-row journal**,
terminal, consumed claim and exact N/A counts with process/device acquisition
blocked. The single failed capture remains in the close audit. H0 file
interpretation also blocks process/device acquisition. P455 and its grant are
consumed; no replay or follow-up device authority is created.

Canonical timeline, seconds from the original grant:

| Event | Seconds |
| --- | ---: |
| Live session start | 0.000 |
| Candidate transfer start / complete | 16.371 / 17.893 |
| Native ready and fixed read intent | 43.358 |
| Fixed read complete | 47.204 |
| Original-A transfer start / complete | 55.455 / 57.045 |
| Original-A final health proved | 105.138 |
| H0 audit and task close | 112.435 |

P454's ten unaccounted tree entries and `RECOVERY_NOT_PROVED` comparison remain
unchanged. The selected pair identifies no additional tree paths and supplies
no writable-root admission. Further work starts with H0 analysis of this exact
history; another writable Debian candidate still requires qualified exact
history and fresh complete protected current-root admission. P452, P453, P454
and P455 are never replayed.

Private evidence:
`workspace/private/outputs/s22plus-autoboot-evidence-p455-h0-20261023-1/`.
The task's `closed.json` binds the consumption and `closure-audit.json`;
`retrieval-1/` preserves acquisition and both raw files;
`p452-file-interpretation.json` binds authentication and the retained-boot join.
Frozen host/runtime/collector sources and the terminal-tool intent/result retain
the exact execution provenance.
