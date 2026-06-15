# NATIVE_INIT_V2462_AUDIO_ACDB_PAYLOAD_DECODE_REPLAY_DESIGN_2026-06-15

## Scope

Host-only decode/design unit following V2461. No device step ran. No native
`/dev/msm_audio_cal` open or calibration ioctl was issued.

Inputs:

- Private evidence root: `workspace/private/runs/audio/v2461-acdb-compat-live-20260615-190530/`
- Primary private JSONL: `workspace/private/runs/audio/v2461-acdb-compat-live-20260615-190530/device-artifacts/msm-audio-cal-diag-threadset-p4368.jsonl`
- Public V2461 report: `docs/reports/NATIVE_INIT_V2461_AUDIO_ACDB_COMPAT_IOCTL_LIVE_CAPTURE_2026-06-15.md`
- UAPI header: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/4.0/include/uapi/linux/msm_audio_calibration.h`
- Driver source: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/4.0/dsp/audio_calibration.c`
- Calibration utility source: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/4.0/dsp/audio_cal_utils.c`
- Q6 core source: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/4.0/dsp/q6core.c`
- Audio ION source: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/4.0/dsp/msm_audio_ion.c`

Raw `bytes_hex` and raw dmabuf data are not included in this report.

## Decision

`v2462-acdb-header-decoded-dmabuf-missing-replay-gated`

V2461 captured the compat ioctl command order and the kernel-consumed ioctl
headers, but it did **not** capture the calibration payload bytes needed for a
safe native replay. The decisive field is `audio_cal_data.mem_handle`: it is a
userspace dma-buf file descriptor imported by the kernel with `dma_buf_get(fd)`,
not an in-band payload pointer. The one Android `AUDIO_SET_CALIBRATION` call
sets `CORE_CUSTOM_TOPOLOGIES_CAL_TYPE` with `cal_size=4916` and `mem_handle=37`;
those `4916` bytes live behind fd `37`, outside the copied ioctl header.

Native ACDB replay therefore remains blocked until the dmabuf content behind the
`AUDIO_SET_CALIBRATION` mem_handle is captured or reconstructed and hashed.

## Kernel ABI facts

### Ioctl buffer copy boundary

`audio_cal_shared_ioctl()` copies only the first `data_size` bytes from the user
argument:

- it first copies `size` from the first 4 bytes of `arg`;
- rejects `size < sizeof(struct audio_cal_basic)` or `size > MAX_IOCTL_CMD_SIZE`;
- allocates `kmalloc(size)`;
- then `copy_from_user(data, arg, size)`.

Source: `audio_calibration.c:389`, `audio_calibration.c:412`,
`audio_calibration.c:416`, `audio_calibration.c:425`, `audio_calibration.c:429`.

All 28 V2461 fd-matched entries have `data_size=32`. The observer copied up to
512 bytes for diagnosis, but bytes after offset `32` are not consumed by this
kernel ioctl path. Several entries contain printable stale tail data after the
kernel-consumed 32 bytes; those tails are intentionally ignored for replay.

### 32-bit compat path

The stock audio HAL path is 32-bit. `audio_cal_compat_ioctl()` remaps the 32-bit
`_IOWR('a', N, compat_uptr_t)` command numbers to the native command constants
and then calls `audio_cal_shared_ioctl()` with `compat_ptr(arg)`.

Source: `audio_calibration.c:520`, `audio_calibration.c:522`,
`audio_calibration.c:535`, `audio_calibration.c:541`, `audio_calibration.c:566`.

### Command semantics

After validation, `audio_cal_shared_ioctl()` dispatches by `hdr.cal_type`:

- `AUDIO_ALLOCATE_CALIBRATION` -> registered `alloc` callbacks;
- `AUDIO_DEALLOCATE_CALIBRATION` -> registered `dealloc` callbacks;
- `AUDIO_SET_CALIBRATION` -> registered `set_cal` callbacks.

Source: `audio_calibration.c:464`, `audio_calibration.c:466`,
`audio_calibration.c:467`, `audio_calibration.c:471`, `audio_calibration.c:479`.

For `CORE_CUSTOM_TOPOLOGIES_CAL_TYPE`, q6core registers callbacks via
`q6core_init_cal_data()`. `q6core_set_cal()` calls `cal_utils_set_cal()` and then
`q6core_send_custom_topologies()` for the custom-topology calibration index.

Source: `q6core.c:1662`, `q6core.c:1666`, `q6core.c:1727`, `q6core.c:1742`,
`q6core.c:1750`, `q6core.c:1764`, `q6core.c:1773`.

### Mem-handle ownership

`cal_utils_set_cal()` requires a pre-existing cal block when `mem_handle > 0`; if
no allocation exists for that handle, it fails with `-EINVAL`. On success, it
sets `cal_block->cal_data.size` from `cal_data.cal_size` and stores any in-band
cal-info bytes after `struct audio_cal_type_basic`.

Source: `audio_cal_utils.c:997`, `audio_cal_utils.c:1001`,
`audio_cal_utils.c:1002`, `audio_cal_utils.c:1022`, `audio_cal_utils.c:1026`,
`audio_cal_utils.c:1034`.

`create_cal_block()` stores `basic_cal->cal_data.mem_handle` as
`ion_map_handle`. If `mem_handle > 0`, it imports that fd through
`cal_block_ion_alloc()`.

Source: `audio_cal_utils.c:621`, `audio_cal_utils.c:642`,
`audio_cal_utils.c:643`, `audio_cal_utils.c:644`.

`cal_block_ion_alloc()` calls `msm_audio_ion_import()`. That import routine is
explicitly documented as importing an ION buffer with a file descriptor, calls
`dma_buf_get(fd)`, maps the dma-buf, and returns kernel virtual/physical mapping
metadata.

Source: `audio_cal_utils.c:595`, `audio_cal_utils.c:605`,
`msm_audio_ion.c:445`, `msm_audio_ion.c:459`, `msm_audio_ion.c:475`,
`msm_audio_ion.c:476`, `msm_audio_ion.c:493`.

### Q6 topology effect

`q6core_send_custom_topologies()` sends the cal block to ADSP only if ADSP is
ready and `cal_block->cal_data.size > 0`. It maps the cal block memory into Q6,
then sends `AVCS_CMD_REGISTER_TOPOLOGIES` with `payload_size` equal to the saved
`cal_size`.

Source: `q6core.c:1560`, `q6core.c:1567`, `q6core.c:1576`,
`q6core.c:1582`, `q6core.c:1590`, `q6core.c:1609`, `q6core.c:1614`,
`q6core.c:1615`, `q6core.c:1624`, `q6core.c:1643`.

## V2461 decoded command sequence

The kernel-consumed command body is the first 32 bytes of each captured 512-byte
observer sample:

- `struct audio_cal_header` at offset 0: `data_size`, `version`, `cal_type`,
  `cal_type_size`;
- `struct audio_cal_type_header` at offset 16: `version`, `buffer_number`;
- `struct audio_cal_data` at offset 24: `cal_size`, `mem_handle`.

| seq | command | cal_type | buffer | cal_size | mem_handle | consumed size | consumed SHA-256 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `ALLOC` | 2 `CVP_VOCPROC_STATIC_CAL_TYPE` | 0 | 0 | 17 | 32 | `2d51f3b3eeef5cd1805627920c77924aeaa94208615c433bb9ce6200ddb9c95d` |
| 2 | `ALLOC` | 3 `CVP_VOCPROC_DYNAMIC_CAL_TYPE` | 0 | 0 | 18 | 32 | `50031a75a73e95af5e929a997dfd832c3cddd880933208fbd98d4661d563802f` |
| 3 | `ALLOC` | 4 `CVS_VOCSTRM_STATIC_CAL_TYPE` | 0 | 0 | 19 | 32 | `53a777df0c6fd3ce5d09390bde14cb3725fc1b6ee9ba5bba0925ffb254212711` |
| 4 | `ALLOC` | 5 `CVP_VOCDEV_CFG_CAL_TYPE` | 0 | 0 | 20 | 32 | `b3b30bad159828b2d495c0f2e5db4327c906c32005814db0778f1a1c41d39fd0` |
| 5 | `ALLOC` | 10 `ADM_CUST_TOPOLOGY_CAL_TYPE` | 0 | 0 | 21 | 32 | `25a7c8889718483d5b7dd62948e1d9e69646f186a0409834f9a2337848d95d85` |
| 6 | `ALLOC` | 11 `ADM_AUDPROC_CAL_TYPE` | 0 | 0 | 22 | 32 | `94560823f8163af5135e61943c989dc5c3e7e9eb21d36be6377923f05fc45677` |
| 7 | `ALLOC` | 11 `ADM_AUDPROC_CAL_TYPE` | 1 | 0 | 23 | 32 | `47db70ef18619550d93aada178b23583d55ef73f1db86ff0b14193c43f95bfe0` |
| 8 | `ALLOC` | 12 `ADM_AUDVOL_CAL_TYPE` | 0 | 0 | 24 | 32 | `05590c79c730a04f37cea62698d5f1ba26562243643f2d131c06892eca932a7e` |
| 9 | `ALLOC` | 12 `ADM_AUDVOL_CAL_TYPE` | 1 | 0 | 25 | 32 | `c7f4205ad025f73ae60ca86990b24191c56d70d9d1cee829a1696458680ad724` |
| 10 | `ALLOC` | 14 `ASM_CUST_TOPOLOGY_CAL_TYPE` | 0 | 0 | 26 | 32 | `1e4be76b025077553cba9d8c1964b1ee9b5900f24bb181b39a6c1ac92354a970` |
| 11 | `ALLOC` | 15 `ASM_AUDSTRM_CAL_TYPE` | 0 | 0 | 27 | 32 | `d34a88808d24e204b0f8efecb45dcd34f96816ed921c669e8a17d5d8be339632` |
| 12 | `ALLOC` | 16 `AFE_COMMON_RX_CAL_TYPE` | 0 | 0 | 28 | 32 | `42ed2b833eddb99a6cfde7157202517635289c07ff4095d7084235c0640112a8` |
| 13 | `ALLOC` | 17 `AFE_COMMON_TX_CAL_TYPE` | 0 | 0 | 29 | 32 | `5a5ced8fe3ca29e46e2714f499208e5b26955efa85defc7ffc15e15f6de12566` |
| 14 | `ALLOC` | 19 `AFE_AANC_CAL_TYPE` | 0 | 0 | 30 | 32 | `a046cad4b74d65134fbacddb2012de581e405a4663f2e8bba070ad0f48ed16a0` |
| 15 | `ALLOC` | 24 `AFE_CUST_TOPOLOGY_CAL_TYPE` | 0 | 0 | 31 | 32 | `6e53d9ff297ecddcce0356a5e690609f57ec5c5575b236a12fdff9ec063475da` |
| 16 | `ALLOC` | 25 `LSM_CUST_TOPOLOGY_CAL_TYPE` | 0 | 0 | 32 | 32 | `954ed4513c8ab195bce2af9fc71183a04e23737dfe6814f0738b489de6f608b0` |
| 17 | `ALLOC` | 27 `LSM_CAL_TYPE` | 0 | 0 | 33 | 32 | `37569c2d6543b76c8f90850a7038ebf3e3a4fc2060eb1f0df7c49029930690ca` |
| 18 | `ALLOC` | 34 `ULP_AFE_CAL_TYPE` | 0 | 0 | 34 | 32 | `22071142789789b38a3a5145cda62c9fb60601d2a49ba070453530ee66be2788` |
| 19 | `ALLOC` | 35 `ULP_LSM_CAL_TYPE` | 0 | 0 | 35 | 32 | `7e4c699f69c91baa548dd2b5f1fa2c7812dedd30e3025b79fd53043a9ed0c019` |
| 20 | `ALLOC` | 37 `AUDIO_CORE_METAINFO_CAL_TYPE` | 0 | 0 | 36 | 32 | `f3200dc65dc3ee5346e3da8912a35fc0ef3fc1854862b569338a8644bcd724fe` |
| 21 | `ALLOC` | 39 `CORE_CUSTOM_TOPOLOGIES_CAL_TYPE` | 0 | 0 | 37 | 32 | `d93dbef0f5a1f4b13afb4effe6456ecf3972cbaec30ee385301fa9f831648037` |
| 22 | `ALLOC` | 40 `ADM_RTAC_AUDVOL_CAL_TYPE` | 0 | 0 | 38 | 32 | `3fddfbf13224d944059c05f77d5f09e2bb8b3c65cf99ae771a752a03c5a577b3` |
| 23 | `ALLOC` | 46 `AFE_LSM_TX_CAL_TYPE` | 0 | 0 | 39 | 32 | `3676deeb7a457bc806a0f2a8ef92c439a7dda31c90cd7ed2a49b8a032d275452` |
| 24 | `ALLOC` | 48 `ADM_LSM_AUDPROC_CAL_TYPE` | 0 | 0 | 40 | 32 | `2659d1173a87f54fe447b308ce8898ec70a5887a39fa4aa867ff876724d4bf9f` |
| 25 | `ALLOC` | 49 `ADM_LSM_AUDPROC_PERSISTENT_CAL_TYPE` | 0 | 0 | 41 | 32 | `de04e454e3d1ae53995161729a575e21f993d1a2fb663b4da1fd47609cb20b6c` |
| 26 | `DEALLOC` | 39 `CORE_CUSTOM_TOPOLOGIES_CAL_TYPE` | 0 | 0 | 37 | 32 | `d93dbef0f5a1f4b13afb4effe6456ecf3972cbaec30ee385301fa9f831648037` |
| 27 | `ALLOC` | 39 `CORE_CUSTOM_TOPOLOGIES_CAL_TYPE` | 0 | 0 | 37 | 32 | `d93dbef0f5a1f4b13afb4effe6456ecf3972cbaec30ee385301fa9f831648037` |
| 28 | `SET` | 39 `CORE_CUSTOM_TOPOLOGIES_CAL_TYPE` | 0 | 4916 | 37 | 32 | `581399368f48b1959c61cfaf3fd1b62de5038f643e6735ae96df7b3ac54b6608` |

The full 512-byte observer sample hashes are already recorded in the V2461
public report. For replay, the consumed-hash column above is the safer canonical
identity for the ioctl argument because it matches the kernel copy boundary.

## Replay implications

### What V2461 is sufficient for

V2461 is sufficient to define the ioctl skeleton for the Android-good custom
Q6-core topology registration edge:

1. Open `/dev/msm_audio_cal`.
2. Ensure ADSP/Q6 core is up.
3. Allocate at least `CORE_CUSTOM_TOPOLOGIES_CAL_TYPE`, buffer `0`, with
   `mem_handle=<dmabuf fd>`.
4. Issue `AUDIO_SET_CALIBRATION` for `CORE_CUSTOM_TOPOLOGIES_CAL_TYPE`, buffer
   `0`, `cal_size=4916`, `mem_handle=<same dmabuf fd>`.
5. Keep the `/dev/msm_audio_cal` fd and dmabuf fd alive until after the bounded
   PCM probe, then explicitly deallocate the same cal block and close fds.

The broader Android init sequence also allocated many other cal types. V2462
should not claim that topology-only replay is enough to fix the earlier native
`pcm_prepare()` missing-cal-block failure. It is only the smallest source-backed
pilot gate derived from the captured payload.

### What V2461 is not sufficient for

V2461 did not capture the 4916-byte topology payload behind mem_handle `37`.
Because the kernel imports `mem_handle` as a dma-buf fd, the captured 32-byte
`AUDIO_SET_CALIBRATION` ioctl header alone cannot reproduce Android's topology
registration.

A native replay that sends only the V2461 ioctl header with a bogus integer `37`
would be invalid: fd `37` is per-process and must refer to a real dma-buf in the
native replay process.

### Cleanup and fd lifetime

`audio_cal_release()` decrements a global reference count and calls
`dealloc_all_clients()` when the count reaches zero. That deallocates all cal
types through callbacks with `buffer_number=ALL_CAL_BLOCKS` and `mem_handle=-1`.

Source: `audio_calibration.c:350`, `audio_calibration.c:378`,
`audio_calibration.c:380`, `audio_calibration.c:382`, `audio_calibration.c:357`,
`audio_calibration.c:364`, `audio_calibration.c:365`, `audio_calibration.c:366`,
`audio_calibration.c:368`.

Therefore a future native pilot must keep `/dev/msm_audio_cal` open across the
playback attempt. Closing it immediately after `AUDIO_SET_CALIBRATION` can erase
the calibration state before the PCM prepare path uses it. The pilot should clean
up explicitly with `AUDIO_DEALLOCATE_CALIBRATION` for the topology cal block and
then close fds after route reset / PCM result capture.

## Next safe unit

Native replay is still gated. The next meaningful unit should be an Android-good
measurement hardening unit that captures the dma-buf bytes referenced by the
`AUDIO_SET_CALIBRATION` mem_handle:

- trigger condition: on fd-matched `/dev/msm_audio_cal` `AUDIO_SET_CALIBRATION`
  where `cal_type=CORE_CUSTOM_TOPOLOGIES_CAL_TYPE`, `cal_size>0`, and
  `mem_handle>0`;
- observation method: while the traced thread is stopped at ioctl entry, duplicate
  the target process fd via `/proc/<tgid>/fd/<mem_handle>` from the root observer,
  `mmap(PROT_READ)` exactly `cal_size` bytes, compute SHA-256, and store raw bytes
  only under `workspace/private`;
- public output: only length, SHA-256, and structural sanity checks; no raw bytes;
- hard stops: do not issue native `/dev/msm_audio_cal` ioctls, do not write mixer
  or PCM state during this measurement, and always clean up the temporary Magisk
  module before checked rollback to V2321.

Only after this dmabuf payload is pinned should a native N3 replay runner be
implemented. That runner's first live form should be a bounded topology-only
pilot, not a full speaker proof:

1. materialize ADSP and `/dev/snd` using the already validated V2334 path;
2. materialize `/dev/msm_audio_cal`;
3. allocate a real dma-buf/ION fd of the captured length, fill it with the
   captured topology bytes, and keep it open;
4. issue only the minimal `CORE_CUSTOM_TOPOLOGIES_CAL_TYPE` alloc/set sequence;
5. apply the already observed route, run the existing low-amplitude PCM probe,
   capture bounded dmesg tail, reverse-reset route, deallocate topology cal,
   close fds, and roll back to V2321.

The future native replay gate must remain fail-closed if the dmabuf source,
length, SHA-256, allocation mechanism, or cleanup path is missing.

## Validation

Host-only validation for this unit:

- re-read `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and `tests/GOAL.md`;
- inspected recent git history and V2461 report;
- parsed private V2461 JSONL without emitting raw `bytes_hex`;
- decoded the 28 fd-matched ioctl headers against `msm_audio_calibration.h`;
- inspected `audio_calibration.c`, `audio_cal_utils.c`, `q6core.c`, and
  `msm_audio_ion.c` for ownership/lifetime semantics;
- no device command, native calibration ioctl, mixer write, PCM write, or flash
  was run.
