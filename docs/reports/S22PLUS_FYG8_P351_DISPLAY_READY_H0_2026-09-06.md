# S22+ FYG8 P351 display successor — H0 ready

Date: 2026-09-06. Exact target: SM-S906N / g0q / S906NKSS7FYG8.
Result: **H0 candidate, static promotion and independent capability review PASS**.
No connected command, Download request, transfer or live run was performed.
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
