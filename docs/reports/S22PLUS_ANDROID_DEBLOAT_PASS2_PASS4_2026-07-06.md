# S22+ Android debloat pass2-pass4

Date: 2026-07-06

Device:
- Samsung Galaxy S22+ `SM-S906N` / `g0q`
- Build: `S906NKSS7FYG8`
- Root before passes: Magisk `uid=0(root) gid=0(root) context=u:r:magisk:s0`

Scope:
- User-0 package-manager debloat only.
- No boot/system/vendor/vbmeta partition writes.
- Restore mechanism for user-0 uninstalls: `cmd package install-existing --user 0 <package>`.

Reference:
- A90 precedent: `docs/reports/ADB_DEBLOAT_2026-04-22.md`
- A90 minimal status: `docs/reports/MINIMAL_BOOT_STATUS_2026-04-22.md`
- A90 allowlist: `docs/plans/MINIMAL_BOOT_ALLOWLIST_2026-04-22.txt`
- A90 research: `docs/reports/ADB_DEBLOAT_RESEARCH_2026-04-22.md`

## Pass2

Pre-count after pass1:

```text
active user-0 packages: 432
```

Candidate source:
- A90 allowlist/research plus S22+ currently installed packages.
- Kept: SystemUI, Settings, Launcher, GMS/GSF/Play Store/WebView, package/permission controller, phone/telecom/IMS/telephony, network stacks, Magisk, KG/FMM/attestation-class packages.

Execution log:

```text
/tmp/s22_debloat_pass2_uninstall_20260706T125439Z.log
processed: 177
success: 175
failure: 2
```

Failures / remaining candidates:

```text
com.osp.app.signin -> Failed to uninstall a package
com.samsung.android.themecenter -> DELETE_FAILED_INTERNAL_ERROR
```

Post-count:

```text
active user-0 packages: 257
disabled user-0 packages:
  com.samsung.android.game.gos
  com.samsung.android.knox.zt.framework
```

Health:

```text
sys.boot_completed=1
root=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
```

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

## Pass3

Candidate source:
- More aggressive server/device-use trim from the pass2 remainder.
- Still preserved core Android UI, GMS, Play Store, phone/IMS/network, root, KG/FMM/attestation.

Execution log:

```text
/tmp/s22_debloat_pass3_uninstall_20260706T125745Z.log
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

Observed pass3 stubborn packages after uninstall:

```text
com.samsung.android.game.gos
com.sec.android.sdhms
```

Both behaved like the prior A90 case: `pm uninstall --user 0` returned `Success`,
but the packages remained present for user 0.

Post-count before reboot:

```text
active user-0 packages: 154
```

Reboot validation:

```text
boot_completed_after=5s
sys.boot_completed=1
build=S906NKSS7FYG8
root=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
active user-0 packages: 154
```

Core package check passed for the same core list as pass2.

Conclusion:
- Pass3 is the last known-good debloat checkpoint.
- Do not exceed pass3 without a smaller, reboot-validated candidate split.

## Pass4 Incident

Pass4 candidate list:

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

Execution log:

```text
/tmp/s22_debloat_pass4_uninstall_20260706T130044Z.log
processed: 13
success: 13
```

Immediate count:

```text
active user-0 packages: 141
```

Failure:
- After reboot, the device played boot sound and showed boot animation but did not
  enter the Android home screen.
- Host initially saw no ADB/USB device.
- Later ADB appeared as `unauthorized`, then the operator reached recovery/download
  mode.

Interpretation:
- Pass4 crossed the safe boundary.
- The boot-stopping package is likely inside the 13-package pass4 set.
- Pass3 is proven good; pass4 is not.

Likely higher-risk pass4 suspects:
- `com.android.bluetooth`
- `com.google.android.documentsui`
- `com.android.mtp`
- `com.samsung.android.wallpaper.res`
- `com.qualcomm.location`

## Recovery plan

Best case, if Android ADB becomes authorized:

```bash
for p in \
  com.android.bluetooth \
  com.android.cameraextensions \
  com.android.mtp \
  com.android.uwb.resources \
  com.google.android.documentsui \
  com.qualcomm.location \
  com.samsung.android.app.telephonyui.esimclient \
  com.samsung.android.nfc.resources.korea \
  com.samsung.android.providers.factory \
  com.samsung.android.wallpaper.res \
  com.skms.android.agent \
  com.skp.seio \
  com.skt.prod.dialer
do
  adb shell cmd package install-existing --user 0 "$p"
done
adb reboot
```

If TWRP/recovery ADB is available and `/data` is mounted/decrypted:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/s22_debloat_pass4_rescue.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/s22_debloat_pass4_rescue.py --apply
```

The helper backs up:

```text
/data/system/users/0/package-restrictions.xml
```

and edits only the pass4 package entries to restore user-0 installed state.

