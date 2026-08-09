# Goal: A90 native bridge to Debian runtime

Build the operator-owned Galaxy A90 5G into a Debian-oriented personal server
where native-init performs only the vendor-kernel and hardware bridge-up that
Debian cannot yet perform, then transfers PID 1 and the steady-state runtime to
the immutable SD-backed Debian root with `switch_root`.

`AGENTS.md` and `docs/operations/targets/A90_TARGET_CONTRACT.md` are binding.
This file records current state and the next bounded unit; it grants no device
authority. `GOAL.md` is the separate S22+ objective. Target identities,
artifacts, transports, evidence, recovery, and commands never cross between
the two goals.

The pre-H2 goal history is preserved at
`docs/archive/roadmaps/GOAL_A90_PRE_H2_2026-08-05.md`.

## Current State

- H11 is the exact installed healthy resident at `0.11.179`, build
  `phase3-minimal-h11-direct-debian-boot-auto-benchmark`. On an armed boot it
  keeps the boot splash and serial recovery path, skips the fixed splash wait,
  HUD, QRTR, netservice, early WiFi lifecycle/test, WiFi autoconnect, and boot
  chime, then dispatches the existing one-shot handoff. Any unarmed, latched,
  cache-refused, or failed return restores the full native service path without
  replay.
- The fresh Phase3 network/SSH rootfs, H11 marker namespace, deterministic A/B
  boot, exact compiled binding, and benchmark execution closure are bound by a
  42-path independent review. `PASS_GO` has HIGH/MEDIUM/LOW zero and grants no
  device authority. The final host manifest is private and immutable; its
  candidate and rollback copies are exact.
- Fresh run03 D0 re-proved installed H10 `0.11.178` health, exact H11 candidate
  and V2321 rollback, direct NCM, and absent remote rootfs/work/stage
  destinations. The attended F1 then staged the exact rootfs once, transferred
  and flashed the boot-only H11 candidate once, and closed
  `PASS_A90_RESIDENT_INSTALLED` / `RESIDENT_HEALTHY` with self-test `11/1/0`,
  candidate replay false, rollback zero, source exact, work absent, and the
  global guard released.
- H11's first boot proved the fresh binding and unarmed
  `binding=1 enable=0 latch=0` state while staying on the complete native
  fallback path. Attended D1 run `a90-d1-attended-20260810-03` then armed once,
  rebooted once, visibly reached Debian, completed the direct handoff, and
  automatically returned exact H11 at `binding=1 enable=1 latch=1`. The host
  NCM observer missed its deadline, and the original host parser rejected the
  exact H11-only direct marker before final-health publication. The reviewed
  no-replay tail subsequently validated the exact seven-record prefix and
  appended only final-health and closed records. The nine-record journal is
  terminal and must never be resumed; arm, reboot, cleanup, handoff, and
  candidate replay remain forbidden.
- Exact replay of that immutable opening log and the returned native log proves
  boot-to-dispatch at 2403 ms, boot-to-`switch_root` at 2839 ms, and the
  dispatch-to-`switch_root` handoff at 436 ms. The operator confirmed visible
  Debian. Same-intent durable evidence also records Debian PID1 at 3260 ms and
  DRM master at 4350 ms, but its SSH phase recorded `dropbear=0`; final proof
  must therefore remain separate from the speed and visibility result.
- The H0 incident repair admits `native_direct_handoff_ready` only zero or one
  time at the exact runtime/services boundary, reparses persisted benchmark
  output from its two exact raw logs with type-exact comparison, and opens only
  the exact historical seven-record no-replay tail. Independent review returned
  reusable `PASS_GO` at execution closure
  `21a7a7921d50b71cfff7d4db61c7de57544711d8576a60e9d64ed8913b83677e`
  with HIGH/MEDIUM/LOW zero and 79 combined tests passing. The exact tail
  closed `NO_PROOF_OBSERVER_RESIDENT_HEALTHY`: final H11 health is `11/1/0`
  with pstore empty, exact source and receipt, absent work, cleanup dispatch
  zero, payload/partition/flash zero, and result SHA256
  `82b42da6f9a2dd9f892ec2085f280411054fff675a62f4ecb10d6cea41d82950`.
  The speed and visible-display claim is proved, but H11 did not prove full
  personal-server readiness. H12 `0.11.180` now has host-only independent
  `PASS_GO` for direct Debian boot with Debian-owned NCM/Dropbear/DRM and a
  minimal native Wi-Fi companion in a private mount namespace, shared network
  namespace, redacted read-only export, and durable heartbeat. Deterministic
  run07 rootfs and boot artifacts are exact, but H11 remains installed: H12
  grants no live authority and still needs fresh exact D0 and live binding.
- H10 resident install and D1 run `a90-d1-attended-20260810-02` are terminal.
  The exact no-rearm continuation dispatched one reboot, completed all 15
  handoff stages, returned exact H10 health, and closed
  `CLOSED_EXACT_NO_REPLAY`; neither terminal transaction may be resumed.
- The records-derived comparison proves H8 `handoff_begin` to
  `switch_root_exec` at 43501 ms versus H10 at 990 ms: -42511 ms, 43.94x
  faster, and 97.72% lower elapsed time. H10 loop attach was 57 ms, root mount
  100 ms, writable setup 17 ms, init check 9 ms, and mount moves 1 ms.
- H8 and H10 both retained exact same-intent Debian PID1, Dropbear, DRM, native
  return, and final health evidence, but their host observers required ACM
  before using Debian NCM and reached the same 30-second bridge deadline.
  Their `NO_PROOF_OBSERVER_RESIDENT_HEALTHY` terminals remain unchanged.
- The repaired observer binds the exact same A90 NCM at a new USB epoch before
  SSH without requiring ACM, rechecks that epoch through SSH and service proof,
  then requires a later exact native ACM epoch, version, self-test, guard
  continuity, and final health. Arm and reboot dispatch primitives are
  unchanged and no terminal action was replayed.
- The persisted benchmark loader now re-enters the canonical segment parser
  and rejects duplicate completed handoffs, multiple persisted-result
  locations, type-confused receipts, and stale USB epochs. Independent review
  returned reusable `PASS_GO` at execution closure
  `2cb8f48f17337ead623bdd7caddb6f62bdc554e4c926c722c0c67295fe020e64`
  with HIGH/MEDIUM/LOW zero; 317 main A90 tests and 295 reviewer tests pass.
- H3 remains the earlier automatic-handoff benchmark line. Its
  attended D1 ordinal armed once, rebooted once, displayed Debian, retained all
  15 mandatory benchmark stages, returned automatically, cleaned its work
  copy, and closed exact H3 health without replay. The missed same-ordinal SSH
  observation remains correctly `NO_PROOF_OBSERVER_RESIDENT_HEALTHY`.
