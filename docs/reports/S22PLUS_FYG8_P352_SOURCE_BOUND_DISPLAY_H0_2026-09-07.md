# P352 source-bound display successor — H0

P351 remains CLOSED/19, consumed and NO_PROOF with verified rollback. This unit
prepares a fresh P352 candidate; it does not repeat a device effect or grant
connected authority. A90 and S20+ receive no command.

## Problem and change

The consumed renderer expected `msm`, whereas the bound vendor `msm_driver`
declares `msm_drm`. Its original fake DRM repeated the incorrect expectation.
The actual P351 name was not recorded, so the source-informed reproduction is
strong causal evidence, not a retained live name read.

A second H0 defect was found behind that guard: selecting a unique lowest
refresh rate rejects the source-generated 30Hz HS/PHS pair if both survive
runtime filtering. Their vertical front/back porches differ by one line, so
DRM timing comparison does not deduplicate them. Merely fixing the name is
insufficient against that nominal producer input.

P352 derives the exact `1080x2340x30xcmdHS` tuple from the selected panel DT and
vendor conversion. It requires one exact returned match and retains its type
metadata. Missing, duplicate or altered timing fails closed; no alternate mode
or retry is added. The full tuple is in
`workspace/public/src/scripts/analysis/s22plus_fyg8_display_kms_contract_h0.py`.
The generated renderer continues to use the unchanged P351 readiness/provider
path, white counter layout, two WC buffers, matched flip events and completed
disable. Consumed P350/P351 source templates are byte-preserved.

Failure output now adds bounded cached context only: ioctl/stage, requested
property, object counts/selection, at most 31 driver-name bytes as hex and
sixteen complete mode summaries with bounded hex names. It adds no device read,
new log collection or success witness. The readiness-only kernel-log exception
retains its original scope.

## Source audit and remaining uncertainty

Source-informed fixture inputs are sealed in
`tests/fixtures/s22plus-display-kms-source-v3.json`. The mode extractor checks
the exact stock inputs, merge-tool identities, all applicable merged-DT digests
against the retained P351 prerequisite receipt, and source/tool/producer bytes
again at completion. Checked merge bytes are privately cached for reuse.

The fixture models nominal generated modes, not the actual panel/controller/PHY
filter result. It covers the full nominal set, a filtered subset containing the
selected mode, preferred metadata, absent/duplicate/changed modes and malformed
names. The original renderer fails at name validation and the name-only repair
fails at mode selection against the source-derived producer. These are distinct
regressions. Actual runtime mode acceptance and visible output remain UNPROVED.

The bounded source audit also checked:

- GEM_NEW authentication, descriptor DRM master and post-drop ioctl permissions;
- linear XRGB8888 with a 4352-byte pitch, GEM mapping and framebuffer offsets;
- primary-plane default z-order/alpha/blending and property reset;
- atomic event CRTC ID and user-data production;
- connector backlight enable path and Samsung default-brightness parser.

No further definite source mismatch was found in those checks. Initial splash
state, successful TEST_ONLY/commit/disable, actual panel light and hardware
behavior remain live unknowns. Competing scanout is still refused. A blocked
kernel modeset still needs attended physical recovery; process termination is
not demonstrated recovery.

## Separate USB diagnostic assessment

P351's retained failure is consistent with an endpoint disappearing between
inventory snapshots, but its exact cause is UNPROVED. The original diagnostic
flattened `UsbfsEndpointDeparture` into generic `UsbfsIdentityError`. Direct
stat failure details were not retained. Later recovery captures share the
sequence's raw directory, so file timestamps must separate those acquisitions;
the later successful snapshot must not be attributed to the failed attempt.

The shared consumer now records the allowlisted `usbfs-endpoint-departed` kind
without a path or exception text. It still throws the same fatal measured
evidence failure. No retry, departure resnapshot, identity relaxation or
transfer behavior changes. A real host fixture injects stat ENOENT during the
second inventory through the existing producer/consumer and verifies one
enumeration, one diagnostic, no snapshot or transaction publication.

Independent review returned PASS_GO for this diagnostic capability. P351's
same-journal rollback establishes that run's successful attended recovery; it
does not prove unattended recovery or the successor's current binding.

