# S22+ FYG8 P351 display successor — closed and rolled back

Current state: **CLOSED/19, consumed, NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK**.
Candidate and exact rollback transferred once each; final rooted FYG8 health
passed, recovery_required=false. The H0 history below precedes the live result.

Date: 2026-09-06. Exact target: SM-S906N / g0q / S906NKSS7FYG8.
Result: **H0 candidate, static promotion and independent capability review PASS**.
During H0 qualification no connected command, Download request, transfer or live
run was performed. Later D0/D1 preparation is recorded below.
P350 remains consumed; A90 and S20+ received no command.

## Result and scope

P351 integrates the [reviewed display providers](S22PLUS_FYG8_DISPLAY_PROVIDER_ASSESSMENT_H0_2026-09-06.md),
bounded regulator/DRM readiness and the white high-visibility layout into a fresh
candidate. It retains the three fixed authenticated same-descriptor sessions:
USB before, one display command, USB after. There is no later-action lease.

The A/B Image, init, renderer, boot image and AP agree. The builder independently
decodes the final AP's compressed boot member and checks the complete ramdisk,
including all twelve display additions. The 73-module USB plan stays unchanged.
Common offline bundle verification passed first in rehearsal and then during
local ready publication. No connected preparation or F1 approval was created.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Candidate AP | 30965801 | `f9e2783feeae6848962dc0489349cc1fd64da759dcf093becc4e10c4bd3ff37c` |
| Image | 41490944 | `4873dc3ac17d9d5fc5da21a969ba48e6b71f122742db08ae3fbfc54442813082` |
| Ready declaration | 5289 | `5652bfd60bcc0484b808cf666bec480cf02b79651e41f78ee0f6c98c30ce52ec` |
| Candidate static receipt | 43952 | `c02d942591edc3deadf67825ae3216360c4502976aed806edd707f7605b6ea62` |
| Executability prerequisite | 2400987 | `40eaaf46a7dbb2293cf647a3962f71e528dd2a9bfce207ebecc5e6d455bc0d8a` |

The fresh run ID is `c351f1e0a90b5e6d7c8a9b0c1d2e3f0b`. Its last byte was
selected before packaging to preserve the existing IKCONFIG compressed length;
the exact Image transform verifies that only the declared identity changes.
The builder result digest is
`d3828fd5c4b5b3e99dc3cdb281ec646c7cd60b0d582f00da3c5e6434240f7743`.

## Executability prerequisites

The previous symbol-only graph did not establish that the needed DT devices
would be created and bound. The new extractor separately evaluates kernel
fw_devlink suppliers, device creators and driver-consumed relationships. All
eleven stock overlays applied to both applicable pinned vendor DT bases pass:
22 merged trees, each with 54 required nodes. Unknown creators or module
mappings reject; a module's insertion success is not treated as probe success.

The closure includes primary and secondary DSI controller/PHY references,
SDE's required components, SMMU/TBU creation, writeback, indexed RSC RPMh,
BCM voters and command DB. The secondary has no selected panel; its required
resource/component registration is included without inventing a second panel
power requirement. Five named regulator consumers map to S2DOS05, including the
later panel-elvss path; the four initial power names form the readiness witness.

The GPIO-I2C input must retain the root `i2c@50` name with no `reg`, pins 20/21,
index 50 and its sole S2DOS05 child at address `0x60`. Reviewed ADC/OCL properties
remain exact. The generic GPIO-I2C module is never substituted. DP exclusion is
checked against both owned headers, vendor configuration and compiler flags.
Analyzed source bytes and DT tools are hash-bound and rechecked for changes.
The existing 85-module provider/CRC assessment is separately pinned.

Independent review initially found the incomplete DP configuration check,
missing no-`reg` naming check, source-byte receipt race and missing DT tool pins.
All four were corrected before final extraction. Review then returned PASS_GO
for the prerequisite and, after actual packaging/promotion evidence, for the
complete P351 capability. Fifteen named reviewed source hashes are recorded
privately; the candidate's 53 build source identities were independently checked.

## Runtime behavior designed and tested on the host

The child inserts each of the twelve exact modules once. It then waits at most
15 seconds, with 200-ms intervals, for the exact bus/PMIC driver links, four
unique cached regulator names and primary DRM `226:0`. Every snapshot starts
empty, and success requires a second fresh complete snapshot. Optional MDP/DSI
driver links are diagnostic fields, not additional success gates.

