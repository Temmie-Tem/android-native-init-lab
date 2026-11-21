# S22+ FYG8 component inventory (H0)

Date: 2026-11-22
Target: Samsung Galaxy S22+ `SM-S906N` / `g0q`, firmware `S906NKSS7FYG8`
Scope: H0 (host only, read-only, no device contact). This report authorizes no
device action.
Serves:
- [security side-track candidates](../plans/S22PLUS_FYG8_SECURITY_SIDE_TRACK_CANDIDATES_2026-09-16.md)
- [post-2025-08 CVE backlog](../plans/S22PLUS_FYG8_POST_2025_08_SECURITY_BACKLOG_2026-09-16.md)
- [RF-sensing side track](../plans/S22PLUS_RF_SENSING_SIDE_TRACK_CANDIDATES_2026-11-21.md)

## Input and method

- **Input.** AVB-verified FYG8 logical images on the external lab disk
  (`/mnt/android-lab-sd/extract/ap-fyg8/`). The binding is `ALL_VERIFIED`:
  - the ZIP and AP tar sha256 equal the
    [evidence policy](../operations/S22PLUS_FYG8_STOCK_FIRMWARE_EVIDENCE_POLICY_2026-07-08.md)
    values;
  - vbmeta is byte-identical to the AP tar member;
  - both signatures and all six logical hashtrees verify.
  - Details are in the security side-track memo's 2026-11-22 update.
- **Access.** All six images are F2FS with LZ4 compression. They were attached
  with `udisksctl loop-setup -r` (each loop device reports `ro=1`) and mounted
  read-only. No sudo and no writes.
- **Listing.** 12,711 entries in total: system 7,142, vendor 3,723,
  system_ext 1,065, product 399, vendor_dlkm 369, odm 13.
- **Listing gaps:**
  - `/system/bin`, `/system_ext/bin`, `/product/bin`, `/vendor/bin` and
    `/storage` are not listable by an unprivileged user. Known paths inside
    them can still be read, for example `/vendor/bin/hw/wpa_supplicant`.
  - The 42 `.apex`/`.capex` packages were not expanded.
  - Libraries packed inside APKs were not scanned.
- **Private outputs.** Analysis `s22plus-fyg8-component-inventory.X92j4G46`
  holds `listing.tsv`, `components.py` and `components.json`.

## Security backlog components observed on FYG8

Observed means the file exists in the AVB-verified FYG8 image, with the hash
below. This is not the backlog's `PRESENT` state. `PRESENT` also requires the
vulnerable code lineage, which needs the patch diff.

