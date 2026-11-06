# S22+ ML031: prepared attach cue and fresh dwell/link candidate

Status: **H0 qualified; adoption/owner independently reviewed; awaiting exact
attended approval**. Candidate transfers, device controls and new grants: **0**.
The subsequent preparation completed one fixed seven-read preapproval D0.

ML031 is a new candidate after [consumed ML030](S22PLUS_MAINLINE_ML030_RUN_2026-11-07.md).
The work addresses the concrete preparation failure: the assistant tried to
assemble the physical attach caller during the initial 120-second window.
The fixed caller now imports and exercises the actual retained consumers
before a future launch. The initial H0 phase left the ML030 owner, protocol,
window lengths, source reviews, bridge selector and permanent boundaries unchanged.
[Prospective exact scope](../plans/S22PLUS_ML031_ATTACH_DWELL_LINK_SCOPE_2026-11-07.md)

## New artifact and retained machinery

The unchanged production recipe generated new physical and VM keys and
candidate identities. Their observers and CPIO archives were fully rebuilt
from their saved recipe, seal and original inputs; the resulting bytes match
the selected artifacts. The four signed Debian packages and their fixed files,
Image, DTB, module and all late PHY/RPMh/USB machinery retain their original bytes and
reviewed provenance. No compiler-inlined key bytes were masked for comparison.

The new physical loader passed 20 actual ARM64 loader cases, 1,051 aligned
copy cases and the actual QEMU EL1/EL2/EL3 checks. Both independent boot/AP
packages match. Offline unpacking joins the single `boot.img.lz4` member to
the boot-v4 kernel, exact loader, embedded Image/DTB/archive and preserved
original-A outer envelope. The exact hashes are in the scope proposal.
At that initial H0 close, the ML030-only live validator refused the new AP;
this was an intended boundary before the separate adoption below.

## Fresh protocol qualification

The actual production host collector ran against the newly built ARM64 VM
observer. Only the loopback endpoint, VM first-frame verification and modeled
hardware fixture were substituted; no phone or host network profile was used.

| Case | Guest uptime, seconds | Outcome |
| --- | --- | --- |
| Actual host, emulated UIC and modeled power | 1.649 to 301.777 | One emulated link, result-bound Download and QEMU reset |
| Actual host, retained physical module on QEMU | 1.585 to 301.714 | Module load returned ENODEV; no normal control |
| Early second challenge | Original window | ETIMEDOUT, parked without module result or Download |
| Invalid module permit after the dwell | Same-boot late witness | EACCES, parked without module result or Download |

The first two host gaps were 300.015 and 300.016 seconds after sealing their
first responses. Each witness joined its own boot and nonces. The modeled
positive case traced one QEMU UIC link command and zero SCSI commands.
Its power fields are explicitly modeled; neither it nor QEMU's wrong-board
rejection proves physical g0q power, UFS, five-minute survival or Download.
Unchanged lower-level PHY/RPMh failure evidence is reused by exact byte and
source identity, rather than rerunning the entire historical suite.

## Caller behavior and prelaunch use

The new caller has only `check`, `issue` and `resolve`. It does not open a
task/grant, read connected hardware or drive the transfer. Its operation path
comes from the future exact approved owner. The caller checks the current
Session/grant/consumption/F1 owner, real raw-complete N, original window,
latest sealed absence, active step and absence of request/return/stop state.
It uses the existing local attach lock, avoiding contention with the running
owner's target lease.

Fifteen focused tests cover real transfer/raw consumers, incomplete or changed
transfer output, precise ENOENT/no-child grammar, another topology, incomplete
latest capture, endpoint/request/return races, the strict 60-second boundary,
delayed validation/publication, an exception after publication, duplicate
issuance and the existing resolution/closure interlock. Importing the actual
CLI from another working directory passes before any operation is available.

Prepare these commands and the exact future operation path before N:

```text
python3 workspace/public/src/scripts/host_tools/s22plus_mainline_attach_cue_v1.py --help
python3 -m unittest discover -s tests -p test_s22plus_mainline_attach_cue_v1.py
python3 workspace/public/src/scripts/host_tools/s22plus_mainline_attach_cue_v1.py check <exact-operation-directory>
python3 workspace/public/src/scripts/host_tools/s22plus_mainline_attach_cue_v1.py issue <exact-operation-directory>
python3 workspace/public/src/scripts/host_tools/s22plus_mainline_attach_cue_v1.py resolve <exact-operation-directory> completed <actual-operator-statement>
```

`check` and `issue` are used only after the original N completion/window exists;
they do not make an unstarted task ready. Poll only existing journal/raw state
promptly after a separately approved start. If an endpoint is already selected,
do not issue a cue or disturb the receiver. If the caller returns
`CUE_RECORDED_DO_NOT_DISPLAY`, do not show the physical instruction or retry;
retain the record and obtain its actual cancellation before physical recovery.
Display success immediately while more than 60 seconds remain. The actual
operator reply supplies `completed` or `cancelled`; no answer is inferred.
These are prepared uses of the existing condition, not a new approval layer.

## Validation and evidence

Initial H0 tooling errors were preserved: the loader test first used a Python
environment without the already-retained Unicorn dependency; the cue fixture
initially lived outside the adapter's private-storage tree and its tamper test
omitted changing its own sealed fixture's read-only mode. The corrected
environment and fixtures passed without weakening production checks. The
offline artifact auditor was corrected to respect the retained review/ELF
hash-only record format and the explicit bounded size of loader/AP artifacts.
No failure initiated or repeated a device effect.

Applicable checklist concerns are HOST/ROUTE — real import, caller and prior
missed cue; RETURN — unchanged interlock, physical recovery and no replay;
WIRE/SEMANTIC — actual fresh host/guest exchange with explicit model limits;
ARTIFACT — complete reproduction and actual embedded bytes; PERSIST/AUDIT —
immutable old records and bounded new raw evidence. No new hardware or
execution-control hazard is claimed from ML030's absence result.

Evidence is private under
`workspace/private/outputs/s22plus-mainline-ml031-attach-dwell-h0-20261107-1/`:
physical/VM recipes, `producer-check-1`, loader/EL/package outputs,
`actual-host-vm-modeled`, `actual-host-vm-wrong-board`, guest negative cases,
cue test logs, `qualification-1.json` and review inputs. The before/after
checks bind ML030's consumed records and unrelated dirty files. No external
provider model was invoked. No worker, bridge selector or other target was changed.

## Independent close

The independent reviewer returned **PASS_GO with no open findings** for the
candidate, fixed cue caller and prospective scope. The exact review input is
SHA-256 `e2b69a7ca76858516bf2ae5312d8799749eadc5e73799ce170ab2170686b7277`;
the result at `review/independent-review-1.json` is SHA-256
`c657cd199d2b041e4a1e0cb2b3899f530bc9339942767bb03b68221fdef6131f`.

The reviewer independently rechecked actual ELF symbols and embedded bytes,
both boot/AP packages and the retained outer envelope, reproduced observers
and archives, new identities, 32 sealed captures and all four guest cases.
Additional caller checks covered real Session consumption/F1 ownership,
actual consumed-ML030 rejection and the public resolution path after expiry.
The review also confirmed unchanged current capability/bridge/common/target
bindings, 32 protected ML030 records and 11 unrelated dirty files.

The first independent rechecker interpreted every loader `expected=true`
case as entry, overlooking expected full-kernel/FDT-park behavior. Its
corrected consumer passed; both scripts and raw logs remain in `review/`.
No production guard was changed. This H0 close creates no ML031 live adoption,
task, approval, grant or device action.

## Subsequent ML031 scope adoption and admission