If only stock recovery is available and Android ADB never becomes authorized:
- Factory reset is the destructive fallback.
- It should clear user-0 package-manager restrictions and restore preinstalled
  packages, but it will also clear `/data` apps/settings and may require reinstalling
  the Magisk APK. The patched boot image/root infrastructure itself is not a data
  partition state.

## Current recommendation

Recover to pass3, then stop debloat at `154` active packages for now. Further
package-count trimming should split pass4 into one-package or two-package reboot
validated probes, starting with the least risky overlays/resources and leaving
Bluetooth, DocumentsUI, MTP, wallpaper resources, and Qualcomm location until last.

## Recovery Result

The operator used recovery `erase app data` after the pass4 boot failure.

Post-recovery status:

```text
adb: RFCT519XWGK device usb:2-1.3 product:g0qksx model:SM_S906N device:g0q
sys.boot_completed=1
build=S906NKSS7FYG8
verifiedbootstate=orange
flash_locked=0
```

Package-manager state after data erase:

```text
all user-0 packages: 467
enabled user-0 packages: 465
disabled user-0 packages: 2
```

Disabled packages:

```text
com.google.android.gms.supervision
com.samsung.android.knox.zt.framework
```

Magisk/root status:

```text
/debug_ramdisk/su -> ./magisk
magiskd running
/debug_ramdisk/su -c id:
uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
```

Plain `su -c id` failed because `su` was not in the default shell PATH after the
data erase. Root itself remained available through `/debug_ramdisk/su`.

Core packages were present after recovery:

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

Final interpretation:
- The device recovered to Android after data erase.
- The pass4 package-manager restrictions were cleared by the erase.
- Root infrastructure survived, but command examples should use
  `/debug_ramdisk/su -c ...` until Magisk restores a default `su` path.
- The proven debloat boundary remains pass3 at `154` packages. Pass4 at `141`
  packages is a failed boundary.

Normal-mode reboot validation:

```text
boot_completed_after=7s
sys.boot_completed=1
build=S906NKSS7FYG8
persist.sys.safemode=
device_provisioned=1
user_setup_complete=1
/debug_ramdisk/su -c id:
uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
all user-0 packages: 467
enabled user-0 packages: 465
disabled user-0 packages: 2
```

Disabled packages after the normal-mode reboot:

```text
com.google.android.gms.supervision
com.samsung.android.knox.zt.framework
```

## Forced Safe Mode Note

After the normal reboot, the operator observed a Samsung safe-mode dialog:

```text
Title: 안전 모드에서 휴대전화 시작하기
Body: 문제점이 발견되어 휴대전화를 정상적으로 켤 수 없습니다.
      안전모드에서 나가려면 휴대전화를 전체 초기화 해주세요.
      휴대전화 초기화 전에 안전모드에서 PC나 SD 카드에 데이터를 백업할 수 있습니다.
```

Additional checks:

```text
screen watermark: 안전 모드
sys.boot_completed=1
/debug_ramdisk/su -c id: uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
dumpsys input: KeyDowns: 0 keys currently down
5-second getevent watch: no volume-key events observed
```

Interpretation:
- This is not the usual volume-down-triggered safe mode.
- The framework is forcing a recovery/safe-mode boot because it detected a
  normal-boot problem.
- The device itself recommends full factory reset to leave this mode.
- ADB and Magisk root still work while in this forced safe mode.

The host also pulled a private backup under `workspace/private/` before the
operator clarified that the large `/sdcard/Download` contents were only AP image
and Magisk APK artifacts, not required user data. The backup was left uncommitted.

## Final Factory Reset Recovery

The operator completed full factory reset, setup wizard, and USB debugging setup.

Post-reset validation:

```text
adb: RFCT519XWGK device usb:2-1.3 product:g0qksx model:SM_S906N device:g0q
sys.boot_completed=1
build=S906NKSS7FYG8
persist.sys.safemode=
device_provisioned=1
user_setup_complete=1
all user-0 packages: 467
enabled user-0 packages: 465
disabled user-0 packages: 2
```

Disabled packages after reset:

```text
com.google.android.gms.supervision
com.samsung.android.knox.zt.framework
```

Core package check passed for Settings, Launcher, SystemUI, GMS, Play Store,
WebView, GSF, PackageInstaller, PermissionController, NetworkStack,
SamsungNetworkStack, Phone, Telecom, IMS, TelephonyProvider, and Magisk.

Magisk post-reset repair:

```text
initial Magisk app state: stub versionName=1.0
local APK installed: /home/temmie/다운로드/Magisk-v30.7.apk
installed Magisk versionName=30.7 versionCode=30700
Magisk additional setup prompt accepted
Magisk Superuser entry: [SharedUID] 셸 / com.android.shell allowed
/debug_ramdisk/su -c id:
uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
su -c id:
uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
```

Final state:
- Android boots normally after factory reset.
- Forced safe mode is gone.
- User-0 package restrictions are reset to stock-like `467` package state.
- Magisk root is restored after reinstalling/updating the Magisk APK and allowing
  the shell superuser entry.
