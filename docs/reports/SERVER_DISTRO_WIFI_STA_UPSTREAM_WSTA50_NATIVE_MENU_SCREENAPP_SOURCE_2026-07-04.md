# WSTA50 Native Menu Screenapp Source

- Date: 2026-07-04
- Scope: native/HUD/menu source integration for the WSTA operator path
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta50-native-menu-screenapp-source-pass`

## Summary

WSTA50 moves the WSTA operator path from host-only documentation into the native menu
surface without authorizing any native public action.

Added a read-only WSTA operator screen:

- Network menu item: `WSTA PUBLISH`
- Direct display alias: `screenapp wsta` or `screenapp dpublic`
- Native draw function: `a90_app_network_draw_wsta_operator()`

The screen presents the proven flow:

```text
WSTA45 -> WSTA43 -> WSTA42
publish is host-runbook only
native menu is display-only and does not connect
WSTA48 provides the redacted aggregate result
```

This is intentionally not a Wi-Fi connect, DHCP, cloudflared, public tunnel, native reboot,
or flash control surface.

## Touched Source

- `workspace/public/src/native-init/a90_app_network.c`
- `workspace/public/src/native-init/a90_app_network.h`
- `workspace/public/src/native-init/a90_menu.c`
- `workspace/public/src/native-init/a90_menu.h`
- `workspace/public/src/native-init/v319/40_menu_apps.inc.c`
- `workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c`
- `workspace/public/src/native-init/v319/80_shell_dispatch.inc.c`

## Safety

- No device command ran.
- No boot image was built or flashed.
- No native reboot, Wi-Fi association, DHCP, public tunnel, public smoke request, or
  external service action ran in this unit.
- The menu entry is read-only display guidance.  It does not call Wi-Fi command handlers,
  scan/ping collectors, D-public runners, or cloudflared.
- No raw public URL, confirm token, SSID, PSK, BSSID, IP, gateway, or DNS value is
  committed.

## Validation

Focused source tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_native_wsta_operator_screenapp_source \
  tests.test_native_audio_screenapp_status_v2822 \
  tests.test_native_changelog_audio_productization_v2851 \
  tests.test_native_audio_profile_screen_v2831 \
  tests.test_native_audio_stage_screen_v2833
```

Result: `Ran 13 tests ... OK`

Host-only native-init compile:

```text
PYTHONPATH=workspace/public/src/scripts/revalidation PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 - <<'PY'
from pathlib import Path
from types import SimpleNamespace
import build_native_init_boot_v724 as builder
args = SimpleNamespace(
    cross_gcc='aarch64-linux-gnu-gcc',
    strip='aarch64-linux-gnu-strip',
    init_binary=Path('/tmp/a90_wsta50_init_compile'),
)
builder.build_init(args)
PY
```

Result: AArch64 static init binary compiled and stripped.  The emitted warnings were
pre-existing unrelated native-init warnings.

```text
git diff --check
```

Result: pass

## Next

WSTA now has native menu visibility for the bounded operator publish path.  The next
meaningful step should be a deliberately gated persistent exposure design or a live
screenapp validation in a new boot artifact, not another host-only productization pass.
