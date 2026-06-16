# NATIVE_INIT V2578 — ACDB lower-get ABI recon

## Scope

Host-only ABI reconnaissance after V2575/V2577. No device action, Android handoff, native
calibration ioctl, speaker write, raw ACDB payload capture, or private vendor binary commit was
performed.

## Decision

- decision: `v2578-lower-get-abi-host-recon-complete`
- private manifest: `workspace/private/runs/audio/v2578-acdb-lower-get-abi-recon/v2578-lower-get-abi-recon.json`
- input libacdbloader sha256: `25ae25afda6f52fc75d9b72e7f9df22094c7e3b243efb7257654ec9445bcd0a1`
- input libaudcal sha256: `3f214dc18758d360cbc39d8a5323ff76baf6b5eb6c247de141bd6d5e91f4295d`

## Export Inventory

| symbol | value | size | type |
| --- | ---: | ---: | --- |
| `acdb_loader_send_common_custom_topology` | `0x00008cf1` | `2620` | `FUNC` |
| `acdb_loader_send_audio_cal_v5` | `0x00009d31` | `876` | `FUNC` |
| `acdb_loader_get_calibration` | `0x0000e26d` | `104` | `FUNC` |
| `acdb_loader_adsp_get_audio_cal` | `0x0000e8f5` | `352` | `FUNC` |
| `acdb_loader_get_audio_cal_v2` | `0x0000ea55` | `136` | `FUNC` |
| `acdb_loader_store_get_audio_cal` | `0x0000e715` | `480` | `FUNC` |

## Findings

1. **Public-send live routes remain closed.** V2570 and V2574 both reached the public
   `send_audio_cal_v5` boundary without useful per-device `acdb_ioctl` GET rows; V2575 closed that
   strategy, and V2577 shows the common-topology entry arm is not a remaining timing race.
2. **The lower-get surface is real and exported.** `acdb_loader_get_audio_cal_v2`,
   `acdb_loader_adsp_get_audio_cal`, `acdb_loader_get_calibration`, and
   `acdb_loader_store_get_audio_cal` are all present in the V2324 stock `libacdbloader.so`.
3. **Common topology still uses cal_type 39, but V2577 makes this public function a poor capture
   point in own-process mode.** The host RE sees the expected cal-type setup, while live execution
   arms before the real call and still records no target rows before timeout.
4. **The next useful path is lower-level GET request construction, not another public-function
   rerun.** The direct `acdb_ioctl` commands and getter request structs need one more static pass
   before a live pure-read helper should issue them.

## Metadata Snippets

### `acdb_loader_send_common_custom_topology`
- `line 52: 8d66: 00 24                        	movs	r4, #0 / 8d68: 80 ed 00 8b                  	vstr	d8, [r0] / 8d6c: 27 20                        	movs	r0, #39 / 8d6e: 06 f0 e9 ff                  	bl	#28626 / 8d72: 00 28                        	cmp	r0, #0`
- `line 64: 8d84: 0e 90                        	str	r0, [sp, #56] / 8d86: ab 68                        	ldr	r3, [r5, #8] / 8d88: 27 20                        	movs	r0, #39 / 8d8a: 29 68                        	ldr	r1, [r5] / 8d8c: 0e aa                        	add	r2, sp, #56`
- `line 62: 8d80: 11 90                        	str	r0, [sp, #68] / 8d82: 20 20                        	movs	r0, #32 / 8d84: 0e 90                        	str	r0, [sp, #56] / 8d86: ab 68                        	ldr	r3, [r5, #8] / 8d88: 27 20                        	movs	r0, #39`
- `line 75: 8da6: 00 20                        	movs	r0, #0 / 8da8: 05 97                        	str	r7, [sp, #20] / 8daa: 0e 90                        	str	r0, [sp, #56] / 8dac: 87 4f                        	ldr	r7, [pc, #540] / 8dae: 7f 44                        	add	r7, pc`

