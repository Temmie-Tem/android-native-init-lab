# NATIVE_INIT V2755 — Audio Route Core Writer Host-Only

Date: 2026-06-19
Scope: host-only native-init audio route writer implementation
Previous unit: V2754 split `audio route` into `core`, `feedback`, `endpoint`, and `blocked` layers with per-control safety policy metadata.

## Decision

Implement the first write-capable `audio route` path, but only for `--layer core`.

This is the smallest route-writer step that moves toward the native-init audio feature without crossing the active speaker safety boundary:

- allowed for write: `audio route internal-speaker-safe --apply --layer core`
- allowed for write: `audio route internal-speaker-safe --reset --layer core`
- still refused: `feedback`, `endpoint`, `blocked`, and default `all`
- still refused: any selected route containing `SpkrLeft BOOST Switch`

No device action, no ALSA live route write, no boot image build, and no flash were performed in this unit.

## Implemented Behavior

The core writer uses the same ALSA control discovery path as `audio app-type`:

1. open `/dev/snd/controlC<card>`
2. resolve a control by exact ALSA element name with `SNDRV_CTL_IOCTL_ELEM_LIST`
3. validate element info with `SNDRV_CTL_IOCTL_ELEM_INFO`
4. fill either integer or enumerated values
5. write with `SNDRV_CTL_IOCTL_ELEM_WRITE`

Integer controls support the pinned zero-fill contract. Enumerated controls resolve the requested enum string by iterating `snd_ctl_elem_info.value.enumerated.item` and matching the returned enum name.

Write order:

- apply: forward V2378 order
- reset: reverse V2378 reset order

## Safety Boundary

`audio_route_layer_write_allowed()` allows only `core`.

Non-core write attempts return before any ALSA write attempt:

- boost-selected layers: `audio.route.refused=write-mode-blocked-smart-amp-boost-review`
- other non-core layers: `audio.route.refused=write-mode-blocked-non-core-layer`

This intentionally keeps `feedback` and `endpoint` unavailable for live writes until speaker-protection policy is decided.

## Validation

Commands:

```bash
mkdir -p workspace/private/builds/native-init/v2755-audio-route-core-writer
aarch64-linux-gnu-gcc -std=gnu99 -Wall -Wextra -Werror -fsyntax-only \
  -I workspace/public/src/native-init workspace/public/src/native-init/a90_audio.c
aarch64-linux-gnu-gcc -std=gnu99 -Wall -Wextra -Werror \
  -I workspace/public/src/native-init -c workspace/public/src/native-init/a90_audio.c \
  -o workspace/private/builds/native-init/v2755-audio-route-core-writer/a90_audio.o
file workspace/private/builds/native-init/v2755-audio-route-core-writer/a90_audio.o
sha256sum workspace/private/builds/native-init/v2755-audio-route-core-writer/a90_audio.o
python3 -m py_compile \
  tests/test_native_audio_route_core_writer_v2755.py \
  tests/test_native_audio_route_layer_policy_v2754.py \
  tests/test_native_audio_route_contract_v2753.py \
  tests/test_native_audio_app_type_command_v2752.py \
  tests/test_native_audio_command_profile_contract_v2751.py \
  workspace/public/src/scripts/revalidation/native_audio_speaker_profiles_v2749.py \
  workspace/public/src/scripts/revalidation/native_audio_speaker_feature_entrypoint_v2750.py
PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest \
  tests.test_native_audio_route_core_writer_v2755 \
  tests.test_native_audio_route_layer_policy_v2754 \
  tests.test_native_audio_route_contract_v2753 \
  tests.test_native_audio_app_type_command_v2752 \
  tests.test_native_audio_command_profile_contract_v2751 \
  tests.test_native_audio_speaker_profiles_v2749 \
  tests.test_native_audio_speaker_feature_entrypoint_v2750 -v
```

Result:

- `a90_audio.c` syntax-only compile: pass
- AArch64 object build: pass
- object type: `ELF 64-bit LSB relocatable, ARM aarch64, version 1 (SYSV), not stripped`
- object SHA256: `a3be4a7d4ca37f1d4854ad60d23c690ac8814cd3ecc1c13aea9d02ff427c3e46`
- Python py_compile: pass
- unittest: `Ran 34 tests ... OK`

## Next Step

Build a test boot image with the V2755 `audio route --layer core` writer and run a bounded device validation:

1. flash only through `native_init_flash.py`
2. health-check `version/status/selftest`
3. materialize `/dev/snd` and ADSP as needed
4. run `audio route internal-speaker-safe --apply --layer core`
5. run `audio route internal-speaker-safe --reset --layer core`
6. rollback to V2321 and confirm `selftest fail=0`

Do not run `feedback`, `endpoint`, or `blocked` route writes in that validation.
