# NATIVE_INIT V2579 — ACDB direct-GET request-layout extractor

## Scope

Host-only static extraction after V2578. No device action, Android handoff, native calibration
ioctl, speaker write, ACDB command execution, or raw payload capture was performed.

## Decision

- decision: `v2579-direct-get-layout-host-extracted`
- private manifest: `workspace/private/runs/audio/v2579-acdb-direct-get-layout-extractor/v2579-direct-get-layout.json`
- input libacdbloader sha256: `25ae25afda6f52fc75d9b72e7f9df22094c7e3b243efb7257654ec9445bcd0a1`
- store pattern validation: `True` missing `[]`
- adsp pattern validation: `True` missing `[]`

## Store Getter Layout

`acdb_loader_store_get_audio_cal` is the first concrete direct-GET candidate. It preserves the
caller arguments as request pointer (`r0`), output buffer argument (`r1`), and output length pointer
(`r2`), branches on `req+28`, uses `req+32`/`req+40` as the instance gate, and issues small
`out_len=4` ACDB queries whose real payload path is indirect through the input struct.

| case | selector | gate | command | in_len | out_len | fields | confidence |
| --- | ---: | --- | ---: | ---: | ---: | --- | --- |
| `store_selector_37` | `37` | not used on this branch | `0x13091` | `12` | `4` | req+12, *out_len_io, out_buf_arg | high for size/command/field offsets; indirect payload semantics still require a build-only harness |
| `store_selector_0_no_instance` | `0` | req+32 == 0 or req+40 == 0 | `0x13265` | `20` | `4` | req+12, req+16, req+24, *out_len_io, out_buf_arg | high for selector and ioctl ABI; output is indirect via input struct |
| `store_selector_0_instance` | `0` | req+32 != 0 and req+40 != 0 | `0x13263` | `32` | `4` | req+12, req+16, req+24, req+36:u16, req+32, req+40, *out_len_io, out_buf_arg | medium-high; branch is instance-specific and still needs cal-type mapping |
| `store_selector_1_no_instance` | `1` | req+32 == 0 or req+40 == 0 | `0x11399` | `12` | `4` | req+16, *out_len_io, out_buf_arg | high for selector and command; output is indirect via input struct |
| `store_selector_1_instance` | `1` | req+32 != 0 and req+40 != 0 | `0x1326b` | `24` | `4` | req+16, req+36:u16, req+32, req+40, *out_len_io, out_buf_arg | medium-high; branch is instance-specific and still needs cal-type mapping |

Computed command checks:

- `0x13091 + 466 = 0x13263`
- `0x13091 + 468 = 0x13265`
- `0x13091 + 474 = 0x1326b`
- alternate literal = `0x11399`

## ADSP Getter Layout

`acdb_loader_adsp_get_audio_cal` is not ready for live direct GET. It reads the same request-family
offsets, but it goes through selector-specific internal helpers before the final command path.

| case | selector | fields | command/helper | live readiness |
| --- | ---: | --- | --- | --- |
| `adsp_selector_0_or_default` | `0` | req+12, req+16, req+20, req+32, req+36, req+40 | `0x111` | blocked: branch calls internal helpers before an indirect-output command; request ABI not yet sufficient for a live direct GET |
| `adsp_selector_1` | `1` | req+12, req+16, req+20, req+32, req+36, req+40 | `0x111 after selector-specific helper` | blocked: selector-specific helper at 0xe9c0 must be resolved before issuing live commands |

## Wrapper Constraints

- `acdb_loader_get_audio_cal_v2` is only a thin gate: `req != NULL`, initialized flag true, and
  `*(uint32_t *)req != 0` before tail-calling a lower getter. It is not a substitute for request
  layout pinning.
- `acdb_loader_get_calibration` requires a `24`-byte external struct and delegates internally; it is
  not the first speaker-cal live route because that external struct is not yet mapped to the Android
  speaker cal sequence.

## Interpretation

V2579 narrows the next executable path to a build-only helper around the `store_get_audio_cal`
request-family, not another public `send_audio_cal_v5` or common-topology hook rerun. The safe next
step is to generate a future helper that constructs 44-byte request structs for the five store cases,
allocates bounded output buffers privately, and stops after pure-read return/zero-buffer checks.
Live execution is still blocked until that helper has build-only forbidden-symbol checks and an exact
future gate; no `AUDIO_SET_CALIBRATION` or speaker write is permitted here.

## Next Unit

V2580 should be build-only: create the pure-read `store_get_audio_cal` harness with no live default,
cover the five request cases above, reject real SET/ioctl symbols, and preserve the V2530 rule that
success requires `ret==0` plus non-all-zero output rather than requested length alone.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_direct_get_layout_extractor_v2579.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_direct_get_layout_extractor_v2579`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_direct_get_layout_extractor_v2579.py --write-report`
- `git diff --check`
