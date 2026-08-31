# S20+ G986N attended root-health public exec repair v1 H0

Date: 2026-08-31

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`)

Status: **PASS_GO; HOST ROTATION COMPLETE; NO DEVICE REQUEST**

## Outcome

The terminal read-closed root-health incident was reduced to one exact host
framing defect. The qualified predecessor runner passed this argv for each
public snapshot:

```text
adb -s <internally-selected-serial> exec-out sh -c
    shlex.quote(<423-byte-public-script>)
```

ADB 34.0.5 constructs `exec-out` by copying the first command (`sh`) and
applying its own `escape_arg()` to every later argv element. The qualified
predecessor therefore caused the already-quoted 449-byte value to be escaped a
second time. Its modeled 524-byte service delivers the prequoted string, not
the 423-byte script, as remote `sh -c` argv.

The current corrected runner removes that prequote only:

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

After exact H0 qualification and independent review, the candidate was applied
as a host-only active-runner/test/contract identity rotation. No ADB, `su`,
device, USB, socket, network, write, reboot, mode transition, transfer, Odin,
or partition operation occurred during qualification or rotation.

## Evidence and identities

The qualified predecessor was accepted only at 39,820 bytes and SHA-256
`7967f85dc1418473c66b418cedfc2c15063a141fed2550d040eb122fec04584a`.
The in-memory two-fragment transform produces exactly 39,819 bytes and SHA-256
`24f69cc5aa43c70558e3594534ee684db0a038e972d1b0db2f1b8d8446af2d44`.
Any active-source drift, missing/duplicate replacement, script mutation, root
argument change, or extra candidate edit is rejected.

| Object | Size | SHA-256 |
|---|---:|---|
| Public snapshot script | 423 | `f17aac6c9c946968b18ac91a05c6d8f006fef1857533518495a97d5e71d9813b` |
| Predecessor prequoted public argument | 449 | `0fa4c7d3b01941f467f5ad2da51059f5b7ae5d054267a39fdca2cac878f8e4f9` |
| Predecessor double-escaped exec service | 524 | `206586836f8f8bc43a0f6b1d414c9d2df9b3fa7d41e1c9629b4d1ce460a0771f` |
| Current corrected single-escaped exec service | 456 | `8ff45512fd92c37671396cf1d0abeb5b591dd1cdf37a5ee7bbc489d9f3acdbbf` |
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

The post-rotation H0 record is
`workspace/public/src/scripts/revalidation/s20plus_g986n_attended_root_health_public_exec_repair_v1_h0.py`,
22,337 bytes at SHA-256
`1dfb6818b1bfea084257edda081f14507323dfe954c48d5ccbf4f7122b9eb716`.
Its normalized SHA-256 is
`867837b8bcfea220086e86286c880ce23e1f918c20f1978a6bec456b42e4b61e`.
The focused hostile test is 16,396 bytes at SHA-256
`27d14dbeb8627388562cd6d7d726c750b375e7df83384b2ad4fc153b61f7895e`.

The pre-rotation model passed `py_compile`, render-plan validation, scoped diff
checking, and 21/21 focused tests. Independent hostile review reproduced the exact transform,
checked the ADB source paths, active runner call sites, target-contract
command closure, root-argument preservation, claim boundary, gates, and CLI,
then returned `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`.

The post-rotation record reconstructs only the exact reviewed predecessor from
the current corrected runner, re-applies the two-fragment transform in memory,
and requires equality with the current bytes. Its expanded focused suite passes
22/22; the corrected active-runner suite passes 28/28. Independent
post-rotation review returned `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0` after one
terminology correction distinguished the qualified predecessor from the
current corrected runner.

## Incident relation and claim boundary

The incident failure signature remains the SHA-256 of
`RootHealthD0Error:selected target public snapshot has the wrong field count`,
namely
`a796e18647a44a3cbf815f57dc6e2539c7ab8d6852ae83397affafaa04f007e7`.
It records three host commands, one public snapshot, zero root commands, and
zero device effects.

The following are proved by exact source and constructor analysis:

- the qualified predecessor prequotes the public script;
- ADB 34.0.5 escapes that exec-out argv again;
- the modeled predecessor service delivers the prequoted string rather than
  the raw script;
- the current corrected runner delivers the exact raw public script once; and
- the root script and its required shell quoting remain unchanged.

The double escaping coherently explains the observed field-count closure, but
the failed public stdout was intentionally not retained. Therefore it remains
`SUPPORTED`, not `PROVED`, that this was the only runtime cause. Current root
health and the candidate's live result remain `UNKNOWN`.

## Post-rotation boundary

The active runner, focused test expectation, binding target contract command
closure, exact identities, and goal record were rotated together. Focused and
document regressions pass, and the independent post-rotation review is closed.
The mechanical host rotation is complete; this is not a device invocation.

Even after that rotation, the consumed incident request cannot be replayed. A
later connected root-health invocation requires a new direct attended request
and may execute only the fixed runner-owned `su -c` read. Generic `su`, R1,
F1, writes, persistent mutation, and recovery-path changes remain outside this
qualification.