- H4 run `a90-v3406-debian-display-f1-20260805-11` staged its exact fresh 2 GiB
  keyed rootfs and transferred boot-only candidate `0.11.172` exactly once.
  The F1 observer then rejected the cumulative native log before it could write
  `candidate-boot-ready`; the candidate was not replayed.
- The same durable run performed one exact V2321 rollback and closed terminal
  `ABORTED_F1_V2_CANDIDATE_UNCERTAIN_ROLLED_BACK`. Exact V2321
  `0.9.285/v2321-usb-clean-identity-rodata`, self-test fail zero, pstore zero,
  the bounded control channel, guard release, and final health all passed.
- The incident is classified `HOST_OBSERVER_CUMULATIVE_UNARMED_LOG_REJECTION`.
  The exact thrown branch and source semantics identify the global
  exactly-one log count as the likely cause, but no candidate log receipt was
  durably recorded, so H4 candidate health is not retroactively claimed.
- The H0 repair accepts one or more cumulative state lines only when every
  `A90AUTO state=` line is exactly `unarmed-stay-native`; missing, malformed,
  armed, dispatch, and mixed states still fail closed. F1 and resident-install
  journal consumers now share that rule. All 240 focused tests pass and
  independent review returned `PASS_GO_NEW_CAMPAIGN_ONLY` with no unresolved
  HIGH or MEDIUM finding and no device authority.
- The exact H4 source remains on SD, while its work and staging paths are
  absent. Post-rollback SD inventory is 61408048 KiB total, 54419468 KiB used,
  and 3862568 KiB available at 93% use. This is below the margin required for
  another fresh 2 GiB source plus 2 GiB work copy.
- The exact V2321 boot rollback remains present and hash-verified. Physical
  Download and TWRP recovery remain demonstrated and available.
- H5 run `a90-v3406-debian-display-f1-20260805-12` published its exact fresh
  2 GiB source and re-proved the source SHA, absent work/stage, absent H5
  enable/latch namespace, and exact V2321 starting health. Its candidate was
  never attempted: the A90 ModemManager guard found the transient global rule
  already owned by a concurrent S22+ F1 corridor and failed closed before
  candidate intent. The run is terminal `ABORTED_F1_V2_BEFORE_CANDIDATE` with
  candidate/rollback counts `0/0` and no replay.
- A post-terminal D0 re-proved exact V2321 `0.9.285`, self-test fail zero,
  pstore zero, and the exact A90 bridge. It observed only the expected run-12
  final source present; work and run stage remained absent. The other-target
  guard later released without A90 intervention.
- H5 run `a90-v3406-debian-display-f1-20260805-13` reused that exact published
  source read-only, staged and copied zero rootfs bytes, and installed boot-only
  candidate `0.11.173` exactly once. The durable result is
  `PASS_A90_RESIDENT_INSTALLED` / `RESIDENT_HEALTHY`, with candidate/rollback
  counts `1/0`, candidate replay false, and the global guard released.
- The post-install read-only D0 proved exact H5 build
  `phase3-minimal-h5-fresh-campaign-auto-benchmark`, self-test `11/1/0`, and
  exclusive unarmed state `binding=1 enable=0 latch=0`. SD capacity remained
  61408048 KiB total, 54419496 KiB used, and 3862540 KiB available at 93% use;
  no second 2 GiB staging copy was created.
- D1 run `a90-d1-attended-20260805-09` bound the exact installed H5 resident,
  immutable run-12 source, absent work, rollback, recovery, and one action. It
  armed once and rebooted once. The immediate host observation failed because
  exact bridge continuity did not validate, so the arm or reboot was not
  resent and Debian PID 1, SSH, and display visibility are not mechanically
  claimed for this ordinal.
- Read-only reconciliation found one new complete 15-stage benchmark segment
  followed by a partial returned-native segment. The exact opening 31-marker
  prefix and 19-marker appended suffix are now parsed independently. The
  selected complete segment records `switch_root_exec`, total handoff
  126444 ms, initial source SHA 37459 ms, post-display source SHA 11410 ms,
  and work copy 76068 ms.
- The same durable ordinal cleaned the fixed work copy exactly once and closed
  `NO_PROOF_OBSERVER_RESIDENT_HEALTHY`. Result payload SHA256 is
  `d1971edf46127cdc78d7cd678a42b5b071e1cbe4a6275300b607da1b05837fa3`.
  Exact H5 returned with `binding=1 enable=1 latch=1`, immutable source exact,
  work absent, guard released, and resident health true. No payload, partition
  write, flash, rollback, or replay occurred.
- H0 diagnosis identified the observer failure before NCM rebind: the runner
  performed exact bridge validation immediately during normal post-reboot
  by-id absence. The repaired observer now waits at most 30 seconds only while
  that exact bound path is absent, then requires the unchanged exact bridge;
  a present mismatch still fails immediately. Independent review returned
  `PASS_GO` with HIGH/MEDIUM zero and 230 related tests pass.
- Pre-reclaim read-only capacity was 61408048 KiB total, 54419524 KiB used, and
  3862512 KiB available at 93% use. No D1 transaction is active and no target
  is A90 F1-armed. Runs 11-13 and D1 run09 are terminal and must never be
  resumed or replayed. No A90 command was sent to S22+, and its files and
  device state remained untouched.
- A fresh read-only reclaim inventory re-proved exact H5 `0.11.173`, selftest
  fail zero, pstore zero, `binding=1 enable=1 latch=1`, exact H4 run-11 and H5
  run-12 2 GiB source identities, absent work/stage, and 3862508 KiB available.
  Its device-write and other-target-command counts are zero. The run01 draft
  manifest was superseded by later inventory-validation closure changes and is
  never live-eligible; the inventory itself passes the final loader.
- The exact one-use attended H4-source reclaim capability now has independent
  `PASS_GO` at execution closure
  `2c6f7b431cb82638638b4f891daa9a56deae27d1cb48621b93cadcab97cf8842`
  with HIGH/MEDIUM zero and 143 related tests passing. It selects only the
  host-preserved H4 run-11 source, protects the installed H5 run-12 source,
  requires final exact H5 health and latched state, and permits one unlink with
  no retransmit, payload, partition write, flash, restore, or S22+ authority.
- Live run `a90-h5-h4-source-reclaim-20260806-02` used that closure once and
  closed `PASS_H4_SOURCE_RECLAIMED_FROM_HEALTHY_H5`. One nonrecursive unlink
  removed only the H4 run-11 device source; the H5 run-12 source remained exact
  and work remained absent. Free space increased exactly 2097152 KiB to
  5959660 KiB available, within the bound 2031620..2162692 KiB. Final H5 health
  and `binding=1 enable=1 latch=1` passed. Dispatch count is one, retransmit is
  false, and payload, partition write, flash, rollback, and S22+ command counts
  are zero. Private result SHA256 is
  `127d5c147452561857502f4ad3f1b5e60ad1ac31e4c0cbe37c216cd6bf5e721e`.
