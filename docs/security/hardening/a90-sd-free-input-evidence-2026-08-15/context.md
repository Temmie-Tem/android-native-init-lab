# Working Context: A90 SD-Free Inputs And Evidence

Date: 2026-08-15
Repository: `android-native-init-lab` (all listed paths are repository-relative)
Baseline revision: `fda348a072eba8a53c2de7c9904c52429a7dddaf`; the collection
below was rebound after the later H24 13-entry/11-role and `WP-H0-1` status
corrections to its Debian-supervised-WLAN input
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0, host-only investigation and documentation

## Question

What must replace the remaining SD-backed inputs and evidence before either the
selected isolated-Debian architecture or the Debian-supervised WLAN research
path can become a candidate?

The answer is not one replacement directory. The current lane has four data
classes with different confidentiality, integrity, lifetime, and authority:

1. a public SSH client authorization key;
2. persistent private Wi-Fi station credentials and policy;
3. an Android/vendor property compatibility input;
4. same-run transition and service evidence.

Combining those classes into a generic cache bundle would make the new path
shorter but would preserve the most dangerous property of the old SD design:
one mutable tree would simultaneously influence boot, privileged vendor
services, remote authentication, and the evidence used to grade them.

## Method And Contact Boundary

I read the current common and A90 contracts, current goal, selected plans,
H24 manifest, exact public native consumers, historical evidence writer, and
the public host Wi-Fi staging code. I did not run the staging code or its test:
both are device-mutating workflows and the test creates private evidence.

Contact counters are: physical device `0`, target-bearing `/dev` contact `0`
(one host `/dev/null` validation sink only),
USB `0`, device network `0`, `workspace/private` read/list/stat `0`, S22+ `0`,
S20+ `0`, payload `0`, reboot `0`, flash `0`, and live command `0`. The only
repository writes are this H0 documentation set, its focused host test, and the
security index entry.

## Evidence Collection Identity

The collection digest is computed over the listed files in this exact order as
the concatenation of `relative_path NUL size NUL sha256 NUL`:

`6bd63492c56ac099936d2594d38cec36095138cd93cd2214746f895a09a4e62f`

Artifact count: `22`. Source drift at analysis time: `none`.

