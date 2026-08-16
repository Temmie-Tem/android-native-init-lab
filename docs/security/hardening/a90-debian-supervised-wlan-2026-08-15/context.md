# Working Context: A90 Debian-Supervised WLAN Control Plane

Date: 2026-08-15
Repository: `android-native-init-lab` (all listed paths are repository-relative)
Input revision: `fda348a072eba8a53c2de7c9904c52429a7dddaf`
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0, host-only investigation and documentation

## Question

Can the A90 steady state have one administrative owner, Debian PID 1, while
preserving the vendor WLAN control plane that WSTA18 proved must remain live?
This is narrower than asking whether Qualcomm WLAN can be reimplemented. The
candidate idea is to supervise a manifest-pinned vendor compatibility capsule
from Debian, not to replace WCNSS/WMI or the kernel driver.

## Method And Contact Boundary

I inspected the public WSTA reports, current A90 contract and goal, selected and
retired architecture documents, H24 manifest, and the exact public native source
that assembles the persistent WLAN service tree. The bound evidence inputs were
read-only; this directory and its focused regression test are the documentation
output. I did not read private run artifacts and did not reproduce any live
result. Public reports are therefore treated as historical observed evidence;
statements about why individual services are required are marked inferred until
ablation proves them.

Contact counters for this analysis are: physical device `0`, target-bearing
`/dev` enumeration/open `0`, USB `0`, device network `0`, `workspace/private`
`0`, S22+ `0`, S20+ `0`, payload `0`, reboot `0`, flash `0`, and live command
`0`. One host `/dev/null` sink was used for JSON syntax validation; it was not a
target or transport contact.

## Evidence Collection Identity

The collection digest is computed over the listed files in this exact order as
the concatenation of `relative_path NUL size NUL sha256 NUL`:

`d34f4d88fa2509305f15f6863ae65923eef72c69a1b297fe3a037e67933357de`

Artifact count: `28`. Source drift at analysis time: `none`.