- Historical-image GC run `a90-h5-historical-image-gc-20260806-01` bound a
  fixed set of twenty obsolete rootfs, clean-image, and WSTA snapshot files.
  All twenty exact byte identities have private mode-`0600` host recovery
  copies. The initial host aggregate validator rejected expected
  post-staging manifest enrichment before deletion intent or dispatch; the
  narrow validator repair passed independent incident rereview at closure
  `6046591ba7172eaecaf6c664f08520e0c4f271194038d788cc62a41bcd619401`
  with 70 tests and HIGH/MEDIUM zero.
- The same run then dispatched one nonrecursive unlink and closed
  `PASS_HISTORICAL_IMAGES_AND_SNAPSHOTS_RECLAIMED_H5_HEALTHY`. All twenty
  selected paths are absent, protected H5 run-12 is exact, work/stage are
  absent, and available SD space increased by 40370236 KiB from 5959648 to
  46329884 KiB. Final H5 `0.11.173`, self-test `11/1/0`, pstore zero, and
  `binding=1 enable=1 latch=1` passed. Dispatch count is one, retransmit is
  false, and payload, partition write, flash, rollback, and S22+ command
  counts are zero. Private result SHA256 is
  `2c83dfbdfd362082bed2bfec313c7665afd1621e06714a6da0c168fc91d715ff`.
- H6 host preparation now follows the required rootfs-first order. Run
  `a90-v3406-debian-display-f1-20260807-01` has one fresh private observer-keyed
  2 GiB rootfs with SHA256
  `b242fa73ee926d150ef8b8887734210bc4fd41f71597730647932c578fb1fd64`.
  Its absent remote destination is
  `/mnt/sdext/a90/runtime/debian-bookworm-arm64-phase2-display-v3406-keyed-20260807-01.img`.
- The corrected non-LTO H6 A/B build is byte-identical at boot SHA256
  `5e6774018d7e4601bde766521a78d58d90a7ec5851297d8f5c32bf13b7fa07fa`,
  version `0.11.174`, build
  `phase3-minimal-h6-observer-complete-baseline-auto-benchmark`, compiled
  binding `75c0f131e814ab27a123961c17a8082034425e371c9412284a7b78bc17f42231`,
  and fresh H6 enable/latch namespace. The superseded pre-rootfs H0 draft is
  not selected by any public manifest and has no live authority.
- Independent review returned `PASS_GO` for corrected H6 full thirteen-file
  closure `b9f4ddb19d177506bd2d271b50b1e7c305ebe74d1647d0dacbe3dd711a373c70`
  with HIGH/MEDIUM zero and 367 tests passing. No device, USB, private, or
  S22+ reviewer contact occurred.
- Fresh connected D0 for run `a90-v3406-debian-display-f1-20260807-01` passed
  after an H0-only direct-USB observer-route repair. It re-proved exact H5
  `0.11.173`, self-test `11/1/0`, pstore zero, exact H6 candidate and rollback,
  and absent H6 rootfs/work/stage destinations. D0 and path-preflight receipt
  SHA256 values are `50fcd36ecb6dc7fb421eed7b2a821b7bea9680f64b59f603930b56de3a1d8848`
  and `6493244c0ab1dbc0351750ac1e1bc29b913e3a4eaacab4e3425d798feec12ffd`.
  The failed route check issued no device command; the successful D0 issued
  reads only. S22+ was untouched.
- H6 immutable host preparation and resident-install compatibility binding are
  complete. The resident manifest SHA256 is
  `ef65322de1aa5d45b83a71b134b5cd5ea01aefd5cde706a58d1d20f2323b2091`
  and the approval-binding SHA256 is
  `6f5edde21ac92feb6bade8a67173c6a5b251994bec8d30288a16ba21252aa915`.
  This H0 preparation grants no live authority. No H6 staging, candidate
  transfer, flash, reboot, or D1 action has occurred yet; H5 remains exact and
  terminal.
- The first H6 live transaction consumed that compatibility approval and is
  terminal `ABORTED_F1_V2_BEFORE_CANDIDATE`. An operator invocation supplied
  the Debian NCM endpoint as the host serial-bridge endpoint, so the staging
  child rejected exact bridge continuity before its first device command.
  Candidate and rollback transfer, device write, flash, and reboot counts are
  all zero. No staging bytes reached A90, H5 remains unchanged, and S22+ was
  untouched. The immutable manifest and transaction must never be replayed;
  the unchanged reviewed capability may be rebound to one fresh campaign.
- Run02 generated a fresh keyed rootfs and passed a fresh read-only D0, but its
  host finalizer correctly rejected the new rootfs SHA against the run01-bound
  compiled candidate before publishing a final manifest. It has no live
  authority and must not be reused. Device effects were D0 reads only; no
  staging, transfer, flash, reboot, or S22+ command occurred.
- Run03 now supplies the corrected rootfs-first rebind. Its fresh keyed rootfs
  SHA256 is `feea09dd81fc342032c94629f47d06e743788efc9dc7bba9ca0067f346d4d490`
  at the compiled `20260807-03` destination. The deterministic non-LTO A/B
  candidate is byte-identical at boot SHA256
  `aa7cba7f730e12b08f6498a3307493eed033674d51c968b4ea4d2d3280ea98bb`,
  build receipt SHA256
  `e0e2544770d1538ddc566d41e1a878db687a4da61a1926d994544f657d43cfd3`,
  and compiled binding
  `238a1ae3aa1f4a2a1a8c46d8368fa4e025d0a0be7fb4ed77e7ccd80b410d1483`.
  All 374 focused tests, both host-only audits, static AArch64 inspection, and
  Android boot-image inspection pass. Fresh run03 D0 re-proved exact H5 health,
  the new candidate and rollback, and absent run03 rootfs/work/stage with no
  write, payload, flash, or reboot. Fresh independent review returned
  `PASS_GO` with HIGH/MEDIUM zero for exact named execution-critical closure
  `20314ba25b75a2202b6e814d48275ec6e7c530dbc9c0b0c2e88551d1f42276e3`.
  The reviewer made no implementation edit and contacted no device, USB,
  private artifact, or S22+ endpoint.
- Run03 then staged and verified the fresh 2 GiB source once and installed the
  exact boot-only H6 candidate once. Durable result SHA256
  `784114e680ea91ee029cdad383f09b1b306972870670803d7c1d4592ea9ee45a`
  is `PASS_A90_RESIDENT_INSTALLED` and `RESIDENT_HEALTHY`: H6 `0.11.174`,
  self-test `11/1/0`, exact source, absent work, candidate count one, rollback
  count zero, and replay false. The ModemManager guard released without
  residue. S22+ was untouched. Run03 F1 is terminal and must never replay.