| SHA256 | Bytes | Repository-relative path |
| --- | ---: | --- |
| `a90560db2985b588a1aa53c0a2078bb6d930865895167a5b71e5bba2acec076b` | 11157 | `AGENTS.md` |
| `fca649759d6275267f71fc303d978c31220bbcf9bb95c24c47283fd813566b88` | 26900 | `GOAL_A90.md` |
| `ed9f51212db33bd822dc96ecf12feeda05ce255d088c402c4742851d173fad51` | 89405 | `docs/operations/targets/A90_TARGET_CONTRACT.md` |
| `356c599afac5600126cd03ab2c27ed1b209f1edae74513881ffe08a925302867` | 18735 | `docs/operations/NATIVE_INIT_WIFI_LIFECYCLE_COMMANDS.md` |
| `84511114e43da3b44a42cdd2778e514c7e081633296657a9ef01a4a1b4ea6f41` | 29521 | `docs/plans/A90_HEADLESS_HANDOFF_MINIMUM_AND_WIFI_OWNERSHIP_DECISION_2026-08-13.md` |
| `9c48c21e813f27681d60cfd5e4881b73e8c4544abe2bca02b4a2f37dac0860c6` | 79078 | `docs/plans/A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md` |
| `06cadec22833439c3c72fdc26e4d72dfeaf44959ee882c81347ca05d73fb9168` | 34818 | `docs/plans/A90_UFS_HANDOFF_ARCHITECTURE_AND_PRODUCTION_REDUCTION_PLAN_2026-08-12.md` |
| `f3c641c133f5f6b52d316292239d9fc792a42572f1b86b3c552d7c94a5bd897a` | 7614 | `docs/reports/A90_H14_IMMUTABLE_FIRSTBOOT_ISOLATED_DEBIAN_MISMATCH_H0_2026-08-14.md` |
| `f732b1ff9ff48dfd97383ad14c2c1e75f5eea227c3d80c85cddab68300099d73` | 36328 | `docs/security/hardening/a90-debian-supervised-wlan-2026-08-15/proposals/debian-supervised-wlan.md` |
| `40c26c5878db21737600bc29864db9123cc4650ec39d7f0d7395209c2df70a8f` | 7801 | `workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h24/manifest.toml` |
| `d8697da63a093eaaed73339a158b2992ad3121a2a2ebc01597a10f8b05363ec6` | 33086 | `workspace/public/src/native-init/a90_auto_handoff.c` |
| `199b4f55075384c64d3b1f82deb7b5b630b4d306bfc058c5e50a896f28297abf` | 258111 | `workspace/public/src/native-init/a90_server_distro.c` |
| `47735e8b83f8113b4afb53a48d9884465876a2cb756513b0cc9f9c4142d7cb4f` | 77217 | `workspace/public/src/native-init/a90_wificfg.c` |
| `ff3cd7ea0dd56bcb7083cdeeba13d798d91dd69eccf1ab2138edf5a1f82598be` | 1824 | `workspace/public/src/native-init/a90_wificfg.h` |
| `2a6863c0fd5f1dc2559ccee45031e389c956d6e094d8602364fd1875b919128f` | 277766 | `workspace/public/src/native-init/v724/90_main.inc.c` |
| `4e68735fa2acc06fa4c101d8dbab6380d7785c4d9c7edfe47448ab26031b57e2` | 3253399 | `workspace/public/src/native-init/helpers/a90_android_execns_probe.c` |
| `53df5ecc1302216981331dd94bb43d51269711a8d9fb9ef53159ac95fabbe739` | 52916 | `workspace/public/src/scripts/revalidation/a90_flat_builder/build.py` |
| `f57d7612c915d46b4190ab208f7b6320099576dc440c0999c6328fd756d11e2c` | 23716 | `workspace/public/src/scripts/server-distro/a90_ondevice_evidence_v1.py` |
| `62cc6d79165bdab3894228eabed4aa7e76885bb5ea327afce8e0c8668676a644` | 81873 | `workspace/public/src/scripts/server-distro/a90_h24_ufs_d1_runner_v1.py` |
| `fb8665527aa2fbfe58aadddada9976215d8b852415aad73506b3f9abea7f210f` | 12696 | `workspace/public/src/scripts/revalidation/a90_wifi_profile_stage.py` |
| `5b6bf6cf47eea915f739782a8b48aa94b834b09ca9f00ebb5ea37cad61e94b85` | 60156 | `workspace/public/src/scripts/revalidation/native_wifi_connect_carrier_handoff_v2174.py` |
| `855353e3ccd603c19e3d17ebbc7a96d76b284d66e1873a8d3f83113846248f55` | 12093 | `tests/test_a90_wifi_profile_stage.py` |

## Evidence Registry

| ID | Type | Evidence | Establishes |
| --- | --- | --- | --- |
| `E01` | observed source | H24 handoff source | Native publishes the run identity on SD, then the switch path hard-gates an SD evidence-directory bind into Debian. |
| `E02` | observed source | historical evidence writer and H24 D1 runner | Debian writes phase records to the shared SD tree, and H24 D1 later cross-checks that SD run identity against enable and latch. |
| `E03` | observed source | H24 manifest and helper | H24 compiles an SD property snapshot; the helper accepts either the SD prefix or a cache prefix and bind-mounts the selected tree read-only. |
| `E04` | observed source | native Wi-Fi config module | Native Wi-Fi reads SD first and cache second; secrets may be referenced only under the SD secret root or cache config root. |
| `E05` | observed source | public profile staging tool | A host tool can build and transfer cache profiles, but uses live NCM/tcpctl commands, mutable replace semantics, and current private inputs. |
| `E06` | authority evidence | common and A90 contracts | Current routine D1 does not authorize persistent credential/configuration changes or arbitrary cache staging; H24 commands require separately reviewed D1/F1 authority. |
| `E07` | observed source | flat builder and H17 auth overlay | One canonical public Ed25519 client key can be taken from a private host input, bound by hash, embedded in the boot ramdisk, and copied to tmpfs without UFS write. |
| `E08` | selected design | isolated-Debian logging and key design | Native-only cache receipts plus authenticated host observation replace a Debian-writable evidence channel; the server host key is generated per boot in private tmpfs and only its public fingerprint is retrieved. |
| `E09` | negative content evidence | H14 immutable-firstboot audit | The existing UFS firstboot is not the new evidence producer or service contract and cannot be treated as a post-exec receipt writer. |
| `E10` | sequencing evidence | GOAL and reduction plan | SD evidence and property dependencies must be removed before any headless successor identity; physical SD removal occurs only after a healthy SD-free resident and a fresh no-SD D0. |
| `E11` | design evidence | Debian-supervised WLAN review | Both the native-supervisor baseline and clean Debian relaunch need the same typed SD-free inputs; the property requirement may shrink only after service ablation. |

