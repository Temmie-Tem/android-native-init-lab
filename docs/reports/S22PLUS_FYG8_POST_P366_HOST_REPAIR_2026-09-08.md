# S22+ post-P366 host recovery and arrival evidence repair

Scope: H0 only. Repair the actual Samsung Download-arrival producer/consumer
join and resumed ADB capture allocation. Review cross-device final absence
without changing its semantics. P366 remains consumed; its journal, raw
receipts, prepared binding and reporting disposition are not rewritten.

## Changes

`SamsungOdinBackend.wait_download` now retains native-return acquisition-local
raw topology, then performs the existing strict Odin ticket revalidation and
publishes a native Download-arrival record. That record binds the run, exact
endpoint, sequence, current topology/controller/device path and original plus
revalidation snapshot identities. Its receipt is returned with the endpoint
and used by the return-window consumer. The consumer reopens the real nested
Odin receipts through the production parser and checks that acquisition time
belongs to the original sealed CONTROL interval and host boot.

This fixes the P366 path that demanded a P318 rollback phase record although
its actual backend never emitted that phase. It does not enable the legacy
P318 phase lifecycle for native-return runs. A later recovery acquisition gets
its own sequence record; it requires no fabricated Download-start history or
byte-identical global inventory from an earlier USB generation. Partial raw
inventory and failed ticket revalidation cannot qualify arrival. Existing
strict target selection, generation checks, transfer authority and no-replay
rules remain in place. Historical legacy receipt reading remains available;
no consumed result is retroactively upgraded.

`AdbReadOnlyClient.bind_raw_capture_dir` now resumes above the highest allocated
numeric prefix in both `raw-adb/` and the run root, where observer receipts are
written. Complete receipts and partial outputs both reserve their numbers.
Rebinding the same client never rewinds its in-memory allocation. Existing
exclusive file creation and fixed observer-output no-clobber checks remain.
This prevents the P366 resumed client's counter from starting at zero and
colliding later with retained evidence. It is not permission to repeat a
previous observer acquisition or overwrite a fixed output.

## Final absence scope decision

The existing final path has two global checks: Odin absence in `verify_final`
and Download count in `_wait_final_health`. Their result field currently means
global absence. Filtering another device only at the first check would neither
finish validation nor preserve that meaning. Both checks remain unchanged.

A future separate reviewed change could define exact-target absence after
durable rollback completion, record foreign endpoints explicitly and retain
global uniqueness before any transfer. That is not required to report a
completed rollback and observed Android return. It is not implemented here.

## Validation and independent review

The new integration tests run the actual Samsung backend, temporary sysfs
reader, topology parser/publisher, Odin wait/revalidate/persist/receipt reader
and native return-window consumer. Only platform enumeration and immutable
node identity are simulated; no P318 phase file or Odin receipt is fabricated
by the test. Review caught and corrected an initial flat-path fixture mismatch
before qualification: actual Odin receipts live under `receipts/`.

Seven arrival tests cover the real producer/consumer join, recovery after a
recorded departure and fresh generation, incomplete/ambiguous topology, failed
revalidation, changed raw receipts and a coherently forged identity projection.
Two resumed-client tests cover complete/partial retained files, root-level
observer ordinals, no-clobber preservation, monotonic allocation and different
run rejection. All nine pass. The final combined batch passes 133 tests, including D0,
generic F1, P318 integration, P363 return and P366 lifecycle regressions.
All four changed Python files pass `py_compile`. Independent review returned
`PASS_GO` for the four frozen source/test hashes; its private receipt SHA-256
is `70534b92054c5fbff70ed978d465814a31e7cbc54e92072d519f6757d5a2443f`.
This qualifies the host capability only.

Private test logs and independent reviews are under
`workspace/private/outputs/s22plus_fyg8_p366/`, including
`host-repair-final-tests.log`, `host-repair-independent-review.json` and
`final-download-absence-scope-review.json`.

Execution source SHA-256:

- `device_action_d0_v2.py`: `3537ad22bd11db20ff42f4672690a4a51a4b29f00d9c830b73e17a985e4bdaa7`
- `device_action_f1_live_v2.py`: `d13ddbaa5e19fba39813aae461c319525d145bed2678c9e1f6b2a6604f6fbbb6`

No connected D0/D1/F1, image build, candidate preparation or device replay was
performed. Existing consumed source closures keep their original hashes; a
future candidate needs fresh qualification and its own current authority.
A90 and S20+ received no command or source change from this unit.
