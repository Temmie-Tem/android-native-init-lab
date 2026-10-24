# P458 production two-boot integration

Status: **PASS_H0_PRODUCTION_INTEGRATION**. This report covers the operator-selected
[production integration](S22PLUS_DEBIAN_REBOOT_P458_INTEGRATION_DESIGN_H0_2026-10-25.md),
following the separate [feasibility prototype](S22PLUS_DEBIAN_REBOOT_P458_H0_2026-10-24.md).
No device, ADB, server or external-provider call belongs to this work. A90 and
S20+ remain untouched. H0 artifacts and independent review are capability
qualification, not a physical baseline, attended grant or demonstrated recovery.

## Resulting production path

The selected `p458` specialization uses the actual automatic Debian package,
protected root checker, supervised early writer, installed SysV init/hooks,
SSH evidence parser and V3 owner. It retains one N transfer and one original-A
return, with first health, one ordinary reboot, second health and one final
shutdown in the same operation. Both health windows require their own local
service and pinned SSH 120-second proof. The second window starts at the original
durable reboot intent; neither reconnect nor result reconstruction extends it.
The approved synchronous and persistent connector continuations use that same
selected step sequence. Uncertain controls and transfers never replay.

The new [policy](../operations/S22PLUS_DEBIAN_REBOOT_V1.md) is incorporated by the
common details and exact target contract. It specializes the prior two writable
lifetimes to four across two boots. Each boot retains both complete protected
root admissions. Candidate data seals the pre-build ext4 mount count M; M,
M+1, M+2, M+3 and M+4 are checked at their exact boundaries, without resetting
or inferring a baseline from missing files. Four current paths authenticate
phase, source, run, boot and count. Second-boot admission requires the exact
first pair with completed services and a terminal reboot intent. A third startup
or a clean error-unmount cannot renew consumption.

The fixed pre-build D0 reader validates the existing GPT and Android32 statfs
before its additional 4096-byte native_data read, retains raw evidence, and
attempts final Android health even if the read fails. No automatic retry,
filesystem mount, node creation, partition flag change or device write is added.
Synthetic H0 baselines are explicitly labelled; the actual physical image
consumer rejects them. A future physical candidate needs a fresh reviewed D0
receipt, a build/qualification using that receipt, and its finite attended grant.

P456's exact pair from closed clean P457 becomes immutable history. The optional
old `shutdown-start` rule is derived from the sealed producer and raw authenticated
SSH boot, not a retrieved P457 file: absence is allowed; presence requires the
exact 37 bytes and restrictive metadata. Only dmesg.0 and dmesg.1.gz through
.4.gz join the finite rotation rules. The existing boot-count ceiling remains
100000, reserving two increments. No arbitrary file/history wildcard is added.

## Validation and limits

The final frozen build and full production ARM64 corpus passed all **25 cases**:
one actual two-boot lifecycle, two actual post-mount/pre-file error controls,
and twenty-two targeted admission, receipt and consumption failures. The normal
run starts at boot-count 99998, observes 99999 and 100000, and includes the exact
optional shutdown marker and all five permitted rotation names. Each boot has
local service proof and pinned SSH intervals of 120720 and 122290 ms. One actual
QEMU kernel restart and final poweroff, four complete protected admissions,
clean M=0 to M+4 and four exact final on-disk records are verified. The independent
reviewer reopened all 125 command captures and independently checked allocated
bytes outside native_data against the exact initial GPT/zero layout.

The counted error controls complete real RW setups, fail before file creation,
then cleanly unmount at M+1 and M+3. The M+1 disk rejects the identical fault
image on retry before another mount. The second-root control first proves that
the reconstructed phase-two fixture is admissible. Its corrupt/missing/incomplete
prior-pair and existing-second-file variants then reject in the protected root
consumer. Wrong initial count and the consumed M+4 root reject before mount;
dirty state remains a completed read-only observation with no writable admission.
Rotation size uses real allocated data and the link case a valid hardlink pair.

**121 unique focused tests** pass: the 120-test combined run plus the current
eight-test owner run replacing its earlier seven-test version. This covers
baseline ordering and post-failure health, fixed host windows, no control replay,
result-publication loss, both connector continuations and exact temporary network
ownership. Thirty-one mutations of actual wire evidence reject. The production
terminal serializer also saves/reopens actual two-boot payloads (40176 bytes)
and a late-failure payload (16278 bytes), with fixture ownership labelled.
Touched Python compiles; both new and retained single-boot C branches cross-compile
for ARM64 and their binaries are inspected.

The actual **38021161-byte boot-only AP** passes archive/payload qualification.
A/B construction is identical, with eighty-two selected modules and fifteen
declared member substitutions; all other template metadata/bodies remain exact.
The new strict consumer reopens the full corpus and raw captures. The output is
`h0-synthetic-package.json`, explicitly `H0_SYNTHETIC`, with no `image.json`.
The real physical image consumer rejects its extracted image shape with
`synthetic baseline cannot qualify device use`.

