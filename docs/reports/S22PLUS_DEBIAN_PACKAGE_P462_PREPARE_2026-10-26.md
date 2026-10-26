# S22+ P462 offline Debian package preparation

State: **PASS_READY_H0_AND_UNEXECUTED_ENTRY**, with independent capability
**PASS_GO**. This report covers H0 implementation and concrete preparation
for S22+ FYG8 only. No P462 task grant or image transfer has occurred.
A90, S20+ and their existing changes remain untouched.

## Bounded capability

P462 retains P461's two Debian boots, four admitted native_data writable
lifetimes, cron configuration lifecycle, ordinary first reboot and final
Download/original-A return. It adds one fixed installation of the already
embedded Debian `hello` 2.10-5 arm64 package. The second boot verifies and
executes it without installing again. The package remains installed on success.

The [package specialization](../operations/S22PLUS_DEBIAN_PACKAGE_V1.md)
pins the archive and package-manager programs. The package has no maintainer
scripts, conffiles or triggers, and its dependency is already installed.
There is no download, apt operation, dependency installation or upgrade.

Two independent ARM64 dpkg measurements produced the same successful state:
49 payload files, one documentation directory, two dpkg info files and
replacements of the existing status/status-old files. Every other package
paragraph is unchanged; status-old equals the original status. The source
declaration seals these 54 exact final rows. Protected admission continues
to reject every undeclared, missing, changed or linked entry.

Before the installation intent, the original database must match, new paths
must be absent and dpkg audit must succeed with empty output. The fixed
installer has a 30-second budget within the original boot deadline. Completion
requires settled child work, empty audit/verify output, exact post-state,
absence of transaction remnants, successful hello output, synchronization
and re-verification. Authenticated completion gates the ordinary reboot.
Second-boot admission joins that first runtime chain to the exact installed
state; it does not learn a new accepted state from the live filesystem.

The pinned dpkg transaction includes its ordinary temporary-file and journal
writes. A failed or uncertain installation can leave partial native_data
state. Original-A restoration does not undo it. The parent never retries,
repairs, removes or cleans up the package after uncertainty; the existing
attended physical recovery remains necessary for a failed native boot.

## Android readiness correction

The previous P461 run completed automatic Download and original-A transfer,
then stopped on one fixed Android readiness read reporting that the exact
target was temporarily absent. Its health-only continuation closed healthy.
The shared readiness observer now recognizes only that exact bounded failure
as not ready and repeats the existing inventory/read sequence within its
original deadline. Unexpected diagnostics, changed targets, malformed raw
evidence and source-guard failures still reject. Controls and transfers are
not retried. A late read cannot create a successful readiness result.

## Qualification to date

- The existing reviewed fixed D0 measured clean native_data M=34 with matching
  Android health before and after. That receipt predates the source changes;
  it neither grants a new operation nor proves the complete current root.
- Two actual ARM64 dpkg measurements agree on the exact successful filesystem
  effects. Retained signed Debian metadata authenticates the embedded package.
- The physical-format A/B build matches and its helpers compile as ARM64.
  The original producer accepts both physical and virtual builds.
- The production VM completes both boots, the real installation and hello
  execution, second-boot verification, exact first-pair retention and clean
  M=34 to M=38. Samsung Download is substituted by VM power-off and remains
  a separate physical proof requirement.
- Twenty-five package/evidence/configuration tests and 67 owner/qualification/
  entry tests pass. The shared readiness implementation has a separate
  independent PASS_GO with its 17 focused tests and actual raw/prelaunch checks.
- All 69 ARM64 cases pass: the normal two-boot path, 49 root cases and 19
  runtime failures. Independent raw rederivation confirms the complete corpus,
  including successful checker admission followed by strict hardlink rejection,
  and failure without completion for unsettled child work or transaction remnants.
- The original package consumer rederives the complete corpus and accepts the
  38,103,081-byte boot-only AP, actual CPIO and retained template. Final
  independent PASS_GO has no findings and binds 160 host and 182 runtime sources.
- Cold original image admission passes from an unrelated directory in a fresh
  Python process, without a preloaded builder path and with file writes,
  process/network effects and raw acquisition denied during validation.
- Both phase constructors, the original eight-step sequence and rejection of
  nonexecutable constructor data as a grant pass. The independent prepared-entry
  check accepts actual persisted `Controller.bundle(current=True, approval=False)`
  and rejects all nine missing/altered approval fixtures in memory.
- The separate bridge review binds 20 current sources and two unchanged resident
  inputs. The original consumer and connected worker accept v8. Actual task
  status shows no approval, grant or dispatch, including all continuation paths.
- Repository boundary, document links and scoped diff checks pass. Existing
  unrelated changes remain separate from this preparation.

Private evidence is retained under
`workspace/private/outputs/s22plus-debian-package-p462-h0-20261026-1/`, including
the first VM's host-selection failure, original raw outputs and source snapshots.
The second corpus stopped on an invalid link-count fixture: e2fsck rejected
the inconsistent inode before mounting, so the intended tree check was not
exercised. The corrected fixture creates a real hardlink. Its third build again
passes both normal boots; the original independent root/runtime branches run
in parallel with their unchanged per-case bounds and consumers.
Prior P461 artifacts, approval, consumption and closure remain unchanged.

## Execution boundary

The intended operation remains one attended `debian-autoboot` operation within
3600 seconds: one N transfer, two Debian boots, one ordinary reboot, one final
Download request and one original-A return with Android health. The exact task
is `9065a476db83c9d3e786165ecf3b81cf24d187951cf3f228b5966e4643f595b3`.
Its source snapshots, capability bindings and entry checks pass. The remaining
execution prerequisite is the fresh finite attended grant and current physical
Download recovery availability. No operator approval record, grant or entry
attempt exists at this preparation boundary. H0 success is not physical package
persistence or automatic recovery from an unresponsive experimental component.
