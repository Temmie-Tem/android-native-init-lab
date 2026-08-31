# S20+ G986N attended root-health public exec repair v1 H0

Date: 2026-08-31

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`)

Status: **PASS_GO_NOT_ACTIVE; CANDIDATE NOT APPLIED; NO RETRY AUTHORITY**

## Outcome

The terminal read-closed root-health incident was reduced to one exact host
framing defect. The active runner passes this argv for each public snapshot:

```text
adb -s <internally-selected-serial> exec-out sh -c
    shlex.quote(<423-byte-public-script>)
```

ADB 34.0.5 constructs `exec-out` by copying the first command (`sh`) and
applying its own `escape_arg()` to every later argv element. The active runner
therefore causes the already-quoted 449-byte value to be escaped a second time.
The modeled 524-byte service delivers the prequoted string, not the 423-byte
script, as remote `sh -c` argv.

The exact candidate removes that prequote only:

```python
PUBLIC_SHELL_ARGUMENT = PUBLIC_SNAPSHOT_SCRIPT
```

It also changes the render-plan description from
`single-shlex-quoted-fixed-literal` to
`single-raw-fixed-script-argv-ADB-escaped-once`. The resulting 456-byte ADB
service delivers the byte-identical raw public script as the final remote argv.

The root read is deliberately unchanged. ADB's `shell` path joins its
non-option argv without applying `escape_arg`, so its existing runner-owned
`shlex.quote(ROOT_READ_SCRIPT)` is required and still resolves to exactly
`[su, -c, <584-byte-root-script>]` at the remote shell boundary.

No candidate bytes were applied to the active runner. No ADB, `su`, device,
USB, socket, network, write, reboot, mode transition, transfer, Odin, or
partition operation occurred during qualification.

## Evidence and identities

The active runner was accepted only at 39,820 bytes and SHA-256
`7967f85dc1418473c66b418cedfc2c15063a141fed2550d040eb122fec04584a`.
The in-memory two-fragment transform produces exactly 39,819 bytes and SHA-256
`24f69cc5aa43c70558e3594534ee684db0a038e972d1b0db2f1b8d8446af2d44`.
Any active-source drift, missing/duplicate replacement, script mutation, root
argument change, or extra candidate edit is rejected.

| Object | Size | SHA-256 |
|---|---:|---|
| Public snapshot script | 423 | `f17aac6c9c946968b18ac91a05c6d8f006fef1857533518495a97d5e71d9813b` |
| Active prequoted public argument | 449 | `0fa4c7d3b01941f467f5ad2da51059f5b7ae5d054267a39fdca2cac878f8e4f9` |
| Active double-escaped exec service | 524 | `206586836f8f8bc43a0f6b1d414c9d2df9b3fa7d41e1c9629b4d1ce460a0771f` |
| Candidate single-escaped exec service | 456 | `8ff45512fd92c37671396cf1d0abeb5b591dd1cdf37a5ee7bbc489d9f3acdbbf` |
| Root read script | 584 | `128ba6294378442b9e2a580086c2a8f6fc2f06afe30e642066f9bca4af314da1` |
| Retained root quoted argument | 594 | `e5db5a7bb0fb78553e033649bc16496c008b9e5882b88f0c84234c1dede657aa` |

The exact installed ADB remains
`/usr/lib/android-sdk/platform-tools/adb`, 716,968 bytes, SHA-256
`05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226`,
from Ubuntu source version `34.0.5-12build1`. The source semantics were checked
against AOSP tag `platform-tools-34.0.5`:

- `client/commandline.cpp` constructs `exec:` with the first command raw and
  `escape_arg()` around every later argv element;
- the same file's `adb_shell()` joins the command argv without escaping; and
- `adb_utils.cpp` implements the single-quote and embedded-quote transform.

The H0 model is
`workspace/public/src/scripts/revalidation/s20plus_g986n_attended_root_health_public_exec_repair_v1_h0.py`,
20,359 bytes at SHA-256
`080898d84d66dbe0695d84d4bf328f7fa71e5db1efc7061e330f06725fc3a83a`.
Its normalized SHA-256 is
`b507ec66a7ab3223fc8dbc38e083895b44ff553cc65517a438b03a5c3de4084e`.
The focused hostile test is 14,392 bytes at SHA-256
`6052f28d5c29670b42fd2d194cbf2d943a07563da61cc02ef6f2a9166a0d26ca`.

`py_compile`, render-plan validation, scoped diff checking, and 21/21 focused
tests passed. Independent hostile review reproduced the exact transform,
checked the ADB source paths, active runner call sites, target-contract
command closure, root-argument preservation, claim boundary, gates, and CLI,
then returned `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`.

## Incident relation and claim boundary

The incident failure signature remains the SHA-256 of
`RootHealthD0Error:selected target public snapshot has the wrong field count`,
namely
`a796e18647a44a3cbf815f57dc6e2539c7ab8d6852ae83397affafaa04f007e7`.
It records three host commands, one public snapshot, zero root commands, and
zero device effects.

The following are proved by exact source and constructor analysis:

- the active runner prequotes the public script;
- ADB 34.0.5 escapes that exec-out argv again;
- the modeled active service delivers the prequoted string rather than the raw
  script;
- the two-fragment candidate delivers the exact raw public script once; and
- the root script and its required shell quoting remain unchanged.

The double escaping coherently explains the observed field-count closure, but
the failed public stdout was intentionally not retained. Therefore it remains
`SUPPORTED`, not `PROVED`, that this was the only runtime cause. Current root
health and the candidate's live result remain `UNKNOWN`.

## Remaining activation gates

This qualification creates no standing device authority. Before applying the
candidate, all of the following remain required as one reviewed rotation:

1. rotate the active runner and focused test expectations;
2. update the binding target contract's public-snapshot argv and exact
   runner/test identities;
3. rotate every affected document assertion and activation atom;
4. run focused and aggregate regression tests;
5. obtain post-rotation independent `PASS_GO`; and
6. mechanically activate only the exact reviewed closure.

Even after that rotation, the consumed incident request cannot be replayed. A
later connected root-health invocation requires a new direct attended request
and may execute only the fixed runner-owned `su -c` read. Generic `su`, R1,
F1, writes, persistent mutation, and recovery-path changes remain outside this
qualification.
