# S22+ FYG8 P3.31 bounded resident-reconnect H0 readiness

Date: 2026-09-03
Target: `SM-S906N / g0q / S906NKSS7FYG8`
Status: `PASS_GO_P331_H0` / `PASS_P331_PROCESS_V2_READY_MANIFEST_HOST_ONLY`

## Outcome

P3.31 is ready for a fresh attended Process-v2 preparation. It is a narrow
resident precursor, not a resident installation. The boot-only candidate may
open exactly two authenticated native-PID1 CDC-ACM sessions separated by one
clean reconnect. Each session accepts exactly one fixed heartbeat/status
command, requires a fresh distinct nonce and HMAC-SHA256 authentication, and
then closes. PTY, caller-selected commands, arbitrary file transfer,
persistence and an unbounded service loop remain absent.

Any later live run still requires fresh exact-target D0 preparation, a newly
returned approval, attendance, one candidate transfer at most, mandatory exact
Magisk rollback, final rooted FYG8 health and a matching F1 ledger closure row.
Neither this report nor the ready manifest is live authority.

## Exact host closure

- Run identity: `c331f1e0a90b5e6d7c8a9b0c1d2e3f9b`.
- Final build result: `46253B/39c4ae4d6c156f3cac1eed5037dd5172e5dafedf2f24238de431f4e32ceb35d4`.
- Candidate AP A/B: `28631081B/729b33c3bad602e1d5863fa8cfa6a4bdf22f194a74d378f7417879897bf4d08d`.
- Candidate boot: `100663296B/026e126260e0be5ec2bdf171f40f2588556d89b9894fe07fd16a0568474c622a`.
- Candidate static receipt: `30639B/6a895b54f47a6c939bf480e3817080e7ae28d0bb15e31925648891c198fad906`.
- Exact rollback AP: `23367721B/d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.
- Current ready-2 manifest: `6159B/d3857ebb312d3e9859169f98872596411d8c89ebd735791b92c505167c310d50`.
- Runtime: `18203B/b146a1b9c46fc5db520c20d8c250dcc565c9882723ba82398fb8d1cd60f69750`.
- Observer: `25273B/59d82f28dd50d8a1e39b4b267667bb4a56310acd71667b4df96499d43cdd558d`.
- Live runner: `442942B/badee11c3308daba6dfc0bfb224c83535a28429de92522189fcda96cab71c862`.

The durable receipt retains bounded per-session host TX bytes. Reopening
stable-reads the immutable raw RX, splits the two ordered sessions, validates
each RX identity and frame CRC, derives each challenge nonce digest from the
raw frame, validates each TX identity, and rejoins TX to the top-level
identity. Malformed nested values normalize to a bounded parser failure rather
than escaping the recovery path.

## Validation and review

- P3.31 focused runtime, observer, artifact, adapter, build, static, evidence
  and live tests: `28/28` PASS.
- Common Process-v2 plus P3.27-P3.30 live regressions: `151/151` PASS.
- Prepare wrapper: `4/4` PASS; audit-only reported `created=false`,
  `device_contact=false`, `odin_invoked=false` and `live_authorized=false`.
- Current-tree raw-first scan: `1844` Python files and `420` subprocess
  modules, verdict `PASS_S22PLUS_FYG8_RAW_FIRST_OBSERVER_BOUNDARY_H0`.
- Touched Python compiled and `git diff --check` passed.
- Independent Luna MAX review first found two receipt-parser defects. After the
  bounded raw-session binding and exception normalization repair, focused
  hostile re-review returned `PASS_GO_P331_H0` with no remaining material
  blocker.

The first ready-1 D0 contacted only the exact S22+ and stopped before any
reboot, Download request, Odin or transfer because the P331 decoder rejected
the retained P330 record. Its immutable raw baseline is
`2097136B/3136c504434fac224f9fb9ffe1f688d1bf73062fbb75cb0da8117a885f3e05c6`.
The exact P330 decoder finds one integrity-clean, foreign-free
`NO_PROOF_OBSERVER` record at offset `1657877`, with no candidate-success
claim. A P331-only preflight exception now treats only those exact bytes and
semantics as proof that P331 is absent. Changed bytes reject, and the exception
expires on raw drift or candidate intent. Independent proportional review
returned `PASS_GO_P331_PREDECESSOR_BASELINE_H0`; ready-1 remains preserved and
ready-2 replaces it for fresh preparation.

No Odin, reboot or transfer occurred during the H0/D0 preparation work. P3.30
remains consumed and is not replayed. A successful P3.31 F1 would prove a
reconnectable bounded authenticated channel; choosing retained boot versus a
Magisk R1 resident install remains a separate post-result decision.
