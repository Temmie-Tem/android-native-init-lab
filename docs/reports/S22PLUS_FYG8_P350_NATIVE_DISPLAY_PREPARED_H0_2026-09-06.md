# S22+ FYG8 P350 fixed native display preparation

Date: 2026-09-06. Target: SM-S906N / g0q / S906NKSS7FYG8.
Current state: CLOSED/19 and consumed. Candidate and exact Magisk rollback
transferred once each. Result: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`; final
rooted FYG8 health passed. Preparation sections below are historical stages.

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

## Consumed P350 result and recovery

The operator returned the exact fresh approval. Candidate AP and exact Magisk
rollback each transferred once. The initial USB/read-only session passed. The
second authenticated session completed its framing, but the fixed display child
returned exit 1 at 101 ms. All nine `DISPLAY_LOAD_DONE` records are present,
followed by `DISPLAY_FAIL stage=drm-readiness errno=2`.

The executed source maps that error to opening `/sys/class/drm/card0/dev`.
It occurred before DRM node creation, DRM master, buffer allocation or any
frame submission. Module insertion returning success is not proof of driver
probe completion or DRM registration. Missing dependency, deferred probe,
registration failure and timing remain unclassified; this run does not distinguish
them. No `DISPLAY_FLIP` or `DISPLAY_DONE` record exists. The third qualification
session was not attempted, so qualification is 1/3. The second session's final
nonce command nevertheless returned successfully, preserving evidence of the
parent protocol's return after the child failure.

During physical Download waiting the runner stopped on `measured USB endpoint
inventory failed`, before rollback transfer. One ordinary same-journal recovery
resumed only the preapproved exact rollback. Rollback completed once and final
Android/root, original boot/supporting partition hashes and absent Download
passed. This does not change the display result into a PASS. The inventory
failure's cause remains unproved. No candidate or display command was replayed.

Actual prepared and `validate_live_result` consumers reopened the terminal
record successfully: CLOSED/19, `recovery_required=false`, outcome
`p350_native_display_events_unproved_rollback_verified`.

| Final evidence | Bytes | SHA-256 |
| --- | ---: | --- |
| Live result | 21491 | `5d10afcdcd436f37f97abc3f1165ef3dc690f4ea85f996b7f394eb26d8ef2c81` |
| Candidate observer | 13953 | `570eefed40f2ce5f92498e240b88f0e3175efa1cef25c1cfd42538cc3a088b86` |
| Candidate raw RX | 1626 | `661d0255951b96326a355391baa5df1af307d6f0442326650b54ca7bd61f8ebc` |

The private `live-close-h0-analysis.json` replays the actual authenticated raw
sessions and records bounded fixed display messages and command statuses. The
prepared execution closure and the reviewed source table above preserve source
provenance. A90/S20+ received no command.

### Canonical timeline

| Event | UTC |
| --- | --- |
| `live_session_start` | `2026-09-06T11:43:41.077920Z` |
| `candidate_flash_start` | `2026-09-06T11:43:57.795036Z` |
| `candidate_flash_done` | `2026-09-06T11:43:59.453592Z` |
| `candidate_boot_ready` | `2026-09-06T11:44:11.506540Z` |
| `rollback_flash_start` | `2026-09-06T11:46:43.001223Z` |
| `rollback_flash_done` | `2026-09-06T11:46:44.626746Z` |
| `rollback_boot_ready` | `2026-09-06T11:47:31.264717Z` |
| `live_session_end` | `2026-09-06T11:47:31.286425Z` |

### Operator observation and next display design

The operator reported not observing the screen. Do not reinterpret that as
unchanged or blank output. The assistant had failed to explain the intended
position and ten-second observation interval before execution. The intended
old layout was a dark background, two small ID rows near the top, a counter at
22% height and a moving block around 30–36% height. Raw evidence independently
shows this attempt stopped before painting/submission.

The operator requested a clearer, larger, white-background layout. Future H0
layout work should provide an actual preview before another experiment. It does
not replay or modify consumed P350, prove DRM readiness, or authorize another
transfer. No additional device effect is part of closing this run.

### White-background layout H0 implementation

Following the operator's visibility request,
`workspace/public/src/native-init/s22plus_native_display_visible_layout_h0.c`
implements only pure pixel generation. It is not included in consumed P350 or
any flashable successor. The full background is white, the black central counter
is 550 pixels tall (old counter: 60), and the green block is 180x320 pixels.
The counter is at y=650..1199 (28–51% of screen height); the block is at
y=1420..1739 (61–74%) and moves left to right. The run ID occupies two footer
rows. There is no full-screen alternating flash.

The optional host-only preview entry writes PPM bytes; it has no device access.
Host and repository AArch64 compilation passed with warnings as errors, and
`file` identified the object as AArch64 ELF. Actual C output at counters 00/05/09
was checked for dimensions, white background and moving-block positions, then
visually inspected. Preview:
`workspace/private/outputs/s22-display-renderer-h0/visible-layout-preview.png`.
The displayed sample run ID is illustrative, not an assigned future candidate.
This layout does not resolve the consumed run's missing DRM registration.

## Retained-source DRM readiness diagnosis

H0 analysis found a definite missing prerequisite in P350's display path:
**`s2dos05-regulator.ko` and its `i2c-gpio.ko` bus instantiator are absent from
the 82-module plan.** This is not yet proof of the first live probe failure.
No new device command, module insertion, candidate build or transfer was used.

### Evidence chain

The actual consumed boot artifact was reopened by its exact SHA-256. Its
41,490,944-byte Image (`b0cce785...`) contains `# CONFIG_I2C_GPIO is not set` and
`CONFIG_I2C_ALGOBIT=y`; `CONFIG_REGULATOR_S2DOS05` is absent. Neither missing
provider appears in the fixed 73-module USB plan or nine display additions.
The exact reduced `msm_drm.ko` still declares **`softdep=pre: s2dos05-regulator`**,
as well as the already-satisfied `msm-mmrm` prerequisite.

