# S22+ backlog libraries, GYJ1 → GZH3 (H0)

Date: 2026-11-22
Target: Samsung Galaxy S22+ `SM-S906N`. `S906NKSU7GYJ1` (Android 16, SPL
2025-10-01) against `S906NKSS9GZH3` (Android 16, SPL **2026-08-05**, the
latest stable build on FUS as of 2026-11-22).
Scope: H0 static patch-diff summary. Host-only, read-only, no device contact.
No reproduction, no proof of concept, no exploit work, and no
instruction-level reconstruction of any fix.
Follows the [FYG8 → GYJ1 lineage report](S22PLUS_FYG8_BACKLOG_LIBS_LINEAGE_H0_2026-11-22.md).

## Inputs and provenance

| | GZH3 |
|---|---|
| Source | Samsung FUS, `samloader download` of `S906NKSS9GZH3/S906NOKR9GZH3/S906NKSS9GZE4/S906NKSS9GZH3` |
| ZIP | `SM-S906N_5_20260819114040_va0pv8xmdn_fac.zip`, sha256 `5fa94705c82d7748283b45430bed9baf3971be0ef3f3e18b1d7e6f516df8efc5` |
| AP tar | `AP_S906NKSS9GZH3_…_OS16.tar.md5`, sha256 `3223f175b6b2a1385d962bf185a4206dbb684a23354c92c7e6899412ea90dad8` |
| vbmeta / vbmeta_system | `d9aa56b2…51e3` / `b9ac12db…c27d` |
| AVB | both signatures valid; **same key** as FYG8 (sha1 `e03300ab…a65c`); `system` and `vendor` hashtrees verified |
| Security patch (vbmeta props) | boot, system, vendor: `2026-08-05`; system OS 16, vendor OS 12 |

FUS lists six stable builds between the two: GYK3, GYL1, GZA1, GZB2, GZE5,
then GZH3. The GYJ1 → GZH3 window therefore spans the Nov-2025 to Aug-2026
SMRs. Builds with the Oct/Nov-2026 SMRs are not on FUS yet. That means the
fixes for `libsecuibc.so` and `libsmkvextractor.so` cannot be tested.

Both sides are Android 16 builds, so toolchain noise is much smaller than
in the FYG8 → GYJ1 pair.

## Result

| Library | GYJ1 → GZH3 | Advisories in window |
|---|---|---|
| `libsavsvc.so` (system and vendor) | **13 functions changed**, 917/917 exports | Aug-2026: CVE-2026-21069 (VC1), 21071 (MPEG4), 21072 (VC1) |
| `libsavsac.so` | **1 function changed**: `sflacd_dec` (596 → 652 B), 316/316 exports | Jul-2026: CVE-2026-21042 |
| `libpadm.so` (all four copies) | **byte-identical** | Jul-2026: CVE-2026-21049 ("Android 14, 15, 16") |
| `libimagecodec.quram.so` | large rework: 2,715 common, 46 added, 53 removed, 2,559 size-changed, `.text` +243,836 B | many Quram rows, Nov-2025 to Jul-2026 |
| `libsecuibc.so`, `libsmkvextractor.so`, `libsecjpegquram.so`, `libMyFilterPlugin.camera.samsung.so` | byte-identical | fixes are Oct/Nov-2026, outside the window |

### `libsavsvc.so`

- **System copy.** 12 of the 13 changed functions are in the VC1 decoder
  (`svc1d_*`, `svc1_expand_*_ap_frm`):
  - `svc1d_get_last_frame` and `svc1d_get_last_frame_mt`: 768 → 828 B;
  - `svc1d_vld_elh`, `svc1d_vld_slh`, `svc1d_vld_plh`, `svc1d_vld_plh_ap`;
  - `svc1d_dec`, `svc1d_dec_mt`, `svc1d_df` and `svc1d_mt_init_2dwave`.
- The one other changed function is in the MPEG4 decoder,
  `smp4vd_vld_mb_dp` (3,956 → 3,968 B).
- No new strings.
- **The vendor copy** (`/vendor/lib64/libsavsvc.so`, `619ff8fc…` →
  `17368323…`) changes in **the same 13 functions**.
- The delta is confined to exactly the two codec families named in the
  Aug-2026 advisories (two VC1 and one MPEG4). It touches no other codec.
- No CVE was linked to a specific function. Two VC1 advisories share one
  decoder.

### `libsavsac.so`

- The only change is in the FLAC decoder entry, `sflacd_dec`.
- The library's Jul-2026 advisory, CVE-2026-21042, says "remote OOB write"
  and does not name a codec.
- Two FLAC-named advisories exist: CVE-2026-21066 (Aug-2026,
  `libcodec2_sec_flacdec.so`) and CVE-2026-21115 (Oct-2026). They may reach
  this decoder too.
- **This is a candidate delta. Attribution is open.**

### `libpadm.so`: advertised fix not visible

- Samsung lists CVE-2026-21049 (SVE-2026-1820, SMR-JUL-2026) as affecting
  "Android 14, 15, 16". GZH3's SPL is 2026-08-05.
- Even so, the system and vendor copies, both 32-bit and 64-bit, are
  byte-identical to GYJ1.
- The vendor copies are even identical to **FYG8**. The Oct-2025 `libpadm`
  fix shipped only in the `/system` copy. The frozen vendor partition (OS 12)
  never received it.
- Possible explanations, none verified:
  1. The item does not apply to this model, even though the Android range
     matches.
  2. The fix ships in a different binary.
  3. The item was deferred on this quarterly build.
- **Recorded as an open observation, not as a lineage break.**

### `libimagecodec.quram.so`

- The size of the rework (export set changed, about 12 % more code) rules
  out function-level attribution at summary level.
- The Quram rows from Nov-2025 to Jul-2026 stay at their current states.

## State change

- **CVE-2026-21069, CVE-2026-21071, CVE-2026-21072 (`libsavsvc.so`):
  `PUBLISHED` → `DIFFED`.** Lineage is continuous from FYG8 (917/917 through
  both pairs). A low-noise pre/post-fix delta was identified and confined to
  the VC1 and MPEG4 decoder functions, in both copies. Per-CVE attribution
  inside the VC1 pair is open.
- **CVE-2026-21042 (`libsavsac.so`): `PUBLISHED` → `PRESENT`.** Lineage is
  continuous from FYG8 (316/316). There is a single-function candidate delta
  (`sflacd_dec`), but attribution is open.
- **CVE-2026-21049 (`libpadm.so`): stays `PUBLISHED`.** Lineage is present,
  but no fix is visible in the first build whose SPL covers it.

## Private outputs

Analysis `s22plus-gzh3-compare.YUuibTvm` holds:
- `extract.sh`, `verify_avb.py` and `avb-verified.json`;
- `libdiff.py` (now parameterised by `LIBDIFF_A`/`LIBDIFF_B`);
- `libdiff.{fyg8-gyj1,gyj1-gzh3,v_gyj1-v_gzh3}.json`;
- library copies in `fyg8/`, `gyj1/`, `gzh3/`, `vendor/` and `l32/`.

The GZH3 package is at `workspace/private/inputs/firmware/S906NKSS9GZH3_SKC/`.
