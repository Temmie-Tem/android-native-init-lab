# NATIVE_INIT_V2463_AUDIO_ACDB_DMABUF_CAPTURE_SUPPORT_2026-06-15

## Scope

Host-only implementation unit following V2462. No device step ran. No native
`/dev/msm_audio_cal` open or calibration ioctl was issued.

This unit extends the existing Android-good ptrace observer so the next bounded
Android handoff can capture the dmabuf payload referenced by V2461's
`CORE_CUSTOM_TOPOLOGIES_CAL_TYPE` set-calibration call.

## Decision

`v2463-acdb-dmabuf-capture-helper-ready`

V2462 proved that the V2461 ioctl header is insufficient for native replay: the
kernel consumes only the first 32 ioctl bytes and imports `audio_cal_data.mem_handle`
as a process-local dma-buf fd. V2463 implements the missing observer capability:
while the traced Android audio thread is stopped at ioctl entry, the helper can
recognize the custom-topology set-cal header, duplicate the target process fd via
`/proc/<tgid>/fd/<mem_handle>`, `mmap(PROT_READ)` the bounded payload length, and
write that payload only to a private binary artifact.

The public contract remains metadata-only. Raw dmabuf bytes are never written to
`docs/` or committed.

## Implementation

Touched public source:

- `workspace/public/src/android/acdb_payload_capture/a90_acdb_ioctl_capture_diag_v2449.c`
- `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_diag_observer_planner_v2449.py`
- `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_diag_observer_live_handoff_v2450.py`
- `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py`
- `tests/test_native_audio_acdb_m1_diag_observer_planner_v2449.py`
- `tests/test_native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py`

### Helper behavior

The helper adds opt-in options:

- `--dmabuf-out-dir <private-dir>`
- `--max-dmabuf-bytes <limit>`; default staging path uses `65536`, above the
  observed `4916`-byte topology payload.

For fd-matched `/dev/msm_audio_cal` ioctl entries, it still records the bounded
request-buffer hex in private JSONL as before. It additionally decodes only the
kernel-consumed first 32 bytes as:

- `data_size`, `version`, `cal_type`, `cal_type_size`;
- `type_version`, `buffer_number`;
- `cal_size`, `mem_handle`.

It attempts dmabuf capture only when all of these hold:

- request command is the observed compat set-cal command or its native-size
  counterpart;
- `cal_type == 39` (`CORE_CUSTOM_TOPOLOGIES_CAL_TYPE`);
- `cal_size > 0`;
- `mem_handle > 0`.

The helper does not contain the forbidden public symbol names for issuing audio
calibration ioctls. It uses neutral internal constants only and never opens
`/dev/msm_audio_cal` itself.

### Artifact policy

Private binary payloads are written under the pulled artifact tree, e.g. the
boot-service observer uses `artifacts/dmabuf/` and the host-coordinated late
observer uses `artifacts/dmabuf-late/`.

JSONL records contain only dmabuf capture metadata: status, cal type, cal size,
mem handle, capture length, write length, errno fields, and private path. The
host summarizers hash private `dmabuf*.bin` files and expose only relative path,
size, and SHA-256 in result summaries.

## Safety boundary

Preserved hard stops:

- no helper-open of `/dev/msm_audio_cal`;
- no native calibration ioctl;
- no native replay;
- no mixer/PCM/tinyplay writes in this unit;
- no Magisk persistent install;
- no public raw payload bytes.

This is Android-good measurement plumbing only. Native replay remains blocked
until a future live run actually captures the dmabuf payload length/hash and the
private bytes needed for a bounded replay pilot.

## Validation

Commands run:

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_m1_diag_observer_planner_v2449.py \
  workspace/public/src/scripts/revalidation/native_audio_acdb_m1_diag_observer_live_handoff_v2450.py \
  workspace/public/src/scripts/revalidation/native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py \
  tests/test_native_audio_acdb_m1_diag_observer_planner_v2449.py \
  tests/test_native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py

aarch64-linux-gnu-gcc -O2 -static -s -Wall -Wextra \
  -o workspace/private/builds/audio/v2463-dmabuf-helper-build/a90_acdb_ioctl_capture_diag_v2449 \
  workspace/public/src/android/acdb_payload_capture/a90_acdb_ioctl_capture_diag_v2449.c

file workspace/private/builds/audio/v2463-dmabuf-helper-build/a90_acdb_ioctl_capture_diag_v2449

python3 -m unittest discover -s tests -p 'test_native_audio_acdb_m1_diag_observer_planner_v2449.py' -v
python3 -m unittest discover -s tests -p 'test_native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py' -v

python3 workspace/public/src/scripts/revalidation/native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py \
  --dry-run --materialize-module-template \
  --module-out-dir workspace/private/builds/audio/v2463-dmabuf-module-smoke
```

Results:

- AArch64 helper build: `ELF 64-bit LSB executable, ARM aarch64, statically linked`.
- V2449 focused tests: `6` tests passed.
- V2451 focused tests: `9` tests passed.
- Materialized dry-run: `future_live_ready=True`, `command_safety.ok=True`,
  `future_live_blockers=[]`, `adds_private_dmabuf_payload_capture=True`.
- `git diff --check`: pending in final commit validation.

## Next unit

Run a bounded Android-good live rerun of the already validated hybrid late-observer
path with the V2463 helper. Expected success evidence:

- fd-matched `AUDIO_SET_CALIBRATION` for cal type `39` still appears;
- one `dmabuf_capture` event reports `status=ok` for `cal_size=4916`, `mem_handle=37`;
- pulled private artifact includes the matching `dmabuf*.bin` file;
- result summary records only size and SHA-256;
- Android cleanup and checked rollback to V2321 finish with native `selftest fail=0`.

Do not issue native calibration ioctls before that payload is captured.
