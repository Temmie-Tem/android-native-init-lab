# WSTA62 Native Persistent-State Screen Live

- Date: 2026-07-04
- Scope: rollback-gated live validation of the V3396 WSTA persistent-state native screen
- Candidate: `A90 Linux init 0.11.152 (v3396-wsta-persistent-state-screen)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3396_wsta_persistent_state_screen.img`
- Boot SHA256: `499f2b348d5d6ed9a5d219043d4fbef25dc4c158f542a4eec014b293c5e9872f`
- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Decision: `wsta62-native-persistent-state-screen-live-pass`

## Summary

WSTA62 validates the WSTA61 persistent-state screen in a real V3396 boot artifact.
The screen remains a display-only operator surface.  It does not read or display
raw public URLs, Wi-Fi identifiers, network addresses, credentials, confirm-token
values, or lease identifiers, and it does not add native connect, DHCP, public
tunnel, reboot, flash, userdata, or switch-root behavior.

The V3396 source/build audit required the new redacted persistent-state text:

```text
STATE: PUBLIC_OFF LEASE-GATED
PROOF: WSTA55 START / WSTA58 RENEW
URL: REDACTED PRIVATE-RUN ONLY
NATIVE: DISPLAY-ONLY NO CONNECT
```

Live `screenapp wsta` and `screenapp dpublic` both presented the `WSTA D-PUBLIC`
screen successfully:

```text
screenapp.safety=display-only-explicit
screenapp.title=WSTA D-PUBLIC
screenapp.valid=1
screenapp.rc=0
screenapp.presented=1
```

## Preflight

Rollback and recovery gates were re-confirmed before flashing:

- V3396 candidate SHA256 matched
  `499f2b348d5d6ed9a5d219043d4fbef25dc4c158f542a4eec014b293c5e9872f`.
- v2321 rollback SHA256 matched
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- v2237 fallback SHA256 matched
  `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- v48 fallback image was present with SHA256
  `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
- TWRP recovery image SHA256 matched
  `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`.
- TWRP recovery tar SHA256 matched
  `6d9e929462ea4c85f257b080431d387d5bfb787ff800bd4178c823c3874d862a`.
- Pre-flash resident was V3395 with `selftest fail=0`.

## Flash And Health

Candidate flash used only the checked helper:

```text
native_init_flash.py --from-native
expected_version=v3396-wsta-persistent-state-screen
local_sha256=499f2b348d5d6ed9a5d219043d4fbef25dc4c158f542a4eec014b293c5e9872f
remote_sha256=499f2b348d5d6ed9a5d219043d4fbef25dc4c158f542a4eec014b293c5e9872f
boot_readback_sha256=499f2b348d5d6ed9a5d219043d4fbef25dc4c158f542a4eec014b293c5e9872f
phase.native_init_flash.total.elapsed_sec=61.971 ok=1
```

Post-flash identity and health:

```text
version: 0.11.152 build=v3396-wsta-persistent-state-screen
selftest: pass=12 warn=1 fail=0
status: selftest fail=0
```

Post-screenapp health remained clean:

```text
selftest: pass=12 warn=1 fail=0
status: selftest fail=0
runtime: sd writable=yes
transport: serial/ncm/tcpctl ready
storage: sd mounted rw
```

## Screenapp Live Result

An initial parallel screenapp attempt was invalid because two cmdv1 transactions
contended for the serial transaction lock and one frame was corrupted.  The bridge
recovered immediately, `version` returned the V3396 identity, and the invalid
attempt was not counted as live proof.

After an explicit `hide` and settle delay, both aliases passed as single serialized
commands:

```text
cmdv1 screenapp wsta
screenapp.app=wsta
screenapp.safety=display-only-explicit
screenapp.title=WSTA D-PUBLIC
screeninfo: presented framebuffer 1080x2400
screenapp.valid=1
screenapp.rc=0
screenapp.presented=1
status=ok
```

```text
cmdv1 screenapp dpublic
screenapp.app=dpublic
screenapp.safety=display-only-explicit
screenapp.title=WSTA D-PUBLIC
screeninfo: presented framebuffer 1080x2400
screenapp.valid=1
screenapp.rc=0
screenapp.presented=1
status=ok
```

## Safety

- Only the boot partition was flashed, and only through `native_init_flash.py`.
- No forbidden partition was touched.
- No Wi-Fi association, DHCP, public tunnel, public smoke request, credentialed
  network action, userdata action, switch-root, or persistent public exposure ran.
- No raw public URL, confirm token, SSID, PSK, BSSID, MAC, IP, gateway, DNS value,
  lease id, or device serial is committed in this report.
- The V3396 screen remains display-only and explicitly redacted.

## Validation

Prior source/build validation for V3396:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_native_wsta_operator_screenapp_source \
  tests.test_build_native_init_boot_v3395_wsta_screenapp_live \
  tests.test_build_native_init_boot_v3396_wsta_persistent_state_screen \
  tests.test_server_distro_wsta24_native_wifi_uplink_client \
  tests.test_server_distro_wsta26_scan_failure_diagnostic \
  tests.test_server_distro_wsta58_renewal_manual_stop_proof
```

Result: `Ran 29 tests ... OK`

Live validation:

- V3396 checked-helper flash: pass.
- `version`, `status`, `selftest`: pass with `fail=0`.
- `screenapp wsta`: pass, `presented=1`.
- `screenapp dpublic`: pass, `presented=1`.
- post-screenapp `status`/`selftest`: pass with `fail=0`.

## Next

The WSTA persistent-state native screen is now live-proven.  The next meaningful
step is the persistent exposure ladder itself: keep public exposure default-off,
reuse the fixed WSTA58 cleanup/redaction gates, and only run public exposure under
fresh short-lived private lease artifacts and explicit operator gates.