All eleven retained DTBO entries define the selected S6E3FAC_AMB655AY01 panel's
same four required supply names. Their order changes between overlay groups and
is preserved in the private receipt; set equality does not imply order equality.

| Panel supply | DT provider under `/i2c@50/s2dos05_pmic@60/regulators/` |
| --- | --- |
| `panel_vdd3` | `s2dos05-ldo1` |
| `panel_vci` | `s2dos05-ldo4` |
| `panel_vddr` | `s2dos05-buck1` |
| `panel_aee_fd` | `s2dos05-avdd-elvdd-elvss-fd` |

The enabled provider has compatible `samsung,s2dos05pmic`; its enabled parent
has compatible `i2c-gpio`. These nodes are in an overlay fragment explicitly
targeting `/`. All four retained base DTs lack competing provider definitions.
One base-0/overlay-0 host merge confirms the final root path. This is not a claim
that this pair was the runtime-selected DT; the prerequisite set holds in all
eleven inspected overlay definitions.

The exact source call chain is:

1. `i2c_gpio_probe` registers its bit-banged adapter; I2C core then enumerates
   firmware children. Without that adapter the PMIC's I2C client cannot exist
   through this DT path.
2. The matching S2DOS05 I2C driver registers the panel regulators with
   `devm_regulator_register`.
3. `dsi_panel_parse_power_cfg` reads the selected panel's named supply entries.
   `dsi_panel_get` calls `ss_dsi_panel_vreg_check` and then `dsi_panel_vreg_get`
   before panel registration. The selected normal panel does not take the
   PBA/bridge skip branch.
4. The optional regulator lookup searches DT mappings and registered names;
   absent providers cannot be replaced by a dummy in this optional check.
   The early missing-provider path returns `-EPROBE_DEFER`, propagated through
   panel acquisition before `component_add` and eventual DRM registration.
5. `msm_drm_register` ignores its platform-driver registration return values
   and returns zero. Successful `finit_module` therefore does not establish
   successful probe, component binding or `card0` creation.

The vendor precheck has a counter escape after more than 30 failures. That is
not proof of working panel power and is not a reason to wait through repeated
failures or relax the prerequisite. No such repeated probe history is observed
in the retained P350 evidence.

### Real-consumer checks and limits

The four inspected display source files match their retained original source
copies byte-for-byte. The actual reduced binary's `dsi_panel_get` disassembly
retains calls to `regulator_get_optional` and `devm_regulator_get`.
Host compilation of the unchanged relevant C function bodies, with explicitly
stubbed provider/registration APIs, produced:

- missing provider: `-517` (`-EPROBE_DEFER`);
- present named providers: `0`;
- failed platform registration: module init still returned `0`.

The fixture also cross-compiled to AArch64 with warnings as errors. It proves
these source branch semantics, not the actual kernel's first failure. The
retained A/B rollback observer blobs are identical (`2097136B/909ef99f...`), but
contain no candidate run-ID or the inspected probe-entry messages. Display
matches examined there were bootloader records, not a timestamp-correlated
candidate probe trace.

Thus an early resource error, another missing dependency, or unfinished deferred
binding may precede the missing panel-power check. The immediate single readiness
read at the end of the 101-ms command cannot distinguish these possibilities.
**Waiting alone cannot supply the two absent drivers.**

### Qualification gap and next bounded unit

The previous H0 module graph followed `modinfo depends` and versioned symbol
imports. It did not close this `softdep`, named-regulator dependency or I2C
instantiation chain. Packaging and symbol checks passed their stated checks but
were insufficient to establish display executability. Their old PASS receipts
and the consumed live NO_PROOF result remain unchanged.

Independent review confirmed these are genuine missing prerequisites and agreed
that the first live probe stop remains unproved. The smallest next H0 unit is to
assess these exact providers' source, initialization effects, binary/config
compatibility and dependency/load order, including their predecessor devices,
within the existing experiment-executability requirements. Then design a bounded
readiness witness that separates module insertion, probe/binding and DRM
registration before frame submission. The new white layout can be incorporated
in a separately qualified successor; P350 cannot be replayed.

Private reproducible analysis and source/input hashes:
`workspace/private/outputs/s22-display-readiness-diagnosis-h0/` contains
`analyze.py`, `result.json`, `check_consumers.py`, the exact C function fixture,
its host/AArch64 outputs and `dsi_panel_get.disasm`. No firmware, raw log or
private device identity is published. A90/S20+ received no command.
