# NATIVE_INIT V2754 — Audio Route Layer Policy Host-Only

Date: 2026-06-19
Scope: host-only native-init audio route API refinement
Previous unit: V2753 added the `audio route` dry-run contract and blocked route writes because the proven route contains `SpkrLeft BOOST Switch`.

## Decision

Refine `audio route` into explicit route layers and per-control speaker/policy metadata. This keeps moving toward the productized `audio` command surface while preserving the active safety boundary: **no WSA smart-amp gain/boost writes**.

No device action, no ALSA route write, no boot image build, and no flash were performed.

## Implemented Contract

Command usage now accepts a layer filter:

```text
audio route [profile] [--dry-run|--apply|--reset] [--layer all|core|feedback|endpoint|blocked]
```

Layer meanings:

- `all`: complete V2378/V2748 route contract.
- `core`: stream and codec route controls that do not directly target the WSA speaker endpoint.
- `feedback`: VI-sense feedback-path controls observed in the working route.
- `endpoint`: `SpkrLeft` endpoint controls.
- `blocked`: controls blocked by hard safety policy; currently `SpkrLeft BOOST Switch`.

Each route control now carries:

- `role`
- `layer`
- `speaker`
- `policy`
- reset capability
- smart-amp boost marker

The dry-run output adds layer-aware counters:

```text
audio.route.layer=<filter>
audio.route.selected.apply.count=<n>
audio.route.selected.reset.count=<n>
audio.route.selected.smart_amp_boost_blocked=<0|1>
```

## Write Behavior

Write modes remain refused, but V2754 distinguishes why:

- selected layer includes `SpkrLeft BOOST Switch`:
  - `audio.route.refused=write-mode-blocked-smart-amp-boost-review`
- selected layer does not include boost:
  - `audio.route.refused=write-mode-blocked-route-writer-not-implemented`

This makes the next safe implementation step concrete: implement the non-boost writer first, then decide separately whether endpoint/boost policy can ever be enabled.

## Validation

Commands:

```bash
mkdir -p workspace/private/builds/native-init/v2754-audio-route-layer-policy
aarch64-linux-gnu-gcc -std=gnu99 -Wall -Wextra -Werror -fsyntax-only \
  -I workspace/public/src/native-init workspace/public/src/native-init/a90_audio.c
aarch64-linux-gnu-gcc -std=gnu99 -Wall -Wextra -Werror \
  -I workspace/public/src/native-init -c workspace/public/src/native-init/a90_audio.c \
  -o workspace/private/builds/native-init/v2754-audio-route-layer-policy/a90_audio.o
file workspace/private/builds/native-init/v2754-audio-route-layer-policy/a90_audio.o
sha256sum workspace/private/builds/native-init/v2754-audio-route-layer-policy/a90_audio.o
python3 -m py_compile \
  tests/test_native_audio_route_layer_policy_v2754.py \
  tests/test_native_audio_route_contract_v2753.py \
  tests/test_native_audio_app_type_command_v2752.py \
  tests/test_native_audio_command_profile_contract_v2751.py \
  workspace/public/src/scripts/revalidation/native_audio_speaker_profiles_v2749.py \
  workspace/public/src/scripts/revalidation/native_audio_speaker_feature_entrypoint_v2750.py
PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest \
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
- object SHA256: `e16d3a8b9b43ec18269dffc7ddddb1363024fedb533c955e716d370de5d068b6`
- Python py_compile: pass
- unittest: `Ran 29 tests ... OK`

## Next Step

Implement the route writer only for a non-boost layer after one more host-side design pass:

1. Resolve ALSA controls by name using the existing App-Type Config control-resolution pattern.
2. Write only layer `core` first; keep `feedback`, `endpoint`, and `blocked` refused.
3. Device-test the core route write under rollback to V2321 before broadening scope.

The current unit deliberately does not attempt this live path.