- D1 run `a90-d1-attended-20260807-01` consumed the installed H6 ordinal with
  one arm and one reboot. The exact automatic handoff completed and returned
  H6 at `binding=1 enable=1 latch=1`; one post-return cleanup removed the work
  copy and final resident health passed. Result SHA256
  `921bfa253300d099b8df8e92506592e2fc306e95a90b20e44f674264c990d9a5`
  is terminal `NO_PROOF_OBSERVER_RESIDENT_HEALTHY`, with no replay, payload,
  partition write, flash, or S22+ command. Its complete 15-stage benchmark has
  `handoff_total_ms=127738`: initial source SHA 37841 ms, post-display source
  SHA 11432 ms, and work copy 77627 ms dominate. Debian PID 1, SSH, service
  ownership, and display were not mechanically captured because the repaired
  observer still evaluated bridge continuity while the bound A90 by-id was
  absent; read-only reconciliation and the journal-bound cleanup tail restored
  exact final health without another arm or reboot.
- H0 incident diagnosis proved the observer accepted the still-present
  pre-disconnect ACM epoch and could then accept wrapper metadata whose exact
  bound serial-candidate snapshot was already absent. The repair now requires
  bound-path absence before exact return, rejects malformed candidate metadata,
  retries only an absence snapshot within the existing deadline, and still
  rejects a present mismatch without retry. Independent capability review is
  `PASS_GO` with HIGH/MEDIUM/LOW zero, 273 proportional tests plus 9 adversarial
  cases passing, runtime closure
  `406028e6c9cef5ba381ddcae4c204c5ccf2fa728cb10f99d68174c59f6a72c04`,
  and full public closure
  `938b24b04cf33ec5265906e7e443b04611807ea3260d92c9ef219c51aaa7ca6e`.
  Arm, reboot, execute, reconcile, dispatch, retry, and replay behavior is
  unchanged; the reviewer contacted no device, USB, private artifact, or S22+.
- The H6 timing diagnosis separates publication from handoff cost. D1 sent no
  rootfs payload, but native handoff currently performs an initial source hash,
  a post-display source hash, a full source-to-work copy, a work hash, and a
  post-copy source hash. These three measured groups consumed 126900 of 127738
  ms (99.34%), representing about 10 GiB of logical reads and 2 GiB of writes
  for one 2 GiB image. Full-LTO cannot materially remove this storage cost.
- H7 host qualification now removes that fixed work-copy lane without claiming
  a device result. Native-init opens the exact source once with `O_NOFOLLOW`,
  hashes the same FD before and after bounded display cleanup, attaches that FD
  read-only to loop0, revalidates backing device/inode, mounts only the fixed
  `/run`, `/tmp`, `/etc/dropbear`, and `/var/log` writable tmpfs set, and binds
  only the private shared evidence directory into Debian. No 2 GiB work copy or
  copy hash remains in the handoff corridor.
- H7 also closes the recurring observer race at the correct boundary. Debian
  durably records same-ordinal PID 1, Dropbear listen, and DRM/display-ready
  facts; native-init replays the latest complete records after return; the host
  runner grades the raw log against the exact durable intent. Exact USB bridge
  re-enumeration and NCM binding remain host-observed PASS gates, while live
  SSH/service/candidate-return observations are corroboration only.
- Final independent review is `PASS_GO` with HIGH/MEDIUM zero. The native
  252-member closure is
  `f17aac71d21701a9e7a4db62f825029fd73aea7f281759061ec47d8ef8a37a03`,
  the host benchmark execution closure is
  `c040331e0a67c1be1876d4a18a630378786cdb0f722ec5b1de1e66350c0fed70`,
  and the H7 manifest SHA256 is
  `12b0f4e818e4de2c2f83e2f4d4d42466d3924f0124082c812eb65f68d7acca65`.
  Related 278-test independent validation, 270-test main validation, 40 D1
  transition tests, H7 audit, and the full AArch64 static build pass. The
  no-authority boot SHA256 is
  `9edcbf8821c5fb5069576ca403ed04e873e9dfcf79dedb59e2d976d6981af4a2`.
  This was H0 only: no A90 or S22+ command, D0, D1, F1, payload, flash, reboot,
  or live authority occurred.
- The H7 F1 integration now binds the original host-preserved run05 rootfs,
  a fresh byte-identical A/B rebuild at the same boot SHA256 `9edcbf88...`,
  build receipt `5786bc0a...`, and compiled binding `12fd4ad7...`. Adding the
  exact H7 identity to the F1 orchestrator changed the benchmark execution
  closure, so the earlier `c040331e...` receipt is not reused. Fresh independent
  review is `PASS_GO` at Phase3 closure `15d2012f...` and benchmark closure
  `5cc93e91...`, with HIGH/MEDIUM zero and no new hazard or incident.
- Fresh run05 connected D0 re-proved exact installed H6 `0.11.174`, self-test
  `11/1/0`, exact V2321 rollback, direct A90 NCM reachability, and absent H7
  source/work/stage paths. D0 and path-preflight SHA256 values are
  `3ca9d90cc5ed092eb8fe9e5ca200b78e39643aab6ae5328ef58e485ad07abd55`
  and `9186cbf7b75f3f011de6b866c522945e7a0c3d02826460053c84d55254ac9553`.
  Device write, payload, flash, reboot, and S22+ command counts are zero. The
  next gate is immutable H7 host-manifest publication; review and D0 grant no
  live authority.
- Run `a90-v3406-debian-display-f1-20260807-05` then staged the exact original
  2 GiB H7 source once and transferred boot-only candidate `0.11.175` exactly
  once. Durable result SHA256
  `a999966b424705985efe4b1a34edaf2e12efecc21b919832e61b895ba64e8990`
  is `PASS_A90_RESIDENT_INSTALLED` / `RESIDENT_HEALTHY`: self-test `11/1/0`,
  pstore zero, exact source, absent work, candidate count one, rollback count
  zero, resident reboot zero, and replay false. The ModemManager guard released
  with no rule residue. S22+ received no command. This F1 is terminal and must
  never replay; H7 is now the installed resident.
- Attended D1 run `a90-d1-attended-20260809-01` armed H7 once and rebooted
  once. Automatic handoff reached the read-only root mount, writable tmpfs set,
  Debian init verification, and display marker, then returned native with
  `E19` before `mount_moves_done` or `switch_root_exec`. The exact cause is
  `ENODEV`: native `/dev` was not a mountpoint, and H7 deliberately refused to
  create the fallback `/dev` in the immutable rootfs. Debian PID 1, SSH, and
  DRM/display ownership are therefore not claimed.
