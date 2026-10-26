# S22+ mainline home-server assessment

Date: 2026-10-27. Target: SM-S906N / g0q / S906NKSS7FYG8.
Status: **H0 ADVISORY — no image build, activation, device command or firmware change**.

The operator subsequently selected this mainline/Linux-only product direction
on 2026-10-27. [GOAL.md](../../GOAL.md) records the final architecture, current
state and next bounded unit; this assessment does not activate device actions.

## Recommendation

Make mainline the preferred development direction for the headless server,
while retaining the proved FYG8 kernel and original Android return artifacts.
Android preservation is a temporary recovery strategy, not a final product
requirement. The operator's intended endpoint may retire Android once an
independent Linux rescue path and usable Download recovery replace its role.
The sister r0q port makes a bounded g0q canary credible. It does not yet qualify
unattended service, battery management, sustained thermal control or recovery
on g0q. Keep first boot, storage admission and resident operation separate.

The useful reuse is Debian userspace, retained root data, host evidence and
recovery procedures. Vendor modules, platform preparation, USB ownership,
watchdog control and kernel-specific health predicates need new qualification.
Do not regard this as replacing only two opaque files and inheriting old PASS.

## Evidence checked

- The public [r0q port](https://github.com/cammo1997/SM-S901E-Linux-Part-Working)
  was created 2026-10-17, ten days before this assessment. It describes a
  mainline-derived 7.2.11 kernel with local and pending-upstream patches.
  Its installation removed Android; that installation procedure does not fit
  this project's Android-preservation scope.
- Its [current checklist](https://github.com/cammo1997/SM-S901E-Linux-Part-Working/blob/main/CHECKLIST.md)
  reports CPU frequency scaling and idle states, partial suspend/resume,
  and leaves battery charge-limit control unfinished. It does not supply a
  g0q sustained-load or watchdog reset qualification.
- The local [ABL/FDT report](S22PLUS_FYG8_ABL_DT_HANDLING_H0_2026-10-27.md)
  confirms matching live RAM banks/splash and the reason an embedded DTB can
  avoid ABL's DT selection/overlay path. It also records Gunyah-specific live
  state, so bypassing ABL's DT does not remove the hypervisor.
- The [port boot log](https://github.com/cammo1997/SM-S901E-Linux-Part-Working/blob/main/docs/boot-log.md)
  records a DTB/remote-processor reservation collision fixed by loader DTB
  relocation. Review loader, kernel, DTB and initramfs placement together,
  including runtime reservations; matching RAM banks alone is insufficient.

## Charging and electrical limits

The [Linux 7.2 MAX77705 charger driver](https://github.com/torvalds/linux/blob/v7.2/drivers/power/supply/max77705_charger.c)
exposes writable charge-current and input-current limits. It does not expose
an 80-percent end threshold or a charging-bypass control. Its current setters
clamp to a nonzero minimum: requesting zero current is not a documented
charging-disable operation. Charger presence and battery percentage are not
proof of an unattended charge policy.

The port's [battery-info patch](https://github.com/cammo1997/SM-S901E-Linux-Part-Working/blob/main/kernel/upstream-patches/tabs8/max77705-charger-battery-info.patch)
and [review fixes](https://github.com/cammo1997/SM-S901E-Linux-Part-Working/blob/main/kernel/upstream-patches/tabs8/max77705-charger-review-fixes.patch)
address real current/voltage encoding and error-handling issues. Its r0q DTS
uses a 3700 mAh battery description and reduced charging limits. Do not copy
those limits to g0q merely by changing capacity to 4500 mAh. Verify the exact
battery model, charge-voltage/current/termination limits, temperature sensing,
input limits and error behavior against g0q's retained vendor evidence.

Proposed qualification: confirm units and readback, actual battery current
direction, temperature response, input removal/return and behavior after the
policy process fails. A future percentage policy needs validated charge
disable/enable with hysteresis; reducing float voltage is not an exact SOC cap.
Actual bypass means supplying the system without cycling/charging the battery,
not just lowering a current setting. A percentage cap does not eliminate aging
or swelling risk. The driver also programs charging timers/watchdog state, so
review those settings rather than assuming Samsung's full policy survives.

For the first canary, avoid charger programming, OTG source mode and PD voltage
negotiation. Use the already qualified physical connection with bounded,
attended duration; leaving the driver absent does not prove charging is off.

## Thermal, frequency and idle power

[SM8450's Linux 7.2 DT](https://github.com/torvalds/linux/blob/v7.2/arch/arm64/boot/dts/qcom/sm8450.dtsi)
contains TSENS, EPSS cpufreq and DCVSH interrupts. Its CPU thermal zones have
trip points but do not provide the GPU-style cooling maps. The
[cpufreq driver](https://github.com/torvalds/linux/blob/master/drivers/cpufreq/qcom-cpufreq-hw.c)
can observe hardware frequency limitation and update scheduler pressure;
its LMh interrupt is optional. The separate
[LMh driver](https://github.com/torvalds/linux/blob/master/drivers/thermal/qcom/lmh.c)
does not list an SM8450 compatible. These are distinct paths: enabling
CONFIG_QCOM_LMH alone does not prove SM8450 thermal protection.

Required evidence on this device is an increasing-load trace joining sensor
readings, requested and achieved frequencies, thermal/cooling or hardware-limit
state, and recovery after load removal. Include battery and PMIC temperature,
charging-plus-CPU/network load, idle heat and long-duration equilibrium. Use
conservative frequency/core limits first; do not discover the safe temperature
limit by driving the phone to its critical shutdown trip. Keep emergency
protection in place while verifying an earlier operational limit.

The [r0q DT](https://github.com/cammo1997/SM-S901E-Linux-Part-Working/blob/main/kernel/sm8450-samsung-r0q.dts)
also carries bandwidth votes and clk_ignore_unused/pd_ignore_unused workarounds.
Disabled multimedia nodes do not automatically mean minimum idle power.
Suspend is optional for a server; reliable CPU idle, bounded idle consumption
and preventing an unqualified automatic system suspend are still necessary.

## Watchdog and failure recovery

[Linux 7.2 gunyah_wdt.c](https://github.com/torvalds/linux/blob/v7.2/drivers/watchdog/gunyah_wdt.c)
provides an SMC watchdog with a 1–32 second timeout. The
[SCM discovery code](https://github.com/torvalds/linux/blob/v7.2/drivers/firmware/qcom/qcom_scm.c)
detects the Gunyah UUID and registers it when an enabled emulated MMIO watchdog
is not selected. This implementation does not require copying the old vendor
gh-watchdog DT node. The port's
[published config](https://github.com/cammo1997/SM-S901E-Linux-Part-Working/blob/main/kernel/config-r0q.aarch64)
has CONFIG_GUNYAH_WATCHDOG disabled; CONFIG_QCOM_WDT=m is not an equivalent proof.

Qualification must establish supported hypercalls, actual driver identity,
timeout/readback and an attended expiry reset with no writable root. Then
separately test userspace failure and defined kernel-stall classes. A normal
reboot or a visible /dev/watchdog does not establish those outcomes. Hypervisor
or whole-SoC failure remains outside a guest watchdog's demonstrated coverage.
The inspected driver also calls stop during probe; loading/probing it is not
automatically a read-only observation of the inherited watchdog state.
Choose reboot-loop stopping/fallback behavior, not merely infinite watchdog
reboots into the same failed image. USB power cycling is not a phone reset
while the internal battery supplies the SoC.

## Storage protection

The first canary should compile out UFS and disable both controller and PHY
nodes. A RAM-only build may also omit CONFIG_BLOCK if its chosen configuration
allows it. Supply no mass-storage gadget, storage helper, installed root mount
or remote-processor workload. This bounds Linux-side storage activity; ABL
still reads its ordinary boot inputs before Linux starts.

A later read-only UFS phase must establish RO before exposing usable writers,
with no automount, journal replay, fsck repair or discard. For a writable
native_data phase, use the exact partition identity and predeclared range.
Partition BLKROSET flags and a dm-linear mapping are useful accident barriers,
not isolation against privileged raw writes through the parent LUN. A strong
software boundary needs write-range enforcement covering parent/partition I/O,
discard/write-zero operations and relevant SCSI/UFS pass-through paths, plus
restricted module/raw-device access. Do not claim hardware write protection.
Leave modem and other remote processors disabled until their storage/firmware
requirements are separately understood. NFS root after the RAM canary is an
option for testing userspace without first enabling local filesystem writes.

## First g0q canary

1. Pin a reproducible base kernel, port patches, config, loader revision,
   DTB and RAM-only initramfs. Audit the live g0q reservations, partial-goods
   information and load/decompression/DTB/initramfs regions for overlap.
   Retain reserved ranges even when their corresponding device is disabled.
2. Start with one little CPU, fixed USB2 peripheral NCM, required clocks,
   interrupt/timer/SCM/PMIC/USB-PHY dependencies and a tiny RAM PID1. Disable
   UFS, Wi-Fi/BT, PCIe, GPU/display, audio, camera, touch and remote processors.
   Do not copy the full r0q peripheral-enable list or charging setup.
3. Emit bounded authenticated evidence: candidate/DTB/initramfs identities,
   current boot identity, actual PID1, basic memory/timer health, selected
   USB state and absence of UFS block devices. A USB descriptor alone is not
   proof that the intended kernel or PID1 ran.
4. Perform one reviewed boot-only transfer under a fresh finite attended
   grant. End with the original Android artifact and verified health. Early
   failure retains physical Download recovery; no timeout is called automatic
   recovery unless its actual return path has been demonstrated.
5. Only after that closure, qualify watchdog/reset, thermal/charging,
   read-only UFS and then current protected native_data admission. Historical
   dirty ext4 or uncertain package state is not cured by changing the kernel.

The first success criterion is mainline g0q + RAM PID1 + authenticated USB +
original Android return. It is not an unattended-server qualification.

## Resident operation and alternatives

The intended final model can be power-on into resident Debian, with recovery
independent of the normal writable root. Returning to Android after every
session is an experimental-stage procedure, not a requirement for that final
model. Replacing its role requires a known-good rescue kernel/initramfs, a
demonstrated way to select or restore it when normal boot fails, and retained
host recovery artifacts. A watchdog that only reboots the same broken root
does not supply this fallback. Android removal must be distinguished from
removing the bootloader, hypervisor, calibration or device-identity partitions
that Linux may still depend on.

Keep stock vendor_boot, DTBO, vbmeta, recovery, bootloader and Android storage
as currently retained during initial qualification. Resident use initially changes only the reviewed boot
payload and uses the existing dedicated native_data, after its own admission.
Keeping the original boot artifact on the host makes Android recoverable; it
does not make the phone dual-boot. Verify actual PIT/slot behavior before
assuming that names such as boot_a imply an independently bootable B slot.
Do not install TWRP or copy the sister port's partition writes as part of this
proposal. A recovery-partition carrier is a separate policy and recovery change.

Before residency, demonstrate clean reboot and crash recovery, watchdog return,
startup without the development host, USB/network reconnection and return after
power loss/low battery. Preserve known-good kernel+DTB+initramfs+matching modules
as one versioned set. Resident updates need a separately designed failure-safe
selector/rollback mechanism; changing boot under a running server does not
provide automatic rollback. Expose only the services needed, and keep important
data backed up away from the phone.

Mainline improves maintainability but does not update the frozen Samsung
bootloader, hypervisor, TrustZone or peripheral firmware. Do not call this a
fully current security platform. [Kernel.org](https://www.kernel.org/category/releases.html)
currently projects upstream 5.10 EOL in December 2026; that is not a statement
about Samsung's exact backport schedule. A one-time 7.2.11 build is not a
maintenance plan either. Reproduce it first, then track a maintained release
and minimize/review the local patch set rather than assuming it is LTS.

[Droidian](https://docs.droidian.org/faq/) uses Halium and Android kernel/drivers.
It can help a phone-oriented distribution reuse vendor functionality, but does
not resolve this project's old-kernel/ABI objective by itself. A FYG8 rebuild
with required namespace/cgroup options is a bridge option, subject to vendor
module ABI validation; 5.10 itself is not incapable of containers. postmarketOS
is useful as a mainline hardware-enablement source while retaining Debian
userspace. A maintained general-purpose server can host important services
while the S22+ remains a research or secondary node.

## Scope and method

Five Exa searches requested 25 results across power, thermal/recovery and
operational alternatives/maintenance. Conclusions above rely on the linked
primary sources and current local report, not search-result counts. Source
inspection is not g0q hardware validation. No A90 or S20+ actions occurred.
