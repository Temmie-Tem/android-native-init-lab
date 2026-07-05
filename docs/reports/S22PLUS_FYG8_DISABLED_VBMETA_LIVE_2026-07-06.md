# S22+ FYG8-Derived Disabled Vbmeta Live - 2026-07-06

## Scope

Live flash attempt for the FYG8-derived disabled-vbmeta AP authorized in
`AGENTS.md` and staged in
`docs/reports/S22PLUS_FYG8_DISABLED_VBMETA_PREFLIGHT_2026-07-06.md`.

## Pre-Flash State

Android was booted and ADB-authorized before the flash.

```text
sys.boot_completed=1
ro.bootloader=S906NKSS7FYG8
ro.build.version.incremental=S906NKSS7FYG8
ro.product.model=SM-S906N
ro.boot.verifiedbootstate=orange
ro.boot.veritymode=enforcing
ro.boot.boot_recovery=0
```

Candidate and rollback AP hashes matched the preflight gate:

```text
candidate_ap_sha256=804ff43b9f68278b026bd31d7703ca778518bb53a08e336e18b5016e3d2a2b4b
rollback_ap_sha256=fdf42fb913ac82bba7414d41a2995300c9bc56d31e7cddf907b487e7b2ae707b
```

## Flash

Command shape:

```text
odin4 --reboot -a workspace/private/outputs/s22plus_fyg8_disabled_vbmeta/AP.tar.md5 -d /dev/bus/usb/<redacted>
```

Odin4 transcript:

```text
Reboot into normal mode
Check file : workspace/private/outputs/s22plus_fyg8_disabled_vbmeta/AP.tar.md5
Setup Connection
initializeConnection
Receive PIT Info
success getpit
Upload Binaries
vbmeta.img.lz4
(100%)
Close Connection
```

Result: Odin4 exited `0`.

## Post-Flash State

Android did not return as an ADB-authorized `device` within the 180 second
`adb wait-for-device` window. Follow-up inspection showed ADB enumerating but
unauthorized:

```text
adb_state=unauthorized
usb_mode=Google/ADB-compatible interface
```

This is not a shell-level boot proof. It is evidence that an Android-side ADB
daemon appeared after the disabled-vbmeta flash, but `sys.boot_completed`,
`ro.boot.veritymode`, and FYG8 build props remain unverified until the operator
accepts the USB debugging RSA prompt on the device.

## Current Blocker

Blocked on host ADB authorization:

```text
error: device unauthorized.
This adb server's $ADB_VENDOR_KEYS is not set
Try 'adb kill-server' if that seems wrong.
Otherwise check for a confirmation dialog on your device.
```

`adb kill-server` plus reconnect did not clear the unauthorized state.

## Next Step

Operator should unlock the phone and accept the USB debugging RSA prompt. Then run
the planned validations:

1. Android shell props: `sys.boot_completed`, FYG8 build, verified boot state,
   and verity mode.
2. Recovery validation with `adb reboot recovery`, if Android shell access returns.
3. TWRP ADB readback of vbmeta prefix SHA against
   `9c0e5b9615f8dac2a902f709927ff3fccaa4e074b34adbd0f8cd7498db78ba13`.
4. Reboot back to Android and record final props.

Do not rollback solely due to `unauthorized`; rollback is reserved for no boot,
recovery loop, or operator-confirmed failure.

## Follow-Up - ADB Authorization Still Blocked

Later continuation checks found the same state:

```text
adb_state=unauthorized
usb_mode=Google/ADB-compatible interface
git_worktree=clean
```

Host-side checks:

```text
~/.android/adbkey exists
~/.android/adbkey.pub exists
ADB_VENDOR_KEYS was unset initially
ADB_VENDOR_KEYS=$HOME/.android adb start-server did not clear unauthorized
```

Conclusion: the remaining gate is the device-side USB debugging RSA approval
dialog. There is no current host-side proof path for `sys.boot_completed`,
`ro.boot.veritymode`, recovery boot, or vbmeta readback while ADB remains
unauthorized.