| SHA256 | Bytes | Repository-relative path |
| --- | ---: | --- |
| `6cd7e24235396089baab844b0e568a93fb82528bf7fc6cb6c5cfc62d83ef0793` | 17014 | `AGENTS.md` |
| `e1b361b525f7d731ef69c766f050c177f6ba1bf2d958b092f685393dc27a9ae1` | 31302 | `GOAL_A90.md` |
| `ed9f51212db33bd822dc96ecf12feeda05ce255d088c402c4742851d173fad51` | 89405 | `docs/operations/targets/A90_TARGET_CONTRACT.md` |
| `edd64a434330f79a3b1ec542c12822e5b201362c212484c7b67d67b4ffbb61a9` | 97237 | `docs/operations/CAMPAIGN_LEDGER_A90.md` |
| `5c4c669f058bb003519dc04813158d2e408901c05eb9354a7a082d728a56a01b` | 12667 | `docs/reports/A90_NATIVE_WIFI_OWNERSHIP_PERMANENCE_EVIDENCE_H0_2026-08-15.md` |
| `2591fdc1adf180b11907944710c0ddd3d18d146a749c73f0d6750cbfe72afa27` | 6642 | `docs/reports/A90_NATIVE_WIFI_SIDECAR_PROC_ROOT_EXPOSURE_HOST_INCIDENT_2026-08-13.md` |
| `69c364e9e7ba2cdc45e6a754f165c66ac402a0e18143327b0b764b226cea0aaf` | 14908 | `docs/reports/A90_ISOLATED_DEBIAN_SECURITY_DERIVATION_H0_2026-08-15.md` |
| `52559a249be12cd26302a0f6a32128f9dd456ac1d4482170634fb95b4eb59882` | 16665 | `docs/plans/A90_H16_H24_ISOLATED_DEBIAN_COMPARISON_BASELINE_2026-08-14.md` |
| `9c48c21e813f27681d60cfd5e4881b73e8c4544abe2bca02b4a2f37dac0860c6` | 79078 | `docs/plans/A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md` |
| `56f4ab21f9f74c4e86166939f768f09232a5a6d7387753c5b72cbaea263932b0` | 45317 | `docs/plans/A90_ATOMIC_WIFI_OWNERSHIP_DIAGNOSTIC_RESIDENT_DESIGN_2026-08-14.md` |
| `163cebf09f481dbf333400c5afc4f232d5b935a332a113512b76eb192bee855e` | 6384 | `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA14_LINKSTATE_SCAN_BLOCKED_2026-07-04.md` |
| `1c7984a85af3cb059244d7f3e7ed5b21516a60657bd947a275a4ed7e4faa5b71` | 4991 | `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA18_CONTROL_PLANE_BLOCKED_2026-07-04.md` |
| `055359850d4141f360b0bed0e5cffe2f2f27bb0be4bc9e8ca7c0cbafbe1c256d` | 6149 | `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA19_NATIVE_OWNED_CHROOT_WIFI_PASS_2026-07-04.md` |
| `240a46ed525673d474b7b103155b32249069faf44511268c384331d84cad4f9c` | 3174 | `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA20_NATIVE_SERVICE_BOUNDARY_PASS_2026-07-04.md` |
| `d74e4a5ed1a933a8915045964d653cf8f143aaa48c5ba04ee3ff6b87584d8a2b` | 3045 | `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA22_NATIVE_SERVICE_CLIENT_LIVE_PASS_2026-07-04.md` |
| `17cc423f7069f6a6b9cf06d81e5d52254382d81997e245c8f51b8060e2a730ee` | 3850 | `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA23_UPLINK_SERVICE_LIVE_PASS_2026-07-04.md` |
| `7650b6efc5744318f64982c214551f7c86c04fd6547bf3ac0452621f76fbfa74` | 4377 | `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA24_UPLINK_CLIENT_LIVE_PASS_2026-07-04.md` |
| `fa61a9c128ca754ec5c5879bb890a569c4d14f592c4676143e6123a49ba2a82e` | 6647 | `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA31_NATIVE_SCAN_RECOVERY_V3388_LIVE_2026-07-04.md` |
| `80353f052dbbea98a4f9ed1eb3977902ae7d006bbb6b348586227d3ba3d9b1a8` | 5903 | `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA40_WSTA41_MATERIALIZATION_CONFIRMED_AUTOCONNECT_PASS_2026-07-04.md` |
| `f453ec1f09bf5b8fea414ec0d1c112ab1014fd09d599ceb4f55d7d939b09c2cf` | 4202 | `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA42_NATIVE_UPLINK_DPUBLIC_TUNNEL_PASS_2026-07-04.md` |
| `ddb47f6b13665ea1f975cc7236d4abe925980a164b75f133934b495e14bbd0a7` | 4305 | `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA43_ORCHESTRATED_NATIVE_UPLINK_DPUBLIC_PASS_2026-07-04.md` |
| `40c26c5878db21737600bc29864db9123cc4650ec39d7f0d7395209c2df70a8f` | 7801 | `workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h24/manifest.toml` |
| `4e68735fa2acc06fa4c101d8dbab6380d7785c4d9c7edfe47448ab26031b57e2` | 3253399 | `workspace/public/src/native-init/helpers/a90_android_execns_probe.c` |
| `2a6863c0fd5f1dc2559ccee45031e389c956d6e094d8602364fd1875b919128f` | 277766 | `workspace/public/src/native-init/v724/90_main.inc.c` |
| `199b4f55075384c64d3b1f82deb7b5b630b4d306bfc058c5e50a896f28297abf` | 258111 | `workspace/public/src/native-init/a90_server_distro.c` |
| `c72e23ad9f10b2051b67210b09dc39fa35a00644df2e8ff9977a736f2d8078da` | 8227 | `workspace/public/src/native-init/a90_config.h` |
| `66994481315f10523bb1fc7ffa625144170425f397ddbd3fcfe1f89aa1d1ca11` | 51638 | `workspace/public/src/scripts/server-distro/a90_isolated_debian_security_derivation.py` |
| `26d5b1d9a8a9973760e1671ea5f83c804c061edc97fe701e804457cc5a1a59de` | 7663 | `tests/test_a90_isolated_debian_security_derivation.py` |

## Evidence Registry