| Partition | Path | Size | sha256 | ELF build-id | Backlog link |
|---|---|---:|---|---|---|
| system | `/system/lib64/libimagecodec.quram.so` | 2,701,280 | `926b1fd1ac6dd738edc9a5a9a7e004c5bcaea83d93d3dc829ba9d926e2193a1a` | `616cea8390d023e14fa3852e064cde4d60748e97` | Quram lineage (CVE-2025-21043 …) |
| system | `/system/lib/libimagecodec.quram.so` | 2,795,256 | `4faa826543d56e52a962612e54e264b2d5ada8325ddc0a30d2b1202e4622cbd7` | `3fbec9119ab28bbb5361d96c6f0dbed1a5dd16b5` | 32-bit twin |
| vendor | `/vendor/lib64/libimagecodec_native.quram.so` | 2,824,312 | `f610ccf17f756bf739a3cefc23616d8241bdfefb949594c0cde755428a8dec23` | `452377c5340538a378eee58fb74373f8e1cc1c10` | vendor-side Quram build |
| system | `/system/lib64/libsavsvc.so` | 1,268,504 | `748024e4f45154ee98859d1dfd148d506a0f91be69d4764ce354aa58604b2295` | `a520c83577b092f33902e432c4b96459` | CVE-2025-21034, 2026-2106x/7x |
| vendor | `/vendor/lib64/libsavsvc.so` | 1,247,080 | `e2531951bb787be822e3d01a9f84fe1550d6113a45700893980dd04e40aec82c` | `2d9e7a439189aa1f0cb1de7e0268829b` | same family |
| system | `/system/lib64/libsavsac.so` | 500,168 | `7ed1aed06a7f6cb59ba874236587e0a8d6cab37925e75ef48fa16b115351776b` | `5f0c37a12e44dc3b8b5b9135340e3b70` | CVE-2026-21042 |
| vendor | `/vendor/lib64/libsavsac.so` | 588,232 | `c86b4a1807aa1fe4d7b20a9303fc9aee7a80a7bed3e05bf9c1832e838ea71a31` | `be1062a5bd7d57c7c15493fc4b599d54` | same family |
| system | `/system/lib64/libpadm.so` | 117,608 | `6d4b1b537bdbfb018eb5be58f32824618a54860382e18fef919abaa69a2711f7` | `595d6592f67f1c460829d3d45b7a83ba` | CVE-2025-2105x, 2026-21049 |
| vendor | `/vendor/lib64/libpadm.so` | 118,720 | `fcb6549ae7081b3dde3eac38cd00418028bd1034f8ecdfbf2debbb941e426a44` | `ade94aec25cd774147c77e6801edb2ee` | same family |
| system | `/system/lib64/libsecuibc.so` | 273,848 | `5174984f88eaf42ecda99cbfe59824a6110b4896e7bbb1f09351c12b6ad2dca5` | `0a943e7d616b0ddd3674bacca2fa9355` | CVE-2026-21153/21154 |
| system | `/system/lib64/extractors/libsmkvextractor.so` | 145,432 | `bb168209c480198a0d084a21e6887fbab2391611a8fc6ad41d1ed159748b3167` | `8a383ed06708553b985baeab7a946282` | CVE-2026-21114/21116/21156 |
| system | `/system/lib64/libMyFilterPlugin.camera.samsung.so` | 61,704 | `12b36b804470802e772c0476644253bc5bb5a506681e4b8e48ba741bb55512e6` | `6d3730d3b830c2dbd886639bc645a98e` | CVE-2026-21152 |
| system | `/system/lib64/libedmnativehelper.so` | 44,080 | `0f5ef6e4586154605359efa91e54aa6c04ad5ab69fed2361a96dc5db82d43f9c` | `e59e2b3cfb61c598ff16fa72859ac5aa` | CVE-2026-21150 (edmnativehelper) |
| vendor | `/vendor/lib64/libsec-ril.so` | 6,954,648 | `d1878d445b1504b580d77a11d2ce9e283f15db993e3df11f5fc905a446b6455f` | `133163f8ddf06a70e7c1bb05fd96423d` | CVE-2025-58475 |
| vendor | `/vendor/lib64/libril_sem.so` | 1,070,480 | `ff13de75e12664e1a9a1d3a21574c63d4c34644ee4b07102ced965e6e08b24c2` | `41c4baa4a7293ef58d596c66a4bb9c72` | CVE-2026-21068 |
| vendor | `/vendor/lib64/libcodec2_sec_flacdec.so` | 73,432 | `936dddeb90d4f77e63f2ecbd8789498211e8b48a1915503cb576e04dc6e735fe` | `5c3dd1440e7d87164cafb12c0d8ab9af` | CVE-2026-21066; Oct-2026 advisory spells it `libcodec2-sec-flacdec.so` |
| vendor | `/vendor/bin/hw/wpa_supplicant` | 3,394,096 | `3cc0a0d8f1dade5f31a17912752211f55444088baed84fb780057bdb807d886c` | `bd99db5ce489c6992834648033153ab1` | CVE-2026-21094 |

Also present with no direct backlog row: `libsecjpegquram.so`,
`libedmnativehelperservice.so`, `libsimba.media.samsung.so` and
`libsheifdecadapter.so`. Full hashes are in private `components.json`.

