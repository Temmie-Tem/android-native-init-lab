# A90 H16 to H24 to Isolated-Debian Comparison Baseline

Date: 2026-08-14
Selected target: Samsung Galaxy A90 5G only
Tier: H0 historical comparison and successor-design boundary
Status: documentation baseline; no device or live authority

## Decision

H16 is the first direct-UFS live **mechanical handoff-boundary baseline**. Its exact
same-intent log reached `switch_root_exec` at `CLOCK_BOOTTIME` 11,760 ms. That
fact is important and must be used when assessing every later design.

It is not a complete personal-server PASS. H16 did not prove authenticated
SSH, Debian PID 1, automatic return, DRM/display ownership, final Wi-Fi, or
full server readiness. Its terminal was
`NO_PROOF_H16_PERSISTENT_DEBIAN_PHYSICAL_RETURN_HEALTHY` only after the
operator physically returned and exact native health was re-established.

H24 is the exact installed resident and the latest live UFS attempt. Its build
manifest directly extends `phase3-minimal-h16`, so H16 is also the correct
implementation ancestry baseline. H24 mounted and verified UFS plus the four
writable tmpfs paths, but its consumed D1 stopped at outer `persistent-hud`
`rc=-22 errno=22` before evidence bind, Wi-Fi bind, or `switch_root`.

The selected isolated-Debian successor therefore does not start from a blank
design and does not simply revert to H16. It preserves H16's successful UFS
mechanics and the later safety fixes, removes the gates that are not required
for a headless server, and replaces the unsafe shared-namespace/in-place-root
transition with a native supervisor and an isolated Debian child.

This document allocates no successor ordinal, version, build, state path,
artifact, qualification, approval, or command. H16 and H24 effects are
historical and consumed; neither may be replayed or reinterpreted.

## Exact evidence boundary

The public record supports these facts:

- H14 introduced the reviewed read-only direct-UFS design, but its live F1
  candidate failed resident verification at the unarmed synchronous Wi-Fi
  gate before any UFS mount and was rolled back.
- H15 made Wi-Fi asynchronous and installed successfully, but its D1 stopped
  before latch, UFS mount, or `switch_root`: a numeric userdata `dev_t` captured
  in one boot changed in the next boot while the stable partition identity did
  not.
- H16 resolved the sole `PARTNAME=userdata` in each native session, required
  exact stable identity and same-session numeric stability, and then reached
  the direct-UFS `switch_root_exec` boundary.
- H17 added a boot-private observer key path, firstboot integration, and a
  persistent native HUD/server path. Its live handoff reached `root_mounted`
  but not `writable_set_ready` or `switch_root_exec`; the captured evidence
  proved only an outer post-root `EPERM` window.
- H18 added exact stage/rc/errno attribution. Its consumed live attempt
  identified outer `firstboot-overlay rc=-1 errno=1`, restored cleanly, and did
  not reach `switch_root_exec`.
- H19 through H23 were host-only successor experiments. They are useful design
  evidence but none is a later live UFS success.
- H24 installed successfully as a resident, then its separate consumed D1
  mounted verified UFS and the writable set before failing at the persistent
  HUD bootstrap. The inner failing syscall remains unproved.

Consequently, H16 remains the live direct-UFS root-exec-boundary reference;
H24 remains the exact installed starting resident and latest live failure
reference. Neither fact upgrades the other run's missing evidence.

## Comparison matrix

| Boundary | H16 live baseline | H24 installed/attempted lineage | Selected isolated-Debian design |
|---|---|---|---|
| Version/build role | `0.11.184`, first direct-UFS `switch_root_exec` boundary reach | `0.11.192`, exact installed resident and consumed D1 refutation | No identity allocated; H0 only |
| Manifest ancestry | Extends `v3404-effective` | Directly extends `phase3-minimal-h16` | Must be a fresh post-H25 identity only after H0 feasibility |
| UFS identity | Fresh same-session dynamic `dev_t` plus exact stable identity | Inherits H16 identity policy and exact UFS content | Preserve same-session identity; mount only inside child mount namespace |
| UFS mount | Exact read-only `ro,noload,nosuid,nodev` | Same; live-mounted and content-verified | Preserve exact flags and immutable content validation |
| Root transition | Native PID 1 performs in-place BusyBox `switch_root` | Intended to retain that transition but failed before it | Native PID 1 remains supervisor; one isolated child uses `pivot_root` |
| Last live stage | `switch_root_exec` at boot time 11,760 ms | `persistent-hud` EINVAL after `writable_set_ready` | Future `DEBIAN_EXEC`, then `SERVICE_READY`; not implemented |
| Observer/auth | Manifest key rejected by appliance root | Boot-private observer auth overlay added | Keep boot-private auth; prove same-run authenticated SSH |
| Display/HUD | Display marker existed, but no current DRM/display proof | Persistent native HUD/private card-root added and became the failing gate | Remove HUD/display from headless acceptance; display is optional later |
| Wi-Fi helper model | Persistent native helper with private mount namespace, not isolated PID/network namespaces | Inherits that helper model and adds more persistent server machinery | Native owns Wi-Fi; Debian gets a distinct netns and bounded veth/IP path |
| Debian `/proc` | In-place handoff/shared process model; no production isolation claim | Shared-process ancestry made surviving native sidecars unsafe to expose | Fresh PID namespace and matching private procfs; no native task is nameable |
| Debian `/dev` | Successful topology did not prove exposure, but lacked H24's later always-fresh minimal-device contract | Host-qualified fresh tmpfs minimal `/dev` plus mandatory devpts; H24 failed before live reaching it | Preserve fresh minimal `/dev`; no native devtmpfs, block, userdata, or DRM |
| Evidence storage | Direct UFS root still depended on the SD evidence sidecar | Still retains SD evidence bind and compiled SD Wi-Fi property root | Cache-backed bounded records and one-way pipes; SD absent from runtime |
| Failure return | Persistent Debian did not automatically return; operator physically returned | Pre-switch failure restored mounts and returned exact native health | Parent never leaves native root; exact child/network cleanup or recovery park |
| Terminal meaning | Mechanical root-exec boundary reached; full server readiness unproved | HUD lane refuted; exact native fallback healthy | Persistent Debian remains `HEALTH_PENDING_PERSISTENT_DEBIAN` until attended return |