Only failure during that post-insertion readiness phase arms one non-clearing
`SYSLOG_ACTION_READ_ALL` attempt of at most 32768 bytes. The current readiness
snapshot and bounded log tail go through the existing private framed capture.
A read failure is not retried. This cannot prove absence of earlier errors.
Insertion failures and later DRM failures do not invoke that diagnostic.

After DRM open/master and the existing UID/GID 65534/no-capability transition,
the renderer paints a white background, large counter, green block and run ID.
It retains ten matching flip completions, buffer reuse only after completion,
and completed disable before normal cleanup. The observer requires the exact
ordered insertion/readiness/frame output; kernel-log text cannot supply a
success witness. The parent retains the 60-second child and physical-recovery
responsibility; process termination is not recovery from a wedged kernel call.

## Validation

- 21 focused tests passed: actual readiness C and generated white-renderer
  fake-DRM cases, typed readiness/output negatives, real authenticated wire
  parsing/durable reopening, and DT/provider/configuration mutations.
- Common typed-evidence tests: 29 passed. Common F1 live-path fixtures: 74 passed.
  The predecessor P350 real-wire reopening tests also passed (2).
- The full current-tree raw-first audit passed. Targeted P351 rule/template
  mutations and the retained P350 failure-audit rule were checked separately.
  The broader historical mutation suite was interrupted for proportional scope
  after passing tests; it is not reported as a complete suite pass.
- AArch64 static renderer A/B compilation and C harness cross-compilation
  passed; `file` confirmed AArch64 ELF. Touched Python compilation passed.
- Final AP-to-boot join, entire ramdisk inventory, exact modules, generated
  source/plan reopening, prerequisite pins and real promotion verification passed.
- Repository-boundary, document-link and staged diff checks passed.

## Remaining live evidence

Actual P351 provider binding, DRM completion, visible panel output, rollback and
final health are **UNPROVED**. The last verified device health remains the P350
closed rollback result; no fresh health observation was taken during this H0 unit.
The [P351 target clause](../operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md)
requires fresh connected preparation and the ordinary returned attended F1
approval. The operator must be available for host authentication, visible-screen
observation and physical Download recovery. This H0 unit adds no F1 ledger row.

Private evidence is under `workspace/private/outputs/s22plus_fyg8_p351/`:
`stock-candidate-build-v1-20260906-01/`, the static/promotion outputs and
`h0-work/` prerequisites, test logs, raw-first receipt and independent review
record. The public [ready declaration](../../workspace/public/src/device-action/manifests/s22plus_fyg8_p351_process_v2_ready_1.json)
is preparation metadata only and grants no live authority.

## First connected preparation stop

After the operator requested the next preparation step, the fixed read-only D0
ran once in `p351-ready1-prepared-20260906-1`. Initial Android boot completion,
root and exact boot/supporting hashes passed. Its immutable observer capture
is `2097136B/909ef99f3b8bdaba9765d435d1ac296a6c799e556fa9d833f5ae9d03f336a682`
and contains one retained P350 binary run ID. The actual baseline decoder rejects
that evidence family; it is not a clean P351 baseline.

The runner preserved `STOP_DEVICE_ACTION_D0_V2_BASELINE_REJECTED`. This result
is not reusable and does not establish final health/target continuity. There is
no `prepared.json` or F1 approval token. No reboot, Download request or transfer
occurred. A90/S20+ received no command. An attended ordinary reboot needs its
separate fresh D1 approval before a new D0 attempt; the failed invocation and
its capture remain unchanged. The H0 candidate and ready declaration are unchanged.

## Approved D1 and successful fresh preparation

The operator explicitly approved D0/D1 through F1-code issuance. A fresh fixed
P351 invocation reused the unchanged reviewed P296/P320 ordinary-reboot engine;
its H0 self-test passed before one reboot. The durable result confirms changed
boot ID, exact rooted FYG8 return, original boot/supporting hashes, absent Odin
endpoint and no other-target commands. Linked D1 result:
`2963B/e152cb16952dc7601ee9ea3fc126baf6c7ce0def2e0252f4b69764989e74c257`.
The old baseline stop, predecessor journals and candidates were not changed.

