# S22+ ML035: known-zero SH1 and the duplicate BCM producer

The operator requested unrestricted-time Argon/Opus discussion of ML034's
SH1 confirmation failure, a correction and the next physical experiment.
The selected bounded change removes six unused display BCM producers from
the exact no-display mainline configuration. Its completion criterion is a
qualified fresh candidate and one separately approved attended run through
original-A health closure. H0 qualification alone does not meet the physical
criterion or grant authority.

## Retained observation and reproduced defect

[ML034](S22PLUS_MAINLINE_ML034_RUN_2026-11-10.md) returned `BCM_VALUES`, detail
zero, at the initial USB admission check. Its known SH1 row held X=0/0/0 and
Y=0/0/0 while the enabled four-node USB request passed the preceding checks.
The result came before overlay/UFS initialization or any local/link command.
ML034 is consumed `NO_PROOF` / `ANDROID_CLOSED_HEALTHY`; its raw evidence,
source artifacts and approval remain immutable.

The actual retained `sm8450.c` registers distinct `bcm_sh1` and
`bcm_sh1_disp` objects with the same name. Their provider has one voter,
and both resolve the same command-DB address. Core sync-state iterates nodes
in binding-index order and commits each node separately. A live normal USB
request can therefore be followed by a zero vote from the unused display
object. The unchanged observer correctly records that accepted command.
Ignoring the display object only in the observer would conceal its producer
command.

The complete retained SM8450 tables contain the same defect for SH0/SH1,
ACV/MC0 and MM0/MM1. The fixed DT has eleven enabled providers on one apps
voter. Its only enabled ICC consumers are SCM and USB. Their paths use normal
nodes, and the 150-node graph has no edge from a normal node into the disjoint
ten-node DISP graph. The retained debugfs write client has an unconditional
`#undef INTERCONNECT_ALLOW_WRITE_DEBUGFS`; its initializer is a stub even
with `CONFIG_DEBUG_FS=y`. KUnit is disabled. The four-package RAM root starts
one fixed observer without a general command or display client.

The H0 reproduction executes 21 mechanically extracted, byte-identical
functions, the full real node/BCM tables and binding indices, the actual
four-node apps path and eight-node USB-DDR path, `icc_set_bw`, and both the
ICC and BCM confirmation consumers. It models command-DB addresses, three
VCDs, stable sorting, kernel plumbing and RPMh submission. Those models do
not prove historical physical ordering or electrically applied state.

| Case | Retained producer | Corrected producer |
| --- | --- | --- |
| USB request, then sync-state | Known SH1 Y=0/0/0; `BCM_VALUES` | Y=1/1/1; ICC/BCM confirmation passes |
| Sync-state, then USB request | Final USB confirmation passes; alias zero commands occurred earlier | Confirmation passes without alias commands |
| USB request disabled | Confirmation rejects | Confirmation rejects |
| RPMh submission failure | Confirmation becomes unknown despite `icc_set_bw` returning zero | Same fail-closed result |
| Same-batch duplicate SH1 objects | Confirmation becomes unknown | Duplicate objects are absent from the selected tables |

SH0, ACV and MC0 on the USB-DDR path and MM0's normal keepalive remain valid
in the corrected command stream. ACV retains its normal mask 8. Normal MM1,
which has no request, still legitimately produces a zero vote; the test does
not prohibit all zero commands. All ten DISP nodes retain their indices and
have no BCM registrations. Nine cases per architecture pass on the host and
with a statically linked AArch64 fixture under QEMU user emulation.

These results prove a reachable source defect and its H0 correction. They do
not identify which object produced ML034's historical row, prove the time of
its sync-state, establish an electrical vote, or identify ML033's unobserved
rejecting branch. A later `BCM_VALUES` would show that this correction was
insufficient on the device, not erase the executed counterexample.

## Correction and discussion

The source-pinned transport preparation removes only six unused BCM
registrations and their orphan object definitions from `gem_noc_bcms`,
`mc_virt_bcms` and `mmss_noc_bcms`. It retains all nodes, links, binding IDs,
normal BCMs and observer predicates. The exact reduced DT is separately pinned.
Among the retained transport source closure and relevant ICC sources, only
`drivers/interconnect/qcom/sm8450.c` changes.

This changes ordinary boot-time ICC commands, including initial alias votes
and their later sync-state zero commands. Normal requests and keepalive floors
can persist where an alias previously overwrote their command. Power or
thermal behavior on the new mainline boot is consequently not assumed to
match an earlier run. The original Android A kernel and its health criteria
are unchanged. The late module adds no refresh vote, new address/value,
extra retry, observer relaxation or new UFS operation.

