# S20+ G986N mainline y2q host bring-up

Target `SM-G986N` / `y2q` / `G986NKSS8IYC2`. The bounded unit is an
ARM64 mainline kernel, y2q DTB and RAM initramfs with a USB 2.0 CDC ACM
PID 1 witness. The generated files are separate host artifacts. Boot image
packaging and physical execution remain open.

## Imported board support

The [y2q DTS](../../workspace/public/src/mainline/s20plus_y2q_h0/sm8250-samsung-y2q-h0.dts)
includes the [Linux v6.18 Samsung SM8250 common DTS](https://github.com/torvalds/linux/blob/v6.18/arch/arm64/boot/dts/qcom/sm8250-samsung-common.dtsi)
used by the upstream Galaxy S20 and S20 FE. It inherits the primary DWC3
peripheral, USB 2.0 PHY, Qualcomm clocks, regulators and interconnect
declarations. The first build disables UFS and its PHY, the framebuffer,
and GPIO/PMIC keys. It keeps the splash reservation and the y2q ramoops
record layout. The [kernel configuration fragment](../../workspace/public/src/mainline/s20plus_y2q_h0/y2q.fragment)
omits pstore, the block layer, networking, module loading and USB host support.

The [RAM init](../../workspace/public/src/mainline/s20plus_y2q_h0/init.c)
checks PID 1, mounts devtmpfs, sysfs and configfs, and binds one ACM
function to the UDC name derived from the upstream DWC3 device. Its marker
carries a host-generated build ID that also appears in the gadget descriptor.
It provides a bounded write window and parks in PID 1. A future host
observation must receive a complete marker from the matching endpoint.

## Stock handoff and live observation

- The six retained combinations of the three stock kona DTBs and Korean
  board overlays 13 and 14 each match the new DTB's ramoops region and
  record, console, ftrace and PMSG sizes. The UFS controller and PHY power
  references match the five upstream PM8150 rails in both Korean overlays.
  UFS voltage constraints, link initialization, and the boot splash mode
  remain hardware-specific follow-ups. [Stock DTB and DTBO provenance](S20PLUS_G986N_EARLY_BOOT_OBSERVATION_H0_2026-09-05.md#ramoops-and-pmsg)
- Both Korean overlays fail libfdt application to this DTB with
  `FDT_ERR_NOTFOUND`. Each overlay has 202 external fixup names and the
  mainline DTB lacks 186 of them. Across all six merged stock trees, 11
  of 29 distinct enabled fixed reservation ranges are outside the union
  of fixed candidate reservations. The differences include Samsung secure
  firmware and debug reservations. This comparison covers static DT ranges.
  The real bootloader DT/DTBO selection, firmware carveouts and final memory
  map remain to be established before packaging a physical candidate.
- The active pstore readiness profile made one global ADB inventory
  invocation. The private failure signature matched the exact-target
  selector's result for one plausible row that failed the complete identity
  and healthy transport predicate. Zero calls were addressed to S20+, S22+,
  A90 or any other target. Current Magisk, Android PID 1 and pstore metadata
  remain unobserved. The attempt closed read-only with zero device effects.
  Its private failure receipt has SHA-256
  `eeb2e65492b11d993d8136572e3aded679a9626cb14be1c55280d9081bcc09f5`.

## Host build and verification

Build input is the [kernel.org Linux 6.18 source archive](https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.18.tar.xz)
at SHA-256 `9106a4605da9e31ff17659d958782b815f9591ab308d03b0ee21aad6c7dced4b`.
Configure with `ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-`,
`KCONFIG_ALLCONFIG=<absolute y2q.fragment> allnoconfig` and a separate
kernel output directory. Compile the DTS with the Linux include directories
and `dtc -@`. Compile the static init with the ARM64 GCC toolchain and a
private `build-id.h` defining `Y2Q_BUILD_ID` as 32 lowercase hex characters.
Use Linux `usr/gen_init_cpio` to package `/init`, `/config`, `/dev`,
`/dev/console` and `/sys`.

- The resolved kernel config contains every requested built-in and excludes
  the five explicitly disabled options in the fragment.
- The DTB has the exact y2q compatible strings, USB high-speed peripheral
  mode, USB 2.0 PHY and disabled deferred device nodes. DTC warnings match
  the unchanged upstream x1q build byte for byte.
- The init is an ARM64 static ELF. The newc archive lists only the five
  declared entries with root ownership. An ARM64 user-mode execution
  outside PID 1 returned status 1 at the PID check.
- QEMU `virt` booted the generated Linux 6.18 Image with this initramfs.
  The serial log recorded the build-bound `INIT_ENTERED` marker from
  PID 1 and then the expected `UDC_NOT_PRESENT` result. The virtual board
  supplies its own DTB. Physical DWC3 probing, USB attach and host ACM
  marker reception remain unverified.

Generated binaries, logs and hashes are under
`workspace/private/outputs/s20plus-y2q-mainline-h0-20261122.yy9l1A/`.
