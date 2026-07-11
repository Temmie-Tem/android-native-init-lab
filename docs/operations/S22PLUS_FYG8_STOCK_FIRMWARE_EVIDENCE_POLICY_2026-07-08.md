# S22+ FYG8 Stock Firmware Evidence Policy

Date: 2026-07-08

Scope: Samsung S22+ `SM-S906N` / `g0q` / `S906NKSS7FYG8`.

Current evidence note, 2026-07-11: the original ZIP remains intentionally
removed, while the complete six-file extracted stock firmware set listed below
is present again. A live helper must still verify every exact size and SHA256;
directory presence alone does not satisfy this policy.

This document defines the local evidence accepted when `AGENTS.md` requires the
full stock `S906NKSS7FYG8` firmware to be present before an S22+ recovery or
boot-only live gate.

Either evidence form is acceptable:

1. Original SamFW full firmware ZIP:
   - Path: `workspace/private/inputs/firmware/SAMFW.COM_SM-S906N_SKC_S906NKSS7FYG8_fac.zip`
   - SHA256: `f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8`

2. Extracted stock firmware set:
   - Directory: `workspace/private/inputs/firmware/SAMFW.COM_SM-S906N_SKC_S906NKSS7FYG8_fac/`
   - All six files below must exist with exact byte size and SHA256:

| File | Size | SHA256 |
| --- | ---: | --- |
| `AP_S906NKSS7FYG8_S906NKSS7FYG8_MQB99315260_REV00_user_low_ship_MULTI_CERT_meta_OS15.tar.md5` | 11499653242 | `7934579fc2e7fc8097b58cb28e915578a972718b2cdc3f53d3f9b5e9bd5a0bb2` |
| `BL_S906NKSS7FYG8_S906NKSS7FYG8_MQB99315260_REV00_user_low_ship_MULTI_CERT.tar.md5` | 114319472 | `e5aeb59de4ed16c21111945900aeda4743b717361b0919084e9d284d08e4e0ba` |
| `CP_S906NKSS7FYG1_CP30713288_MQB98036461_REV00_user_low_ship_MULTI_CERT.tar.md5` | 68833389 | `08495982043835aa233061c70dfc42b327684e93cf7c7e02d89278a5ea3ec445` |
| `CSC_OKR_S906NOKR7FYG8_MQB99315260_REV00_user_low_ship_MULTI_CERT.tar.md5` | 24811623 | `bb13931519fa48a9a9a08c2a00619088e037650fd573280296dedcaa5355984d` |
| `HOME_CSC_OKR_S906NOKR7FYG8_MQB99315260_REV00_user_low_ship_MULTI_CERT.tar.md5` | 24780908 | `b8753e80cf1053b0dfe33ecdc3389c6c5c0df41ae5184d4b221ec9fe0672c514` |
| `_FirmwareInfo_Samfw.com.txt` | 719 | `80daa81f48e8928827f804a34156f9d7cf2df2d7dc6160748d3b4296c674146f` |

The extracted set was verified against the ZIP member list by matching member
names, sizes, and CRC32 values. It is accepted so the large ZIP may be removed
for local storage pressure while retaining immediately usable AP/BL/CP/CSC
inputs.

This policy is evidence-only. It does not authorize full firmware flashing,
BL/CP/CSC flashing, non-boot partition writes, Magisk module installation,
multidisabler, format data, raw host `dd`, fastboot, or any action outside the
specific active `AGENTS.md` exception.

`magisk_patched-30700_NJTCd.tar` is not stock firmware evidence and must not be
used to satisfy this policy.
