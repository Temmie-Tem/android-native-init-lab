# S22+ FYG8 P350 fixed native display preparation

Date: 2026-09-06. Target: SM-S906N / g0q / S906NKSS7FYG8.
Capability/build sections below are H0 evidence. Fresh connected D0 preparation
subsequently passed; no Download request, transfer or display run has occurred.

## Result and scope

P350 packages the reduced display module and a static DRM renderer with the
existing authenticated native PID1 runtime. The bounded observation is three
same-descriptor sessions: USB witness, one fixed display command, USB witness.
It has no retained shell lease or reconnect requirement. P349 remains paused;
its hour-long RAM-workspace experiment is separate.

The renderer loads exactly nine packaged modules once, preserving the existing
73-module USB plan. The display module receives the retained selected-panel
parameter and a strictly parsed LCD identifier from the current kernel command
line. The parent accepts only the fixed display command and consumes its flag
before fork. There is no arbitrary privileged shell command or module retry.

After opening the exact DRM node and obtaining master, the helper drops groups,
UID/GID to 65534 and capabilities before rendering. It uses the WC dumb-buffer
route for ten numbered frames and requires completed page-flip events and a
successful final disable. The parent bounds this child to 60 seconds; the whole
observation is bounded to 150 seconds. Missing completion or protocol failure
requires the existing attended physical Download and exact Magisk rollback.

DRM completion events and visible output are separate claims. Even a successful
machine receipt reports `visible_panel_output=UNPROVED`; operator observation
must corroborate changing screen content. Host mocks do not prove module probe,
runtime ABI, physical display, transitive absence of persistent writes, recovery
or final device health.

## Artifacts and validation

Two independent A/B packaging passes produced the same 30,822,441-byte sole-boot
AP, SHA-256 `41b9272b933567000ed1efa44339ad5376d9151bc10eecb7edcc92edb1a4e31e`.
The boot container remains 100,663,296 bytes. The packager audits every retained
ramdisk entry and the exact added renderer/module inventory, then decompresses
the actual AP member and joins it to the fully audited boot artifact.
Supporting partitions are unchanged. Exact Magisk rollback remains
23,367,721 bytes / digest prefix `d2373bf8`.

Validation completed:

- Cross-compiled native sources with warnings as errors; inspected AArch64 ELF
  outputs and compared deterministic A/B artifacts.
- Three renderer/loader/parameter tests, including nine mocked renderer paths
  and valid/invalid panel parameter parsing; four observer sequence tests.
- 84 production live-receipt/routing regressions, including real authenticated
  P350 RX/TX replay, rejection of forged counts, repeated TX and incomplete frame
  semantics, and retained P345/P348/P349 behavior.
- Python compilation for 14 touched/new sources, repository boundary check and
  whitespace check.
- Non-publishing common-bundle promotion rehearsal and full-tree raw-first audit
  passed. The additional broad legacy audit test sweep was stopped during
  redundant whole-tree rescans without a reported failure; focused changed-path
  raw-first regressions passed (five tests covering P345/P348/P349/P350).
  Total focused tests: 96. The audit binds P350 execution sources and unchanged raw capture/
  exchange consumers; frozen population counts remain 49/129/133.

Independent review returned **PASS_GO** for this bounded capability after
reviewing the final execution closure and the validation receipts above.
Final ready manifest publication and reopening passed with
`PASS_P350_PROCESS_V2_READY_MANIFEST_HOST_ONLY`; manifest identity is
`5289B/5de919d0`, bundle digest prefix `affa90e7`. No live run directory was
created and no device authority was issued. Capability qualification does not
authorize a device run. Fresh
exact connected preparation, returned attended approval and physical recovery
availability remain required by the selected target contract.

## Evidence and host storage

Private build and promotion evidence is under
`workspace/private/outputs/s22plus_fyg8_p350/`; bounded tests, build logs and
cleanup receipts are under `workspace/private/outputs/s22-display-renderer-h0/`.
The first rehearsal's empty-directory identity rejection is retained. The fix
allows only the exact zero-length directory entry; all files remain hash/size
bound. Candidate bytes did not change.

