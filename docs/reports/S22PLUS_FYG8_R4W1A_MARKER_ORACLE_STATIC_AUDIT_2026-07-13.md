# S22+ FYG8 R4W1-A Marker Oracle Static Audit

Date: 2026-07-13 KST

Verdict: `PASS_R4W1A_PRIMARY_ORACLE_SELECTED_HOST_ONLY; A1_IMPLEMENTATION_READY; A1_LIVE_BLOCKED; NO_LIVE_AUTHORIZATION`

## Scope

This unit is host-only. It parsed the exact FYG8 super image and effective
SELinux policy, inspected exact system binaries and init metadata, checked the
matching Samsung kernel sources, and implemented a bounded streamed-bugreport
parser. It did not contact a device, enumerate USB, build or package a boot
artifact, run a connected dry-run, create a policy exception, or flash.

## Artifact Recovery

The stock AP member was decoded to an Android sparse super image and converted
to a regular super image with the pinned local kernel build-tools `simg2img`.
The new host-only LP parser independently validated AOSP liblp v10 geometry,
checksums, table bounds, block-device size, and primary/backup slot-0 identity
before extracting only named partitions.

Key metadata:

| Item | Value |
| --- | --- |
| sparse super SHA256 | `f418abff8cf0612d7c145d6f6de0ac6a13bbdd8b5a6458b5ae8c18f2bf8243c8` |
| geometry SHA256 | `f7962585ff73e934e18bba0279ce1cb506f9703c969a9dbbb46750bc45cb0224` |
| slot-0 metadata SHA256 | `c8674395bee9548fa3d38c0bedf626fdc4312b1e0651eac2f17e469a9b63cd5f` |
| super block-device size | `12475957248` |
| system image SHA256 | `d225ba954bb05f4738c6d5f1e9a3f9dffa38e488ca192aec9563bcbafd111647` |
| odm image SHA256 | `937e692aff25c4a88d27b2b93e4b23abe39ebe034a95c6b18416b2667c263e76` |
| product image SHA256 | `8604829ba08f0f585d30e33121b85cec3cfa26aff69340a2be10383206c52803` |
| system_ext image SHA256 | `d6aa196410579173d0ea42fe7070fdc1bb2ed9da83d3086c87de0adff4cf29b9` |
| vendor image SHA256 | `a885cb219d3d21aea87aacb514650857d46f9e2d3b2bfa2fb7a7f1754c5dacf2` |

All filesystem inspection used local read-only F2FS loop mounts. Every loop was
unmounted and deleted before this report.

## Exact FYG8 Policy Result

The ODM `precompiled_sepolicy` SHA256 is
`9f3060ccc428a4fdd11183d7206c253dfc6735489208dbd0e3e5fe1b34667880`.
It equals the exact `HS=` value in vendor policy-version metadata. Setools 4.6.0
parsed a temporary staged copy made from the already SHA-validated in-memory
bytes and returned these load-bearing results:

- `/proc/last_kmsg` is `proc_last_kmsg`;
- `shell -> proc_last_kmsg:file read` has zero allow rules;
- exact authorized readers are `bootchecker`, `dumpstate`, `incidentd`,
  `system_server`, and `vendor_init`;
- shell may set `ctl_dumpstate_prop`, write `dumpstate_socket`, and connect to
  the `dumpstate` Unix stream socket;
- init transitions `dumpstate_exec` to the `dumpstate` process domain; and
- `dumpstate` may open and read `proc_last_kmsg`.

Therefore direct non-root candidate `cat /proc/last_kmsg` is not a viable
oracle. DAC mode `0444` does not override the exact SELinux denial.

## Service And Snapshot Chain

Exact FYG8 hashes:

| Artifact | SHA256 |
| --- | --- |
| `dumpstate` | `b5de4fb2c0339c04dc6b9cc0c8063cb189d736b4a429f23417c9c09a20bfbe96` |
| `bugreportz` | `e10c143f8909bd8f79cf7528c1c1d12c81acbbd1e4e4e57e226652be508feaaa` |
| `dumpstate.rc` | `14ea29bf7ec4a37dadae5a68d0c494d86292b8bc1df8831eb36c566b31094c8b` |
| `plat_file_contexts` | `30a0b3a5317968e0fc82291dfdd75506d6355c478cbab830a1d34a7bd3d09214` |
| `sec_log_buf_main.c` | `296f4fc175d958feb35b92c8736faf6361ade2e7c447d9a9af5a93f59bdb97b8` |
| `sec_log_buf_last_kmsg.c` | `ba9e0f9f0832cbf666e55b51804515fc8298203fd37958ccdfb6bfbbe3524443` |

