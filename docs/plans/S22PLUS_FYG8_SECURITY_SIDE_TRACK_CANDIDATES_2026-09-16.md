# S22+ FYG8 security side-track candidates

Date: 2026-09-16
Target: Samsung Galaxy S22+ `SM-S906N` / `g0q`
Baseline: `S906NKSS7FYG8`, Android 15, 2025-08 security patch
Status: candidate memo only; no device action is authorized by this document.

Related: [post-2025-08 CVE backlog](S22PLUS_FYG8_POST_2025_08_SECURITY_BACKLOG_2026-09-16.md),
[RF-sensing side track](S22PLUS_RF_SENSING_SIDE_TRACK_CANDIDATES_2026-11-21.md)
(Candidate E shares its Qualcomm WLAN host driver target).

## Purpose

Record a bounded security-research side track for the preserved FYG8 baseline without displacing the main native-PID1 / Debian bring-up work.

The intended value is not "build an exploit". The useful outputs are:

- verify which post-2025-08 Samsung/Android vulnerabilities actually map to the exact FYG8 image;
- confirm the relevant proprietary component and vulnerable code lineage are present;
- compare pre-fix and post-fix binaries where both firmware samples are available;
- identify the patched validation or memory-safety boundary;
- document reachability and affected privilege boundary without overstating exploitability;
- compare stock Android attack surface with the reduced native-PID1 / Debian userspace surface;
- keep reproducible hashes, firmware identity and evidence boundaries.

## Scope boundary

This track should remain secondary to the S22+ bring-up frontier.

Default stopping point for each candidate:

1. advisory and affected-version verification;
2. exact FYG8 component-presence verification;
3. exact binary hash / ELF build-id capture;
4. patched comparison sample identification;
5. static binary diff and root-cause hypothesis;
6. optional bounded local crash / memory-safety reproduction in an isolated research setup;
7. stop before exploit weaponization unless a separate explicit research decision is made.

Do not infer that every CVE published after 2025-08 affects FYG8. Each item must independently prove:

- Android 15 is affected;
- the relevant component exists on `SM-S906N` FYG8;
- the FYG8 binary belongs to the vulnerable code lineage;
- no independent Mainline/app/module update already removed the vulnerable path;
- the claimed call path is reachable in the tested configuration.

## Candidate A — Quram image-codec lineage

Priority: high

### CVE-2025-21043

Candidate reason:

- Samsung `libimagecodec.quram.so`;
- remote memory-corruption / arbitrary-code-execution class;
- patched immediately after the FYG8 2025-08 baseline;
- public reporting indicates in-the-wild exploitation, making it a useful ground-truth candidate;
- strong comparison point for later Quram fixes.

Suggested questions:

- Is `libimagecodec.quram.so` present in the exact FYG8 system image, and at what path?
- What SHA-256 and ELF build-id identify it?
- Can the corresponding first patched S22+ firmware be obtained without changing the physical research device?
- Which functions differ between the FYG8 and first-patched binaries?
- Does the patch add bounds checking, integer/size validation, or change allocation/copy behavior?
- Which Android service / framework path reaches the decoder on FYG8?

### CVE-2025-21055

Candidate reason:

- later Quram memory-corruption issue;
- useful for testing whether multiple fixes cluster in the same parser/decoder families;
- can show whether the proprietary image surface accumulated repeated security debt across releases.

### CVE-2026-21095 / CVE-2026-21096

Candidate reason:

- 2026-09 DNG/JPEG critical RCE-class fixes in `libimagecodec.quram.so`;
- Android 15 is inside the published affected-version range;
- FYG8 predates the fix by roughly a year;
- useful long-range diff target if the vulnerable lineage is confirmed on FYG8.

Research note: affected-version membership alone is not proof that the exact FYG8 binary contains the final vulnerable function. Confirm by component and binary lineage.

## Candidate B — Samsung proprietary video codec

Priority: medium

### CVE-2025-21034

Component candidate: `libsavsvc.so`

Candidate reason:

- native OOB-write / potential code-execution class;
- Android 15 is within the published affected range;
- different attack surface from Quram, useful for learning media-codec reverse engineering rather than only image parsers.

First gate:

- locate `libsavsvc.so` in extracted FYG8 images;
- if absent, close this candidate for FYG8 rather than broadening the claim;
- if present, preserve hash/build-id and locate a patched comparison binary.

