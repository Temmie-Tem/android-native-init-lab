# S22+ FYG8 post-2025-08 security backlog

Date: 2026-09-16
Target: Samsung Galaxy S22+ `SM-S906N` / `g0q`
Baseline: `S906NKSS7FYG8`, Android 15, 2025-08 security patch
Status: candidate backlog only; no device action is authorized by this document.

Related planning memos:

- [Security side-track candidates](S22PLUS_FYG8_SECURITY_SIDE_TRACK_CANDIDATES_2026-09-16.md)
- [RF-sensing side track](S22PLUS_RF_SENSING_SIDE_TRACK_CANDIDATES_2026-11-21.md). Its Wi-Fi part concerns the Broadcom BCM4389 `dhd.ko` driver; the corrected vendor is recorded in the component inventory.

Last SMR checked: Nov-2026 (rows added 2026-11-22). Latest FUS build checked: `S906NKSS9GZH3` (SPL 2026-08-05).

FYG8 component hashes and build-ids (step 0, 2026-11-22):
[FYG8 component inventory](../reports/S22PLUS_FYG8_COMPONENT_INVENTORY_H0_2026-11-22.md).
- Observed on FYG8: most component families.
- Not found under the advisory spelling: `libsimba.heifdec.media.samsung.so`,
  `libimagecodec.media.quram.so`, `libmdnie.so`, `libsamsungtts.so` and
  `libcodec2secqcelpdec.so`. See the report's listing caveats.
- Observing a file does not promote a row to `PRESENT`; that also needs the
  code lineage.

## Evidence rule

Every item in this file starts at `PUBLISHED` only.

`PUBLISHED` means that Samsung publicly lists Android 15 inside the affected-version range, or that the vendor bulletin otherwise makes the item relevant enough to triage against FYG8. It does **not** prove that the exact FYG8 `SM-S906N` image contains the vulnerable component or vulnerable code lineage.

Promotion requires device/firmware-specific evidence:

- `PUBLISHED`: advisory claim only;
- `PRESENT`: relevant component and matching code lineage observed in exact FYG8 firmware;
- `DIFFED`: relevant pre/post-fix code delta identified;
- `REPRODUCED`: bounded runtime behavior reproduced on an isolated research target/sample.

Do not infer exploitability from Android-version membership alone.

## Lab layer

The lab's S22+ work runs native-init (Debian userspace) and mainline
kernels, not stock Android. The `Lab layer` column says whether a row's
component runs in that setup. It follows the triage fields "Stock-only
surface?" and "Native-PID1 + Debian surface?" below.