## What H16 proved and what it did not

H16 proved the following reusable mechanics:

1. the multi-gigabyte SD work-copy is not required for the Debian root;
2. the existing UFS appliance can be resolved from stable identity on each
   boot without reusing a cross-boot numeric `dev_t`;
3. the UFS root can be mounted read-only with journal replay disabled;
4. the immutable content and bounded writable set can pass;
5. the ordered handoff can reach the final root-exec boundary; and
6. after an attended physical return, the exact native resident can be proved
   healthy with userdata unmounted and unchanged.

H16 did not prove the product outcome. The observer key did not authenticate,
the appliance intentionally had no automatic-return timer, and no exact
same-intent receipt proved Debian PID 1, SSH authentication, DRM/display,
final Wi-Fi, or server workload health. A black screen and an open port cannot
fill those gaps. The 11,760 ms stamp is therefore a mechanical timing anchor,
not a successful-server boot time.

## Why later versions became larger and failed earlier

The failures after H16 were not evidence that UFS or `switch_root` had stopped
working. They occurred in newly inserted pre-exec gates intended to close
H16's missing product evidence:

- H17 added observer authorization, firstboot integration, persistent native
  HUD, shared-run state, and persistent-service observation. It failed after
  the root mount and before the writable set completed.
- H18 added exact failure attribution and identified firstboot-overlay EPERM.
- H19-H23 iterated host-only on overlay/HUD ownership and device isolation;
  review prevented unsafe variants from reaching the device.
- H24 retained observer authorization, disabled firstboot overlay, and added a
  delayed-DRM private-card-root HUD plus an always-fresh minimal Debian `/dev`.
  Its live D1 passed UFS and writable setup but the new HUD bootstrap returned
  EINVAL before root transition.

This is the central regression delta: the successful H16 UFS core stayed in
the ancestry, while authentication, display ownership, service observation,
and device isolation accumulated in front of `switch_root`. Some additions
were necessary safety work; persistent HUD and display acceptance were not
necessary for a headless server and created a blocking dependency.

It would still be wrong to rebuild H16 unchanged. H16 retained the persistent
native Wi-Fi helper model, shared native process visibility after handoff, SD
evidence/property-root dependencies, and weaker Debian-device isolation. The
new design keeps the proven storage mechanics without inheriting those
production hazards.

## Carry forward unchanged

The isolated successor must preserve these exact classes of behavior:

- target/profile binding, boot-only transfer, exact rollback, attended
  recovery, post-transfer source revalidation, and candidate no-replay;
- fresh per-session userdata resolution and stable UFS identity;
- `ro,noload,nosuid,nodev` UFS mount, immutable content manifest, and zero UFS
  mutation;
- bounded writable tmpfs paths and boot-private SSH authorization;
- fresh minimal tmpfs Debian `/dev`, mandatory devpts, and zero native-devtmpfs
  or userdata-block exposure;
- durable launch intent, one child maximum, exact failure attribution, and
  recovery park on ambiguity;
- exact final native health only after attended return or recovery; and
- comparable stage timestamps that never act as safety predicates.

## Remove rather than repair

Do not carry these H16-H24 mechanisms into the formal headless path:

- persistent native HUD, DRM presenter, display marker as a success gate, and
  the private-card-root bootstrap;
- firstboot overlay injection and boot chime;
- shared PID/proc visibility between Debian and surviving native Wi-Fi tasks;
- general shell commands as health or inventory machinery;
- hard SD evidence bind and compiled SD Wi-Fi property root;
- automatic-return assumptions for a deliberately persistent Debian runtime;
- W0/atomic Wi-Fi ownership diagnostics and their brokers; and
- benchmark thresholds inside launch, fallback, or health decisions.

## Replace with explicit new boundaries

