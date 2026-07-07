# S22+ Android debloat reapply to safe boundary

Date: 2026-07-06

Device:
- Samsung Galaxy S22+ `SM-S906N` / `g0q`
- Build: `S906NKSS7FYG8`
- Root: Magisk 30.7

Scope:
- Reapply package cleanup after factory-reset recovery from the prior pass4
  incident.
- User-0 package-manager uninstall only.
- No partition writes.
- Explicitly excluded the known-bad pass4 package set.

## Starting State

```text
adb: <S22_SERIAL_REDACTED> device usb:2-1.3 product:g0qksx model:SM_S906N device:g0q
sys.boot_completed=1
build=S906NKSS7FYG8
persist.sys.safemode=
root=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
user-0 packages: 467
disabled packages: 2
```

Disabled packages at start:

```text
com.google.android.gms.supervision
com.samsung.android.knox.zt.framework
```

## Safety Boundary

Known-good target:
- Previous pass3 boundary: `154` user-0 packages.
- Previous pass3 reboot validation was clean.

Known-bad boundary:
- Previous pass4 boundary: `141` user-0 packages.
- Previous pass4 caused forced Samsung safe mode and required factory reset.

The following pass4 packages were kept installed and excluded from this run:

```text
com.android.bluetooth
com.android.cameraextensions
com.android.mtp
com.android.uwb.resources
com.google.android.documentsui
com.qualcomm.location
com.samsung.android.app.telephonyui.esimclient
com.samsung.android.nfc.resources.korea
com.samsung.android.providers.factory
com.samsung.android.wallpaper.res
com.skms.android.agent
com.skp.seio
com.skt.prod.dialer
```

## Pass1+2 Reapply

Candidate construction:
- Pass1 package list extracted from
  `docs/reports/S22PLUS_ANDROID_DEBLOAT_PASS1_2026-07-06.md`.
- Pass2 package list reused from `/tmp/s22_debloat_pass2_present.txt`.
- Known-bad pass4 packages excluded.
- Current user-0 installed intersection only.

Execution log:

```text
/tmp/s22_redebloat_pass12_20260706T140937Z.log
processed: 212
success: 210
failure: 2
```

Failures:

```text
com.osp.app.signin -> Failed to uninstall a package
com.samsung.android.themecenter -> DELETE_FAILED_INTERNAL_ERROR
```

Post-pass1+2 state:

```text
user-0 packages: 257
disabled packages: 1
disabled package:
  com.samsung.android.knox.zt.framework
```

Reboot validation:

```text
boot_completed_after=6s
sys.boot_completed=1
persist.sys.safemode=
root=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
user-0 packages: 257
```

## Pass3 Reapply

Candidate construction:
- Pass3 package list reused from `/tmp/s22_debloat_pass3_present.txt`.
- Known-bad pass4 packages excluded.
- Current user-0 installed intersection only.

Execution log:

```text
/tmp/s22_redebloat_pass3_20260706T141114Z.log
processed: 115
success: 105
failure: 10
```

Failures:

```text
com.google.android.sdksandbox -> DELETE_FAILED_INTERNAL_ERROR
com.knox.vpn.proxyhandler -> Failed to uninstall a package
com.osp.app.signin -> Failed to uninstall a package
com.samsung.android.knox.app.networkfilter -> Failed to uninstall a package
com.samsung.android.knox.er -> Failed to uninstall a package
com.samsung.android.knox.kfbp -> Failed to uninstall a package
com.samsung.android.knox.knnr -> Failed to uninstall a package
com.samsung.android.knox.sandbox -> Failed to uninstall a package
com.samsung.android.themecenter -> DELETE_FAILED_INTERNAL_ERROR
com.sec.enterprise.knox.cloudmdm.smdms -> Failed to uninstall a package
```

Post-pass3 state before reboot:

```text
user-0 packages: 154
disabled packages: 0
```

The known-bad pass4 packages remained installed.

Core package check passed for:

```text
com.android.settings
com.sec.android.app.launcher
com.android.systemui
com.google.android.gms
com.android.vending
com.google.android.webview
com.google.android.gsf
com.google.android.packageinstaller
com.google.android.permissioncontroller
com.google.android.networkstack
com.samsung.android.networkstack
com.android.phone
com.android.server.telecom
com.sec.imsservice
com.android.providers.telephony
com.topjohnwu.magisk
```

Final reboot validation:

```text
boot_completed_after=6s
sys.boot_completed=1
persist.sys.safemode=
root=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
user-0 packages: 154
disabled packages: 0
```

## Result

The S22+ is back at the previously proven safe debloat boundary:

```text
safe boundary: 154 user-0 packages
root: OK
forced safe mode: absent
known-bad pass4 set: retained
```

Do not apply the old pass4 set as a batch again. If further package-count
reduction is needed, probe only one or two packages at a time with a reboot
validation after each probe.
