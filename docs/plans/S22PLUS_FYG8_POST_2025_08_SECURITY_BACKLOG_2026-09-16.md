# S22+ FYG8 post-2025-08 security backlog

Date: 2026-09-16
Target: Samsung Galaxy S22+ `SM-S906N` / `g0q`
Baseline: `S906NKSS7FYG8`, Android 15, 2025-08 security patch
Status: candidate backlog only; no device action is authorized by this document.

Related planning memo:

- `docs/plans/S22PLUS_FYG8_SECURITY_SIDE_TRACK_CANDIDATES_2026-09-16.md`

## Evidence rule

Every item in this file starts at `PUBLISHED` only.

`PUBLISHED` means that Samsung publicly lists Android 15 inside the affected-version range, or that the vendor bulletin otherwise makes the item relevant enough to triage against FYG8. It does **not** prove that the exact FYG8 `SM-S906N` image contains the vulnerable component or vulnerable code lineage.

Promotion requires device/firmware-specific evidence:

- `PUBLISHED`: advisory claim only;
- `PRESENT`: relevant component and matching code lineage observed in exact FYG8 firmware;
- `DIFFED`: relevant pre/post-fix code delta identified;
- `REPRODUCED`: bounded runtime behavior reproduced on an isolated research target/sample.

Do not infer exploitability from Android-version membership alone.

## Backlog