| Old mechanism | Replacement |
|---|---|
| Native PID 1 disappears through in-place `switch_root` | Native PID 1 remains a minimal supervisor; one direct child becomes Debian PID 1 and `pivot_root`s |
| Shared PID/proc model | Fresh Debian PID namespace plus matching private procfs |
| Shared native network namespace | Fresh Debian netns, exact veth pair, default-drop forwarding/NAT |
| SD evidence directory bind | Cache-backed append-only records and two bounded one-way pipes |
| Persistent HUD/display proof | Headless SSH/workload health; optional display is a later capability |
| Reverse root transition/automatic timer | Exact child namespace teardown or attended reboot/recovery |
| Port-visible or screen-visible inference | Authenticated same-run PID1, SSH, network, mount, and workload receipts |

## Comparable performance baseline

The H16 stage sequence is retained as a historical timing vocabulary, not as a
required implementation shape. The new design maps it as follows:

| H16 stage/metric | Isolated successor anchor |
|---|---|
| `handoff_begin` | durable `HANDOFF_INTENT` |
| `userdata_identity_initial_done` | first exact UFS identity receipt |
| `display_release_done` | optional native-owner cleanup; eventually absent |
| `userdata_identity_post_display_done` | final pre-mount UFS identity receipt |
| `root_mounted` | private-child `ufs_root_mounted` |
| `writable_set_ready` | private-child `writable_set_ready` |
| `distro_init_verified` | `debian_init_verified` |
| `display_marker_ready` | removed; no headless equivalent |
| `mount_moves_done` | `old_root_detached` after private pivot |
| `switch_root_exec` | `DEBIAN_EXEC` |
| no H16 equivalent | `NETWORK_READY`, authenticated `SSH_READY`, `SERVICE_READY` |

Every future comparison must report at least:

- `boot_to_debian_exec_ms` and `handoff_intent_to_debian_exec_ms`;
- `boot_to_authenticated_ssh_ms` and `debian_exec_to_ssh_ms`;
- UFS mount/content validation, writable-set, network setup, and cleanup times;
- native supervisor/Wi-Fi and Debian CPU, RSS, wakeups, and available thermal/
  clock observations; and
- the exact build/profile, root content, cache state, and observation method.

H16's public 11,760 ms value is `boot_to_switch_root_ms`. It must be compared
only with the new boot-relative exec value. The public record does not supply
an exact H16 `handoff_begin_to_switch_root_ms`, so no such number is invented.
H16 also supplies no authenticated-SSH or final-Wi-Fi timing baseline.

Performance collection is observational. Missing power, clock, or thermal
telemetry is `na`; a slower benchmark never causes rollback, and a faster
benchmark never substitutes for safety or health evidence. Full-LTO is tested
only after one functionally identical non-LTO baseline closes.

## Successor acceptance delta

A future isolated successor is not acceptable merely because it matches or
beats H16's root-exec time. It must additionally prove, in one exact run:

1. the H16-derived UFS identity, read-only mount, content, and writable-set
   mechanics;
2. one Debian child with distinct PID/mount/network namespaces and no replay;
3. private procfs, detached old root, sanitized FDs/capabilities, and minimal
   `/dev` with no native task/device path;
4. native-owned final Wi-Fi plus exact veth/netfilter policy;
5. Debian PID 1, boot-private authenticated SSH, and selected service health;
6. SD-free durable stage/failure evidence;
7. deterministic pre-release fallback and post-release cleanup/recovery park;
8. exact boot-only rollback and physical Download/TWRP recovery; and
9. `HEALTH_PENDING_PERSISTENT_DEBIAN` while live, with exact native
   `RESIDENT_HEALTHY` only after attended return or recovery.

Until host feasibility, negative tests, independent capability review, fresh
identity, fresh connected D0, and separate attended F1/D1 approvals exist,
this remains a comparison and design boundary only.

## Canonical public evidence

- `docs/operations/CAMPAIGN_LEDGER_A90.md`
- `docs/reports/A90_H15_UFS_DEVT_CROSS_BOOT_DRIFT_INCIDENT_2026-08-10.md`
- `docs/reports/A90_H16_PERSISTENT_DEBIAN_RETURN_OBSERVER_INCIDENT_2026-08-10.md`
- `docs/reports/A90_H17_POST_ROOT_MOUNT_NATIVE_FALLBACK_INCIDENT_2026-08-10.md`
- `docs/reports/A90_H18_FRAMED_LOG_PREFIX_FINALIZER_INCIDENT_2026-08-12.md`
- `docs/reports/A90_H23_DEBIAN_DEVTMPFS_EXPOSURE_INCIDENT_2026-08-12.md`
- `docs/reports/A90_H24_PERSISTENT_HUD_BOOTSTRAP_EINVAL_INCIDENT_2026-08-12.md`
- `workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h16/manifest.toml`
- `workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h24/manifest.toml`
- `workspace/public/src/scripts/server-distro/a90_h16_persistent_physical_return_v1.py`
- `workspace/public/src/scripts/server-distro/a90_boot_benchmark_v1.py`

Private manifests, journals, raw logs, credentials, device/network identifiers,
and artifacts remain under `workspace/private/` and are not used or committed
by this H0 comparison.
