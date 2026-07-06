# S22+ Google Store / Play services removal probe

Date: 2026-07-06

Device:
- Samsung Galaxy S22+ `SM-S906N` / `g0q`
- Build: `S906NKSS7FYG8`
- Starting debloat boundary: `154` user-0 packages

Scope:
- User-0 package-manager operations only.
- No partition writes.
- Goal: test whether Google Play Store and Play services can be removed after
  the safe `154` package debloat boundary.

## Starting State

```text
sys.boot_completed=1
persist.sys.safemode=
root=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
user-0 packages: 154
disabled packages: 0
```

Present Google packages:

```text
com.android.vending
com.google.android.gms
com.google.android.gsf
com.google.android.configupdater
com.google.android.modulemetadata
com.google.android.onetimeinitializer
com.google.android.packageinstaller
com.google.android.partnersetup
com.google.android.permissioncontroller
com.google.android.setupwizard
```

## Play Store Only

Command:

```text
cmd package uninstall --user 0 com.android.vending
```

Immediate result:

```text
Success
user-0 packages: 153
com.android.vending: missing from user-0 package list
root: OK
```

Reboot result:

```text
sys.boot_completed=1
persist.sys.safemode=
root: OK
user-0 packages: 154
com.android.vending: installed=true enabled=0
```

Interpretation:
- Store-only user-0 uninstall does not persist across reboot.

## Play Store + Play Services

Command:

```text
cmd package uninstall --user 0 com.android.vending
cmd package uninstall --user 0 com.google.android.gms
```

Immediate result:

```text
Success
Success
user-0 packages: 152
com.android.vending: missing from user-0 package list
com.google.android.gms: missing from user-0 package list
com.google.android.gsf: present
com.google.android.packageinstaller: present
com.topjohnwu.magisk: present
root: OK
```

Reboot result:

```text
sys.boot_completed=1
persist.sys.safemode=
root: OK
user-0 packages: 154
com.android.vending: installed=true enabled=0
com.google.android.gms: installed=true enabled=0
```

Interpretation:
- Removing Store and Play services together still does not persist across reboot.
- Both packages are restored/enabled by the platform/OEM package policy during
  boot.

## Disable Probe

Command:

```text
pm disable-user --user 0 com.android.vending
pm disable-user --user 0 com.google.android.gms
```

Immediate result:

```text
Package com.android.vending new state: disabled-user
Package com.google.android.gms new state: disabled-user
user-0 packages: 154
disabled packages: 2
```

Reboot result:

```text
sys.boot_completed=1
persist.sys.safemode=
root: OK
user-0 packages: 154
disabled packages: 0
com.android.vending: installed=true enabled=0
com.google.android.gms: installed=true enabled=0
```

Processes observed after reboot:

```text
com.google.android.gms.persistent
com.google.android.gms
com.google.android.gms.unstable
com.android.vending
com.android.vending:background
com.android.vending:quick_launch
```

Interpretation:
- `disable-user` also does not persist across reboot for these two packages.
- Package-manager debloat cannot currently remove or disable this pair
  persistently on this build.

## Result

The S22+ remained healthy:

```text
sys.boot_completed=1
persist.sys.safemode=
root=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
user-0 packages: 154
disabled packages: 0
```

But Play Store and Play services are not removable through ordinary user-0
package-manager operations.

Next options, if this needs to go further:
- Full Google framework batch probe (`vending` + `gms` + `gsf` + setup helpers),
  one reboot-validated unit, higher risk.
- Systemless masking through Magisk, reversible but no longer just
  package-manager cleanup.
- Leave them present and focus on non-restoring package candidates.