- Read-only reconciliation and the exact historical seven-record tail closed
  the same ordinal without another arm, reboot, handoff, or cleanup dispatch.
  Result SHA256
  `098b0a50ea1f9cdb210d92fc9faf8a797b33eca27d172e7529adf2fd73805ea1`
  is `REFUTED_AUTO_HANDOFF_NATIVE_HANDOFF_RESIDENT_HEALTHY`: exact H7
  `0.11.175`, self-test `11/1/0`, `binding=1 enable=1 latch=1`, immutable
  source exact, work absent, replay false, and payload, partition write, flash,
  and rollback zero. S22+ received no command.
- The E19 repair mounts private `tmpfs` on the existing new-root `/dev` before
  bounded node creation, never writes the immutable image, and tracks devpts
  and `/dev` cleanup through failure and returned `execve`. The final host
  parser evaluates every appended segment and rejects complete/failed mixtures
  in either order. Independent review returned `PASS_GO` with HIGH/MEDIUM/LOW
  zero, 267 A90 tests, full AArch64 static inspection, native closure
  `0682012c0ef3607e33e3382eb45903828493d33a3033f30b2c22278cfd47d8a2`,
  and benchmark closure
  `23bdeb0f7c82aa5abb3d68d2d1856e01ebe306adc0d21993a06b74f54b601a0e`.
  The old H7 manifest still binds the refusing implementation; deployment of
  this C repair requires a new candidate identity and state namespace.
- H8 `0.11.176` is the exact installed resident and remains healthy after its
  terminal D1 ordinal. That ordinal completed all 15 handoff stages in 43501
  ms and produced durable same-intent Debian PID 1, Dropbear, DRM-master, and
  display-ready evidence before automatic native return. Its latch is consumed
  and the ordinal must never be replayed.
- H9 `0.11.177` introduced the fast source-integrity receipt. A missing or
  changed receipt requires one full source SHA before arm; routine boot verifies
  the durable receipt and exact source metadata, and the post-display phase
  revalidates the same open source identity and loop backing without another
  2 GiB hash. Legacy profiles retain their two full SHA passes.
- Independent H9 review initially found three host regressions: legacy H2-H8
  proof rejection, an unqualified generic H9 D1 route, and hybrid benchmark
  acceptance. All three were repaired. A later main-agent precedence check
  invalidated the first rereview because its same-path design violated the A90
  replacement-candidate rule. The next review found the receipt path missing
  from the operational binding; after that repair, adversarial rereview found
  mixed contradictory pre-transfer state output could pass a substring check.
  Both are repaired. A later `PASS_GO` at manifest `8054fb53...` became
  non-reusable when the first live-path D0 invocation stopped host-side before
  device contact: standard per-run observer keying produced rootfs SHA
  `dc35040a...`, not the H8-derived `e2028b02...` that candidate had compiled.
  Rebinding that rootfs under the same H9 version/build and state namespace was
  independently rejected `NO_GO` because replacement identity would be
  ambiguous. H9 remains unchanged and archived; no D0 read or device effect was
  consumed.
- H10 `0.11.178` is the fresh successor for the standard per-run observer-keyed
  rootfs. It has a new build identity, fresh `20260809-03` destination, and new
  enable/latch/receipt namespace. Its deterministic A/B boot remains
  byte-identical at SHA256 `145ab5d0...`; rootfs is `38d9ce41...`, manifest is
  `57ffe40e...`, effective manifest is `81da1c2f...`, build receipt is
  `a8323448...`, compiled binding is `decc6995...`, native closure is
  `3359e10f...`, Phase3 public closure is `226f914e...`, and benchmark closure
  is `194bbb07...`. Host audits and 371 focused integration tests pass. Fresh
  clean public-host-only independent review returned `PASS_GO` with
  HIGH/MEDIUM/LOW zero and 126 reviewer tests. Reviewer private, device, USB,
  network, and S22+ contact was zero. H10 has no live authority and no A90 or
  S22+ command was sent.
- Fresh run03 connected D0 then re-proved exact H8 `0.11.176`, self-test fail
  zero, pstore zero, direct A90 USB-NCM, exact H10 candidate and V2321 rollback,
  and absent H10 final/work/stage paths. The standard resident-install manifest
  and compatibility binding were prepared from committed H10 closure with no
  live authority. Device write, payload, flash, reboot, and S22+ command counts
  remained zero.
- The first run03 F1 transaction published and verified the exact 2 GiB H10
  source once, then stopped terminally before candidate intent because the
  host ModemManager guard's `pkexec` process did not arm. Its raw receipt is
  empty with no return code, candidate and rollback transfer counts are zero,
  candidate replay is false, and no guard residue remains. The transaction is
  `ABORTED_F1_V2_BEFORE_CANDIDATE`, must never resume, and H8 remains installed
  and healthy. S22+ was untouched.
- The incident successor reuses only that exact published H10 source in a fresh
  campaign. It performs no rootfs staging, copy, unlink, mount, or handoff;
  binds H8 starting health, absent work/new-stage/enable/latch/receipt, one
  boot-only H10 candidate, exact V2321 rollback, attendance, guard, no replay,
  and final `RESIDENT_HEALTHY`. Independent rereview first rejected substring
  receipt validation and mutable profile poisoning; both were repaired.
  Final `PASS_GO` has HIGH/MEDIUM/LOW zero at closure `cb54905e...`, runner
  `47f55ebd...`, and resident promotion `1fae5f20...`; 334 main and 23 reviewer
  public/mocked tests pass. Reviewer edits and device, USB, private, network,
  and S22+ contacts are zero.
- Fresh run `a90-v3406-debian-display-f1-20260810-01` passed exact D0 from
  installed H8, then consumed the unchanged no-stage capability while attended.
  It transferred and flashed the exact boot-only H10 candidate once, booted
  H10 `0.11.178`, and closed `PASS_A90_RESIDENT_INSTALLED` /
  `RESIDENT_HEALTHY`. Self-test is `11/1/0`, pstore is empty, the published
  source and inode/use guards are exact before and after candidate, and rootfs
  staging/copy/cleanup counts remain zero. Candidate replay is false, rollback
  count is zero, the guard released without residue, result SHA256 is
  `c2c603b986425d0691572de8b8a8a4a05a42957a9f61cef9fb683ca01c210e2b`,
  and S22+ was untouched. This F1 transaction is terminal and must never replay.
- The successor D1 adapter is now H10 receipt-aware. Its opening D0 proves the
  exact unarmed resident, source metadata, absent work, and absent receipt;
  native arm alone performs one full SHA and must publish the exact fresh
  qualification sequence. Later checks use the same source metadata and exact
  14-line receipt without another full SHA. Unexpected work is never removed,
  and the absence close has cleanup dispatch count zero. Two review-found
  blockers, native receipt nanosecond formatting and the 4096-byte cmdv1x
  decoder bound, are closed. Final independent `PASS_GO` binds code-native
  closure `85dc1812...`, the manifest-validated 17-file public closure, and the
  exact installed H10 artifact identity with 270 reviewer tests and no open
  finding. The first live opening attempt stopped before journal publication
  because its parser rejected the normal eight-line serial wrapper around one
  exact successful marker. It created only an empty host transaction directory:
  no arm intent, arm, reboot, or device effect occurred. The repaired parser
  accepts the normal wrapper but rejects every malformed same-tag line, and a
  fresh read-only D0 passed exact H10 health, the 11-field source identity,
  receipt/work absence, `enable=0/latch=0`, and the exclusively unarmed log.
