# WSTA82 Native Execute Gate Screen Live

- Date: 2026-07-04
- Scope: live validation of the V3397 WSTA execute-gate native screen
- Candidate: `A90 Linux init 0.11.153 (v3397-wsta-execute-gate-screen)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3397_wsta_execute_gate_screen.img`
- Boot SHA256: `788e907cc3ffd24a6bc377e1751fed4921b15bc9974dba21333c736de454ff92`
- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Decision: `wsta82-native-execute-gate-screen-live-pass`

## Summary

WSTA82 validates the WSTA81 execute-gate screen in a real V3397 boot artifact.
The screen remains a display-only operator surface.  It does not start Wi-Fi,
DHCP, a public tunnel, public smoke, userdata handoff, switch-root, native
reboot, or any WSTA58 live exposure.

The V3397 source/build audit required:

```text
STATE: PUBLIC_OFF EXEC-GATED
GATE: WSTA80 READY -> WSTA58
URL: REDACTED PRIVATE-RUN ONLY
NATIVE: DISPLAY-ONLY NO AUTOSTART
```

Live `screenapp wsta` and `screenapp dpublic` both presented the `WSTA
D-PUBLIC` screen successfully:

```text
screenapp.safety=display-only-explicit
screenapp.title=WSTA D-PUBLIC
screeninfo: presented framebuffer 1080x2400 on crtc=133
screenapp.valid=1
screenapp.rc=0
screenapp.presented=1
```

## Preflight

Rollback and recovery gates were confirmed before checked-helper flashing:

- V3397 candidate SHA256 matched
  `788e907cc3ffd24a6bc377e1751fed4921b15bc9974dba21333c736de454ff92`.
- v2321 rollback SHA256 matched
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- v2237 fallback SHA256 matched
  `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- v48 fallback SHA256 matched
  `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
- TWRP recovery image SHA256 matched
  `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`.
- TWRP recovery tar SHA256 matched
  `6d9e929462ea4c85f257b080431d387d5bfb787ff800bd4178c823c3874d862a`.
- Pre-flash resident was V3396 with `selftest fail=0`.

## Hot-Reload Attempt

A first no-flash hot-reload display attempt was intentionally not counted as a
pass:

- Staged V3397 init ELF to
  `/mnt/sdext/a90/flash-staging/init_reload_wsta82_v3397`.
- Device-side staged init SHA256 matched
  `d88fef092972dcb669ca0b2550d017fa140bc5c291cd6ae6eebb3d3dd28fd9da`.
- `reload INIT-RELOAD-EXECVE ...` entered V3397 and printed the new banner.
- Because the resident autohud was not running at that moment, the hot-reloaded
  PID1 could not adopt the display owner and reported `selftest fail=1` with
  `kms not initialized`.
- A direct `screenapp wsta` then prepared KMS but failed SETCRTC with
  `Permission denied`, so hot-reload was rejected as a valid display proof path.

The device was immediately warm-rebooted back into the still-flashed V3396 boot
image.  V3396 returned with `selftest fail=0` before any checked-helper flash to
V3397.  This is a display-ownership boundary of hot-reload, not a V3397 boot
artifact failure.

## Flash And Health

Candidate flash used only the checked helper:

```text
native_init_flash.py --from-native
expected_version=v3397-wsta-execute-gate-screen
local_sha256=788e907cc3ffd24a6bc377e1751fed4921b15bc9974dba21333c736de454ff92
remote_sha256=788e907cc3ffd24a6bc377e1751fed4921b15bc9974dba21333c736de454ff92
boot_readback_sha256=788e907cc3ffd24a6bc377e1751fed4921b15bc9974dba21333c736de454ff92
phase.native_init_flash.total.elapsed_sec=65.402 ok=1
```

Post-flash identity and health:

```text
version: 0.11.153 build=v3397-wsta-execute-gate-screen
status: BOOT OK shell 5.1s
selftest: pass=12 warn=1 fail=0
```

Post-screenapp health remained clean:

```text
selftest: pass=12 warn=1 fail=0
status: BOOT OK shell 5.1s
runtime: backend=sd root=/mnt/sdext/a90 writable=yes
transport: serial/ncm/tcpctl ready
storage: sd mounted rw
```

## Screenapp Live Result

The serialized `screenapp wsta` command passed:

```text
cmdv1 screenapp wsta
screenapp.app=wsta
screenapp.safety=display-only-explicit
screenapp.title=WSTA D-PUBLIC
screeninfo: presented framebuffer 1080x2400 on crtc=133
screenapp.valid=1
screenapp.rc=0
screenapp.presented=1
status=ok
```

The serialized alias `screenapp dpublic` also passed:

```text
cmdv1 screenapp dpublic
screenapp.app=dpublic
screenapp.safety=display-only-explicit
screenapp.title=WSTA D-PUBLIC
screeninfo: presented framebuffer 1080x2400 on crtc=133
screenapp.valid=1
screenapp.rc=0
screenapp.presented=1
status=ok
```

The staged hot-reload init file was removed after the checked-flash proof:

```text
/mnt/sdext/a90/flash-staging/init_reload_wsta82_v3397: No such file or directory
```

## Safety

- Only the boot partition was flashed, and only through `native_init_flash.py`.
- No forbidden partition was touched.
- No Wi-Fi association, DHCP, public tunnel, public smoke request, credentialed
  network action, userdata action, switch-root, or persistent public exposure ran.
- No raw public URL, confirm token, SSID, PSK, BSSID, MAC, IP, gateway, DNS value,
  lease id, or device serial is committed in this report.
- The V3397 screen remains display-only and explicitly redacted.
- The device is intentionally left on healthy V3397 for the next WSTA unit.

## Validation

Prior source/build validation for V3397:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest \
  tests.test_native_wsta_operator_screenapp_source \
  tests.test_build_native_init_boot_v3396_wsta_persistent_state_screen \
  tests.test_build_native_init_boot_v3397_wsta_execute_gate_screen \
  tests.test_server_distro_wsta24_native_wifi_uplink_client \
  tests.test_server_distro_wsta26_scan_failure_diagnostic -v
```

Result: `Ran 19 tests ... OK`

Live validation:

- Hot-reload display proof attempt: rejected, recovered to V3396 `fail=0`.
- V3397 checked-helper flash: pass.
- `version`, `status`, `selftest`: pass with `fail=0`.
- `screenapp wsta`: pass, `presented=1`.
- `screenapp dpublic`: pass, `presented=1`.
- staged init cleanup: pass.
- final `selftest`: pass with `fail=0`.

## Next

The WSTA execute-gate native screen is now source-built and live-proven.  The
remaining WSTA ladder is no longer blocked on native UI visibility; continue only
with an explicitly selected WSTA80/WSTA58 live proof using fresh private tokens,
or with default-off operator UX that does not start public exposure.
