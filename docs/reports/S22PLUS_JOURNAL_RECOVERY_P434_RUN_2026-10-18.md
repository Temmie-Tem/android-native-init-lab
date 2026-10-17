# S22+ P434: journal replay completed; selected root not admitted

Status: **RECOVERY_NOT_PROVED; ANDROID_CLOSED_HEALTHY**.
The approved P434 operation is consumed and closed. Execution date:
2026-10-18 (Asia/Seoul). There was one candidate N transfer, one original-A
transfer and no additional recovery transfer. No F1 owner remains. A90 and
S20+ received no command.

The strict journal writer completed and the separate read-only checker passed.
The superblock changed from `state=1 recover=1 orphan=0` to
`state=1 recover=0 orphan=0`. All 8,971 selected comparison entries, including
the two sealed historical files, matched. The complete tree nevertheless had
one entry beyond the selected accounting. P434 therefore did **not** prove
the complete selected root, and P435 was not started or granted authority.

## Observed result

| Check | Result |
| --- | --- |
| Initial protected state | Dirty journal: `clean=0 state=1 recover=1 orphan=0` |
| Strict writer | Completed, stage 5, error 0, I/O error 0 |
| Writer accounting | 24 reported writes, 95,232 bytes; this is not a count of unique disk bytes |
| Writer settlement | Reaped and settled, status 0, no adopted descendant |
| Separate read-only checker | Proved, reaped and settled, status 0 |
| Post-replay protected state | `clean=1 state=1 recover=0 orphan=0` |
| Selected table comparison | Expected/matched 8,971; missing, metadata, content and findings all 0 |
| Boot-input subset | Expected 8,175; no missing, metadata or content mismatch |
| Full tree | 8,977 entries: 6,825 files, 1,006 directories, 1,146 links, zero other types |
| Allowed total | 8,971 table entries + four fixed entries + one admitted mutable extra = 8,976 |
| Complete-root result | `exact=0`; `RECOVERY_NOT_PROVED` |
| Cleanup | Partition RO, protected mount unmounted, authenticated DETACH and same-boot return completed |
| Final return | Exact changed-boot original Android32 health; `ANDROID_CLOSED_HEALTHY` |

The protocol's `JR1_ROOT extra=1` counts an **admitted mutable extra**, not the
unknown entry. The unaccounted count is independently derived as
`8977 - (8971 + 4 + 1) = 1`. The helper emits the complete root result only
after its mutable-data and historical single-link checks return successfully.
The observed count mismatch is sufficient to reject full admission.

The comparison retains the existing declared mutable `wtmp` metadata/size
exception. Its matched count does not mean that every byte of that mutable
log equals the installation archive. Other immutable table checks and both
exact historical-file checks remain required.

The current output does not name the unaccounted path or provide its content.
It does not establish that this is P432's runtime record, that replay created
the entry, or that installed Debian init or services ran. P433's earlier
runtime-file absence was from dirty home blocks and cannot establish its
post-replay absence. No unexpected file was admitted, deleted or repaired.

## Authority and recovery

The operator returned the prepared one-operation/1800-second attended P434
approval in response to the physical-attendance/Download-recovery prompt.
Only line wrapping and one whitespace character inside the hexadecimal task
hash were normalized; every non-whitespace character matched the proposal.
The verbatim answer and canonical comparison are retained privately.

Execution used the [qualified P434 selection](S22PLUS_AUTOBOOT_TRANSITION_P434_P435_DESIGN_2026-10-18.md)
at source-tree base commit `56bd83a470b056126f361468491e6bff40c959be`, its exact
reviewed working-tree snapshot, original-A artifact and current common detail
pin. Current Android preflight, actual image/rollback bytes, source capability,
host readiness and global exclusion passed before the first effect.

The owner sent one N, authenticated native health, issued the sole original
pre-EXEC journal intent, observed complete writer/checker/root output and
DETACH, then authenticated the same boot for normal Download return and sent
original A once. The expected complete-root rejection did not trigger another
writer, a repair, another native image or an installed-init transition.

After the proved A transfer, one final-health command reported that the
selected ADB device was not found. The raw exit-1 evidence is preserved.
The existing recovery path continued only health acquisition and completed
without another A transfer, reboot or physical Download action. Thus
`recovered=true` and `normal_return=false` describe the final health
continuation; they do not mean the journal writer was repeated.

Final health proves root, exact original boot/supporting partitions, matching
GPT, native partition presence, Android32 capacity of 34,357,624,832 bytes and
a changed Android boot. Android recovery does not undo native_data writes or
replace the failed complete-root admission.

## Canonical timeline

Times are seconds from the original P434 grant opening. Boot-ready is the
authenticated native-health boundary immediately before the fixed journal
intent. Final closure includes the subsequent H0 audit.

| Event | Seconds |
| --- | ---: |
| Live session start | 0.000 |
| Candidate transfer intent | 18.686 |
| Candidate transfer complete | 20.213 |
| Candidate boot ready / journal intent | 45.727 |
| Journal operation complete | 50.751 |
| Original-A transfer intent | 59.019 |
| Original-A transfer complete | 60.613 |
| Final Android health complete | 108.898 |
| Session close and H0 audit | 281.466 |

## Evidence closure and next bounded step

The H0 audit rederives initial health, both transfers, journal output, native
return and final Android health from the production consumers. It verifies
648 raw command captures, the one classified post-A read failure, the
365-file pre-execution source snapshot and the permanent consumed claim.
Original journal and terminal bytes remain unchanged. Device acquisition is
disabled during this audit; its only allowed subprocesses inspect the two
bound local ELF tools with `file`/`readelf`.

Private evidence, the one-shot task close, original raw outputs and source
snapshots remain under
`workspace/private/outputs/s22plus-autoboot-transition-p434-p435-h0-20261018-1/`.
The existing H0 qualifications are reused; no producer or policy was changed
to accept this result.

P435 remains ineligible until the additional entry is identified and the
selected complete root is qualified. The smallest next acquisition is a
separately prepared, fresh fixed reader of P432's already declared early/runtime
pair from the post-replay filesystem. That can test whether the runtime record
is now visible; its absence would not identify the other entry. It needs its
own current capability/artifact qualification and finite attended grant.
Neither P433's consumed reader nor P434's consumed writer may be replayed.