- Fresh attended run `a90-d1-attended-20260810-02` opened against that closure
  and dispatched arm exactly once. Native returned the exact fresh one-full-SHA
  qualification and armed receipt, and read-only reconciliation proves H10 is
  healthy at `enable=1/latch=0`; however, the arm parser repeated the normal
  serial-wrapper assumption and stopped before reboot intent. The durable
  prefix is exactly `0000` through `0002`: arm count one, reboot count zero,
  replay false. Never restart this ordinal or resend arm.
- The exact run02 incident successor has independent `PASS_GO` for predecessor
  closure `85dc1812...` and successor closure `1562ffe1...` with 279 tests and
  no open finding. It permits only an attended continuation from that exact
  three-record prefix, binds successor code in `0003`, rechecks exact armed
  state and guard health at both reboot boundaries, sends at most one reboot,
  and preserves historical read-only reconcile plus no-replay tail recovery.
- That exact successor is now consumed and terminal. It wrote reboot intent
  once, rebooted once, completed all 15 handoff stages, and returned H10 at
  `enable=1/latch=1`. The measured native handoff from `handoff_begin` through
  `switch_root_exec` was 990 ms: loop attach 57 ms, root mount 100 ms, writable
  set 17 ms, distro-init check 9 ms, and mount moves 1 ms. Same-intent durable
  evidence proves Debian PID1 at 6660 ms uptime, SSH at 8750 ms, and DRM master
  at 8780 ms; PID1-to-SSH was 2090 ms. Final H10 health, exact source/receipt,
  absent work, zero cleanup dispatch, and guard release all passed. The terminal
  is `NO_PROOF_OBSERVER_RESIDENT_HEALTHY`, not full PASS, because the live host
  observer did not prove its path and visible confirmation was unavailable;
  mechanical on-device proof is true and device health is unambiguous. Result
  SHA256 is `547ff237852a7b16a24cd1c7646a389285d50cf50034a8055b588e7043bc1368`.
  Arm and reboot counts are one each, replay is false, and this ordinal must
  never resume or replay.

## Qualified Capabilities

- The H10 one-ordinal receipt-aware auto-handoff D1 v3 capability has reusable
  predecessor evidence at closure `85dc1812...`; its live parser incident ends
  direct reuse. The separately reviewed exact run02 no-replay successor at
  closure `1562ffe1...` consumed only the already armed three-record journal and
  is now terminal. It cannot arm a new ordinal or resume this one.

- The H3 exact compiled-rootfs binding and resident F1 closure has reusable
  independent `PASS_GO` for its named execution-critical hashes and E2 hazard.
- The current auto-benchmark observer/tail closure
  `60610b2deae343892506c0e13ef88e96c6993b5121fa1c88632410db208afd89`
  has independent `PASS_GO`. It binds exact NCM-before-SSH, all 15 mandatory
  handoff stages, a hash-bound opening-marker prefix plus appended suffix, and
  a bounded absence-only wait for the manifest-bound by-id endpoint before
  exact bridge, NCM, and SSH observation. A present mismatch is never retried.
- Historical closure
  `94be39687a91938d4f82d52242ce0025b3b19e4f8c8bbfd6cf46ff729dd3a5f4`
  remains the exact reviewed closure that finalized run09 from its already
  durable seven-record journal tail with no arm, reboot, handoff, or cleanup
  replay. It is retired from future live use by the post-reboot bridge-absence
  incident. The still earlier
  `e17d9e23e3f473d949cf264b54246ac01ec221fe133e0291a200437a0ed13959`
  receipt is superseded by the accumulated-log observer incident.
- The pre-incident H4 replacement closure had independent `PASS_GO` for boot SHA
  `6bc133937f19482739037b67a44b1f2b5da6da9a178a3edf8a9f2e74bd097935`,
  fresh keyed-rootfs SHA
  `8b4bfd99a9324c0a32e76c837e33282afa79739fa32645e3303861e8928a33fa`,
  compiled binding
  `783a528a541e3a8edf82543d7352ed2e47f5d3393245d413ee8507df6e797e09`,
  and benchmark execution closure
  `d521a3f1c663ff65791ba804ad84469592c3825233d5bcfd227dfdc5984a642d`.
  The new incident and changed F1 observer retire that receipt for live reuse;
  the repaired production observer closure
  `5120fea1eb29975cb92216d07627f68ced883c1560a4e6dce807f8839c5e8634`
  is qualified `PASS_GO_NEW_CAMPAIGN_ONLY`. A fresh candidate, qualification,
  exact binding and D0, attendance, recovery, and live campaign remain required.
- Earlier minimal-G attended evidence remains the same-ordinal proof of Debian
  PID 1, key-only SSH, Debian service ownership, direct DRM, operator-visible
  output, automatic native return, cleanup, and resident health.
- `PASS_GO` qualifies a capability, not a run. It is reused across manifests,
  campaigns, qualifications, and ordinals only while the named
  execution-critical closure and hazard assumptions remain unchanged and no
  new hazard or incident occurs.
- Fresh exact target, rollback, recovery, presence, D0, immutable manifest,
  runner binding, and inter-effect health remain live requirements. A review
  receipt alone never dispatches a device action.
- The earlier H9 receipt `PASS_GO` at manifest `8054fb53...`, native closure
  `3359e10f...`, compiled binding `02f441da...`, and benchmark closure
  `4a49b236...` is superseded for live use by the per-run keyed-rootfs binding
  requirement. The attempted same-H9-identity rebind at `aad3ed6d...` /
  `e5bb6528...` was rejected `NO_GO` and is never live-eligible. H10 at manifest
  `57ffe40e...`, native closure `3359e10f...`, Phase3 closure `226f914e...`,
  compiled binding `decc6995...`, and benchmark closure `194bbb07...` had
  independent `PASS_GO`; the subsequent guard-arm incident and changed
  resident validator retire that receipt from live reuse. The fresh no-stage
  successor has independent `PASS_GO` at closure `cb54905e...` and may be
  reused only while that exact closure and its hazard assumptions remain
  unchanged and no new incident occurs. It grants no live authority; fresh
  exact D0, immutable binding, attendance, rollback, recovery, no-replay, and
  final health remain required.