| SMR | CVE | Component / boundary | Published impact | FYG8 state | Priority note |
|---|---|---|---|---|---|
| Sep-2025 | CVE-2025-21034 | `libsavsvc.so` | local OOB write; potential arbitrary code execution | `PUBLISHED` | first proprietary video-codec diff candidate |
| Sep-2025 | CVE-2025-21043 | `libimagecodec.quram.so` | remote OOB write -> arbitrary code execution; Samsung notes exploit existed in the wild | `PUBLISHED` | **P0 first mini-study**; closest high-value fix after FYG8 baseline |
| Oct-2025 | CVE-2025-21044 | fingerprint trustlet | local privileged OOB write | `PUBLISHED` | TEE/trustlet boundary candidate |
| Oct-2025 | CVE-2025-21048 | Knox Enterprise | relative path traversal -> local arbitrary code execution | `PUBLISHED` | privileged-userspace boundary candidate |
| Oct-2025 | CVE-2025-21051 / 21052 / 21053 / 21054 | `libpadm.so` JPEG path | local OOB read/write and memory corruption | `PUBLISHED` | alternate Samsung JPEG implementation family |
| Oct-2025 | CVE-2025-21055 | `libimagecodec.quram.so` | remote OOB read/write | `PUBLISHED` | useful Quram lineage follow-up |
| Nov-2025 | CVE-2025-21071 | fingerprint trustlet | local privileged OOB write | `PUBLISHED` | compare recurring fingerprint trustlet fixes |
| Nov-2025 | CVE-2025-21074 | `libimagecodec.quram.so` | remote OOB read | `PUBLISHED` | Quram lineage |
| Nov-2025 | CVE-2025-21075 | `libimagecodec.quram.so` | remote OOB write | `PUBLISHED` | Quram lineage |
| Dec-2025 | CVE-2025-21072 | fingerprint trustlet | local privileged OOB write | `PUBLISHED` | recurring trustlet-family candidate |
| Dec-2025 | CVE-2025-58475 | `libsec-ril.so` | local privileged OOB write | `PUBLISHED` | modem/RIL boundary candidate |
| Dec-2025 | CVE-2025-58477 | `libimagecodec.quram.so` | remote OOB write in IFD-tag parsing | `PUBLISHED` | parser-specific Quram diff candidate |
| Dec-2025 | CVE-2025-58478 | `libimagecodec.quram.so` | remote OOB write | `PUBLISHED` | Quram lineage |
| Dec-2025 | CVE-2025-58479 | `libimagecodec.quram.so` | remote OOB read | `PUBLISHED` | Quram lineage |
| Dec-2025 | CVE-2025-58480 | `libimagecodec.quram.so` | remote heap-based buffer overflow | `PUBLISHED` | higher-interest Quram memory-safety candidate |
| Jan-2026 | CVE-2026-20968 | DualDAR | UAF -> local privileged arbitrary code execution | `PUBLISHED` | kernel/root-oriented boundary candidate |
| Jan-2026 | CVE-2026-20971 | PROCA driver | UAF -> potential arbitrary code execution | `PUBLISHED` | **high-value kernel/driver candidate** |
| Jan-2026 | CVE-2026-20973 | `libimagecodec.quram.so` | remote OOB read | `PUBLISHED` | long-running Quram lineage |
| Feb-2026 | CVE-2026-20980 | PACM | physical attacker may execute arbitrary commands | `PUBLISHED` | factory/service command boundary |
| Feb-2026 | CVE-2026-20981 | FacAtFunction | privileged physical attacker may execute arbitrary command with system privilege | `PUBLISHED` | service/factory interface candidate |
| Feb-2026 | CVE-2026-20982 | ShortcutService | path traversal -> create file with system privilege | `PUBLISHED` | privileged service filesystem boundary |
| Mar-2026 | CVE-2026-20990 | Secure Folder | local attacker may launch arbitrary activity with Secure Folder privilege | `PUBLISHED` | Knox/Secure Folder boundary |
| Mar-2026 | CVE-2026-21023 | PackageManagerService | local modification of installation restrictions | `PUBLISHED` | lower priority; policy-boundary reference |
| May-2026 | CVE-2026-21018 | SveService | local privileged OOB write -> arbitrary code execution | `PUBLISHED` | privileged native-service candidate |
| Jul-2026 | CVE-2026-21042 | `libsavsac.so` | remote OOB write -> arbitrary code execution | `PUBLISHED` | **high-value remote media candidate** |
| Jul-2026 | CVE-2026-21045 | `libimagecodec.media.quram.so` TIFF parser | remote OOB write | `PUBLISHED` | newer Quram/media naming lineage |
| Jul-2026 | CVE-2026-21046 | fabricKeymaster trustlet | TOCTOU -> local privileged arbitrary code execution | `PUBLISHED` | **high-value TEE candidate** |
| Jul-2026 | CVE-2026-21047 | ImsService | remote OOB write -> potential arbitrary code execution | `PUBLISHED` | **high-value telephony/IMS candidate** |
| Jul-2026 | CVE-2026-21048 | `libimagecodec.media.quram.so` DNG parser | remote OOB write | `PUBLISHED` | Quram DNG lineage |
| Jul-2026 | CVE-2026-21049 | `libpadm.so` | local OOB write -> arbitrary code execution | `PUBLISHED` | media/JPEG lineage candidate |
| Aug-2026 | CVE-2026-21068 | `libril_sem.so` | privileged local stack-buffer overflow -> arbitrary code execution | `PUBLISHED` | **high-value RIL boundary candidate** |
| Aug-2026 | CVE-2026-21069 | `libsavsvc.so` VC1 codec | numeric-conversion bug -> local OOB write | `PUBLISHED` | codec lineage candidate |
| Aug-2026 | CVE-2026-21071 | `libsavsvc.so` MPEG4 codec | local OOB write | `PUBLISHED` | codec lineage candidate |
| Aug-2026 | CVE-2026-21072 | `libsavsvc.so` VC1 codec | local OOB write | `PUBLISHED` | codec lineage candidate |
| Aug-2026 | CVE-2026-21065 | `libcodec2secqcelpdec.so` | local OOB write | `PUBLISHED` | optional codec2/vendor media surface |
| Aug-2026 | CVE-2026-21066 | `libcodec2_sec_flacdec.so` | local OOB write | `PUBLISHED` | optional codec2/vendor media surface |
| Sep-2026 | CVE-2026-21095 | `libimagecodec.quram.so` DNG decoder | remote heap-buffer overflow -> arbitrary code execution | `PUBLISHED` | **critical Quram endpoint** |
| Sep-2026 | CVE-2026-21096 | `libimagecodec.quram.so` JPEG decoder | remote heap-buffer overflow -> arbitrary code execution | `PUBLISHED` | **critical Quram endpoint** |
| Sep-2026 | CVE-2026-21087 | `libmdnie.so` | local arbitrary code execution with system-server privilege | `PUBLISHED` | display/system-server boundary |
| Sep-2026 | CVE-2026-21094 | `wpa_supplicant` | adjacent attacker OOB write | `PUBLISHED` | **high-value network-facing candidate** |
| Sep-2026 | CVE-2026-21104 | KnoxVault trustlet | local privileged heap-buffer overflow -> arbitrary code execution | `PUBLISHED` | **high-value secure-world-adjacent candidate** |
| Sep-2026 | CVE-2026-21085 | Keymaster trustlet | local privileged OOB write | `PUBLISHED` | TEE/key-management boundary |
| Sep-2026 | CVE-2026-21092 | ImsService | remote path traversal -> image-file creation with system-server privilege | `PUBLISHED` | remote privileged-service boundary |
| Sep-2026 | CVE-2026-21101 | DualDAR driver | local privileged input-validation bug -> potential root arbitrary code execution | `PUBLISHED` | **root-boundary candidate** |
| Sep-2026 | CVE-2026-21093 | PROCA trustlet | local privileged stack-buffer overflow -> OOB write | `PUBLISHED` | TEE/PROCA candidate |
| Sep-2026 | CVE-2026-21102 | DualDAR | UAF -> local privileged arbitrary code execution with root privilege | `PUBLISHED` | **root-boundary candidate** |

## Suggested research lanes

Rather than analyzing the list chronologically, use one representative candidate per boundary:

1. **Remote parser** — `CVE-2025-21043` first, then later Quram or `CVE-2026-21042`.
2. **Privileged Android userspace** — `CVE-2025-21048` or ImsService (`CVE-2026-21047`).
3. **Kernel / driver** — PROCA (`CVE-2026-20971`) or DualDAR (`CVE-2026-20968`).
4. **TEE / trustlet** — fabricKeymaster (`CVE-2026-21046`) or KnoxVault (`CVE-2026-21104`).
5. **Network / radio** — `wpa_supplicant` (`CVE-2026-21094`) or `libril_sem.so` (`CVE-2026-21068`).

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

Primary source for this backlog is Samsung Mobile Security monthly SMR material for Sep-2025 through Sep-2026. Candidate descriptions should be rechecked against the current vendor advisory before promotion from `PUBLISHED`.

- https://security.samsungmobile.com/securityUpdate.smsb