## Direct Anchors

| Claim | Frozen source anchor |
| --- | --- |
| SD run publication and evidence tail | `workspace/public/src/native-init/a90_auto_handoff.c:52-64`, `:605-645`, and `:665-731` |
| Mandatory SD evidence bind before Wi-Fi handoff | `workspace/public/src/native-init/a90_server_distro.c:3527-3620` and `:7076-7087` |
| H24 D1 binds the SD run file to enable/latch | `workspace/public/src/scripts/server-distro/a90_h24_ufs_d1_runner_v1.py:401-419` |
| H24 compiled property root | `workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h24/manifest.toml:64` |
| Cache property prefix is only an accepted consumer path | `workspace/public/src/native-init/helpers/a90_android_execns_probe.c:1595-1609` and `:4539-4571` |
| SD-first/cache-second Wi-Fi readers | `workspace/public/src/native-init/a90_wificfg.c:32-45` and `:819-869` |
| Public cache staging code performs live mutation | `workspace/public/src/scripts/revalidation/a90_wifi_profile_stage.py:170-315`; overwrite mechanics are in `native_wifi_connect_carrier_handoff_v2174.py:641-792` and `:1039-1059` |
| Existing public-key boot input | `workspace/public/src/scripts/revalidation/a90_flat_builder/build.py:197-246` and `:1124-1135` |
| Selected native-only receipt and per-boot host-key split | `docs/plans/A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md:879-954` |
| No successor before Gate 3 | `GOAL_A90.md:319-340` and `:368-378` |
| No current UFS-content authority | `docs/operations/targets/A90_TARGET_CONTRACT.md:1049-1059` |

## Observed, Inferred, Proposed

### Observed

- H24 has two hard SD runtime dependencies in its selected handoff: the evidence
  tree and the property snapshot. Its native Wi-Fi configuration also prefers
  SD, but already contains a cache fallback reader.
- The cache Wi-Fi path has a public producer. It is a legacy live staging
  workflow, not an activated current A90 production capability. It uses the
  generic resident transport, mutates configuration and credentials, replaces
  named files, and has no current target-contract authority.
- The cache property prefix has no producer in this evidence collection. The
  helper merely accepts and consumes a tree already present there.
- The historical evidence design deliberately let Debian write to a directory
  also read by native and the host. That solved read-only-root observability but
  made SD availability and a cross-boundary writable mount part of success.
- The existing H17 boot pattern handles a public client key. It does not justify
  placing a Wi-Fi PSK or server private key in the boot artifact.

### Inferred

- A generic cache bundle would let corruption or replacement in one mutable
  namespace affect authentication, privileged WLAN compatibility, and grading.
- Wi-Fi credentials need persistence and rotation, while the server host key
  should be ephemeral. Treating both as “boot-private” without naming their
  lifetime would produce either an unrotatable boot secret or an unavailable
  network after reboot.
- A full Android property snapshot is a compatibility image, not a simple
  config file. Its minimum contents and confidentiality are unproved because no
  private snapshot was inspected. Service ablation should remove or minimize
  that dependency before a production format is selected.
- A native cache receipt can prove only facts visible to native. Authenticated
  SSH and the forced workload probe remain host observations and must not be
  backfilled into native evidence.

### Proposed

- Use four typed channels, with separate roots, schemas, writers, readers,
  digests, lifetimes, cleanup, and authority.
- Reuse the existing public-key validation pattern for the client public key.
- Replace the legacy Wi-Fi staging surface with a separately reviewed,
  generation-based, exact-path, one-use credential provision/rotation
  capability. Until that exists, cache readability is not SD-free readiness.
- Eliminate the property snapshot through WLAN service reduction if possible;
  otherwise generate an exact minimal deterministic property seed. Never copy
  the full private snapshot by default.
- Make native PID 1 the sole device-side receipt writer. Debian gets no cache
  evidence FD or bind. The host joins the native digest with its own strict SSH
  evidence under `workspace/private`.

## Authority Result

This analysis selects an H0 architecture boundary only. It does not activate
the legacy profile stager, create a credential-provision capability, inspect a
credential, allocate a successor identity, modify UFS, or authorize D0, D1, F1,
handoff, reboot, flash, SD removal, or candidate installation.
