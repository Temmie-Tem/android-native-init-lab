# S20+ Download-mode normal return D1 H0

Status: **PASS_GO - PAYLOAD-FREE DOWNLOAD RETURN D1 ACTIVATED**

This bounded action addresses only normal return from Samsung Download mode.
It is not a flash, boot-image transfer, root, recovery, or F1 operation.

Runner: `workspace/public/src/scripts/revalidation/s20plus_g986n_download_exit_d1.py`

- SHA-256: `c00558393235b82e50b8df833fd97064801c3f297f1ce067cefcee27332a2bb6`
- Tests: `tests/test_s20plus_g986n_download_exit_d1.py`
- Host-only tests: 9/9 PASS
- `py_compile`: PASS
- Device/ADB/Odin execution during design: 0
- Independent review: PASS_GO, no unresolved finding, 2026-08-14

Activation is mechanical and creates no current run or approval. Each live
use still requires a fresh attended `exit-download` request and the exact
two-step arm/confirm handoff.

The operator disconnects USB while the phone remains in Download mode. The
`--arm` phase records an empty `odin4 -l` baseline under a shared action guard.
After reconnecting, `--confirm` accepts only the exact token, one exact
Samsung Download endpoint, the allowlisted topology/profile, and a stable
character-device identity. It records intent before one payload-free
`odin4 --reboot -d <endpoint>` command. Odin output and endpoint state are
bounded and private. Any uncertain result retains the guard and forbids replay.

The helper polls only for exact normal Android identity/health after dispatch.
If health is late, `--finalize` is read-only and performs no second Odin
command. A durable healthy result is the only guard-release condition.

Independent review must cover endpoint continuity/physical handoff, malformed
or symlinked journals, foreign/duplicate endpoints, Odin hash and argv
binding, no-payload enforcement, timeout/no-replay behavior, shared F1 guard
isolation, and exact Android return health before activation.
