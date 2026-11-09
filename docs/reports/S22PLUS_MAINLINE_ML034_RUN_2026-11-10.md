# ML034: SH1 confirmation mismatch before UFS, healthy original-A return

ML034 closed **`NO_PROOF / ANDROID_CLOSED_HEALTHY`**. Its authenticated first
response and five-minute same-boot witness passed. The new diagnostic report
identified `BCM_VALUES`: the SH1 confirmation cache had X and Y equal to zero
in all three buckets, while the guard requires Y equal to one. Coverage made
one attempt and observed no trylock failure. It stopped before overlay/UFS
initialization or a local UniPro/link command. Physical Download, one original-A
transfer and seven fresh final-health reads closed the run. No F1 owner remains.

The execution source was commit `822a0dab8c`. The operator returned the exact
1800-second, one-operation approval and current attendance/Download recovery
statement. Existing preapproval health remained fresh when the grant opened.
The exact artifacts and independent reviews remain in the
[H0 qualification](S22PLUS_MAINLINE_ML034_USB_ADMISSION_H0_2026-11-10.md) and
[ML034 policy](../operations/S22PLUS_MAINLINE_UFS_LINK_USB_ADMISSION_V1.md).

## Authenticated observation and one permit

The retained caller issued one valid cue at N+52.311s, with 67.689s left in the
original first-response window. This was later than the approximate +25s
planning aim; no guard or deadline changed. The operator's completed reconnect
response was resolved at +81.876s. That is a response-record time, not a
measurement of physical cable contact.

After 46 absent censuses, the next census selected the exact candidate at
+65.734s. The authenticated base was sealed at +67.704s, within 120s. Raw
rederivation proved packaged Debian SysVinit as initial PID1, the direct
observer, the selected kernel/DT and zero block devices. The base guest uptime
was 54.966s. The same-socket second witness passed after a 300.355s host gap
and 300.495s additional guest uptime. This is a bounded five-minute hardware
observation, not an endurance or installed-Debian claim.

One separate module permit was sent at +370.553s. The complete authenticated
result followed at +370.583s. Module load and result read succeeded; the
operation itself returned `EBUSY(16)` at stage zero.

| Derived field | Observed result |
| --- | --- |
| Final coverage reason | `BCM_VALUES` |
| Coverage calls / first retryable lock reason | 1 / none |
| Selected confirmation row | SH1, index 0 |
| Cached X: active, wake, sleep | 0, 0, 0; matches the required X values |
| Cached Y: active, wake, sleep | 0, 0, 0; required values are 1, 1, 1 |
| Fixed RPMh records, claims, triggers, acknowledgments and reclaims | All zero |
| USB coverage / accepted-reference release flags | Both false |
| Local UniPro commands / link command issued | Zero / false |
| Normal-return eligibility | False |

The interpretation is bound to the actual compiled transport source. This
branch follows successful USB/PM/ICC checks, the selected voter's lock, an empty
pending commit list and a known SH1 confirmation. These preceding checks are
inferred from the reached branch; they are not additional independently sampled
fields. The reported values are lock-protected software confirmation data,
not direct electrical or hardware-register readback. The report contains no
later CN0 row observation.

This rules out a recorded trylock rejection in **this ML034 attempt**. It does
not prove ML033 reached the same branch, explain why the SH1 confirmation was
zero, or justify changing the guard. No second coverage attempt was allowed
after this non-lock failure. The module and candidate remain consumed.

The host stopped normal control at +371.966s. It created no native Download
control intent or packet. The empty ACK capture's `SessionError` and timeout
flag come from the existing late-callback finalizer using the original
first-phase deadline; they are not a timeout of a sent Download command.

## Recovery, health and canonical timeline

The cable cue was resolved before the separate physical Download request.
After the operator reported Download arrival, the original stopped owner
reidentified the target and transferred its original A once. The first
Android boot-readiness observation returned code 1 with a closed-channel
diagnostic and empty stdout. Its raw failure remains preserved; it is not
classified as a failed A transfer or a proved device-disappearance cause.

Raw transfer evidence admitted the existing health-only continuation. It
completed seven fresh health reads, original-A rooted Android health and
`ANDROID_CLOSED_HEALTHY`, without a second transfer or control. The task-owned
network profile was removed and its absence verified; subsequent cleanup
observed it already absent. The global F1 owner was released.

The canonical timeline below uses the grant/session origin, not the N-launch
origin used above. Its combined candidate-ready entry remains `NOT_PROVED`
because the selected late operation failed; independent RAM/USB and witness
facts remain valid.

| Canonical event | Session-relative seconds |
| --- | ---: |
| Live session start | 0.000 |
| Candidate flash start | 25.118 |
| Candidate flash done | 26.962 |
| Combined candidate boot-ready result | NOT_PROVED |
| Original-A rollback flash start | 627.697 |
| Original-A rollback flash done | 629.073 |
| Rollback boot ready | 714.536 |
| Durable live-session close | 714.536 |

## Raw audit and remaining question

Private run evidence is under
`workspace/private/outputs/s22plus-ml034-policy-adoption-h0-20261110-1/`.
`run-audit-1.json` reopens all 533 indexed raw captures plus the separately
sealed cue captures, with acquisition, process creation and sockets blocked.
It rederives both transfers, base/witness/result authentication, cue and census
ordering, seven-read final health, network cleanup and owner closure.
`coverage-interpretation.json` binds the decoded SH1 fields to the retained
compiled source. Old consumed records and unrelated work remain byte-identical.

All five diagnostic/non-success captures are accounted for: the empty ACK
finalizer, three expected owned-profile absence results and the failed first
Android readiness read. A90, S20+ and unrelated Debian boot-journal work were
untouched.

The next H0 question is the relationship between the actual ordinary BCM
command history, its retained confirmation and the active USB consumer.
The current evidence does not establish whether the confirmation expectation,
its producer or the underlying state explains the zero Y values. Investigation
must retain those distinctions and the original guards. No new physical scope
or replay authority follows from this healthy closure.