These are production runtime/consumer results with explicit Samsung platform,
watchdog and USB/network substitutions. They do not demonstrate a physical
reboot, the physical V3/NCM owner, hardware pet, unattended recovery or physical
filesystem persistence. The task opens no F1 grant or live device owner. A future
physical candidate still needs the reviewed D0 baseline, fresh qualification,
exact current target/health/recovery binding and an attended finite grant.

Private final evidence is under
`workspace/private/outputs/s22plus-debian-reboot-integration-p458-h0-20261025-1/`:
`build-final-4`, `vm-final-4/result.json`, `package-final-4`,
`physical-admission-guard.json`, `focused-validation-commands.json` and
`terminal-persist-result.json`. Original failed builds and raw output remain
preserved. No consumed historical artifact, approval or evidence pin was repointed.
The capability review binds the current reviewed workspace; pre-existing
other-target changes are preserved and excluded from this scoped commit.
Independent final review is **PASS_GO**, with no open findings, bound to 148
reachable host/policy sources and 168 runtime sources. The exact approved
[capability binding](../../workspace/public/src/device-action/bindings/s22plus_debian_autoboot_p458_review.json)
passes the original capability consumer. The private independent review is
`review/final-1/independent-review.json`; its SHA-256 is
`a7d25530f7df93ed29a355bc04aabf32672005c2c1fd6737aed3fcdcf072f303`.
The review qualifies the reusable machinery only; it supplies no physical
baseline, live grant, attendance, device health or recovery proof.

## Findings repaired during H0

- The initial namespace build could not use the multiple-UID map under the
  current NoNewPrivs environment. The reboot variant now reuses the exact sealed
  P456 archive and replaces only fifteen declared payload/script members,
  preserving all other metadata and bodies. The consumer rederives every member.
  It also retains the original leading root CPIO record. No permission bypass
  or package installation is used.
- The first baseline implementation validated GPT/stat after the block read and
  lacked a physical consumer guard against synthetic data. Validation now occurs
  before dispatch; physical image admission expressly requires a D0 receipt.
- Second-boot health now checks the boot-count increment before final control.
  NetworkManager rebind uses `--temporary`, verifies the owned UUID/name/MAC and
  old interface first, and permits cleanup only of its exact old/new interfaces.
- The old P456 shutdown script exposed an optional persistent output not present
  in P457's two-file retrieval. The restrictive producer-derived rule above
  records the distinction without claiming prior persistence or metadata.

The first final boundary fixture used a decimal debugfs mode argument and
ignored a nonfatal stderr diagnostic. The real root checker rejected its wrong
metadata before writes. The fixture now uses octal modes and rejects unexpected
debugfs diagnostics even at exit zero. Independent review also required the
reconstructed second-root fixture to restore the authenticated first boot count
and pass a positive admission control before testing prior-record corruption.
Dirty-root observation completion is interpreted separately from root admission;
the unchanged-disk, protected cleanup and explicit clean-only stop remain required.

## Past-failure checklist reconciliation

| ID | Applied evidence and limit |
| --- | --- |
| ABI | Production C cross-compiles for ARM64; actual kernel ext4 RW setup, clean unmount, mount counter and error cleanup are exercised. No new raw block writer or syscall constant is introduced. |
| IO | Separate bounded baseline stream and 450000-byte two-boot SSH envelopes retain stdout/stderr and producer status. Truncation, extra bytes, failed producer and control ACK errors reject. |
| SEMANTIC | Reboot/shutdown acceptance, distinct boot identity, next-root clean admission, local service proof, SSH access, final persistence and Android recovery remain separate claims. |
| WIRE | Actual early-v4/durable-rev7 producers join phase/count/source/run/boot through raw captures and strict consumers. Prior runtime must end in exactly one reboot intent; corrupt or incomplete data cannot admit boot two. |
| PERSIST | Real final snapshots and on-disk records are saved/reopened; durable result-publication loss resumes without retransmitting control. Existing raw failures and consumed provenance remain immutable. |
| ROUTE | Actual builder/package/VM parser and V3 phase-aware factory are exercised. Both connector continuations select all two-boot steps. Synthetic baseline rejection is at physical image admission. |
| ARTIFACT | A/B C output and initramfs equality, exact template member comparison, packaged boot-only archive inspection and runtime/source joins bind the actual artifacts. |
| AUDIT | Faults mutate only regular sparse VM disk fixtures. Reconstructed second-root fixtures are labelled; they are not physical rollback or replay evidence. Optional old marker is a producer expectation, not retrieval proof. |
| HOST | Original NoNewPrivs failure is retained; exact measured template construction is independently checked. Baseline pre-read ordering/final-health failure and foreign/interrupted temporary network ownership are tested. |
| DISPLAY | Not applicable: no display implementation or display proof is selected. |
| RETURN | One N/reboot/shutdown/A sequence, uncertainty and result-publication interruption are tested through the owner. Physical Download/original-A recovery and actual final Android health remain run requirements. |

The table applies the existing eleven IDs; it creates no new generic gate.