After the operator requested the next step and then approved proceeding with
it, revision 66 added a distinct exact ML031 common/target delegation. The
original ML030 common block and policy are unchanged. The new
[followup policy](../operations/S22PLUS_MAINLINE_UFS_LINK_FOLLOWUP_V1.md)
adopts the reviewed proposal while preserving the one-candidate limit,
120/300/540/15-second bounds, one-operation 1800-second attended grant,
closed hardware scope, one original A and no replay. The H0 proposal/review's
original unadopted and rejected-admission records retain their historical bytes.

One declaration table now selects the two exact image closures by AP hash.
ML030 remains the default H0 preparation selection; ML031 requires explicit
selection. There is no unknown-candidate fallback. Each declaration binds its
own manifest, archive, loader, qualification and independent review. ML031's
distinct review schema is joined through its exact reviewed input/evidence
pins and retained kernel/module review, not a copied PASS label. A live normal
task additionally checks its selected policy in both common and target adoption.

The unchanged original Session, guest protocol and terminal transport are
reused. Normal source admission includes the new policy and fixed cue caller.
Recovery omits the optional candidate/cue source dependency; it keeps original
authority, target, A, health and no-replay checks. The bridge source selection
also excludes the cue file from its recovery prerequisites. New capability
and immutable bridge review receipts are required before the revised entry
can run; old review receipts and consumed grants are not repinned.

The actual preparation/consumer accepted both exact artifacts, including the
historical ML030 image, and refused 17 bidirectional mixed/unknown cases.
One hundred thirty-six focused wire/owner/bridge/cue tests and 21 additional
mainline tests passed. Four isolated real-Session cases removed or corrupted
the optional cue source, with either first A recovery or health-only completion
after an already completed A. Each restored A exactly once and replayed no
control. Independent source-consistent fixtures accepted the adopted ML031
case and rejected a missing common link, missing target link or absent policy
status through the actual live task validator. All these tests were H0.

The unchanged guest/kernel/module bytes and complete retained ARM64 VM/raw
proofs were reused. No new kernel build or 300-second VM run was needed for
these admission and authority changes. The new phase's private evidence is
under `workspace/private/outputs/s22plus-ml031-policy-adoption-h0-20261107-1/`,
including the actual scope-adoption statement, before-source snapshot,
`admission-cases.json`, `cue-recovery-final/`, focused logs and source-exact
review inputs. No physical transfer is authorized by this preparation.

## Adopted owner review and preapproval readiness

The final independent adoption/owner/bridge review returned **PASS_GO**, with
no open findings, over 53 mainline sources and 49 bridge sources. Its exact
input SHA-256 is `3387e74a4f25f6d963d4a7bf517147da4519d92480f2243e064a6d6bfdce9614`;
the review result is `b880fb572bee293061333d7ce3e90f89da6e6c87002dfc8b35eb9c1c5500046d`.
The new capability receipt and immutable bridge V35 were published from that
source set. The selector advanced to V35; V34 and the original capability
receipt remain unchanged. The connected worker accepted the new backend
review with its original worker-source hashes and no restart or modification.

The exact ML031 task was prepared from ML030's healthy closed original-A
record. The fixed cue CLI was imported before any N, and its exact check,
issue and actual-response resolution commands were saved for this task.
One named foreground preapproval D0 completed. All seven raw health captures,
current source/artifact/recovery bindings and the existing freshness condition
were revalidated. No approval record, grant, operation, candidate control or
partition transfer was created. The next F1 step still requires the actual
returned exact finite approval and current attendance/usable physical Download.

The adoption directory retains `owner-review-complete.json`,
`prepared-cue-commands.json`, `verified-preapproval-readiness.json`, the
connector declaration and task/source snapshot. Protected ML030 records,
the reviewed H0 proposal/evidence, unrelated work and A90/S20+ are unchanged.
This preparation does not prove physical ML031 boot, five-minute survival,
UFS link or return.
