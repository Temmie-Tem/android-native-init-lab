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

## Original Next Step

At this point the plan still assumed a TWRP recovery ADB shell might be present.
The operator later corrected that the device was in stock/general recovery, not
TWRP. The historical next-step list was:

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

## Follow-Up - Android Boot Verified, Recovery ADB Blocked

After device-side Android ADB authorization was accepted, Android shell-level
boot validation passed:

```text
sys.boot_completed=1
ro.bootloader=S906NKSS7FYG8
ro.build.version.incremental=S906NKSS7FYG8
ro.product.model=SM-S906N
ro.boot.verifiedbootstate=orange
ro.boot.veritymode=
ro.boot.boot_recovery=0
ro.boot.flash.locked=0
```

Additional Android props showed AVB present and the expected unlocked/orange
state:

```text
ro.boot.avb_version=1.2
ro.boot.verifiedbootstate=orange
ro.config.dmverity=G
```

The local candidate hashes remained pinned:

```text
patched_raw_vbmeta_sha256=9c0e5b9615f8dac2a902f709927ff3fccaa4e074b34adbd0f8cd7498db78ba13
candidate_ap_sha256=804ff43b9f68278b026bd31d7703ca778518bb53a08e336e18b5016e3d2a2b4b
rollback_ap_sha256=fdf42fb913ac82bba7414d41a2995300c9bc56d31e7cddf907b487e7b2ae707b
```

`adb reboot recovery` was then issued. ADB did not return as an authorized
recovery shell within 180 seconds. Follow-up USB/ADB inspection showed recovery
or recovery-like ADB enumeration, but still unauthorized:

```text
adb_state=unauthorized
usb_mode=Google/ADB-compatible interface
```

`adb kill-server && adb start-server` did not clear recovery authorization.

Current proof level:

- Android boot after FYG8-derived disabled-vbmeta flash: **verified**.
- TWRP ADB shell and vbmeta prefix readback: **not applicable to this run**.
  The device is in stock/general recovery, not TWRP.
- Recovery ADB shell: **unauthorized**, which is expected to limit host-side
  readback from stock/general recovery.
- No stock-vbmeta rollback has been run because Android boot was already proven
  and the current blocker is authorization, not no-boot or recovery-loop.

## Follow-Up - Stock Recovery Correction

The operator confirmed the recovery UI is stock/general recovery, not TWRP.
Therefore the earlier TWRP/readback expectation is not a completion criterion for
this unit. The live proof for the requested FYG8-derived disabled-vbmeta boot
validation is:

1. The exact FYG8-derived vbmeta-only AP was transferred by Odin4, including
   `vbmeta.img.lz4` at `100%`, and Odin4 exited `0`.
2. Android booted afterward with ADB-authorized shell access.
3. Android reported `sys.boot_completed=1`.
4. Android reported `ro.bootloader=S906NKSS7FYG8` and
   `ro.build.version.incremental=S906NKSS7FYG8`.
5. Android reported `ro.boot.boot_recovery=0`, proving normal Android boot, not
   recovery.

The later `adb reboot recovery` check intentionally moved the device into
stock/general recovery. Host `adb reboot` from that state is denied because ADB is
unauthorized. The operator must select `Reboot system now` on the device to return
to Android, after which a final Android props recapture can be appended.
