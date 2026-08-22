# A90 continuation and postrollback review-blocker repair — H0

Date: 2026-08-22
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 host-only repair and independent review
Device contact: none
Authority: none — capability review creates no candidate, D0, D1, F1,
approval, manifest, run, transfer, reboot, rollback, replay, or live authority

## Result

The current candidate-return continuation and postrollback recovery closures
now have independent `PASS_GO` reviews. This unit did not add an operator step
or device command. It repaired three real execution-boundary defects found by
the first full review and one producer/consumer branch mismatch found by the
second review.

Current exact identities are:

| Surface | Execution closure | Current review SHA-256 |
|---|---|---|
| minimal F1 owner | `455c486c3e4da2ec07b4ccf674c69625a4eb9661ae30c89924ab5f2c3363c0c8` | candidate-specific; no reusable current file |
| candidate-return continuation | `981a3f06ce38a288a8ab9c5ef76234bc38c97b51359fd2f46bfb4ed714d7ae3d` | `22fba68f002bf7e35b9e15d1b12cfed906e33de4bd1a0e56982bcc78f4acd120` |
| postrollback recovery | `148525430a5cd9f875df4cb39766c6c72a8093f2155ea1bc6e312aea8f45cf5d` | `20aaed0b4e3d7aefb940c06db421a55b9113dcc7bf2cc9e074a36328ebf3e9a0` |

Both current review files are canonical JSON, bind the hashes above, contain
zero findings and zero contacts, state `liveAuthority:false`, and are outside
their own execution closures.

## First full-review NO_GO

The first full independent review rejected the H0 implementation for three
specific reasons.

1. **HIGH — bridge raw capture was not private-bound.** The accepted managed
   bridge command could name an arbitrary `--capture` path and the bridge used
   ordinary append-open semantics.
2. **MEDIUM — the exact normal ADB daemon-start banner was only removed from
   persisted logs.** The in-memory backend and native owner still rejected the
   raw banner, so a fresh Recovery-scoped ADB server could stop an otherwise
   valid continuation.
3. **MEDIUM — postrollback recovery did not consume continuation rollback
   prefixes.** A continuation rollback ending in
   `RECOVERY_REQUIRED / ROLLBACK_HEALTH_UNPROVED` had no final-health consumer.

Focused tests were green before this review. The findings were therefore
substance and binding failures, not reasons to relax the tests or producer
parsers.

## Exact repairs

### Managed bridge capture

`serial_tcp_bridge.py` now accepts a capture only beneath the repository's
`workspace/private` root. The root and every existing/created parent must be a
direct owner-private directory. The final file is opened with
`O_NOFOLLOW|O_CLOEXEC|O_APPEND`, must be a direct regular link-count-one file
owned by the current uid/gid, and must have mode `0600`.

The F1 adapter independently requires the bridge metadata path and exact
process argv `--capture` path to resolve to the same private file and rechecks
its direct regular identity. `/tmp`, `/dev`, path traversal, symlink parents,
direct symlinks, writable parents, metadata/argv disagreement, and wrong file
mode are rejected.

### Exact ADB startup banner

`a90_serial_redaction_v1.ADB_STARTUP_BANNERS` is now the single source for the
exception. The continuation backend and native flash owner accept only those
exact bytes for the fixed Recovery inventory producer. Near-miss, extra text,
wrong role, nonzero exit, malformed stdout, or surviving process still fails.
Persisted output remains digest-only/redacted.

### Continuation rollback consumption

Postrollback recovery now accepts the two owner-allowlisted continuation
rollback prefixes, with or without its already published record `41`. It
independently validates:

- the exact uncertain candidate result and joined pending receipt;
- records `24` and optional `25`, including schema, capability, approval-hash
  continuity, qualification digest, state, attribution, physical branch, and
  no-replay fields;
- the ordinary prepared/approval/candidate/rollback/terminal chain already
  required for every rollback; and
- a present uncertain evidence sidecar through the continuation's exact
  mode-`0600` identity/digest/schema/binding validator, with quiescence
  required before final-health observation.

Resume-attributable rollback has no record `25` and rejects a sidecar. A
Native-visible nonphysical finalize has record `25` with no evidence intent
and also rejects a sidecar.

The second review found one remaining mismatch: a physical record-`25` branch
may observe an attributable failure after the operator's System action and
therefore roll back without capturing a sidecar. The consumer initially
required a sidecar for every physical branch. The final rule matches the
producer: absence means the attributable-failure branch; if a sidecar exists,
it must validate completely and be quiescent. The bounded delta review then
returned `PASS_GO` for postrollback recovery.

## No historical revival

Current capability review does not revive H34. Its frozen public input binds:

| Binding | H34 frozen value | Current value |
|---|---|---|
| owner closure | `1c31fb97e8f181e63bd71949b020f647aa8dab45c63d13bd089f6be2659da8a8` | `455c486c3e4da2ec07b4ccf674c69625a4eb9661ae30c89924ab5f2c3363c0c8` |
| continuation closure | `d053e137ca6d984709e53a1200d1e980f6d766ab4dd30cbb012cef2ddd3ee9e1` | `981a3f06ce38a288a8ab9c5ef76234bc38c97b51359fd2f46bfb4ed714d7ae3d` |
| continuation review SHA-256 | `22c0e6a60eb94dd5407d995c8e4b7e283bb149057e0ecbf8164dae5e613b49e9` | `22fba68f002bf7e35b9e15d1b12cfed906e33de4bd1a0e56982bcc78f4acd120` |
| postrollback review SHA-256 | `429c84e57b873619fd840df7afa009d52a99560de6a4c461cf84da3c73aa5429` | `20aaed0b4e3d7aefb940c06db421a55b9113dcc7bf2cc9e074a36328ebf3e9a0` |

H34 remains consumed and non-replayable. A future candidate still needs a
fresh candidate identity, candidate-specific qualification review and
manifest, connected D0, attended binding, and the target contract's F1
conditions.

## Validation and proportionality

- 335 focused continuation/bridge/banner/postrollback tests passed after the
  repair;
- 535 adjacent closure tests passed after the final postrollback one-branch
  correction;
- 29 current-review, historical-qualification, and documentation tests passed
  with three expected private-artifact skips;
- changed Python passed `py_compile` and the scoped diff passed
  `git diff --check`; and
- independent review chronology was `NO_GO` → continuation `PASS_GO` plus
  postrollback `NO_GO` → postrollback `PASS_GO` after the exact branch repair.

The tracked code is larger because the final-health consumer now validates a
previously unsupported durable prefix. Runtime remains the same: no additional
approval, manifest field, user action, device command, retry, candidate
transfer, or rollback attempt was added.

All tests used public source and temporary host fixtures. No device, USB, ADB,
network endpoint, other target, or `workspace/private` live evidence was read
or changed.

## Next

The review machinery is current, but no run is prepared. The next independent
H0 question is the remaining RTIC/stock-equivalence delta. Only after that is
resolved should a fresh candidate qualification be proposed.
