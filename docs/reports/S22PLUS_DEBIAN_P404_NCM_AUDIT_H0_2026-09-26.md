# S22+ P404 NCM observation audit — 2026-09-26

## Result and smallest repair

**A host endpoint-selection false negative is reproduced and repaired H0. The
actual cause of P404's missing NCM observation remains unproved.** No device
command, new image, grant, activation or replay occurred. P404's consumed
`NO_PROOF_ANDROID_CLOSED_HEALTHY` result and retained artifacts are unchanged.

The shared `s22plus_debian_first_boot_v1.py::Owner.usb_link` first checks the
Android USB topology and then the separate allowed native topology. Previously,
when the first path was absent, `resolve(strict=True)` raised
`FileNotFoundError` into the exception handler for the entire network
interface. The second path was never checked, even when a matching NCM
interface and all expected descriptors existed there. P404 inherits this
method. Absence of the Android path can therefore make a valid Debian endpoint
invisible throughout the fixed wait.

The repair catches absence around that individual path resolution and advances
to the other existing allowed path. It changes no topology allowlist, MAC,
descriptor, ancestry, uniqueness, SSH identity, deadline or effect rule.
Malformed/non-absence errors still reject; an absent descriptor or disappearing
interface still cannot become a successful endpoint.

The exact function extracted from the immutable P404 source snapshot fails the
new temporary-filesystem cases, including the candidate-only endpoint for both
owners. The fixed function passes all 10 cases. The fixtures redirect only the
two sysfs roots; actual filesystem reads, symlinks, strict path resolution and
the existing bounded descriptor reader perform the selection. They do not read
the host's real sysfs or interact with a device.

## Retained image and service audit

The audit verifies the consumed AP, boot, init, shutdown overlay, original P401
root archive and all 62 saved execution-source files against their receipts.
The actual P404 boot image contains all 81 declared module bodies with their
expected sizes/digests and the retained root metadata/content manifests.

The kernel extracted from that image has SHA-256
`d510a3f83a6d48392649df325223e9847f85e2ee35989f32db0fb6abff371a3d`.
Its embedded config has SHA-256
`39fa29708f124e3fa7deee49caf433cbbfd182dbb1ff13890f525de8854f15a7`.
`CONFIG_CONFIGFS_FS`, `CONFIG_USB_CONFIGFS`, `CONFIG_USB_CONFIGFS_NCM`,
`CONFIG_USB_F_NCM` and `CONFIG_USB_U_ETHER` are all built in. A missing NCM
module is therefore not supported by these bytes. This static check does not
establish that the module loop, controller initialization or USB binding ran.

The installed archive's `lab-usb` matches the reviewed script. Its private
link identity matches the consumed host plan. Serial SysV ordering is enabled:
rcS `S07mount-configfs` precedes runlevel 2 `S02lab-usb`, which sorts before
`S02ssh`. `S03mdev` supplies device management; the retained udev startup script
rejects this kernel's absent devtmpfs support, while the serial rc driver does
not use that service's failure as a global stop. These are service-graph facts,
not proof that physical Debian init reached those services.

The physical script checks for the fixed UDC, configures NCM, writes the
peripheral role, binds the UDC and brings up `usb0`. The ARM64 VM substitutes
`eth0` configuration for this whole script and bypasses physical module loads.
Its successful PID 1/SSH test consequently does not validate that physical
path. The physical script also lacks the retained native path's bounded
role/UDC settling and explicit high-speed configuration. Those differences
remain observations, not established P404 failures or grounds for speculative
guest changes in this unit.

## Evidence limit and prospective observation

The consumed `network-first` directory is empty. The old observer published an
endpoint only after every filter passed and did not retain unsuccessful USB
or interface observations. Neither the timeout nor the repaired selector proves
that P404 actually enumerated, reached SysVinit, or mounted its root. Its RAM
bootstrap log was unavailable through this transport and was not recovered.
The [first-run result](S22PLUS_DEBIAN_INSTALLED_BOOT_P404_FIRST_RUN_2026-09-23.md)
retains its original meaning.

For a fresh successor, the smallest useful additional host observation is a
bounded private record of the two already-bound USB paths and their network
interfaces during the existing 180-second wait. It should distinguish absent
USB, present USB without a network interface, identity mismatch, disappeared
entry and fully matching endpoint. Use the existing 512-byte descriptor limit,
fixed path scope, finite sample/output budget and raw-before-classification
capture; preserve the endpoint acceptance predicate. A host-side record alone
still cannot distinguish an early bootstrap stop from a later USB failure when
no USB evidence arrives. No independent early-boot witness or automatic
recovery is claimed or introduced here.

The next bounded unit is H0 preparation of a fresh installed-root successor
and that narrow observation addition, with current source/artifact review and
root-health requirements. The old P404 candidate and grant remain consumed.
The current changed runner no longer matches the historic live review pin;
this patch review neither replaces that binding nor activates a new run.

## Validation and provenance

- The 10 new selector cases pass, covering both owners, each allowed topology,
  absent/unrelated paths, MAC mismatch, descriptor rejection, disappearing
  interfaces and ambiguity.
- All 38 existing first-boot/installed-boot owner tests pass; touched Python
  compiles. No C or firmware bytes changed, so no image build was needed.
- An independent reviewer returned **PASS_GO for this H0 patch**, with no
  findings. It also passed 12 supplementary cases across both owners for
  NUL/newline/CR/non-ASCII descriptors, symlink loops and duplicate interfaces.
  This is changed-machinery review, not live activation or a P404 cause claim.
- Scoped diff, local document links and repository-boundary checks pass.

Reviewed changed-file SHA-256 identities:

| File | SHA-256 |
| --- | --- |
| `s22plus_debian_first_boot_v1.py` | `71cc712fbe430b9d559bc54f5c69dc2f22f8fb4a6e092bda6b558ff6ef0eaa79` |
| `test_s22plus_debian_usb_link_v1.py` | `943a229a18d1130e867dc12538ac311c0c667679fd42e72f2324b1990eae27e7` |

Private evidence is under
`workspace/private/outputs/s22plus-debian-p404-audit-h0-20260926-1/`:
the reproducible `audit.py`, `audit.json`, retained/fixed selector outputs and
independent review receipt. `audit.json` SHA-256 is
`7241ad0caeb7230ff94119797446320767a29c7bd35bfe1ab528014bdda8865e`.
Private identifiers and original run evidence remain private. A90/S20+ and
their unrelated work were not changed.
