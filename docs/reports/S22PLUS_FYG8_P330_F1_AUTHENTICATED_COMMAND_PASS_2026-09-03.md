# S22+ FYG8 P3.30 authenticated bounded-command F1 pass

Date: 2026-09-03 KST

Target: `SM-S906N` / `g0q` / `S906NKSS7FYG8`

Status: `PASS_F1_V2_P330_AUTHENTICATED_PID1_BOUNDED_COMMANDS_DIAGNOSTIC_AND_ROLLED_BACK`

## Result

P3.30 proves the authenticated bounded command channel over the native-PID1
CDC-ACM path. The candidate observer accepted the fresh banner, both bounded
pre-auth diagnostic frames, a fresh 32-byte challenge, HMAC-SHA256
authentication, `READY`, all three fixed BusyBox commands, and terminal
`DONE`. All commands exited zero, the frame session closed cleanly, and no
trailing byte was observed.

The two diagnostics were `OPEN_PARSED` stage 1/code 0 and `RNG` stage 2/code
0. Nonce acquisition used zero EAGAIN retries. These diagnostics localize the
handshake but are not proof on their own; the accepted authenticated exchange
and command results provide the proof.

Host-to-device traffic is 369 bytes with SHA-256
`75ae9c610ba29476936f2b5ea0a1fdb7b9329de5ac0dfdb199ab0799d3963831`.
The raw device-to-host stream is 557 bytes with SHA-256
`cda7ec0f2b1cde2a3666c44abe3f207150a725277d704bb051c4bb07959751ca`.
The canonical observer receipt is 8,502 bytes with SHA-256
`089150d86051ff9a77ff78813d566a4d25514907780b7247a6a4fb10cb7af6f1`.

This proves authenticated native-PID1 execution of the three fixed commands
and the bounded command protocol. It does not prove or authorize an
interactive PTY, a persistent service, unrestricted shell access, arbitrary
file transfer, or a general remote-management interface.

## Execution and recovery

Candidate AP 28,631,081 bytes/SHA-256
`f458498c1b33961a9a7049a3ad8e74d4ab67ab64e672ba20af21d074f418175b`
transferred exactly once. Candidate observation completed in 22.96 seconds.
The approved `usb:2-1.3` source and `usb:3-1.3` candidate lane inventory was
exact, only the candidate lane was opened, and same-run Type-C partner
continuity passed.

The first process stopped after the durable candidate observation while
measuring the endpoint required for rollback. It did not replay the candidate.
Recovery reopened the existing journal and exact preapproved Magisk rollback
AP 23,367,721 bytes/SHA-256
`d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
transferred exactly once. Final rooted FYG8 health passed.

The journal is `CLOSED` with 19 records. Candidate/rollback accounting is
1/1, no attempt 2 exists, and `recovery_required=false`. Final live state is
32,367 bytes/SHA-256
`63bddfd1d456e53f9e3fa9977e593f4696b34e1e4814d0b3eb23a20709fc6a7a`.
Final live result is 36,175 bytes/SHA-256
`05092220fdcfd3dda30f072871ee4a621b4549504ef626e80bd82298c43a5df7`.

## Interpretation boundary

The supplemental Carrier decoder remains `NO_PROOF_OBSERVER`; it does not
negate the primary authenticated ACM proof and does not establish a Max77705
causal claim. The formal outcome is
`p330_authenticated_pid1_bounded_commands_diagnostic_rollback_verified`.

P3.30 is closed, consumed, and never replayable. A resident service,
interactive session, broader command set, or file-transfer protocol requires
a fresh successor rather than this candidate or approval.