Argon High and Opus 5.5 each completed two isolated discussion rounds with no
reasoning wall-time cap or tool execution. The second round supplied actual
H0 output and peer conclusions. Both recommended the coherent six-alias
producer correction. Unsupported claims about upstream multi-voter intent,
historical physical causation, literal zero command words, and blanket new
Android health baselines were rejected. A VCD-terminal zero vote has the
commit bit set (`0x40000000`); the observer measures accepted software command
state, not electrical readback. Their advice is not an independent capability
review or a run grant. Private before/after quotas and token records distinguish
account utilization, provider tokens and list-price estimates from billing.

## Qualification, review and scope

The fresh Image and both RAM archives are built. Rebuilding the fixed module
against the new kernel reproduces ML034's module bytes exactly. Both observer
ELFs and CPIO archives were independently reproduced. The loader passed 20
checks, 1,051 aligned-copy cases and actual QEMU exception-level checks; two
boot-only packages are byte-identical. The actual host collector proved a
300.018-second witness and modeled normal return in one ARM64 VM; a separate
VM proved 300.019 seconds and rejected the wrong board before normal control.
Modeled power/virtio/QEMU evidence is not g0q USB, RPMh or UFS hardware proof.
Candidate and owner/bridge independent reviews both returned `PASS_GO` without
findings. The actual consumer accepts all six exact retained declarations and
rejects 93 mixed/unknown cases. Four actual Session fixtures retain original-A
recovery and health-only continuation when optional candidate wire code is
missing or invalid, with one A and no replay. The current shared-policy review
pointer was corrected during review; no earlier receipt was repinned.

The new capability and immutable backend v39 were published under the existing
admission/target locks; the ordinary-terminal worker is unchanged and connected.
The exact ML035 task/proposal and cue caller commands were prepared. Its fixed
foreground D0 completed seven fresh original-A health reads, which were
revalidated from raw evidence. At that preparation boundary no run approval,
grant or operation existed; readiness supplied no run authority.
The [prospective scope](../operations/S22PLUS_MAINLINE_UFS_LINK_BCM_ALIAS_V1.md)
retains the original 120-second first response, same-boot 300-second witness,
540-second total ceiling, 15-second module budget, one late link attempt,
one N and one original A total. The 21-field report and trylock-only USB
admission retain their existing semantics. Physical Download remains the
attended failure-recovery route.

The technical pre-review verified the source mechanism and actual DT/graph
reachability. Final reviews bind the completed Image/module, archive/loader/AP,
qualification and adopted owner/bridge closure. A separately returned finite
one-operation 1800-second approval and current attendance remain required
before the prepared task may run.

The existing checklist applies as follows: ABI/ROUTE use actual functions,
full tables and ARM64 execution; SEMANTIC separates accepted commands from
physical state and records the changed ordinary boot producer; ARTIFACT keeps
fresh candidate outputs separate from consumed provenance; WIRE and RETURN
retain their unchanged strict protocol and original-A recovery. No new display
or storage capability is claimed.

Two private full-table harness mistakes were repaired before the final checks:
the USB-DDR fixture initially selected the wrong aggregator, and it expected
`icc_set_bw` to propagate an error that `qcom_icc_set` discards. A later test's
substring match also included normal `qhs_display_cfg`; exact `_disp` suffix
selection fixed that fixture assertion. Failed sources and raw outputs remain
private. No production predicate or device effect was changed to repair them.

Private evidence roots:

- `workspace/private/outputs/s22plus-ml035-sh1-discussion-h0-20261110-1`
- `workspace/private/outputs/s22plus-mainline-ml035-bcm-alias-h0-20261110-1`
- `workspace/private/outputs/s22plus-ml035-policy-adoption-h0-20261110-1`

A90, S20+ and unrelated Debian journal work remain untouched. Nothing has been
pushed by this task.

## Attended result

After the exact finite approval and current attendance were supplied,
[ML035 ran once](S22PLUS_MAINLINE_ML035_RUN_2026-11-10.md). Its unchanged USB
admission passed on the first attempt and the same-boot five-minute witness
passed. The module then stopped at stage 2 with `EBUSY(16)`, no fixed RPMh
request and no local UniPro/link command. Earlier runtime-PM/clock preparation
had occurred; the precise stage-two predicate remains unobserved.

One original A and a complete health-only continuation returned
`ANDROID_CLOSED_HEALTHY`; N/A each transferred once. The failed first ADB health
read and all 553 indexed raw captures remain retained. The selected correction
and next attended experiment are complete; UFS link completion remains
`NO_PROOF`. ML035 is consumed and cannot replay.