New preparation `p351-ready1-prepared-20260906-2` passed
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. Actual `load_prepared` reopening
verified the final stored target/boot/artifact/source binding. An exact F1 code
was issued for approval-binding digest prefix `e47d8d4b`; the token is private.
Candidate AP remains `30965801B/f9e2783f`, with exact rollback AP `d2373bf8`.
No F1 execution, Download request or candidate/rollback transfer occurred.
The user must return the binding-specific F1 code before execution. Their D0/D1
approval does not authorize F1. Actual P351 display output remains UNPROVED.

## Approved F1 result and recovery

The operator returned the exact prepared F1 approval. Candidate AP
`30965801B/f9e2783f` transferred once, and the first read-only USB session passed.
The authenticated second session completed its framed exchange, but the display
command exited 1 at 200 ms. Its 774-byte output records all twelve successful
module insertions and this fresh readiness snapshot:

```text
DISPLAY_READY ready=1 complete=1 bus=1 pmic=1 rails=15 drm=1 mdp=1 dsi=1 elapsed_ms=2 scans=2
DISPLAY_FAIL stage=driver-name errno=71
```

No frame was submitted. Qualification is 1/3, not a display PASS. The operator
reported no normal-boot response during the candidate phase and did not confirm
the intended counter display. Actual visible output remains UNPROVED.

The runner stopped with `measured USB endpoint evidence failed` while awaiting
physical Download for rollback. The error preceded any rollback transfer;
its cause remains unproved. One ordinary `--recover` invocation used the same
journal and preauthorized rollback after physical Download entry. It transferred
exact Magisk AP `23367721B/d2373bf8` once and verified completed Android, root,
original boot/supporting hashes and absent Download. No candidate, observation,
or rollback was replayed. A90/S20+ received no command.

Terminal result is `21490B/65cb93d962bbf467d9b41582928644c0be0a1b09151a8ed3020790218ecbd3f2`:
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, CLOSED/19, recovery_required=false.
Actual `load_prepared` and `validate_live_result` passed. The immutable capture
was reopened and the failed authenticated second session was independently
parsed through the actual P351 codec; exit 1, 200-ms duration and fixed output
above agree. Observer receipt is `13953B/9afa0bee`; raw capture is
`1898B/9a1949fe`. The canonical ledger received exactly one matching F1 close row. The new
row passed the existing row parser and terminal-attempt classification, with
all previous ledger bytes unchanged. The broader taxonomy audit reports the
same pre-existing pending-review ordinal error on both HEAD's ledger and the
appended ledger; it is not claimed as PASS and no historical row was edited.

### Source-derived driver-name diagnosis

The consumed renderer calls DRM version and requires name `msm`. The bound
vendor `msm_drv.c` declares its DRM driver's name as `msm_drm`, and the kernel's
`drm_version` returns that descriptor name. The original fake-DRM fixture also
returned `msm`, so it failed to expose this mismatch before the live run.
A private source-informed fixture using the hash-checked vendor name reproduces
`driver-name`/errno 71 before any frame. The candidate did not log the returned
string itself; distinguish this source-derived diagnosis from the observed guard
failure. No production source or consumed artifact was changed by the diagnosis.

Private closure evidence is `h0-work/closed-result-audit.json` and
`driver-name-reproduction.json`, alongside the original execute/recover logs.
The next working change belongs to a fresh successor and must qualify the exact
vendor name with an independently grounded fixture. P351 remains non-replayable.

### Canonical timeline

| Event | UTC |
| --- | --- |
| `live_session_start` | `2026-09-06T14:11:28.722275Z` |
| `candidate_flash_start` | `2026-09-06T14:11:45.654151Z` |
| `candidate_flash_done` | `2026-09-06T14:11:47.320598Z` |
| `candidate_boot_ready` | `2026-09-06T14:12:13.250500Z` |
| `rollback_flash_start` | `2026-09-06T14:15:12.920521Z` |
| `rollback_flash_done` | `2026-09-06T14:15:14.483674Z` |
| `rollback_boot_ready` | `2026-09-06T14:16:12.284761Z` |
| `live_session_end` | `2026-09-06T14:16:12.304737Z` |
