# P419 Debian early USB with mandatory RAM evidence

Date: 2026-10-12 KST. Target: S22+ `SM-S906N/g0q/S906NKSS7FYG8` only.
Status: **PASS_GO; CONNECTED_PREPARATION_PASS; AWAITING_RETURNED_ATTENDED_GRANT**.
No candidate transfer or new grant.

## Bounded change

The operator selected a minimum successor retaining Debian-owned initial PID1
and the already established native platform/USB sequence. P419 `v0.5.0-rc.3`
uses the `ram-only` declaration of the existing
[USB-first profile](../operations/S22PLUS_DEBIAN_USB_FIRST_V1.md), through the
same V3 operation, one-operation attended grant and physical original-A owner.
It does not introduce a new transport, effect graph or general native runtime.

P418 added stock `sec_log_buf` before the retained 73-module platform plan and
required successful printk readback before later module and USB effects. This
candidate removes those added dependencies from both preparation and USB
children. The fixed module directory has exactly the original 73 modules;
module bytes/order/parameters, readiness paths, gadget attributes, tty setup,
role transition and UDC binding remain unchanged. No platform failure is ignored.

Every module attempt/completion still has a checked bounded RAM record. The
complete preparation log and its explicit no-retention completion marker must
authenticate with actual PID1 executable, command line, `/init`, helper and
same-boot identity. Invalid HMAC, missing RAM evidence and incomplete module
preparation still fail. Optional USB printk stage diagnostics are absent.
The success criterion remains real USB enumeration and authenticated Debian
initial-PID1/platform evidence, independent of Android recovery health.

RAM evidence is recovered through the successful USB channel only. This variant
makes no reboot-retention claim and its post-return `last_kmsg` reader is
rejected before connected reads. If USB remains absent, physical return may
lose internal-stage evidence. This deliberate limitation isolates the extra
logging dependency without adding a storage writer. P418's strict decoder stop,
two authenticated partial records and unknown failure location remain unchanged;
neither visible lack of a bootloop nor the last BEGIN record proves completion.

## Qualification and provenance

Private evidence root:
`workspace/private/outputs/s22plus-debian-usb-ram-p419-h0-20261012-1/`.
The retained kernel, vendor ramdisk and Debian packages are reused. No kernel
build is required. ARM64 compilation checks both static executables and excludes
logger/kmsg paths from the RAM-only binaries. Actual A/B initramfs and boot/AP
qualification, five ARM64 VM cases and independent review precede any connected
preparation or returned finite attended grant.

The normal and logger-disabled VM cases must prove authenticated full platform
completion under actual Debian PID1, with no `/dev/kmsg` node. Wrong-HMAC,
insertion-failure and missing-RAM-log cases must reject the corresponding path.
Samsung board identity, module insertion and physical USB are substituted in
the VM; VM results never establish real hardware USB or physical recovery.

Final `build-2` contains exactly 73 declared platform modules and 144 frozen
source rows. Both children are static AArch64 ELF executables, with no linked
`sec_log_buf`, `/dev/kmsg` or `/proc/last_kmsg` path. Two initramfs constructions
are identical. `package-1` constructs identical boot/AP pairs and validates
unchanged retained kernel, boot signature and trailer bytes, with only the
declared ramdisk and derived offsets changed. The carrier's old AVB descriptor
is not a signature for the new ramdisk.

| Artifact | SHA-256 |
| --- | --- |
| A/B initramfs, 7,273,496 bytes | `af6e7bfe61dcc3fbb70d61e3f65a4bcc999868880604cf2c516a51c994d9981b` |
| Boot, 100,663,296 bytes | `03b8e8ad2f235847d4e6f50413f1caa0276a550c0be61115cb8159aec6765373` |
| AP, 34,109,481 bytes | `cb575c0ef326e1f8a7c73dc25aa19524352edd914dd2d94fa3ab4ca9a5d21117` |
| Qualified image record | `1a0335b40ee4371acc7a57e4e00d7d8fca72cccca65c5f1160910c3fd3ef2856` |

All five real ARM64 `vm-2` cases passed against 169 frozen VM-source rows.
Normal and logger-off cases return authenticated complete 73-module evidence;
logger-off also verifies disabled printk and absent kmsg device node. Wrong
HMAC produces no accepted response. Insertion failure and missing RAM log
prevent USB publication. Every sentinel disk is unchanged.

Focused checks passed: USB mode/protocol/scope 11, early protocol/owner 12,
V3 session 21, handoff owner 13, root-inspection scope 11 and repository boundary
12, totaling 80 tests. Eight touched Python files passed compilation, including
rechecking the two qualification joins after review. The repository boundary
script, documentation links and diff checks also passed. A separate H0 audit
rejects copied VM receipts with contradictory or missing RAM-mode declarations,
while accepting the unchanged historical P418 retained-mode binding. All device
command acquisition is blocked during that audit.

The final host-source snapshot has 105 files and manifest SHA-256
`fca72ff7207b74db3d53026d27d84d7ba7c82a0d0f7f48395e934193ed7456b4`.
Independent H0 review passed the mode joins and the scoped policy projection;
final independent capability review returned **PASS_GO**, with no unresolved
findings, after inspecting actual artifact bytes and raw VM transcripts. The
current capability binding is
`workspace/public/src/device-action/bindings/s22plus_debian_usb_first_v1_review.json`,
SHA-256 `61f06957bd3e7eccbf12c93bb853654aa5a5a7c2b0ac1468fdbe73c740eacb22`.
The prior P418 binding is preserved byte-for-byte; its consumed run is unchanged.
An isolated export of the scoped index also passed 57 portable tests. Its
projected common-policy pin matches the projected details; the independent
projection review confirmed that unrelated dirty policy work stays excluded.

Execution-critical source snapshots record the complete working tree over
`2c7d3f7a7002f3b5de61390f28f439a214df4d11`, including inherited uncommitted
dependencies. Scoped publication excludes unrelated work; that commit tree
alone is not a new live qualification. Consumed P418 artifacts, grants, raw
evidence and source snapshots are not repinned or edited.

Build-1 and its partial VM evidence are retained. Independent review suggested
joining each VM receipt's declared logging mode directly to the built mode;
the H0 run was stopped for that correction and fresh final artifacts were built.
There was no device failure or action in this host-only correction.

The first capability publication encountered the old read-only binding; the
initial preparation command consequently rejected that stale binding before
creating a preparation directory or touching a transport. The old bytes were
preserved and the reviewed new current binding was atomically published.

The first connected inventory then returned exit zero with the exact ADB
daemon-startup banner on stderr. Strict raw validation rejected it before any
target-specific health command. The inventory selected the exact target, and
the failed raw capture/stop remains unchanged. The foreground profile's fixed
read-only reobservation rule permits the fresh `connected-2` preparation;
no control, transfer, grant or operation reservation was consumed by that read.

`connected-2` completed the fixed rooted original-A/supporting health bracket,
shell-v2, exact GPT and Android32 capacity checks in one Android boot. H0 audit
rederived the stored preparation and all 17 successful raw captures with device
commands blocked, verified the current review and absent F1 owner, and confirmed
no grant or operation exists. The concrete one-operation task SHA-256 is
`466075ccf001ae92a51a6c33fc37b281c796e53f1e88e5b7693e7baf56fa3563`.
Only its returned finite attended approval and current physical attendance
remain before candidate execution; fresh machine preflight still applies.
No A90/S20+ device was contacted and no device control or candidate transfer
occurred during this preparation. Physical USB/PID1 success remains unproved.