### `acdb_loader_send_audio_cal_v5`
- `line 82: 9de2: 18 20                        	movs	r0, #24 / 9de4: 41 f9 00 07                  	vst1.8	{d16}, [r1], r0 / 9de8: 0d 20                        	movs	r0, #13 / 9dea: cd ed 18 0b                  	vstr	d16, [sp, #96] / 9dee: cd ed 16 0b                  	vstr	d16, [sp, #88]`
- `line 99: 9e0e: 14 90                        	str	r0, [sp, #80] / 9e10: bb 68                        	ldr	r3, [r7, #8] / 9e12: 0d 20                        	movs	r0, #13 / 9e14: 39 68                        	ldr	r1, [r7] / 9e16: 14 aa                        	add	r2, sp, #80`

### `acdb_loader_store_get_audio_cal`
- `line 37: e74e: 00 2a                        	cmp	r2, #0 / e750: f0 d0                        	beq	#-32 <acdb_loader_store_get_audio_cal+0x20> / e752: e8 69                        	ldr	r0, [r5, #28] / e754: 25 28                        	cmp	r0, #37 / e756: 32 d0                        	beq	#100 <acdb_loader_store_get_audio_cal+0xaa>`
- `line 38: e750: f0 d0                        	beq	#-32 <acdb_loader_store_get_audio_cal+0x20> / e752: e8 69                        	ldr	r0, [r5, #28] / e754: 25 28                        	cmp	r0, #37 / e756: 32 d0                        	beq	#100 <acdb_loader_store_get_audio_cal+0xaa> / e758: 01 28                        	cmp	r0, #1`
- `line 57: e784: 01 60                        	str	r1, [r0] / e786: 29 6a                        	ldr	r1, [r5, #32] / e788: 43 f2 91 00                  	movw	r0, #12433 / e78c: c0 f2 01 00                  	movt	r0, #1 / e790: 00 29                        	cmp	r1, #0`
- `line 67: e79c: 06 96                        	str	r6, [sp, #24] / e79e: ab 69                        	ldr	r3, [r5, #24] / e7a0: 00 f5 ea 70                  	add.w	r0, r0, #468 / e7a4: d5 e9 03 12                  	ldrd	r1, r2, [r5, #12] / e7a8: cd e9 02 13                  	strd	r1, r3, [sp, #8]`
- `line 119: e818: 04 20                        	movs	r0, #4 / e81a: 00 90                        	str	r0, [sp] / e81c: 41 f2 99 30                  	movw	r0, #5017 / e820: 02 a9                        	add	r1, sp, #8 / e822: c0 f2 01 00                  	movt	r0, #1`

### `acdb_loader_adsp_get_audio_cal`
- `line 60: e972: 21 d0                        	beq	#66 <acdb_loader_adsp_get_audio_cal+0xc4> / e974: d8 bb                        	cbnz	r0, #118 / e976: d6 e9 03 21                  	ldrd	r2, r1, [r6, #12] / e97a: 70 69                        	ldr	r0, [r6, #20] / e97c: 0a ab                        	add	r3, sp, #40`
- `line 61: e974: d8 bb                        	cbnz	r0, #118 / e976: d6 e9 03 21                  	ldrd	r2, r1, [r6, #12] / e97a: 70 69                        	ldr	r0, [r6, #20] / e97c: 0a ab                        	add	r3, sp, #40 / e97e: 07 f0 c0 e9                  	blx	#29568`

## Direct-GET Candidate Notes

- `store_get_audio_cal` selector field evidence points at request offset `+28` and multiple
  small-input size-query paths.
- Conservative literal extraction observes a candidate `0x13265` family from `0x13091 + offsets`
  and an alternate `0x11399` family, but this report does **not** claim final cal_type mapping.
- `adsp_get_audio_cal` reads request fields around offsets `+12`, `+16`, `+20`, `+32`, `+36`, and
  `+40`, which must be pinned before any live direct GET.
- Success for a future live direct-GET remains `ret==0` and non-all-zero output; requested length
  alone is not success.

## Next Unit

V2579 should stay host-only and build a stricter direct-GET request-layout extractor: decode the
literal ACDB command IDs, request field offsets, and out-pointer/size semantics for
`store_get_audio_cal` and `adsp_get_audio_cal`. Do not rerun the V2572/V2577 public-send/common-hook
live paths unchanged.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_lower_get_abi_recon_v2578.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_lower_get_abi_recon_v2578`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_lower_get_abi_recon_v2578.py --write-report`
- `git diff --check`
