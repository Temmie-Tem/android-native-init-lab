# S22+ UFS upstream handover, phase 4b (H0): stage, report V18, adoption, ML066 preparation

Status: **adopted (v76, `f39092fb22`); capability-11 frozen; ML066 prepared,
not run.** Host-only, no device action. The operator approved the
[step-4 design](S22PLUS_MAINLINE_UFS_UPSTREAM_DRIVER_DESIGN_H0_2026-11-28.md)
on 2026-11-28 ("1~4 전부 승인할게, 4a부터 진행해") and asked for 4b
("이여서 진행해").
[Phase 4a](S22PLUS_MAINLINE_UFS_UPSTREAM_4A_H0_2026-11-28.md) built the
gate, the overlay and the PHY render.

## What 4b runs

One composite `g0q_ml030.ko`, loaded once by the authenticated observer
after the 60-second witness and permit. The observer's module and result
paths are unchanged. The floor kernel Image `5139aab5…` is unchanged.

| Part | Source |
| --- | --- |
| Gated `ufshcd` core (+ sysfs, MCQ, TX EQ, debugfs) | pinned 7.2.11, `gate_render.py` + `combine_render.py` |
| `ufshcd-pltfrm`, `ufs-qcom` | pinned 7.2.11, `combine_render.py` (registration hook, platform shutdown) |
| QMP UFS PHY | pinned 7.2.11, `phy_render.py` (three g0q table values) |
| Stage | `g0q_handover.c` |
| Late overlay | `upstream_overlay.py` (`d33d058e…` for route DT `51b58a40…`) |

**Sequence.**
1. Pre-effect admission:
   - board `samsung,g0q`;
   - BOOTTIME ≥ 60 s;
   - the 150-second budget ends before 525 s;
   - one load only.
2. Module init registers the core, PHY and `ufs-qcom` drivers.
3. One worker thread then:
   - applies the overlay;
   - takes the host only once it is bound, under the device lock and pinned by a SCSI host reference;
   - retries the LU 0 open until the device number is live;
   - reads LBAs 1–3 and LBA 62,305,152 with `IOCB_DIRECT` through `vfs_iocb_iter_read`.

   Each read checks the budget last before submission.
4. Init waits for the worker until the budget ends, then freezes the
   report.
5. Init sets the module's asynchronous-probe flag, so loading does not wait
   for the upstream LU scan.

**Shutdown.** At restart the controller's request lists are stopped and HCE
is cleared, both in the W-LU shutdown before the clocks can stop and in a new
`ufs-qcom` platform shutdown (after a runtime resume) for a host without a
W-LU. HCE must read 0 within 1 s. Otherwise `core_reset` is asserted and the
restart parks, the same rule as the fixed storage stage.

**Report V18.**
- Format: 69 fields in a 1024-byte envelope, tag `0xf0300000`.
- Steps: ADMITTED, DRIVERS, OVERLAY, HBA, LU0, GPT, DONE.
- `link_wire.upstream_handover` checks every producer invariant per step,
  including the frozen-report cases.
- Completion requires all of:
  - step DONE;
  - host OPERATIONAL;
  - LU 0 = 62,305,280 × 4096;
  - GPT `a0de4421…`;
  - test block = the retained pattern `1155097a…`.

## Contract (v76)

**Common details.** A new paragraph, "Upstream handover (step 4b)", covers:
- the composite and its fixed rails (S12B 1.256 V, L6B/L9B 1.2 V, L7B 2.504 V, min = max, plus the existing L5B);
- the gate list;
- the budget and the frozen report;
- direct reads;
- stop-or-park at shutdown;
- the stall residual. A stalled probe, scan or shutdown can hold the timer child's restart, and the attended physical Download is then the recovery.

The paragraph delegates no write, mount, BSG, RPMB, ICE, TLMM or series step.

**Version ranges.** The fixed UTP storage stage is now limited to V14–V17.
The write lane, series steps and phase 2c predecessor are limited to V17
(`task_v1.ufs_write`).

**Binding.** A V18 capability pins the seven `s22plus_ufs_upstream_h0`
sources. Original-A recovery skips them, like the other guest build inputs.
The candidate validator requires the component receipt's source digests to
equal them. It also requires the floor Image `5139aab5…`, and that the
overlay baseline is the capability's route DT.

**Review.** Independent Codex review, 4 rounds under the one-round rule.
- **Round 1: HOLD, 9 blocking findings.** They covered:
  - finit/async-scan waits;
  - no shutdown stop-or-park;
  - unbound component sources;
  - a transient open failure;
  - an unlocked bound check;
  - decoder gaps;
  - gate snapshot races;
  - buffered reads;
  - over-broad version text.
- **Rounds 2–3: confirming, limited to the fixes.** They held on fix-introduced items:
  - `__init` code reached from the worker;
  - a host without a W-LU;
  - a recovery dependency;
  - `f_iocb_flags`;
  - a read started after the budget.
- **Round 4: PASS.**

Records: `s22plus-cue-adoption-reviews-20261122/ufs-handover-v76-review-r1..r4`.
The gateway selects v76. The six shared receipts were restaged mechanically.

## Artifacts

All of these are under `workspace/private/outputs/s22plus-ufs-upstream-h0-20261128-1/`.

| Artifact | Identity |
| --- | --- |
| `component-handover-2` (from adopted main) | module `8b0f1318…`, 660,168 bytes, 303 imports, no diagnostics; byte-identical to the reviewed validation build |
| `candidate-handover-1`, `-2` | report V18, witness floor 60 000, distinct APs; joins and reproduction pass |
| `capability-11` | `241c4543…`, 97 sources, 845 evidence rows; check `f80b407c…` |

**Owner review of capability-11.** One Codex round: PASS_GO, no blocking
findings. The review covered:
- the disassembly: gate placement, both stop-or-park calls, no write path in the stage;
- the overlay bytes and the rails;
- candidate freshness, joins and reproduction.

It recorded one non-blocking point: the component's `compile.log` is empty
and is therefore not pinned.

**ML066.** The task is prepared at
`workspace/private/outputs/s22plus-ml066-ufs-handover-h0-20261128-1/task-1`.

| Field | Value |
| --- | --- |
| Task | `7d160500…` |
| Qualified image | candidate a, `09981057…` |
| Preceding closure | ML065 |
| Approval scope | single run, 1800 s, attended |
| Spare | candidate b, qualified-ready |

## Next

ML066 runs this once, attended, under one exact returned single-run
approval. If the link or the gear change fails, the report shows where. The
next report version can set a lower gear limit only through a new contract
change. 4c (read-only mount of `native_data`) follows a completed 4b.