## Validation and preparation status

The final source-derived receipt covers 22 applicable DT merges with the same
thirteen nominal modes. It is `125474B/05a2a739`; all merged hashes match the
retained prerequisite result. Early H0 tuple/serialization issues were repaired
before candidate construction; the final receipt includes unchanged-input
checks and is reopened by its exact pin without recomputing unchanged merges.

The fresh A/B build passed with 62 source inputs exactly matching the printed
pre-build closure. Renderer `710184B/7b66c7a0` is a statically linked ARM
AArch64 ELF. Candidate AP is `30965801B/6cda084d`; the reused Image has only the
fresh identity transform (`41490944B/f701f4d9`). Both APs decompress to the
audited boot bytes, and the complete ramdisk inventory and twelve display
assets match. The 73-module USB plan remains byte-identical.

Static qualification is `46079B/23950e0b`,
`PASS_P352_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY`. The common offline promotion
rehearsal passed with `device_contact=false`, `odin_invoked=false` and no run
directory or lease. Independent capability review returned PASS_GO after
reopening the actual build and checking 90 execution-critical current inputs;
review receipt is `23044B/d8fabc85`, with no open findings. Its scope is the
changed capability and source joins, not a live result or execution approval.

The fresh `s22plus_fyg8_p352_process_v2_ready_1.json` manifest was published
host-only (`5289B/6d0de2b5`). Actual common bundle reopening passed with digest
`1cfe9d7aa4cfa74cf451cbec171591ec0f53c4e1df9d79eef83d046e1a85cf28`.
This is offline preparation only, not a connected `prepared.json` or F1 token.

Validation completed:

- Three generated-C renderer tests, covering both predecessor regressions,
  full/filtered/preferred mode success and seventeen failure cases. Actual C
  success output matches the observer's expected frame/completion bytes.
- Eleven fresh-identity observation/wire/reopening tests.
- 103 common F1 evidence/live host tests.
- 74 USB transition-core and 37 USB identity tests.
- Forty complete raw-first observer regression tests passed in 1,310.880 seconds.
- Raw-first boundary audit PASS, Python compilation, AArch64 compilation and
  ELF inspection, repository boundary check and diff checks.

The raw-first registry adds only P352's separately typed sources and the
reviewed USB diagnostic identity. The only changed existing census member is
`device_action_f1_evidence_v2.py`; census counts are unchanged. Prior identities
and the original failure records remain preserved.

Private working evidence is under
`workspace/private/outputs/s22plus_fyg8_p352/h0-work/`.
No connected preparation or new candidate/rollback transfer occurred in that
H0 unit. The subsequent authorized preparation is recorded below.

## Approved D0/D1 and F1-code issuance

On 2026-09-07 the operator explicitly approved D0/D1 through code issuance and
confirmed physical attendance. The first preparation stopped at the bounded
baseline classifier: its complete retained capture contains one P351 binary
run ID and one long family. The immutable typed stop was reopened successfully,
is non-reusable and records no reboot, Download request or partition transfer.
Stop receipt SHA-256:
`c961b134b608ae02c677126a0eaf3ed6164115bb5f9756c44d92ef57ca2d34cc`.

One fresh private invocation reused the unchanged reviewed P296/P320 ordinary
reboot engine after its H0 self-test. It passed with one reboot, changed boot
ID, healthy rooted FYG8, original boot/supporting hashes, absent Odin endpoint
and no other-target command. Linked result is `2963B/7bf81204`; the primitive's
durable result remains intact. No candidate or observation was replayed.

Fresh preparation `p352-ready1-prepared-20260907-2` then passed
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY` (`3261B/300af461`). Actual
`load_prepared` reopening passed for the stored target, boot, artifacts and
execution closure. The prepared receipt is `30684B/b6a739e8`; its F1 binding
digest prefix is `b72c7fb8`. The binding-specific token is issued to the operator
and is not published here.

Candidate AP remains `30965801B/6cda084d`, exact rollback `23367721B/d2373bf8`.
F1 is not authorized or executed until the operator returns the exact token.
No Download request or candidate/rollback transfer occurred. A90 and S20+
received no command. Visible output remains UNPROVED.