Exact init starts `/system/bin/dumpstate -s` as root with a shell-accessible
stream socket. Exact binaries contain the control-service, stream,
`main_entry.txt`, `LAST KMSG`, pstore fallback, and `/proc/last_kmsg` constants.
The exact Samsung source copies the retained ring into `last_kmsg->buf`, creates
the proc node, and only then imports current early logs and registers the live
logger. Proc reads copy only from that private snapshot.

This removes the prior overwrite dependency: later candidate logs can wrap the
physical ring, but cannot mutate the candidate snapshot already published at
module probe.

## Parser Contract

`s22plus_fyg8_r4w1a_marker_oracle.py parse` requires:

- a direct regular ZIP below fixed archive and expanded-size bounds;
- identical pre/post SHA256 from the same open archive fd;
- unique normalized entry names and CRC-checked EOF for every member;
- exact `main_entry.txt` and `version.txt` metadata;
- one direct main text entry;
- exactly one `LAST KMSG (/proc/last_kmsg)` section followed by a complete next
  section boundary;
- no dump error or dry-run marker; and
- exact R4W1 marker-family cardinality across the complete archive and section.

It supports separate `absent` baseline and `exact` candidate expectations.
Duplicate, partial, foreign, pstore-sourced, corrupt, oversized, symlinked, or
path-unsafe inputs fail closed.

Implementation hashes:

| Artifact | SHA256 |
| --- | --- |
| `s22plus_fyg8_lp_extract.py` | `0f382cf6e7be82005be469dbb708cdef3166109e47ba00696dfb5e32dc385fbc` |
| `s22plus_fyg8_r4w1a_marker_oracle.py` | `bfc7a8d76892931ff7faed25606cc7c7c92cf6ef3f67357316ee25b0fa887462` |
| LP tests | `9fe8c2e40efc40feee1d2f73fd49ec195f80a55f30df18f79bdb536ab8ff2be7` |
| oracle tests | `9006fc3579ec07ac226d082fbc99321e5309da721be805f4646858a2807235b4` |

The private audit result returned
`PASS_R4W1A_PRIMARY_ORACLE_SELECTED_HOST_ONLY`, size 4,322 bytes, SHA256
`f243191c985caf918a2a4504be349fdaa133c10b75caab973c71b1e31c1610dd`.

## Remaining Gate

No exact FYG8 bugreport ZIP was retained locally, so the exact live stream
shape is not yet proven. AOSP documents `main_entry.txt`, the dumpstate source
selects `/proc/last_kmsg` after missing pstore console files, and
`bugreportz -s` streams socket bytes to stdout. Those references support but do not replace
an FYG8 connected proof:

- <https://android.googlesource.com/platform/frameworks/native/+/android16-release/cmds/dumpstate/dumpstate.cpp>
- <https://android.googlesource.com/platform/frameworks/native/+/android16-release/cmds/dumpstate/DumpstateInternal.cpp>
- <https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/cmds/dumpstate/bugreport-format.md>
- <https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main-cg-testing-release/cmds/bugreportz/main.cpp>

The stream path also creates a local ZIP under `/bugreports` before copying it
to the socket. A future policy must explicitly authorize exactly one capture,
inventory before and after, identify only files created by that run, remove
only those exact files through a proven authorized path, and verify cleanup.
Static evidence does not yet prove that candidate shell can perform that
cleanup.

Dumpstate also prefers either pstore console path over `/proc/last_kmsg`. The
future candidate gate must prove both paths absent before capture; the parser
then independently requires the exact `/proc/last_kmsg` section header.

Accordingly, `a1_implementation_ready=true` but `a1_live_ready=false`. This
report activates no helper, policy exception, device action, or flash.

## Validation

- 61 focused and related R4W1 tests passed.
- Python bytecode compilation passed.
- `git diff --check` passed.
- The exact static audit reran after large intermediate-image cleanup and
  returned the same verdict and pinned result hash.
- All local read-only loop devices were removed.
- `ruff` and `pyflakes` were unavailable and were not installed in this unit.