| Lab layer | Runs under native-init / mainline? |
|---|---|
| `stock userspace` | **No.** Samsung Android libraries, services and apps only execute when stock Android boots. Debian ships its own `wpa_supplicant`. The lab's modem path uses its own receivers, not Samsung RIL. |
| `Samsung kernel` | Only in native-init candidates built from the Samsung kernel, and only if their config enables the driver (check the candidate's IKCFG). Never in mainline. |
| `Samsung kernel?` | Kernel involvement is not stated by the advisory. Unverified. |
| `TEE` | Runs below every OS on the device. Reachable only through stock HLOS clients, which native-init does not start. |
| `CP firmware` | Modem firmware is loaded by the lab's modem work. **In scope of the lab stack.** |
| `boot chain` | Traversed by every boot, whatever kernel follows. **In scope of the lab stack.** |

Most rows are `stock userspace`, so they are curiosity-level for the lab.
The rows that touch the lab stack are the `boot chain`, `CP firmware` and
`TEE` rows, plus `Samsung kernel` rows on Samsung-kernel candidates.

## Backlog

| SMR | CVE | Component / boundary | Lab layer | Published impact | FYG8 state | Priority note |
|---|---|---|---|---|---|---|
| Sep-2025 | CVE-2025-21034 | `libsavsvc.so` | stock userspace | local OOB write; potential arbitrary code execution | `PRESENT` | pre-fix lineage confirmed FYG8→GYJ1 (917/917 exports); delta unlocalised in rebuild churn ([report](../reports/S22PLUS_FYG8_BACKLOG_LIBS_LINEAGE_H0_2026-11-22.md)) |
| Sep-2025 | CVE-2025-21043 | `libimagecodec.quram.so` | stock userspace | remote OOB write -> arbitrary code execution; Samsung notes exploit existed in the wild | `PRESENT` | **P0 first mini-study**; pre-fix lineage confirmed by FYG8→GYJ1 diff; per-CVE attribution open ([report](../reports/S22PLUS_FYG8_QURAM_DNG_PATCH_DIFF_H0_2026-11-22.md)) |
| Oct-2025 | CVE-2025-21044 | fingerprint trustlet | TEE | local privileged OOB write | `PUBLISHED` | TEE/trustlet boundary candidate |
| Oct-2025 | CVE-2025-21048 | Knox Enterprise | stock userspace | relative path traversal -> local arbitrary code execution | `PUBLISHED` | privileged-userspace boundary candidate |
| Oct-2025 | CVE-2025-21051 / 21052 / 21053 / 21054 | `libpadm.so` JPEG path | stock userspace | local OOB read/write and memory corruption | `PRESENT` | pre-fix lineage confirmed FYG8→GYJ1; candidate delta `padme_get_qt`; attribution open ([report](../reports/S22PLUS_FYG8_BACKLOG_LIBS_LINEAGE_H0_2026-11-22.md)) |
| Oct-2025 | CVE-2025-21055 | `libimagecodec.quram.so` | stock userspace | remote OOB read/write | `PRESENT` | same FYG8→GYJ1 diff (GYJ1 carries Sep+Oct fixes); attribution open |
| Nov-2025 | CVE-2025-21071 | fingerprint trustlet | TEE | local privileged OOB write | `PUBLISHED` | compare recurring fingerprint trustlet fixes |
| Nov-2025 | CVE-2025-21074 | `libimagecodec.quram.so` | stock userspace | remote OOB read | `PUBLISHED` | Quram lineage |
| Nov-2025 | CVE-2025-21075 | `libimagecodec.quram.so` | stock userspace | remote OOB write | `PUBLISHED` | Quram lineage |
| Dec-2025 | CVE-2025-21072 | fingerprint trustlet | TEE | local privileged OOB write | `PUBLISHED` | recurring trustlet-family candidate |
| Dec-2025 | CVE-2025-58475 | `libsec-ril.so` | stock userspace | local privileged OOB write | `PUBLISHED` | modem/RIL boundary candidate |
| Dec-2025 | CVE-2025-58477 | `libimagecodec.quram.so` | stock userspace | remote OOB write in IFD-tag parsing | `PUBLISHED` | parser-specific Quram diff candidate |
| Dec-2025 | CVE-2025-58478 | `libimagecodec.quram.so` | stock userspace | remote OOB write | `PUBLISHED` | Quram lineage |
| Dec-2025 | CVE-2025-58479 | `libimagecodec.quram.so` | stock userspace | remote OOB read | `PUBLISHED` | Quram lineage |
| Dec-2025 | CVE-2025-58480 | `libimagecodec.quram.so` | stock userspace | remote heap-based buffer overflow | `PUBLISHED` | higher-interest Quram memory-safety candidate |
| Jan-2026 | CVE-2026-20968 | DualDAR | Samsung kernel | UAF -> local privileged arbitrary code execution | `DIFFED` | `CONFIG_DDAR=y` in every native-init candidate; FYG8→GZH3 kernel delta confined to `dd_mmap` + new `dd_vm_close` ([report](../reports/S22PLUS_FYG8_GZH3_KERNEL_PROCA_DDAR_DIFF_H0_2026-11-22.md)) |
| Jan-2026 | CVE-2026-20971 | PROCA driver | Samsung kernel | UAF -> potential arbitrary code execution | `DIFFED` | **lab stack**: PROCA is an LSM, `=y` in every native-init candidate (pre-fix FYG8 source); 12/43 functions changed vs 1.6 % kernel baseline, in task-descriptor lifecycle; attribution by elimination ([report](../reports/S22PLUS_FYG8_GZH3_KERNEL_PROCA_DDAR_DIFF_H0_2026-11-22.md)) |
| Jan-2026 | CVE-2026-20973 | `libimagecodec.quram.so` | stock userspace | remote OOB read | `PUBLISHED` | long-running Quram lineage |
| Feb-2026 | CVE-2026-20980 | PACM | stock userspace | physical attacker may execute arbitrary commands | `PUBLISHED` | factory/service command boundary |
| Feb-2026 | CVE-2026-20981 | FacAtFunction | stock userspace | privileged physical attacker may execute arbitrary command with system privilege | `PUBLISHED` | service/factory interface candidate |
| Feb-2026 | CVE-2026-20982 | ShortcutService | stock userspace | path traversal -> create file with system privilege | `PUBLISHED` | privileged service filesystem boundary |
| Mar-2026 | CVE-2026-20990 | Secure Folder | stock userspace | local attacker may launch arbitrary activity with Secure Folder privilege | `PUBLISHED` | Knox/Secure Folder boundary |
| Mar-2026 | CVE-2026-21023 | PackageManagerService | stock userspace | local modification of installation restrictions | `PUBLISHED` | lower priority; policy-boundary reference |
| May-2026 | CVE-2026-21018 | SveService | stock userspace | local privileged OOB write -> arbitrary code execution | `PUBLISHED` | privileged native-service candidate |
| Jul-2026 | CVE-2026-21042 | `libsavsac.so` | stock userspace | remote OOB write -> arbitrary code execution | `PRESENT` | **high-value remote media candidate**; lineage FYG8→GZH3 continuous; only GYJ1→GZH3 delta is `sflacd_dec`; attribution open ([report](../reports/S22PLUS_GYJ1_GZH3_LIBS_DIFF_H0_2026-11-22.md)) |
| Jul-2026 | CVE-2026-21045 | `libimagecodec.media.quram.so` TIFF parser | stock userspace | remote OOB write | `PUBLISHED` | newer Quram/media naming lineage |
| Jul-2026 | CVE-2026-21046 | fabricKeymaster trustlet | TEE | TOCTOU -> local privileged arbitrary code execution | `PUBLISHED` | **high-value TEE candidate** |
| Jul-2026 | CVE-2026-21047 | ImsService | stock userspace | remote OOB write -> potential arbitrary code execution | `PUBLISHED` | **high-value telephony/IMS candidate** |
| Jul-2026 | CVE-2026-21048 | `libimagecodec.media.quram.so` DNG parser | stock userspace | remote OOB write | `PUBLISHED` | Quram DNG lineage |
| Jul-2026 | CVE-2026-21049 | `libpadm.so` | stock userspace | local OOB write -> arbitrary code execution | `PUBLISHED` | **no fix visible**: all four `libpadm.so` copies byte-identical GYJ1→GZH3 (SPL 2026-08-05) despite "Android 14, 15, 16" ([report](../reports/S22PLUS_GYJ1_GZH3_LIBS_DIFF_H0_2026-11-22.md)) |
| Aug-2026 | CVE-2026-21068 | `libril_sem.so` | stock userspace | privileged local stack-buffer overflow -> arbitrary code execution | `PUBLISHED` | **high-value RIL boundary candidate** |
| Aug-2026 | CVE-2026-21069 | `libsavsvc.so` VC1 codec | stock userspace | numeric-conversion bug -> local OOB write | `DIFFED` | GYJ1→GZH3 delta confined to VC1/MPEG4 decoder functions (system + vendor); per-CVE attribution open ([report](../reports/S22PLUS_GYJ1_GZH3_LIBS_DIFF_H0_2026-11-22.md)) |
| Aug-2026 | CVE-2026-21071 | `libsavsvc.so` MPEG4 codec | stock userspace | local OOB write | `DIFFED` | only MPEG4 function changed: `smp4vd_vld_mb_dp` ([report](../reports/S22PLUS_GYJ1_GZH3_LIBS_DIFF_H0_2026-11-22.md)) |
| Aug-2026 | CVE-2026-21072 | `libsavsvc.so` VC1 codec | stock userspace | local OOB write | `DIFFED` | same VC1 delta as 21069; split between the two open ([report](../reports/S22PLUS_GYJ1_GZH3_LIBS_DIFF_H0_2026-11-22.md)) |
| Aug-2026 | CVE-2026-21065 | `libcodec2secqcelpdec.so` | stock userspace | local OOB write | `PUBLISHED` | optional codec2/vendor media surface |
| Aug-2026 | CVE-2026-21066 | `libcodec2_sec_flacdec.so` | stock userspace | local OOB write | `PUBLISHED` | optional codec2/vendor media surface |
| Sep-2026 | CVE-2026-21095 | `libimagecodec.quram.so` DNG decoder | stock userspace | remote heap-buffer overflow -> arbitrary code execution | `PUBLISHED` | **critical Quram endpoint** |
| Sep-2026 | CVE-2026-21096 | `libimagecodec.quram.so` JPEG decoder | stock userspace | remote heap-buffer overflow -> arbitrary code execution | `PUBLISHED` | **critical Quram endpoint** |
| Sep-2026 | CVE-2026-21087 | `libmdnie.so` | stock userspace | local arbitrary code execution with system-server privilege | `PUBLISHED` | display/system-server boundary |
| Sep-2026 | CVE-2026-21094 | `wpa_supplicant` | stock userspace | adjacent attacker OOB write | `PUBLISHED` | **high-value network-facing candidate** |
| Sep-2026 | CVE-2026-21104 | KnoxVault trustlet | TEE | local privileged heap-buffer overflow -> arbitrary code execution | `PUBLISHED` | **high-value secure-world-adjacent candidate** |
| Sep-2026 | CVE-2026-21085 | Keymaster trustlet | TEE | local privileged OOB write | `PUBLISHED` | TEE/key-management boundary |
| Sep-2026 | CVE-2026-21092 | ImsService | stock userspace | remote path traversal -> image-file creation with system-server privilege | `PUBLISHED` | remote privileged-service boundary |
| Sep-2026 | CVE-2026-21101 | DualDAR driver | Samsung kernel | local privileged input-validation bug -> potential root arbitrary code execution | `PUBLISHED` | **root-boundary candidate** |
| Sep-2026 | CVE-2026-21093 | PROCA trustlet | TEE | local privileged stack-buffer overflow -> OOB write | `PUBLISHED` | TEE/PROCA candidate |
| Sep-2026 | CVE-2026-21102 | DualDAR | Samsung kernel? | UAF -> local privileged arbitrary code execution with root privilege | `PUBLISHED` | **root-boundary candidate** |
| Oct-2026 | CVE-2026-21114 | `libsmkvextractor.so` | stock userspace | local OOB write -> arbitrary code execution | `PUBLISHED` | MKV extractor lineage (also 21116, 21156); GYJ1 also pre-fix (control in [lineage report](../reports/S22PLUS_FYG8_BACKLOG_LIBS_LINEAGE_H0_2026-11-22.md)) |
| Oct-2026 | CVE-2026-21116 | `libsmkvextractor.so` | stock userspace | local OOB write | `PUBLISHED` | MKV extractor lineage |
| Oct-2026 | CVE-2026-21120 | WSM service | stock userspace | UAF -> potential arbitrary code execution with system privilege | `PUBLISHED` | privileged native-service candidate |
| Oct-2026 | CVE-2026-21122 | `libsamsungtts.so` | stock userspace | local OOB write -> arbitrary code execution | `PUBLISHED` | TTS engine surface |
| Oct-2026 | CVE-2026-21124 / 21125 / 21126 | `libsimba.heifdec.media.samsung.so` (cover image, `sheifd` parsing) | stock userspace | input validation / OOB write -> potential arbitrary code execution | `PUBLISHED` | **new HEIF parser family**; compare with Quram lineage |
| Oct-2026 | CVE-2026-21123 | Locksettings | stock userspace | root attacker can access tied-profile data before first unlock | `PUBLISHED` | credential/profile-encryption boundary |
| Oct-2026 | CVE-2026-21115 | `libcodec2-sec-flacdec.so` | stock userspace | local OOB write | `PUBLISHED` | follow-up to CVE-2026-21066 |
| Oct-2026 | CVE-2026-21117 | CocktailBarService | stock userspace | sensitive information access (access control) | `PUBLISHED` | low priority |
| Oct-2026 | CVE-2026-21118 | DownloadProvider | stock userspace | access to files in scoped storage | `PUBLISHED` | low priority |
| Nov-2026 | CVE-2026-21155 | bootloader | boot chain | physical attacker OOB write | `PUBLISHED` | **bootloader boundary**; static diff only (lab ABL work, see contract) |
| Nov-2026 | CVE-2026-21158 | CP | CP firmware | local privileged attacker SIM-lock bypass (improper certificate validation) | `PUBLISHED` | modem/CP boundary; diff-only, never reproduce |
| Nov-2026 | CVE-2026-21153 | `libsecuibc.so` | stock userspace | stack buffer overflow -> local arbitrary code execution | `PUBLISHED` | privileged native-library candidate; GYJ1 also pre-fix (control in [lineage report](../reports/S22PLUS_FYG8_BACKLOG_LIBS_LINEAGE_H0_2026-11-22.md)) |
| Nov-2026 | CVE-2026-21154 | `libsecuibc.so` | stock userspace | dump-data access (improper authorization) | `PUBLISHED` | same library as 21153 |
| Nov-2026 | CVE-2026-21152 | `libMyFilterPlugin.camera.samsung.so` | stock userspace | potential local arbitrary code execution (user interaction) | `PUBLISHED` | camera plugin surface |
| Nov-2026 | CVE-2026-21151 | TransitionPlayer | stock userspace | privileged local arbitrary code execution with launcher privilege | `PUBLISHED` | launcher boundary |
| Nov-2026 | CVE-2026-21156 | `libsmkvextractor.so` | stock userspace | local OOB write | `PUBLISHED` | MKV extractor lineage |
| Nov-2026 | CVE-2026-21149 | StatusBarManagerService | stock userspace | privileged API use | `PUBLISHED` | system-server policy boundary |
| Nov-2026 | CVE-2026-21150 | edmnativehelper | stock userspace | sensitive information access (Android 15–17 only) | `PUBLISHED` | Knox/EDM native helper |
| Nov-2026 | CVE-2026-21148 | Samsung Messages | stock userspace | sensitive information access (incorrect authorization) | `PUBLISHED` | app-level, low priority |
| Nov-2026 | CVE-2026-21141 / 21142 | Samsung Dialer / Contacts | stock userspace | information / profile-config access | `PUBLISHED` | app-level, low priority |
| Nov-2026 | CVE-2026-21143 – 21147 | Samsung Contacts widget/cover-screen components | stock userspace | place calls without permission (exported components) | `PUBLISHED` | app-level, low priority; one family |

Oct/Nov-2026 notes:

- Rows come from the official bulletin page, read 2026-11-22 by automated fetch. Recheck each against the advisory before promotion.
- Excluded because the stated range omits Android 15: CVE-2026-21119 ("Selected Android 16, 17") and CVE-2026-21121 ("Android XR 14").
- Samsung announced 27 SVE items for Oct and 24 for Nov, but disclosed only 13 and 17. The rest are marked "cannot be disclosed at this time".

## Suggested research lanes

Rather than analyzing the list chronologically, use one representative candidate per boundary:

1. **Remote parser** — `CVE-2025-21043` first, then later Quram or `CVE-2026-21042`.
2. **Privileged Android userspace** — `CVE-2025-21048` or ImsService (`CVE-2026-21047`).
3. **Kernel / driver** — PROCA (`CVE-2026-20971`) or DualDAR (`CVE-2026-20968`).
4. **TEE / trustlet** — fabricKeymaster (`CVE-2026-21046`) or KnoxVault (`CVE-2026-21104`).
5. **Network / radio** — `wpa_supplicant` (`CVE-2026-21094`) or `libril_sem.so` (`CVE-2026-21068`).
6. **Boot chain (added 2026-11-22)** — bootloader `CVE-2026-21155`. Static diff only. It overlaps the lab's ABL evidence, but any reproduction would cross the device-safety contract.

**Lab-stack order (2026-11-22).** When the goal is the lab's own stack rather
than curiosity, take lanes in this order: boot chain (6), then CP firmware
(`CVE-2026-21158`), then TEE (4), then kernel (3), the last only for
Samsung-kernel candidates. All of these stay static diff only. Lanes 1, 2 and
5 are `stock userspace`; see [Lab layer](#lab-layer).

This avoids turning the side track into a single-library Quram study and instead covers different Samsung security boundaries on the same preserved FYG8 platform.

## First-pass triage fields

For every candidate promoted beyond `PUBLISHED`, record at minimum:

```text
CVE:
SMR fixed in:
Affected Android range:
Exact FYG8 component path:
SHA-256:
ELF build-id:
Process / SELinux domain / UID if applicable:
Patched comparison firmware:
Patched component SHA-256:
Patch-diff function(s):
Reachability evidence:
Current state: PUBLISHED | PRESENT | DIFFED | REPRODUCED
Stock-only surface?: yes / no / unknown
Native-PID1 + Debian surface?: present / removed / unknown
Notes / uncertainty:
```

## Safety and scope

- Keep physical FYG8 baseline preservation separate from comparison-firmware acquisition.
- Do not update the research device solely to obtain a patched binary.
- Prefer offline firmware extraction and static diff before runtime reproduction.
- A crash is not equivalent to control-flow hijack or arbitrary code execution.
- Do not publish exploit weaponization as a default deliverable.
- Main S22+ native-init work remains the primary project track.

## Public source basis

Primary source for this backlog is Samsung Mobile Security monthly SMR material for Sep-2025 through Nov-2026. Candidate descriptions should be rechecked against the current vendor advisory before promotion from `PUBLISHED`.

- https://security.samsungmobile.com/securityUpdate.smsb
