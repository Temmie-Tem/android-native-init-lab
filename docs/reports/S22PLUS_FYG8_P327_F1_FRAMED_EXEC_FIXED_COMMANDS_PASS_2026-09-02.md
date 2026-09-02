# S22+ FYG8 P3.27 framed fixed-command F1 pass

Date: 2026-09-02 KST

Target: `SM-S906N` / `g0q` / `S906NKSS7FYG8`

Status: `PASS_F1_V2_P327_NATIVE_PID1_FRAMED_EXEC_FIXED_COMMANDS_AND_ROLLED_BACK`

## Result

P3.27 proves the bounded framed command channel built on the P3.26 native-PID1
ACM path. The candidate observer accepted the fresh 49-byte banner, `READY`,
the responses for all three fixed BusyBox commands, and the terminal `DONE`.
All three commands exited zero. PID1 framed execution, BusyBox `ash` command
execution, clean session closure, exact candidate-lane inventory, and same-run
Type-C partner continuity are all true. No trailing byte was retained.

The host transmitted 193 bytes with SHA-256
`7fc87e47578505f608bbcfaa311a8b2564d5472bb3d8ce0c8f1c083af0ec196d`.
The raw device-to-host stream is 445 bytes with SHA-256
`100bf5c9011b4340bed9636becbcc467faac946f85d68001dfad9de77e761813`.
An independent decode found the banner plus eight response frames and
reproduced the three-command proof. The canonical observer receipt is 7,701
bytes with SHA-256
`b8c013edcd2d8184ffab32e6c9e25395af355326f04727940cd976ff6a4161b8`.

This result proves the exact noninteractive protocol and its three pinned
commands. It does not authorize or prove a caller-selected command, an
interactive PTY, a persistent shell, file transfer, ADB substitution, or a
general remote-management service.

## Execution and recovery

Candidate AP 28,631,081 bytes/SHA-256
`024322fd25bf1782c80e2878547c2bb6a9fd314ff21f14c8b37b3805373d3ed0`
transferred exactly once. Candidate observation completed in 8.66 seconds.
The source and candidate lanes were the exact approved `usb:2-1.3` and
`usb:3-1.3` pair; both-lane inventory, the single candidate selector, and
partner continuity passed.

The first process stopped after durable observation while measuring endpoint
evidence. It did not replay the candidate. Recovery resumed only the existing
journal, then exact Magisk rollback AP 23,367,721 bytes/SHA-256
`d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
transferred exactly once. Final rooted FYG8 health passed. The journal is
`CLOSED` with 19 records, candidate/rollback attempts are 1/1, no attempt 2
exists, and `recovery_required=false`.

## Host reporting repair

The device observation was valid, but the reopen validator asked for
`source_topology_sha256` and `candidate_topology_sha256` as top-level lane
fields. The writer had correctly retained the two literal topology names and
their SHA-256 values inside the corresponding `end_inventory.rows` entries.
That schema mismatch converted the already-valid receipt into
`interrupted-before-receipt` in the first state projection. After recovery had
completed and the journal was already closed, canonical result publication
also stopped because 34,047 bytes exceeded the shared 32 KiB record bound.

Commit `365eb86f54` changes no candidate byte or proof criterion. The common
validator now checks the stored literal lane pair, validates the nested exact
inventory, and derives the same topology digests. A run-specific finalizer
pins the frozen run, prepared binding, execution closure, observer/raw/lane
evidence, 1/1 transfers, CLOSED/19 journal, final health, and repaired live
source. It has no device backend and received independent
`PASS_GO_P327_CLOSED_FINALIZER` review.

Focused P327 validation passed 23/23. The default finalizer audit reproduced a
30,381-byte corrected state with SHA-256
`138cf273439433f7fd243b2b56e0b9b7cca24d13b6590245f53af52d510d4e3d`
and a 34,047-byte result with SHA-256
`ee36e0db25ef916a131f99907c5b93daf18eff58defd9693d966e200022973da`.
The explicit host-only publication wrote those exact mode-`0400`, single-link
files. A post-publication audit rederived the same formal result without
changing journal-head, state, or result inode, metadata, or bytes and reported
zero device, ADB, USB revalidation, Odin, candidate, or rollback actions.

## Interpretation boundary

The supplemental Carrier remains `NO_PROOF_OBSERVER`; its ambiguity does not
negate the primary framed ACM proof and does not establish a Max77705 causal
claim. The formal outcome is
`p327_native_pid1_framed_exec_fixed_commands_rollback_verified`.

P3.27 is closed, consumed, and never replayable. A broader command set, PTY,
resident service, or file-transfer protocol must use a fresh successor rather
than this candidate or approval.