- The H5/H4 source-reclaim closure
  `2c6f7b431cb82638638b4f891daa9a56deae27d1cb48621b93cadcab97cf8842`
  has independent `PASS_GO` evidence for hazard
  `SD_CAPACITY_EXHAUSTION_BLOCKING_FRESH_SOURCE_AND_WORK_COPY`. The receipt
  qualified reuse only until first PASS, expiry, closure/hazard change, or a
  new incident. The exact run02 first PASS consumed and retired it; it must
  never dispatch again.
- The historical-image GC closure
  `6046591ba7172eaecaf6c664f08520e0c4f271194038d788cc62a41bcd619401`
  has independent incident-rereview `PASS_GO` for the fixed twenty-file set,
  exact host recovery bytes, protected H5, target-bound health, final use
  guards, and one nonrecursive unlink. Run01's durable dispatch consumed and
  retired the capability; it must never unlink or dispatch again. Its private
  recovery bytes remain evidence and grant no automatic restore authority.
- The corrected H6 observer-complete non-LTO baseline closure
  `b9f4ddb19d177506bd2d271b50b1e7c305ebe74d1647d0dacbe3dd711a373c70`
  had independent `PASS_GO` for the run03 install. It binds the fresh
  run-specific keyed rootfs, deterministic boot, compiled H6 markers, resident
  F1 interpretation, H6 D1 identity, and the then-reviewed post-reboot
  observer. The terminal D1 incident changed that observer hazard assumption,
  so this receipt no longer authorizes another ordinal.
- The repaired H6 observer capability has fresh independent `PASS_GO` at
  runtime closure
  `406028e6c9cef5ba381ddcae4c204c5ccf2fa728cb10f99d68174c59f6a72c04`
  and reviewed full public closure
  `938b24b04cf33ec5265906e7e443b04611807ea3260d92c9ef219c51aaa7ca6e`.
  Reuse lasts only while those closures and hazard assumptions remain unchanged;
  it grants no live authority and never permits replay of H6 D1 run01.
- The H7 read-only-source and durable same-ordinal-evidence capability has
  independent `PASS_GO` at native closure
  `f17aac71d21701a9e7a4db62f825029fd73aea7f281759061ec47d8ef8a37a03`
  and benchmark execution closure
  `5cc93e91103a7aad4fa11af71d56570960e132e21259deeba695e466447ff8d3`,
  with its exact F1 integration bound by Phase3 closure
  `15d2012f2fad35bc794b33cc88a762c82c827ec28d50f8002a5dc258dae2dd9d`.
  The prior benchmark closure `c040331e...` is superseded because the F1
  orchestrator hash changed.
  It is reusable across manifests, campaigns, qualifications, and ordinals
  only while those named closures and the reviewed hazards remain unchanged
  and no new hazard or incident occurs. It grants no device or live authority;
  fresh target, rollback, recovery, presence, D0, runner binding, and
  inter-effect health remain required.
- The H7 D1 E19 incident changes that capability's native mountpoint hazard
  assumption, so its prior receipt is not reusable for another handoff
  ordinal. The exact failed-handoff finalizer and read-only-root `/dev` tmpfs
  repair have new independent `PASS_GO` at native closure
  `0682012c0ef3607e33e3382eb45903828493d33a3033f30b2c22278cfd47d8a2`
  and benchmark closure
  `23bdeb0f7c82aa5abb3d68d2d1856e01ebe306adc0d21993a06b74f54b601a0e`.
  This qualification permits neither H7 replay nor rebuilding the changed C
  under H7 identity. A replacement requires a fresh version/build, rootfs
  destination, enable/latch namespace, manifest, qualification, exact D0, and
  attended boot-only installation.
- H8 now supplies that replacement identity at version `0.11.176` and build
  `phase3-minimal-h8-dev-tmpfs-handoff-repair-auto-benchmark`. Its deterministic
  non-LTO A/B boot SHA256 is
  `cfffb68a4d47f8ae1a76cee7faef8085e1681f1c53155cd6d03d7d87c15f7409`,
  compiled binding is `4221d365...`, native closure remains the reviewed
  `0682012c...`, and the H8 F1/D1 execution closure has independent `PASS_GO`
  at `1a23d1f0...` with benchmark closure `c2a8f666...`. Fresh exact connected
  D0 proves installed H7 healthy, exact H8 candidate and V2321 rollback, and
  the H8 final/work/stage paths absent. An immutable committed-closure resident
  manifest and compatibility binding then selected one attended boot-only
  attempt. The exact 2 GiB source was staged once and H8 installed with one
  candidate transfer, no replay, no rollback, and durable `RESIDENT_HEALTHY`;
  the guard released without residue. The first H8 D1 ordinal has consumed one
  arm and one reboot and returned exact H8 healthy at `binding=1 enable=1
  latch=1`. Its durable current window proves all 15 handoff stages including
  `mount_moves_done` and `switch_root_exec`, plus same-intent Debian PID 1,
  Dropbear, and DRM master evidence. The host observer timed out before the
  later ACM return, and its final parser then rejected a valid bounded pmsg
  window replacement. The independently reviewed historical-closure tail has
  now appended only final-health and close. Result `8a677580...` records a
  complete 43501 ms handoff, all three same-intent on-device evidence phases,
  automatic native return, exact source, absent work, final H8 health, one arm,
  one reboot, and no replay. Its terminal remains
  `NO_PROOF_OBSERVER_RESIDENT_HEALTHY` because the 30-second host bridge wait
  missed the later return; neither durable mechanical evidence nor final
  health is reinterpreted as host-link proof. H8 is consumed and must not be
  replayed. A repeatable baseline requires a fresh successor identity after
  repairing the host observation order/budget.

## Proven Product Path

Earlier minimal-G attended evidence already proves the product mechanism:

```text
native-init strict display and service release
-> immutable SD work-copy verification
-> switch_root
-> Debian sysvinit as PID 1
-> key-only Dropbear SSH and Debian service ownership
-> direct DRM master and visible display output
-> bounded automatic native return
-> exact work cleanup and resident health
```

The H3 line adds two things without changing that product path:

1. a durable two-phase automatic-handoff enable/latch; and
2. bounded boot/handoff telemetry for before-and-after optimization comparison.

H3 now proves first-boot non-dispatch, one armed automatic switch-root stage
sequence, operator-visible Debian output, retained latch, automatic native
return, cleanup, final health, and benchmark telemetry. It does not claim the
missing same-ordinal mechanical Debian PID1/SSH evidence.

## Selected Bounded Unit: Fresh Non-LTO Control with NCM-First Observation

Preserve H7, H8, and H10 F1/D1 runs, consumed namespaces, journals, private
evidence, and no-replay conclusions. H10 is the exact installed healthy
resident. Never resume its terminal F1 or D1 transaction, reset or reuse an old
latch, or reinterpret missing historical host-link proof as a failed device
handoff.