| ID | Type | Evidence | Establishes |
| --- | --- | --- | --- |
| `E01` | observed experiment | WSTA14 direct handoff | Native materialized WLAN; after direct Debian root transition the interface existed but direct scan remained blocked. |
| `E02` | observed experiment | WSTA18 control-plane failure | After native userspace disappeared, Debian retained netdev/phy/rfkill while WCNSS/WMI and protection-domain evidence went down. |
| `E03` | observed experiment | WSTA19 chroot boundary | Keeping native PID 1 and its WLAN control plane alive preserved scan while Debian Dropbear ran. |
| `E04` | observed experiments | WSTA20, WSTA22-WSTA24 | A bounded native-owned status/scan/uplink service was consumable from Debian. |
| `E05` | observed experiments | WSTA31, WSTA40, WSTA42, WSTA43 | Native ownership reached scan, WPA, DHCP, route, and a gated Debian service tunnel. |
| `E06` | observed source | H24 manifest and native source | The current persistent path is a service-object-visible composition, not one daemon: QRTR, PD/RFS services, Android service managers, peripheral-manager services, CNSS processes, a property shim, and a modem hold are present. |
| `E07` | inferred incident | `/proc` sidecar incident | A private mount namespace does not hide surviving native processes from shared procfs; a root/fd/ns capability can remain reachable. |
| `E08` | proposed baseline | selected isolated-Debian design | The current design keeps native as supervisor and hides the entire Debian service surface behind PID/mount/IPC/UTS/network isolation and veth. |
| `E09` | negative design evidence | retired atomic diagnostic | Reproducing the H24-equivalent service set required distinct Android identities and Binder/property/AF_UNIX machinery; it does not prove a smaller clean relaunch impossible. |
| `E10` | derived coverage | isolated-Debian security derivation | The current selected Debian service set has a trace-derived syscall candidate policy; no equivalent derivation exists for a Debian-supervised vendor capsule. |
| `E11` | authority evidence | A90 contract, goal, ledger | H24 is the installed healthy resident, its D1 is consumed, no successor identity or live authority exists, and all future work begins H0. |

### Direct anchors for the decisive claims

| Claim | Frozen source anchor |
| --- | --- |
| Debian retained the WLAN objects but scan failed while firmware, Root PD, and WMI went down | `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA18_CONTROL_PLANE_BLOCKED_2026-07-04.md:15-23` and `:111-117` |
| WSTA18 itself left four architectural responses open, including preserve/relaunch | `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA18_CONTROL_PLANE_BLOCKED_2026-07-04.md:119-127` |
| Native scan stayed healthy while Debian Dropbear was active | `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA19_NATIVE_OWNED_CHROOT_WIFI_PASS_2026-07-04.md:15-24` and `:128-134` |
| H24 selects persistent handoff, the SD property snapshot, and the service-object-visible trigger | `workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h24/manifest.toml:34`, `:64`, and `:72` |
| The selected H24 helper branch constructs the accumulated service tree | `workspace/public/src/native-init/helpers/a90_android_execns_probe.c:58654-58769`; the published order at `:58860-58862` omits the duplicated service-manager pair; property-shim selection begins at `:60957` |
| The `/proc` blocker has exactly two accepted retirement closures | `docs/reports/A90_NATIVE_WIFI_SIDECAR_PROC_ROOT_EXPOSURE_HOST_INCIDENT_2026-08-13.md:108-122` |

## Findings Used By The Proposal

### Observed

- WSTA18 refutes only `native/vendor userspace disappears and Debian inherits
  wlan0`. It does not refute a Debian-supervised relaunch of the existing vendor
  backend.
- H24 uses an accumulated path whose sufficiency was never reached in its
  consumed D1. Its manifest chooses the service-object-visible trigger and a
  persistent helper, then starts native autoconnect separately. The selected
  branch constructs thirteen composite child entries representing eleven
  unique roles: `servicemanager` and `hwservicemanager` are each enqueued
  twice. The published order string lists only the eleven unique roles and
  hides that duplicate pair. A property-service shim and `/dev/subsys_modem`
  holder add two more helper-managed children.
- H24's property snapshot source is under `/mnt/sdext`; that is incompatible
  with the selected SD-free direction and cannot be copied into a successor.
- The public lineage proves native scan/association/DHCP and Debian service
  consumption. It does not prove Debian's `wpa_supplicant` against a separately
  preserved vendor firmware/protection-domain backend.

### Inferred

- The real ownership question has at least four planes: device-backend
  lifecycle, station/network policy, IP routing, and appliance/service policy.
  They need not all be implemented by one binary, but one steady-state PID 1
  can be the sole lifecycle and policy authority.
- Moving the service tree under Debian changes authority; it does not delete
  the vendor TCB. If remote SSH/workload code remains root-equivalent in the
  same process and mount view, the attack surface grows rather than shrinks.
- The minimum service set is unknown. H24's service managers, Binder nodes,
  peripheral-manager services, property shim, and modem holder are an
  accumulated source route, not a live-qualified H24 route and not proof that
  every component is necessary.

### Proposed

- Treat a clean Debian-supervised compatibility capsule as a separate H0
  feasibility program. Prove the minimum service/dependency set by static
  closure plus fail-closed ablation before considering a candidate.
- Keep the current isolated-Debian design as the production baseline until that
  feasibility program closes every security, recovery, and performance gate.
