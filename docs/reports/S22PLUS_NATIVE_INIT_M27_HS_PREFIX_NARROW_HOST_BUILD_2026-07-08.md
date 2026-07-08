# S22+ Native-Init M27 HS Prefix-Narrow Host Build (2026-07-08)

## Verdict

PASS: host-only M27 prefix-narrow discriminator matrix built and statically
validated. No flash, reboot, rollback, partition write, sysfs write, or device
action was performed.

M27 is derived from the M26 live result: `P00` reached `reboot(download)`, while
`P24` did not. M27 narrows that boundary by building candidates for
`P08/P12/P16/P20/P22/P23/P24` under the same M25 HS-only module closure and
DTBO high-speed cap context.

## Public Source

- Builder:
  `workspace/public/src/scripts/revalidation/build_s22plus_m27_hs_prefix_narrow.py`
- Runtime source:
  `workspace/public/src/native-init/s22plus_init_m27_hs_prefix_download.c`
- Tests:
  `tests/test_s22plus_m27_hs_prefix_narrow_build.py`

## Private Output

- Output directory:
  `workspace/private/outputs/s22plus_native_init/m27_hs_prefix_narrow_v0_1`
- Matrix manifest:
  `workspace/private/outputs/s22plus_native_init/m27_hs_prefix_narrow_v0_1/manifest.json`
- Manifest SHA256:
  `e44776fd55ff66eb6b4a197f351cc129000e7120b5ceeab91dd36d88c1988e63`

Every generated Odin AP contains exactly one tar member:

```text
boot.img.lz4
```

## Input Context

- M25 HS-only module-list SHA256:
  `00607484b7b777ee5cb54d7657f0cb554b9b66c42fec0e414d0544c0735d6496`
- M25 DTBO high-speed cap AP SHA256:
  `35afd774444066fd8e2ffe831da11dd73ee47dce3bdd5b1e37675f82344e56b6`
- Patched DTBO raw SHA256:
  `8962cbbded722c85dbdebfbdc2eba5476b9a64e2a2933888b81f947159eddc17`
- Stock DTBO rollback AP SHA256:
  `6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa`
- Stock DTBO raw SHA256:
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`

## Candidate Matrix

| Label | Prefix | AP.tar.md5 SHA256 | boot.img SHA256 | /init SHA256 | Next module |
| --- | ---: | --- | --- | --- | --- |
| P08 | 8 | `60669383e0345dfc5b7f50393ad6aebd3c67307ba32bc107c69eb324d67f499a` | `0ab2daa950bde5932f5651b90e7b32f2a102ccb97fe327fb25698c03c89113ca` | `7640cd759c1ebfa9c8470a4d1456af9ea81a6415681c8a9715e6963ac3f0cabf` | `debug-regulator.ko` |
| P12 | 12 | `3e0d65386966fb351a108f0c1e03dfdf695d365717e42552e970cfdab16af7ab` | `02cdc8b95209559618e7e2da0caa6124d24b9f25d5d5b41fe3dce2fa4294a9a3` | `5add362c7479be1435fdb5d0eb9a88d5e7a6e70f202dbaae406eb76953835ace` | `iommu-logger.ko` |
| P16 | 16 | `32b132e30c8f009e161ae0c71a64ed90d4b1ac1560302a17ef1309b03100f61f` | `730b32b44daf3a8c958fda7094ed1b3ac07d00ea116d768a362fabce043bb8bf` | `7c068bada632fc441d81843e3c70e9743b9e10e4ee3114847cb69051cda1421d` | `qcom_iommu_util.ko` |
| P20 | 20 | `d4669c932312d2f84ce5982bc2df81a4903c23e7f6fae19bff4129aaba56afba` | `5d2a0faee48bb105fa5c0167daabd8447962896bda646ddcfb9781c8e83be008` | `01f88c744d59790991a98e74cec9550803c656c28e29c8daeb51dbe5baafc2b0` | `sec_class.ko` |
| P22 | 22 | `1d7137f60d5743e0cb2145219e8806c6bc1b051a7d8a68749afe5b260cdf3643` | `813016d66fc1f47fda5d7f874563d26feae76f2e98a2eda7c3b8de1ea06973ea` | `a8fdccb3dbe2bf88ecd9cecf72b008609376b76d74505b22bdb3499ba3cfa99a` | `smem.ko` |
| P23 | 23 | `5bc8d767af7794bf7ece761b1d61d080e94b345e99be173556aece49ed40f8fb` | `901459a1f1caeaf0774262108fb728cd4bb05e27b0a61ae57dbdd7b0a2f57b4a` | `a55243f1ff3bda8b8e82feb502a70714a90bdc159f340163c24ffcf24f06eaff` | `socinfo.ko` |
| P24 | 24 | `fff7ecf3ff9233f76ac17f07ecf56a383696d6ecb06b67f84ef39d8f08876180` | `507dc385ac178b2b297cb35f0aeb83b65c81ef07ec2da89ebd51dca1de54c86b` | `21c63aa298ac362e09eba15b63be20fe1d9c6bb82ef09297e172c5f32c0faa2a` | `arm_smmu.ko` |

## Runtime Shape

Each M27 `/init` is freestanding raw-syscall PID1 and contains:

```text
S22_NATIVE_INIT_M27_HS_PREFIX_DOWNLOAD
modules_hs_only_usb2=/s22plus_m27_hs_only_usb2.modules
module_count=40
maximum_speed_dtbo=high-speed
qmp_excluded=1
observation=prefix-download
reboot_request=download
```

The runtime does not create configfs, does not bind UDC, does not probe
`ttyGS0`, and does not attempt ACM. It mounts minimal pseudo-fs, loads the
bounded prefix, then calls `reboot(..., "download")`.

## Validation

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_m27_hs_prefix_narrow.py \
  tests/test_s22plus_m27_hs_prefix_narrow_build.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_s22plus_m27_hs_prefix_narrow_build

aarch64-linux-gnu-gcc -fsyntax-only -nostdlib -static -ffreestanding \
  -fno-builtin -fno-stack-protector -Os -Wall -Wextra -Werror \
  -DM27_PREFIX_LIMIT=24 -DM27_PREFIX_LABEL='"P24"' \
  workspace/public/src/native-init/s22plus_init_m27_hs_prefix_download.c

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_m27_hs_prefix_narrow.py --force

git diff --check
```

Results:

- Python bytecode compile passed.
- Unit tests passed.
- AArch64 freestanding syntax check passed.
- Host builder generated all 7 candidates.
- AP member check passed for every candidate: `["boot.img.lz4"]`.
- Manifest safety is host-only: `live_flash_authorized=false`,
  `device_action=false`.

## Next

No live flash is authorized by this report. The next live-capable unit should
add a fresh SHA-pinned `AGENTS.md` exception and guarded live helper for this
M27 batch, preferably starting from `P08` and stopping on the first no-hit.