Storage cleanup removed 56 verified duplicate packaging scratch files while
preserving candidate, rollback, logs and raw evidence. With operator permission,
the retained kernel build tree moved to the SD card after full checksum
comparison, preserving metadata and the original path through a symlink. The
post-copy checksum dry run had no differences. Root free space was 6.5 GiB and
SD free space 5.4 GiB at the final check; concurrent host work prevents assigning
all free-space change to this cleanup. The retained firmware was already on SD.

[Exact bootloader compatibility review](S22PLUS_FYG8_NATIVE_DISPLAY_BOOTLOADER_COMPATIBILITY_H0_2026-09-06.md)
identified no additional display-specific bootloader change. It does not prove
acceptance of this candidate; module/probe and screen behavior remain live
questions. A90 and S20+ received no device command in this work.

## Reviewed source identity

Canonical source paths are those in the ready/static closure. The independent
review bound these final source bytes; inherited templates retain their own
checked identities.

| Source | SHA-256 |
| --- | --- |
| `S22PLUS_FYG8_TARGET_CONTRACT.md` | `115c6dc9fc1a1f8a832c13127e61d4ca30b53d23ffc313435066b9b4b361f63e` |
| `s22plus_native_display_h0.c` | `0aef36334a305287f98e11470a2a64b44d8e1bd4126adaafd0b9a4ed8e0846d7` |
| `s22plus_native_display_load.inc.c` | `ebd03fc2c9f52f8b0840679b4ccdbd3ac9101965faf52558705bf01693ad2b3e` |
| `prepare_s22plus_fyg8_p350_process_v2.py` | `176673e7f9eb027dbda13b9ef8a5b6a26cbc2fb75667a6be80c4c1d559d3589e` |
| `s22plus_fyg8_p350_process_v2_candidate_static.py` | `a1ef060a67a23c965604fbd6f7358ba84219a0efd839c04e0118b149a199b74b` |
| `s22plus_fyg8_p350_stock_candidate_build.py` | `2cc546ce347ce185a8e859a919fdf7317c2c089e2ffc6e904fc708f7f743f9a4` |
| `s22plus_fyg8_p350_artifact_identity.py` | `31a96966709c41a3288e2a215a316d931b38790af0739fdbb58c8498501a11f2` |
| `s22plus_fyg8_p350_research_shell_observer.py` | `c6590cd5d376a19e325fecfd729b38758a3c5f3fc8c3937cceca85e67a3cd7b6` |
| `s22plus_fyg8_p350_research_shell_runtime.py` | `5527246e591a730ba6d4ea413e51daf18a4f481d1b8c401041c4da31d0eb8957` |
| `s22plus_fyg8_p350_stock_process_v2_adapter.py` | `0efbf7bd2fd0427d88cf70254b1e1d10bd27fc11da5b30add792fdf4c78f6392` |
| `device_action_f1_evidence_v2.py` | `35ac2e009dcf95f15a4f154693e890bef00371b0e4d6afbac59aa2334274daef` |
| `device_action_f1_live_v2.py` | `cc8d4c67efc53b1221baeb034bcc04f53d5a64b7c2c0aaa50c28709bfcd9d536` |
| `s22plus_fyg8_raw_first_observer_audit.py` | `2b13da3ccdcf570bd7e4fa651bc198afe09389c37f02c762f01c4ec128ab4c94` |

## Fresh connected preparation

The operator requested progression to the attended P350 experiment. The ordinary
runner completed fresh D0 in `p350-ready1-prepared-20260906-1` with
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`, then published the exact target,
current boot, topology, candidate/rollback, authentication and execution-source
binding. Actual `load_prepared` reopening passed against the stored files.
The 13 independently reviewed principal source identities were unchanged.

Prepared record: 28,959 bytes, SHA-256
`1498b2fce9ac004b46ec746efd86e058ba37dee698578c780e60a214fbd4070b`.
D0 result: 3,261 bytes, SHA-256
`896dc03a8e4cbe7bd2ad45466dc4248397fd1bac22cdc3f5cea7e0f3d7f2bd0a`.
Both remain private under
`workspace/private/runs/device-action-f1-live-v2/p350-ready1-prepared-20260906-1/`.

This step performed bounded S22+ reads only. Reboot, Download, Odin, partition
transfer and live-authorization flags are false; A90/S20+ received no command.
The fresh approval code was issued for return by the operator, who must be
available for host authentication and physical Download recovery. No old P349
approval is reused and no candidate intent has been recorded.