**Advisory names not found in the listing:**
- `libsimba.heifdec.media.samsung.so` (Oct-2026 HEIF).
  `libsimba.media.samsung.so` and `libsheifdecadapter.so` exist instead.
  Whether either carries the vulnerable HEIF code is open.
- `libimagecodec.media.quram.so` (Jul-2026 naming).
- `libmdnie.so`.
- `libsamsungtts.so`. `SamsungTTS.apk` exists, and its native libraries were
  not scanned.
- `libcodec2secqcelpdec.so`.

Absence in this listing does not prove absence from FYG8, because of the
listing gaps above (APEX, APK-internal libraries, unlistable `bin`
directories).

**Resolved:** the private `libsec-ril.so` copy (sha256 `d1878d44…455f`),
whose provenance was unrecorded, is byte-identical to FYG8
`/vendor/lib64/libsec-ril.so`.

## RF-sensing findings

### Wi-Fi is Broadcom, not Qualcomm (corrects the RF memo)

| Item | Evidence |
|---|---|
| Wi-Fi host driver | `/vendor_dlkm/lib/modules/dhd.ko`, 10,031,024 B, sha256 `9e45a9c3…599f`, build-id `c8837ef2…eec`, string `101.24.18 (wlan=r975668)` |
| Dongle firmware | `/vendor/firmware/bcmdhd_sta.bin` (sha256 `8c703b5c…cdac`), FW-TAG `4389c1-roml/config_pcie_release Version=20.82.44`. Also `bcmdhd_mfg.bin`, `bcmdhd_mon.bin`, `bcmdhd_clm.blob`, `nvram.txt` |
| Bluetooth | `bcm4389.ko` (modinfo: `bcm4361_bluetooth`) and `bcm4389C1_*.hcd` |
| Qualcomm WLAN host driver | absent: no `qca_cld3*`/`wlan.ko` in vendor_dlkm, vendor or the vendor ramdisk |

The `qcacld-3.0` CFR configuration recorded on 2026-11-21 comes from the shared
waipio vendor source tree. It does not describe the S22+ product.

CSI/CFR on the shipped stack:
- `dhd.ko` has 5,338 symbols and none matches `csi`/`cfr`/`sensing`.
- Its strings show no CSI interface.
- The RAM firmware strings show no CSI capability. The firmware is
  ROM-offloaded (`roml`), so ROM content is unknown.
- **No stock CSI path was found.** Broadcom CSI extraction in prior art
  (Nexmon) patches dongle firmware, which the RF memo's boundary excludes.

### UWB

- Stack:
  - `uwb.ko` (sha256 `9ecc58a0…7c8c`, matching the module map);
  - HAL `/vendor/lib64/uwb_uci.hal.so` (sha256 `af27eec6…2deb`);
  - SR100T firmware `/vendor/firmware/uwb/libsr100t_prod_fw.bin` and
    `libsr100t_dev_fw.bin` (224,832 B each);
  - config `/vendor/etc/libuwb-{nxp,uci,feature,countrycode}.conf`;
  - system `semuwb-service.jar`, the `com.android.uwb` APEX, `UwbTest.apk`
    and `UwbRROverlayMccMncRegulation.apk`.
- **The stock HAL contains a CIR logging path.** Strings: `CIR samples received`,
  `_CIR.log`, `unable to open uwb_CIR_data log file`, the `NxpUciR` /
  `NXP_LOG_UCIR_LOGLEVEL` module, and `UWB_UCIX_UCIR_ERROR_LOG`.
  `libuwb-nxp.conf` sets `NXP_LOG_UCIR_LOGLEVEL=0x04` and
  `UWB_UCIX_UCIR_ERROR_LOG=0x01`.
- **Open:** what makes the firmware emit CIR notifications (vendor UCI
  debug/test configuration, `UwbTest.apk`). Also whether the logged samples are
  complete enough for sensing.

## Consequences

- The security side track can start patch diffing from the hashes above.
  Comparison firmware is still needed.
- The RF side track's most plausible stock path moves from Wi-Fi CFR to the
  UWB HAL CIR log.