## Candidate C — Knox / privileged userspace boundary

Priority: high after one successful binary-diff exercise

### CVE-2025-21048

Candidate reason:

- Knox Enterprise path-traversal / arbitrary-code-execution class;
- provides a materially different boundary from media parsing;
- useful for mapping which Samsung privileged services are removed when moving away from stock Android userspace.

Questions:

- Which package/service/library owns the vulnerable path on FYG8?
- What SELinux domain and Linux UID does the relevant process use?
- What filesystem locations are writable/readable across the vulnerable boundary?
- Is the component present or required in the intended Debianized configuration?

## Candidate D — Trustlet / secure-world-adjacent fixes

Priority: later / architecture-focused

Candidates to triage from post-FYG8 Samsung SMRs include Keymaster, fingerprint, KnoxVault and other trustlet fixes whose affected-version range includes Android 15.

Purpose:

- map normal-world -> TEE/trustlet entry surfaces;
- understand which security boundaries remain even after Android userspace reduction;
- distinguish Android service removal from immutable vendor/secure-world dependencies.

Do not treat a trustlet CVE as reachable from an unprivileged app until the exact FYG8 client path and required privilege are demonstrated.

## Candidate E — Wi-Fi / network-facing native components

Priority: medium

Post-FYG8 Samsung/Android fixes involving `wpa_supplicant`, vendor Wi-Fi services or adjacent-network memory corruption are useful because they survive a different threat model than Gallery/IMS/Knox userspace.

Key question for the native-PID1 project:

> If Samsung Android userspace is removed but the stock kernel/vendor Wi-Fi stack remains, which patched vulnerabilities disappear and which remain reachable?

This gives a concrete security comparison between:

- stock FYG8 Android;
- reduced Samsung userspace;
- native PID1 + Debian userspace using retained vendor/kernel support.

## Proposed first mini-study

Start with `CVE-2025-21043` because it has the strongest evidence and sits immediately after the preserved FYG8 baseline.

Minimal deliverables:

- exact FYG8 firmware identity;
- exact Quram library path;
- SHA-256 and ELF build-id;
- first known patched S22+ firmware identity;
- patched library hash/build-id;
- static diff notes naming changed functions where defensible;
- root-cause hypothesis marked as hypothesis until independently supported;
- stock reachability map;
- short note describing whether the same attack surface exists in the current native-PID1 / Debian design.

Success does not require arbitrary code execution. A defensible binary-lineage confirmation plus a bounded patch/root-cause analysis is sufficient.

## Suggested evidence structure

For each candidate keep four states separate:

- `PUBLISHED`: vendor/advisory claim only;
- `PRESENT`: affected component/binary observed on exact FYG8;
- `DIFFED`: relevant pre/post patch code change identified;
- `REPRODUCED`: bounded runtime behavior reproduced on the research target or equivalent isolated sample.

Never promote one state into another without direct evidence.

## Expected project value

This side track can produce three useful outputs beyond vulnerability research itself:

1. a reproducible Samsung firmware reverse-engineering exercise using real patch deltas;
2. a concrete security comparison showing which Android attack surfaces are removed by the native-PID1 / Debian design and which kernel/vendor/TEE surfaces remain;
3. portfolio-quality evidence of firmware triage, ELF analysis, patch diffing, privilege-boundary mapping and evidence discipline.

## Non-goals

- maintaining a public exploit repository;
- testing against third-party devices or services;
- treating CVSS/advisory text as proof of exact-device exploitability;
- updating the physical FYG8 device solely to obtain patched comparison binaries;
- crossing Samsung anti-rollback / SW REV boundaries without a separate project decision;
- allowing this side track to block the main S22+ native-init milestone.

## Update 2026-11-22

State: no candidate has left `PUBLISHED`. The backlog now runs through
SMR Nov-2026.

### Local evidence location (corrected 2026-11-22)

- **The FYG8 logical images are on the external lab disk, not under
  `workspace/private`.** An earlier same-day note here wrongly said they were
  absent. The module-map manifest names old `super-corpus-work` paths that no
  longer exist, but an existing extraction sits at
  `/mnt/android-lab-sd/extract/ap-fyg8/`:
  - `super.img`, plus `logical/{system,system_ext,product,vendor,odm}.img`;
  - boot, vendor_boot, dtbo, recovery, vbmeta and vendor_dlkm images.