The next bounded work is host preparation for one fresh replacement identity
and fresh rootfs destination that keeps the same non-LTO source-integrity
optimization. After its immutable closure and fresh binding are ready, one
attended control cycle may exercise the reviewed NCM-first observer. It must
prove exact Debian NCM continuity through SSH and service, same-intent PID1 and
DRM evidence, later native ACM return, cleanup, and final resident health.

Only after that fresh control produces full host-link proof and a comparable
benchmark may Full-LTO become the following bounded candidate. Receipt
qualification does not replace fresh D0, rollback, recovery, attendance,
immutable manifest, one-shot journals, no-replay, or final-health gates.

## Optimization Order

Do not start Full-LTO or other compiler optimization from an unmeasured state.
The order is:

```text
on-device same-ordinal evidence
-> fresh automatic-handoff correctness
-> repeatable baseline benchmark
-> workload and thermal/power interpretation
-> one bounded build optimization such as Full-LTO
-> same benchmark and correctness closure
-> compare without weakening recovery or no-replay behavior
```

Boot timing, phase duration, temperature, CPU/GPU clocks, memory, storage I/O,
and available power signals are diagnostic covariates. They do not replace the
atomic PID1, SSH, display, return, cleanup, and final-health result.

## Final Architecture

```text
vendor boot chain and source-matched kernel
-> minimal native-init hardware bridge-up
-> immutable SD work-root verification
-> strict native display and service release
-> switch_root
-> Debian init as PID 1
-> Debian-owned services, networking, display, storage, and applications
```

Native-init remains the early hardware-enablement, bounded recovery, and
diagnostic bridge. A function moves to Debian only after a Debian-side consumer
proves equivalent ownership and the rollback/recovery contract remains intact.

## Evidence

- `docs/archive/reports/A90_PHASE3_MINIMAL_H2_TWO_PHASE_AUTO_BENCHMARK_INDEPENDENT_REREVIEW_2026-08-05.json`
- `docs/archive/reports/A90_PHASE3_MINIMAL_H2_LIVE_F1_D1_INTEGRATION_FINAL_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_PHASE3_MINIMAL_H2_POST_INCIDENT_FINAL_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_PHASE3_MINIMAL_H2_BRIDGE_STOP_FOCUSED_FRESH_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_PHASE3_MINIMAL_H2_HISTORICAL_ACM_EPOCH_FOCUSED_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_PHASE3_MINIMAL_H3_EXACT_BINDING_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_H3_AUTO_BENCHMARK_OBSERVER_TAIL_REPAIR_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_PHASE3_MINIMAL_H4_OBSERVER_COMPLETE_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_H4_CUMULATIVE_UNARMED_LOG_OBSERVER_INCIDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_V2321_H3_SOURCE_RECLAIM_CAPABILITY_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_PHASE3_MINIMAL_H5_FRESH_CAMPAIGN_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_PHASE3_MINIMAL_H6_OBSERVER_COMPLETE_BASELINE_INDEPENDENT_REVIEW_2026-08-07.json`
- `docs/reports/A90_PHASE3_MINIMAL_H6_RUN03_REBIND_INDEPENDENT_REVIEW_2026-08-07.json`
- `docs/reports/A90_H6_D1_POST_REBOOT_BOUND_BRIDGE_OBSERVER_INCIDENT_REVIEW_2026-08-07.json`
- `docs/reports/A90_PHASE3_MINIMAL_H7_READONLY_SOURCE_ONDEVICE_EVIDENCE_INDEPENDENT_REVIEW_2026-08-08.json`
- `docs/reports/A90_PHASE3_MINIMAL_H8_E19_REPAIR_INDEPENDENT_REVIEW_2026-08-09.json`
- `docs/reports/A90_H8_PMSG_WINDOW_REPLACEMENT_TAIL_REPAIR_INDEPENDENT_REVIEW_2026-08-09.json`
- `docs/archive/reports/A90_PHASE3_MINIMAL_H9_FAST_SOURCE_RECEIPT_INDEPENDENT_REVIEW_2026-08-09.json`
- `docs/archive/reports/A90_PHASE3_MINIMAL_H10_FAST_SOURCE_RECEIPT_INDEPENDENT_REVIEW_2026-08-09.json`
- `docs/reports/A90_H10_EXISTING_PUBLISHED_SOURCE_INSTALL_INDEPENDENT_REVIEW_2026-08-09.json`
- `docs/archive/reports/A90_H10_RECEIPT_AWARE_D1_ADAPTER_INDEPENDENT_REVIEW_2026-08-10.json`
- `docs/reports/A90_H10_RUN02_PROVED_ARM_NO_REPLAY_RESUME_INDEPENDENT_REVIEW_2026-08-10.json`
- `docs/reports/A90_H10_NCM_FIRST_OBSERVER_AND_BENCHMARK_RECEIPT_INDEPENDENT_REVIEW_2026-08-10.json`
- `docs/reports/A90_PHASE3_MINIMAL_H11_DIRECT_DEBIAN_BOOT_INDEPENDENT_REVIEW_2026-08-10.json`
- `docs/reports/A90_H5_H4_SOURCE_RECLAIM_CAPABILITY_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_H5_HISTORICAL_IMAGE_GC_CAPABILITY_INDEPENDENT_REVIEW_2026-08-06.json`
- `docs/operations/CAMPAIGN_LEDGER_A90.md`

Private manifests, journals, raw logs, rootfs and boot artifacts, rollback
bytes, target identifiers, and run results remain under `workspace/private/`.
They are never committed.

## Process

For each bounded unit:

`STATE -> SELECT -> DESIGN -> IMPLEMENT -> STATIC VALIDATE -> DEVICE -> REPORT -> COMMIT`

Omit `DEVICE` for H0. Preserve immutable inputs after intent, use one durable
intent per effect, never repeat a proven or uncertain transition because an
observer or report failed, and keep A90 and S22+ completely isolated.

## Success Conditions

The A90 goal is complete only when:

- Debian becomes PID 1 through reproducible automatic `switch_root`;
- Debian owns intended steady-state SSH, networking, display, storage, and
  applications;
- automatic return and recovery remain bounded and reliable;
- native-init retains only named hardware-enablement and recovery functions;
- repeatable benchmark evidence supports later optimization decisions; and
- repeated boots and failure injection support personal-server use without
  broadening boot-only partition authority.

## Stop Conditions

- A permanent boundary in `AGENTS.md` would need to change.
- A90 target, rollback, recovery, resident, rootfs, or health identity is
  ambiguous.
- Work would replay an uncertain arm, reboot, handoff, transfer, or candidate.
- The device is not exact `HEALTHY` before a new effect.
- A non-boot partition write, recovery mutation, or forbidden raw primitive
  would be required.
- S22+ tooling, evidence, identity, approval, or command would be treated as
  A90 proof.
