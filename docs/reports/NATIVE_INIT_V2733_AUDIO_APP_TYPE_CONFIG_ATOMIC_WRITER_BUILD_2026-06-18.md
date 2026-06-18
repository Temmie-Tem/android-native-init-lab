# NATIVE_INIT V2733 — App Type Config atomic writer build

Date: 2026-06-18

## Scope

Host-only build of a tiny AArch64 writer for the Qualcomm global
`App Type Config` control.  The goal is to replace V2731's `tinymix`
per-index integer writes with one atomic ALSA `SNDRV_CTL_IOCTL_ELEM_WRITE`.

## Result

- decision: `v2733-app-type-config-atomic-writer-built`
- source_ready: `True`
- tool: `a90_alsa_app_type_config_writer_v2733`
- tool_path: `workspace/private/...` (private manifest only)
- sha256: `f91a42d6fd65052386eae720fb60aae074c7f89114b1106de7432a214c8bf8de`
- file: `ELF 64-bit LSB executable, ARM aarch64, version 1 (GNU/Linux), statically linked, BuildID[sha1]=4ae1a3a71c263c1c95d05d2b9c173212a3ea90bf, for GNU/Linux 3.7.0, stripped`

## Contract

- opens `/dev/snd/controlC<card>` only;
- resolves `App Type Config` by name unless a runtime numid is supplied;
- validates integer control count is at least 128;
- writes all 128 integer slots in one ioctl;
- does not call `tinymix`, `tinyplay`, `/dev/msm_audio_cal`, or any
  speaker playback primitive.

## Validation

- C source token guard passed.
- `aarch64-linux-gnu-gcc -static -Os -Wall -Wextra -Werror` build passed.
- `file` confirms an AArch64 static executable.