- **It is bound to FYG8.** Checked 2026-11-22:
  - `boot`, `vendor_boot`, `dtbo` and `vbmeta` match the retained FYG8
    extractions byte for byte (sha256).
  - `vendor_dlkm.img` matches the module-map manifest
    (`e5386d68…6b26`).
  - The source SamFW ZIP is on the same disk; the
    [evidence policy](../operations/S22PLUS_FYG8_STOCK_FIRMWARE_EVIDENCE_POLICY_2026-07-08.md)
    pins its hash.
  - The extraction log records `super.img` sha256 `f418abff…43c8` but
    `content_checksum_verified: false`. The AVB binding below closes that gap.
- **AVB binding: `ALL_VERIFIED` (2026-11-22, host-only, read-only).**
  - **ZIP and AP tar.** The ZIP sha256 equals the policy value `f831e5fb…a2c8`.
    A streamed pass over the ZIP gives an AP tar sha256 equal to the policy
    value `7934579f…0bb2`.
  - **vbmeta.** `vbmeta.img` (`1031323a…047b`) and `vbmeta_system.img`
    (`6d19a37e…4f96`) taken straight from that AP tar are byte-identical to
    the SD copies.
  - **Signatures.** Both vbmeta signatures verify (SHA256_RSA4096, public key
    sha1 `e03300ab66600a17e63d91ad7f2357380a46a65c`).
  - **dtbo.** The chained dtbo footer verifies with the same key, and its own
    hash matches.
  - **Hash descriptors.** `boot` and `vendor_boot` match.
  - **Hashtree descriptors.** All regenerate to the descriptor root digest and
    match the on-disk tree: `system`, `system_ext`, `product`, `vendor`, `odm`
    and `vendor_dlkm`. Root digests agree between `vbmeta` and
    `vbmeta_system`.
  - **Not covered.** `abl`, `hyp`, `tz` and `xbl` are BL-side; `recovery` was
    not included in this run; `prism` and `optics` have no image on disk.
  - **What the chain proves.** Origin comes from the policy-pinned ZIP hash.
    Signatures and hashtrees bind every logical image block to it.
  - Script and result: private analysis `s22plus-fyg8-avb-binding.r3EEIvVg`
    (`verify.py`, `zip-extract.sh`, `verified.json`).
- No re-download is needed. `PRESENT` checks for
  `libimagecodec.quram.so`, `libsavsvc.so`, `libpadm.so` and the rest can
  read these images read-only.
- **One local `libsec-ril.so` copy exists.** sha256 `d1878d44…455f`, ELF
  build-id `133163f8ddf06a70e7c1bb05fd96423d`, kept under the private FYG1
  AP/CP baseline analysis. Its acquisition path is not recorded in that
  analysis's `verify.py`. Bind it to the FYG8 vendor image before using it for
  CVE-2025-58475.

### Comparison firmware

- The S22 series moved to One UI 8 (Android 16) in late 2025. Reported later
  S906N builds include `S906NKSS9GZE5` (May 2026), and S22 patches were reported
  through at least Aug-2026 (secondary sources).
- Patched comparison binaries will therefore mostly come from the Android 16
  lineage. Expect diff noise beyond the security fix. Prefer the first patched
  Android 15 build where one exists.
- Binary revision 9 against FYG8's 7 means anti-rollback. Acquire comparison
  firmware offline only; never flash it to the research device.

### Candidate A reference

- Google Project Zero, "android-itw-dng" (Benoît Sevens, 2025-12-12), analyzes
  an in-the-wild Quram DNG exploit whose bug "was fixed in April 2025". That
  predates FYG8, so it is a methodology and lineage reference, not an FYG8
  target.
- Attributing it to CVE-2025-21042 / LANDFALL (Unit 42, 2025-11-07) is a
  recollection and was not confirmed in the page text read.
- CVE-2025-21043 still has no authoritative root-cause write-up. Secondary
  blogs disagree (DNG opcode-count check vs IFD entry-size check), so the patch
  diff stays the deciding evidence.

### New boundary families from Oct/Nov 2026

- HEIF decoder `libsimba.heifdec.media.samsung.so`: a second image-parser
  family next to Quram.
- `libsmkvextractor.so`: three fixes in two months.
- Bootloader CVE-2026-21155: physical OOB write; static diff only.
- CP CVE-2026-21158: SIM-lock certificate validation; diff only, never reproduce.
