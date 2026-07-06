# AGENTS.md — operating contract for autonomous Codex runs

This is the binding contract for Codex working this repo, **including unattended /
bypass runs**. It mirrors `CLAUDE.md`. `GOAL.md` says what to pursue; this file says how.
**Safety invariants and flash gates below are absolute and override any sub-goal.**

The work cycle (STATE → SELECT → DESIGN → IMPLEMENT → STATIC VALIDATE → DEVICE → REPORT →
COMMIT → REPEAT) is defined in `GOAL.md`.

## Safety invariants (NEVER violate)

1. **Partitions:** never write/flash `/efs`, `/sec_efs`, modem, RPMB, keymaster, vbmeta,
   bootloader, or any partition other than **boot**. Device changes touch the boot image
   only. These forbidden partitions are **NOT** TWRP/download-mode recoverable = permanent
   brick; the operator's acceptance of boot-flash risk does NOT extend to them.
   **Narrow operator-authorized exception (2026-07-06, S22+ recovery-infra only):**
   for the Samsung S22+ `SM-S906N`/`g0q` on `S906NKSS7FYG8`, Codex may perform one
   bounded Odin4 recovery-infrastructure install of the pinned unofficial g0q TWRP
   recovery tar SHA256
   `0914c68a5353c367216805a3a2fdeb4982c6629368dc021c7fefc10d3d3bd034` and pinned
   `vbmeta_disabled.tar` SHA256
   `0b347193ab3f822b423b2641001781e35fba0c932fcfb85d090b282d0fc6471b`, plus the
   pinned stock recovery-only rollback AP SHA256
   `8d3647313d2e100134f77984d13c7e5dc9946510ab57d8e34dd0cd192ca8586d` if TWRP
   recovery fails and download mode remains available. This exception is limited to
   recovery/vbmeta for S22+ recovery infrastructure, requires the full stock
   `S906NKSS7FYG8` firmware SHA256
   `f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8` to be present,
   requires no auto-reboot and immediate manual boot to recovery after transfer, and
   does not authorize A90 non-boot writes, S22 bootloader/modem/EFS/RPMB/keymaster
   writes, Magisk/root installation, multidisabler, format data, or any other S22
   partition write.
   **Narrow operator-authorized exception (2026-07-06, S22+ Magisk root baseline
   only):** after the S22+ TWRP recovery-infra pass above, Codex may perform one
   bounded Magisk root-baseline install on the same Samsung S22+ `SM-S906N`/`g0q`
   `S906NKSS7FYG8` using the pinned official Magisk `v30.7` APK SHA256
   `e0d32d2123532860f97123d927b1bb86c4e08e6fd8a48bfc6b5bee0afae9ebd5`, and only
   after full boot-partition readback equals stock SHA256
   `4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae`.
   This exception authorizes abandoning the deprecated TWRP-zip root attempt,
   restoring the pinned stock boot-only AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if needed,
   installing the Magisk APK on Android, patching the stock `boot.img` on the same
   device, and flashing only the resulting Magisk-patched boot image as a boot-only
   Odin AP. It does not authorize Magisk modules, multidisabler, format data, full
   AP/full-firmware flashing for root, non-boot partition experiments, or
   bootloader/modem/EFS/RPMB/keymaster writes.
   **Narrow operator-authorized exception (2026-07-06, S22+ FYG8-derived
   disabled-vbmeta only):** after the stock FYG8 vbmeta rollback boot pass, Codex
   may perform one bounded Odin4 vbmeta-only flash on the same Samsung S22+
   `SM-S906N`/`g0q` `S906NKSS7FYG8` using the FYG8-derived disabled-vbmeta AP
   SHA256 `804ff43b9f68278b026bd31d7703ca778518bb53a08e336e18b5016e3d2a2b4b`.
   The contained raw `vbmeta.img` must be derived from stock FYG8 vbmeta SHA256
   `1031323af6c69c6894bb00ca5895463ea3f00066ec4d5eacc2bb58b0b2c6047b` by
   changing only AVB header flags at byte offset 120 from `0x00000000` to
   `0x00000003` (`HASHTREE_DISABLED | VERIFICATION_DISABLED`), producing raw
   SHA256 `9c0e5b9615f8dac2a902f709927ff3fccaa4e074b34adbd0f8cd7498db78ba13`
   and `vbmeta.img.lz4` SHA256
   `6ad2df2b899b195512e2ceb9831909c282f891fe007f3246ec91a72a2e665a9a`.
   The AP must contain exactly one tar member, `vbmeta.img.lz4`, and must not
   carry boot, recovery, vendor_boot, BL, CP, CSC, userdata, or any other
   partition payload. If Android boot or recovery boot fails, restore the pinned
   stock FYG8 vbmeta-only rollback AP SHA256
   `fdf42fb913ac82bba7414d41a2995300c9bc56d31e7cddf907b487e7b2ae707b` and stop.
   **Narrow operator-authorized exception (2026-07-07, S22+ P2 native-init
   first-light boot-only):** after the S22+ TWRP/root/116-package checkpoint
   and the P0/P1 host-only reports, Codex may perform one bounded Odin4
   boot-partition-only flash on the same Samsung S22+ `SM-S906N`/`g0q`
   `S906NKSS7FYG8` using the exact P1 Magisk-preserving native-init chainload
   candidate AP.tar.md5 SHA256
   `4790b8a82e38081ed20e50d9bbbeee29f3821cfbf7b52e2d51da8f17f028ee40`.
   The candidate padded `boot.img` SHA256 must be
   `da9e2f5f71a396f40824493dd8acb9f7404623df075c21fb47f5ecee6f4c2645`; the
   AP must contain exactly one tar member, `boot.img.lz4`, and must not carry
   recovery, vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super,
   persist, userdata, EFS, RPMB, keymaster, modem, or any other partition
   payload. The pinned stock boot-only rollback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` and full
   stock `S906NKSS7FYG8` firmware SHA256
   `f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8` must be
   present before flashing. On no boot, unreachable Android, missing Magisk
   root, or failed first-light proof, restore the pinned stock boot-only AP if
   download mode remains available, then stop. This exception does not authorize
   additional S22+ boot candidates, kernel rebuild flashes, Magisk module
   writes, multidisabler, format data, non-boot partition writes, or any A90
   action.
   **Narrow operator-authorized exception (2026-07-07, S22+ P3 direct-PID1
   first-light boot-only):** after the S22+ P2 Magisk-chainload failure was
   rolled back to stock-boot Android, Codex may perform one bounded Odin4
   boot-partition-only flash on the same Samsung S22+ `SM-S906N`/`g0q`
   `S906NKSS7FYG8` using the exact P3 direct native-init PID1 candidate
   AP.tar.md5 SHA256
   `21838b4e64656cead9804f9034ed554bf6737a9666d07001d30ec66c01364d8b`.
   The candidate padded `boot.img` SHA256 must be
   `bb803901048a089b956d7657ed45496de7416a90c0a35872784b537d7167f2cb`; the
   AP must contain exactly one tar member, `boot.img.lz4`, and must not carry
   recovery, vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super,
   persist, userdata, EFS, RPMB, keymaster, modem, or any other partition
   payload. The expected proof path is direct `/init` PID1 kmsg marker
   `S22_NATIVE_INIT_DIRECT_P3` followed by automatic or manual TWRP recovery
   collection from `/proc/last_kmsg`; this is not an Android/Magisk handoff
   candidate and rooted Android is not expected before rollback. The pinned
   stock boot-only rollback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` and full
   stock `S906NKSS7FYG8` firmware SHA256
   `f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8` must be
   present before flashing. After proof collection or on no boot/no marker/no
   recovery, restore the pinned stock boot-only AP if download mode or recovery
   transport is available, then stop. This exception does not authorize
   additional S22+ boot candidates, Magisk root reinstall, kernel rebuild
   flashes, module loading, non-boot partition writes, or any A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ TWRP+Magisk
   boot-capture restore window only):** after the S22+ P3 incident was rolled
   back to normally booting stock Android with no `su`, and after `GOAL.md`
   redirected the S22+ path away from blind native-init flashes toward rooted
   Android boot-capture measurement, Codex may perform one bounded maintenance
   window on the same Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8`: first
   refresh TWRP by flashing only the exact pinned `g0q` TWRP recovery tar
   SHA256 `0914c68a5353c367216805a3a2fdeb4982c6629368dc021c7fefc10d3d3bd034`
   with auto-reboot disabled, then require direct manual boot to TWRP recovery
   and read-only TWRP proof before any further write, then reboot to download
   mode and flash only the exact pinned Magisk boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.
   The Magisk AP must contain exactly one tar member, `boot.img.lz4`; its
   unpacked boot image SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e` and its
   `boot.img.lz4` SHA256 must be
   `b33b63d9d2c56cbe10170820e88cf136be8fe9ad621a21752da19fdd9b642d31`. The
   primary path must not write vbmeta because Android preflight must already
   show `ro.boot.verifiedbootstate=orange`; the previously proven disabled
   vbmeta state is treated as a precondition, not a new write. The pinned stock
   recovery-only rollback AP SHA256
   `8d3647313d2e100134f77984d13c7e5dc9946510ab57d8e34dd0cd192ca8586d`, pinned
   stock boot-only rollback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`, and full
   stock `S906NKSS7FYG8` firmware SHA256
   `f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8` must be
   present before flashing. On bad TWRP proof, restore only the pinned stock
   recovery AP if download mode remains available, then stop before Magisk. On
   bad Android boot after the Magisk step, restore only the pinned stock
   boot-only AP if download mode remains available, then stop. This exception
   does not authorize vbmeta writes, Magisk modules, multidisabler, format data,
   native-init boot candidates, kernel rebuild flashes, non-recovery/boot
   partition writes, or any A90 action. TWRP persistence after a subsequent
   Android boot is not claimed unless re-verified.
   **Narrow operator-authorized exception (2026-07-07, S22+ Magisk boot-time
   capture M1 only):** after the rooted Android boot-capture post-boot snapshot
   proved normal Magisk root on `SM-S906N`/`g0q` `S906NKSS7FYG8`, Codex may run
   one temporary Android-side boot-time measurement capsule using the checked
   helper
   `workspace/public/src/scripts/revalidation/s22plus_magisk_boot_time_capture_m1.py`.
   This exception authorizes only normal Android `adb reboot`, temporary staging
   under `/data/local/tmp/s22plus_boot_capture_m1_*`, installing exactly two
   Magisk hook scripts
   `/data/adb/post-fs-data.d/s22plus_boot_capture_m1.sh` and
   `/data/adb/service.d/s22plus_boot_capture_m1.sh`, writing bounded text logs
   under `/data/adb/s22plus_boot_capture_m1/`, pulling those logs into
   `workspace/private/runs/`, and then deleting the two hook scripts, staging
   files, and remote log directory. The hook scripts may read `getprop`,
   `dmesg`, `/proc/modules`, module metadata, USB gadget/configfs state, and
   DRM/display state, but must not write sysfs/configfs, load/unload modules,
   change services, install a Magisk module, format/wipe `/data`, touch
   partitions, invoke Odin, flash boot/recovery/vbmeta, or alter any
   non-temporary path. If post-reboot Android or Magisk root does not return,
   stop and do not attempt cleanup through recovery/download-mode unless a
   separately authorized recovery path is needed.
   **Narrow operator-authorized exception (2026-07-07, S22+ M3 observable
   native-init boot-only live gate):** after the M1/M2 measurement units and
   the M3 host build report proved a first observable direct native `/init`
   candidate, Codex may perform one bounded attended boot-partition-only M3
   live gate on the same Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m3_observable_live_gate.py`
   and ack token `S22PLUS-M3-OBSERVABLE-LIVE-GATE`. The exact candidate
   AP.tar.md5 SHA256 must be
   `4a07a5b24101db6e74e102498c557d457c751e13d932f9f5604125629f06ce3b`, the
   contained padded `boot.img` SHA256 must be
   `aa66602e49045de5666b390ef7b434e07cd234d59a4503f9bac021d11383f6d0`, and the
   AP must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M3 candidate may only run as direct PID1, emit the
   `S22_NATIVE_INIT_OBSERVABLE_M3` kmsg/pmsg marker, insert the bundled M2
   USB-first vendor `.ko` set, create a minimal runtime configfs `ncm.0
   link-only` gadget, park for bounded host observation, then attempt a
   `download` reboot for rollback; if that reboot syscall returns, it must park.
   It must not mount persistent partitions, write block devices, start Android,
   install Magisk modules, format data, or reboot for any reason other than the
   bounded post-observation `download` reboot attempt. Before live flash, the helper must
   verify normal Android identity, the exact M3 hashes, the exact Magisk
   boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`, the
   exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`, and a
   single target transport. After the bounded observation window, rollback is
   required: primary rollback is the pinned Magisk boot-only AP to restore the
   rooted measurement environment, with the pinned stock boot-only AP as
   fallback if Magisk rollback transfer fails and download mode remains
   available. This exception does not authorize any M4/display/distro candidate,
   kernel rebuild, recovery/vendor_boot/vbmeta/non-boot flash, raw host `dd`,
   fastboot, multidisabler, format data, or any A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M3.1 marker-only
   native-init boot-only live gate):** after the M3 v0.2 live result failed
   before marker evidence and the host-only M3 postmortem scoped the next unit
   to marker-only proof, Codex may perform one bounded attended boot-partition-
   only M3.1 live gate on the same Samsung S22+ `SM-S906N`/`g0q`
   `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m31_marker_live_gate.py`
   and ack token `S22PLUS-M31-MARKER-LIVE-GATE`. The exact candidate
   AP.tar.md5 SHA256 must be
   `999beeb67f73c39eaa0b637bc3c62fe2d8474fa707110640ae51adca0fbd2cfb`, the
   contained padded `boot.img` SHA256 must be
   `f3dea68c02be295141265820f4acdd425a12460e05957edf75c83a62c4a617c5`, and the
   AP must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M3.1 candidate may only run as direct PID1, create `/dev/kmsg` and fallback
   `/dev/pmsg0`, emit the `S22_NATIVE_INIT_MARKER_ONLY_M31` kmsg/pmsg marker,
   dwell briefly, then attempt a `download` reboot for rollback; if that reboot
   syscall returns, it must park. It must not insert modules, mount or write
   configfs, create a USB gadget, mount persistent partitions, write block
   devices, start Android, install Magisk modules, format data, or reboot for
   any reason other than the bounded post-marker `download` reboot attempt.
   Before live flash, the helper must verify normal Android identity, the exact
   M3.1 hashes, the exact Magisk boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`, the
   exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`, and a
   single target transport. After the bounded observation window, rollback is
   required: primary rollback is the pinned Magisk boot-only AP, with the pinned
   stock boot-only AP as fallback if Magisk rollback transfer fails and download
   mode remains available. After rollback, the helper must collect retained
   evidence from both `/sys/fs/pstore` and `/proc/last_kmsg`; empty pstore alone
   must not be treated as proof that marker-only `/init` did not execute. This
   exception does not authorize USB/NCM bring-up,
   M4/display/distro candidates, kernel rebuild, recovery/vendor_boot/vbmeta/
   non-boot flash, raw host `dd`, fastboot, multidisabler, format data, or any
   A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M3.2 marker-only
   native-init boot-only live gate):** after the M3.1 marker-only live result
   failed before marker evidence and the host-only M3.1 postmortem found the
   uncompressed-newc ramdisk packaging delta, Codex may perform one bounded
   attended boot-partition-only M3.2 live gate on the same Samsung S22+
   `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m32_marker_live_gate.py`
   and ack token `S22PLUS-M32-MARKER-LIVE-GATE`. The exact candidate
   AP.tar.md5 SHA256 must be
   `6073e4988a98f741fa207df4efb8a05e144ad16b3a90f43db2ec408657936fc2`, the
   contained padded `boot.img` SHA256 must be
   `0bb1ef280e42aa2c6069538e77fc21b5330cf9419a19785f79d05da8429bf1fc`, and the
   AP must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M3.2 candidate may only run as direct PID1, use stock-format legacy-LZ4
   ramdisk packaging, create `/dev/kmsg` and fallback `/dev/pmsg0`, emit the
   `S22_NATIVE_INIT_MARKER_ONLY_M32` kmsg/pmsg marker, dwell briefly, then
   attempt a `download` reboot for rollback; if that reboot syscall returns, it
   must park. It must not insert modules, mount or write configfs, create a USB
   gadget, mount persistent partitions, write block devices, start Android,
   install Magisk modules, format data, or reboot for any reason other than the
   bounded post-marker `download` reboot attempt. Before live flash, the helper
   must verify normal Android identity, the exact M3.2 hashes, legacy-LZ4
   ramdisk manifest metadata, the exact Magisk boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`, the
   exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`, and a
   single target transport. After the bounded observation window, rollback is
   required: primary rollback is the pinned Magisk boot-only AP, with the pinned
   stock boot-only AP as fallback if Magisk rollback transfer fails and download
   mode remains available. After rollback, the helper must collect retained
   evidence from both `/sys/fs/pstore` and `/proc/last_kmsg`; empty pstore alone
   must not be treated as proof that marker-only `/init` did not execute. This
   exception does not authorize USB/NCM bring-up,
   M4/display/distro candidates, kernel rebuild, recovery/vendor_boot/vbmeta/
   non-boot flash, raw host `dd`, fastboot, multidisabler, format data, or any
   A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M4T0
   instant-download native-init boot-only live gate):** after the M3.2
   marker-only live incident was rolled back to the rooted Magisk boot baseline,
   retained-evidence probing found `/proc/last_kmsg` but no reliable pstore
   marker channel, and the operator clarified that the loop is fast, Codex may
   perform one bounded attended boot-partition-only M4T0 live gate on the same
   Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m4t0_instant_download_live_gate.py`
   and ack token `S22PLUS-M4T0-INSTANT-DOWNLOAD-LIVE-GATE`. The exact candidate
   AP.tar.md5 SHA256 must be
   `ba445b131fddd79887a4ace357a77a42b1f49367eaeea156a3cfebfd883b1904`, the
   contained padded `boot.img` SHA256 must be
   `4617a8804b93435cd0b6a5307862b4d5f55ca7e25befa0c19b2e7619284979e9`, and the
   AP must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M4T0 candidate may only run as direct PID1, use stock-format legacy-LZ4
   ramdisk packaging, and its first candidate action must be
   `reboot(..., "download")`, with no marker before the reboot syscall. If that
   reboot syscall returns, it may only create `/dev/kmsg` and fallback
   `/dev/pmsg0`, emit `S22_NATIVE_INIT_INSTANT_DOWNLOAD_M4T0`, and park. It
   must not touch watchdog devices, insert modules, mount or write configfs,
   create a USB gadget, mount persistent partitions, write block devices, start
   Android, install Magisk modules, format data, or reboot for any reason other
   than the first-action `download` reboot attempt. Before live flash, the
   helper must verify normal Android identity, the exact M4T0 hashes,
   legacy-LZ4 ramdisk manifest metadata, the exact Magisk boot-only rollback AP
   SHA256 `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`,
   the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`, and a
   single target transport. After candidate Odin transfer, the helper must first
   observe the original Odin download-mode device disconnect; only a later Odin
   reappearance may be counted as M4T0 self-download proof. If the candidate
   self-enters download mode, rollback is required immediately: primary rollback
   is the pinned Magisk boot-only AP, with the pinned stock boot-only AP as
   fallback if Magisk rollback transfer fails and download mode remains
   available. If the original Odin device never disconnects, the helper may
   attempt immediate rollback while still in download mode, but that result is
   no-proof cleanup and must not be reported as M4T0 self-download success. If
   candidate self-download does not appear within the bounded window, the helper
   must stop and require operator/manual download-mode recovery before any
   rollback attempt. After rollback, the helper must collect retained evidence
   from both
   `/sys/fs/pstore` and `/proc/last_kmsg`, but marker absence is expected if the
   first-action reboot succeeded. This exception does not authorize M4A,
   display/distro candidates, kernel rebuild, recovery/vendor_boot/vbmeta/
   non-boot flash, raw host `dd`, fastboot, multidisabler, format data, or any
   A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M4T1
   in-place MagiskBoot native-init boot-only live gate):** after M4T0 failed to
   self-enter download mode, the operator-corrected discriminator moved to
   boot construction, and the host-only M4T1 builder proved that a no-change
   `magiskboot unpack/repack` of the known-booting Magisk boot is
   byte-identical while M4T1 preserves `SAMSUNG_SEANDROID` and `VBMETA`, Codex
   may perform one bounded attended boot-partition-only M4T1 live gate on the
   same Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m4t1_inplace_live_gate.py`
   and ack token `S22PLUS-M4T1-INPLACE-LIVE-GATE`. The exact candidate
   AP.tar.md5 SHA256 must be
   `9f5b4c48b95b710f742d5ea8c7f16ef4802cf27e78469381073d460361d0451c`, the
   contained padded `boot.img` SHA256 must be
   `9ce597e4ba920f1331937dbe4736f923728ff5502b02c02dea8357b3a9d5b9d1`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, and the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`. The AP
   must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M4T1 candidate may only run as direct PID1, must be constructed by
   `magiskboot unpack/repack` from the known-booting Magisk boot with only the
   ramdisk `/init` entry replaced, must not be built with `mkbootimg` from
   scratch, and its first candidate action must be `reboot(..., "download")`,
   with no marker before the reboot syscall. If that reboot syscall returns,
   it may only create `/dev/kmsg` and fallback `/dev/pmsg0`, emit
   `S22_NATIVE_INIT_INSTANT_DOWNLOAD_M4T0`, and park. It must not touch
   watchdog devices, insert modules, mount or write configfs, create a USB
   gadget, mount persistent partitions, write block devices, start Android,
   install Magisk modules, format data, or reboot for any reason other than
   the first-action `download` reboot attempt. Before live flash, the helper
   must verify normal Android identity, the exact M4T1 hashes, in-place
   MagiskBoot manifest metadata, the exact Magisk boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`, the
   exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`, and a
   single target transport. After candidate Odin transfer, the helper must
   first observe the original Odin download-mode device disconnect; only a
   later Odin reappearance may be counted as M4T1 self-download proof. If the
   candidate self-enters download mode, rollback is required immediately:
   primary rollback is the pinned Magisk boot-only AP, with the pinned stock
   boot-only AP as fallback if Magisk rollback transfer fails and download mode
   remains available. If the original Odin device never disconnects, the helper
   may attempt immediate rollback while still in download mode, but that result
   is no-proof cleanup and must not be reported as M4T1 self-download success.
   If candidate self-download does not appear within the bounded window, the
   helper must stop and require operator/manual download-mode recovery before
   any rollback attempt. After rollback, the helper must collect retained
   evidence from both `/sys/fs/pstore` and `/proc/last_kmsg`, but marker
   absence is expected if the first-action reboot succeeded. This exception
   does not authorize display/distro candidates, kernel rebuild,
   recovery/vendor_boot/vbmeta/non-boot flash, raw host `dd`, fastboot,
   multidisabler, format data, or any A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M4T2 raw-park
   native-init boot-only live gate):** after M4T1 in-place MagiskBoot still
   bootlooped and was rolled back cleanly, Codex may prepare and perform one
   bounded attended boot-partition-only M4T2 live gate on the same Samsung S22+
   `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m4t2_park_live_gate.py`
   and live ack token `S22PLUS-M4T2-RAW-PARK-LIVE-GATE`. The exact candidate
   AP.tar.md5 SHA256 must be
   `66d7f24b348702f58efbe1945b0d2751052ed27f6ce1f6fc4e5da63f3a585b24`, the
   contained padded `boot.img` SHA256 must be
   `8103bce76fb3e41d71b64735a64d2f2f29431a44ea1c9a85dc0bc151d71afd15`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, and the
   raw park `/init` SHA256 must be
   `b8371e3ac671ff71e9be752b8ff1087a4f20811c871a43ca8e698eee47783d12`. The AP
   must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M4T2 candidate may only run as direct PID1, must be constructed by
   `magiskboot unpack/repack` from the known-booting Magisk boot with only the
   ramdisk `/init` entry replaced, must not be built with `mkbootimg` from
   scratch, and its first candidate action is infinite park. The raw `/init`
   must have no libc startup, no syscalls, no reboot request, no marker write,
   no module insertion, no configfs gadget work, no watchdog touch, no
   persistent partition mount, no block-device write, no Android start, no
   Magisk module install, no format data, and no self-rollback path. M4T2
   success is an attended observation that the fast reboot loop stops; it is
   not ADB return and not self-download. If the device remains dark/no-transport
   after the observation window, the helper must stop and require operator
   manual download-mode entry before rollback. Rollback from manual download
   mode may be performed only through the same helper's
   `--rollback-from-download --ack S22PLUS-M4T2-ROLLBACK-FROM-DOWNLOAD` mode,
   using the exact Magisk boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not
   authorize display/distro candidates, kernel rebuild,
   recovery/vendor_boot/vbmeta/non-boot flash, raw host `dd`, fastboot,
   multidisabler, format data, or any A90 action.
2. **Flash only via the checked helper by default:** `workspace/public/src/scripts/revalidation/native_init_flash.py`.
   Never `dd`/`fastboot`/raw-write a partition. Never invent a new flash path.
   **Narrow operator-authorized exception (2026-07-02, self-dd ladder only):** the V3358
   `boot-flash-f1 BOOT-FLASH-F1-PAIRED-ROUNDTRIP ...` command may perform the
   design §12.4 paired content-changing roundtrip on the **boot** partition only, and
   only after V3358 was itself flashed through `native_init_flash.py`, rollback images
   and recovery/TWRP were confirmed, the approved staged candidate SHA/version/header
   passed F0-equivalent checks, and the command remains token-gated, guarded by boot
   identity, full-SHA verified, and immediately restored before any reboot. This
   exception also authorizes the V3359
   `boot-flash-f2 BOOT-FLASH-F2-BOOT-CANDIDATE ...` command as the next bounded
   boot-partition-only experiment, and only after V3359 was itself flashed through
   `native_init_flash.py`, rollback images and recovery/TWRP were confirmed, the
   approved staged candidate SHA/version/header passed F0-equivalent checks, and the
   F2 command remains token-gated, guarded by boot identity, full-SHA verified, and
   returns a clean `reboot_required=1` transcript for a host-controlled immediate
   reboot into the self-written candidate. On any target-write/readback failure, F2
   must not reboot and must attempt the designed before.full failure restore if any
   target pwrite started. This exception also authorizes the V3360
   `boot-flash-f3 BOOT-FLASH-F3-SELF-ROLLBACK ...` command as the next bounded
   boot-partition-only experiment, and only after a checked-helper-flashed V3359 (or
   later F2-capable resident) writes V3360 through F2, V3360 boots as the self-written
   candidate, rollback images and recovery/TWRP were confirmed, the approved staged
   v2321 rollback image SHA/version/header passed F0-equivalent checks, and the F3
   command remains token-gated, guarded by boot identity, full-SHA verified, and
   returns a clean `reboot_required=1` transcript for a host-controlled immediate
   reboot into v2321. On any F3 target-write/readback failure, F3 must not reboot and
   must attempt the designed before.full failure restore if any target pwrite started.
   A later same-day amendment authorized exactly one bounded V3362 F4-live
   host-orchestrated validation through `native_init_flash.py --experimental-self-write
   --self-write-mode f3 --self-write-live-authorized`, locked to the v2321 rollback
   image and `boot-flash-f3` self-rollback semantics. That run passed and is recorded
   in `docs/reports/NATIVE_INIT_V3362_SELF_DD_F4_LIVE_2026-07-02.md`. This exception
   does **not** make self-write the default flash path and does **not** authorize
   further arbitrary F4/prod fast-flash use, prefix-only production optimization,
   non-v2321 self-flash candidates, raw host `dd`, fastboot, or any non-boot
   partition write. `native_init_flash.py` remains the recovery-grade fallback path.
   **Narrow operator-authorized exception (2026-07-06, S22+ Odin4 recovery-infra
   only):** the S22+ recovery-infra install above may use `/usr/bin/odin4` with AP
   set to the pinned TWRP tar and `-u` set to the pinned `vbmeta_disabled.tar` because
   this is a Samsung download-mode recovery setup, not an A90 native-init boot flash.
   The local Odin4 help names `-u` as `UMS`; this is the only Linux Odin4 slot that
   maps to the upstream guide's USERDATA-side disabled-vbmeta flow, so the transcript
   must record that residual slot-name risk. No auto-reboot option may be used for the
   TWRP install.
   **Narrow operator-authorized exception (2026-07-06, S22+ Magisk boot-only Odin
   path):** the S22+ Magisk root-baseline install above may use `/usr/bin/odin4` for
   stock boot-only rollback and Magisk-patched boot-only AP flashing because the
   operator selected the official APK patching direction after the deprecated TWRP
   zip attempt. The transcript must record that official Samsung guidance recommends
   Magisk-app patching over custom-recovery installation.
   **Narrow operator-authorized exception (2026-07-06, S22+ FYG8-derived
   disabled-vbmeta Odin path):** the S22+ FYG8-derived disabled-vbmeta unit above
   may use `/usr/bin/odin4 --reboot -a` for the exact vbmeta-only AP SHA256
   `804ff43b9f68278b026bd31d7703ca778518bb53a08e336e18b5016e3d2a2b4b`, because
   this is a Samsung download-mode vbmeta recovery/compatibility experiment, not
   an A90 native-init boot flash. It may also use `/usr/bin/odin4 --reboot -a`
   for the pinned stock FYG8 vbmeta-only rollback AP SHA256
   `fdf42fb913ac82bba7414d41a2995300c9bc56d31e7cddf907b487e7b2ae707b` on failure.
   No other Odin slot or partition is authorized by this exception.
   **Narrow operator-authorized exception (2026-07-07, S22+ P2 native-init
   boot-only Odin path):** the S22+ P2 native-init first-light unit above may
   use `/usr/bin/odin4 --reboot -a` for the exact single-member `boot.img.lz4`
   AP.tar.md5 SHA256
   `4790b8a82e38081ed20e50d9bbbeee29f3821cfbf7b52e2d51da8f17f028ee40`, because
   this is a Samsung download-mode boot-partition-only experiment gated by
   TWRP/root recovery infrastructure and the pinned stock boot-only rollback AP.
   It may also use `/usr/bin/odin4 --reboot -a` for the pinned stock boot-only
   rollback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` on
   failure. No other Odin slot, tar member, candidate hash, or partition is
   authorized by this exception.
   **Narrow operator-authorized exception (2026-07-07, S22+ P3 direct-PID1
   boot-only Odin path):** the S22+ P3 direct native-init first-light unit above
   may use `/usr/bin/odin4 --reboot -a` for the exact single-member
   `boot.img.lz4` AP.tar.md5 SHA256
   `21838b4e64656cead9804f9034ed554bf6737a9666d07001d30ec66c01364d8b`,
   because this is a Samsung download-mode boot-partition-only direct-PID1
   proof gated by TWRP recovery infrastructure and the pinned stock boot-only
   rollback AP. It may also use `/usr/bin/odin4 --reboot -a` for the pinned
   stock boot-only rollback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` on
   failure or after proof collection. No other Odin slot, tar member, candidate
   hash, or partition is authorized by this exception.
   **Narrow operator-authorized exception (2026-07-07, S22+ TWRP+Magisk
   boot-capture restore Odin path):** the S22+ TWRP+Magisk restore window above
   may use `/usr/bin/odin4 -a` without `--reboot` for the exact single-member
   recovery tar SHA256
   `0914c68a5353c367216805a3a2fdeb4982c6629368dc021c7fefc10d3d3bd034`, and may
   use `/usr/bin/odin4 --reboot -a` for the exact single-member Magisk
   boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`. It may
   also use `/usr/bin/odin4 --reboot -a` for the pinned stock recovery-only
   rollback AP SHA256
   `8d3647313d2e100134f77984d13c7e5dc9946510ab57d8e34dd0cd192ca8586d` after a
   TWRP recovery failure, and for the pinned stock boot-only rollback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` after a
   Magisk boot failure. No Odin `-u`/USERDATA/vbmeta slot, other Odin slot,
   other tar member, other candidate hash, or other partition is authorized by
   this exception.
   **Narrow operator-authorized exception (2026-07-07, S22+ M3 observable
   native-init boot-only Odin path):** the S22+ M3 live gate above may use
   `/usr/bin/odin4 --reboot -a` through
   `workspace/public/src/scripts/revalidation/s22plus_m3_observable_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `4a07a5b24101db6e74e102498c557d457c751e13d932f9f5604125629f06ce3b`, and may
   use `/usr/bin/odin4 --reboot -a` for rollback with the exact single-member
   Magisk boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, or partition is
   authorized by this exception.
   **Narrow operator-authorized exception (2026-07-07, S22+ M3.1 marker-only
   native-init boot-only Odin path):** the S22+ M3.1 live gate above may use
   `/usr/bin/odin4 --reboot -a` through
   `workspace/public/src/scripts/revalidation/s22plus_m31_marker_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `999beeb67f73c39eaa0b637bc3c62fe2d8474fa707110640ae51adca0fbd2cfb`, and may
   use `/usr/bin/odin4 --reboot -a` for rollback with the exact single-member
   Magisk boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, or partition is
   authorized by this exception.
   **Narrow operator-authorized exception (2026-07-07, S22+ M3.2 marker-only
   native-init boot-only Odin path):** the S22+ M3.2 live gate above may use
   `/usr/bin/odin4 --reboot -a` through
   `workspace/public/src/scripts/revalidation/s22plus_m32_marker_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `6073e4988a98f741fa207df4efb8a05e144ad16b3a90f43db2ec408657936fc2`, and may
   use `/usr/bin/odin4 --reboot -a` for rollback with the exact single-member
   Magisk boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, or partition is
   authorized by this exception.
   **Narrow operator-authorized exception (2026-07-07, S22+ M4T0
   instant-download native-init boot-only Odin path):** the S22+ M4T0 live gate
   above may use `/usr/bin/odin4 --reboot -a` through
   `workspace/public/src/scripts/revalidation/s22plus_m4t0_instant_download_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `ba445b131fddd79887a4ace357a77a42b1f49367eaeea156a3cfebfd883b1904`, and may
   use `/usr/bin/odin4 --reboot -a` for rollback with the exact single-member
   Magisk boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, or partition is
   authorized by this exception.
   **Narrow operator-authorized exception (2026-07-07, S22+ M4T1
   in-place MagiskBoot native-init boot-only Odin path):** the S22+ M4T1 live
   gate above may use `/usr/bin/odin4 --reboot -a` through
   `workspace/public/src/scripts/revalidation/s22plus_m4t1_inplace_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `9f5b4c48b95b710f742d5ea8c7f16ef4802cf27e78469381073d460361d0451c`, and may
   use `/usr/bin/odin4 --reboot -a` for rollback with the exact single-member
   Magisk boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, or partition is
   authorized by this exception.
   **Narrow operator-authorized exception (2026-07-07, S22+ M4T2 raw-park
   native-init boot-only Odin path):** the S22+ M4T2 live gate above may use
   `/usr/bin/odin4 --reboot -a` through
   `workspace/public/src/scripts/revalidation/s22plus_m4t2_park_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `66d7f24b348702f58efbe1945b0d2751052ed27f6ce1f6fc4e5da63f3a585b24`, and
   the same helper may use `/usr/bin/odin4 --reboot -a` in
   `--rollback-from-download` mode with the exact single-member Magisk
   boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, or partition is
   authorized by this exception.
3. **Rollback precondition:** before ANY flash, confirm the known-good rollback image
   `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
   (SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`, the resident
   clean USB-identity checkpoint) exists, plus the deeper Wi-Fi-proven fallback
   `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`
   (SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`) and the
   final fallback `boot_linux_v48.img`, AND recovery/TWRP is available. v2321 is the
   auto-rollback target; v2237/v48 are deeper fallbacks. If you cannot confirm these,
   DO NOT flash — stop and report.
4. **No cascading bad flashes:** never flash a new experimental image onto a device that
   failed its last boot/health check. Recover first (invariant 8), then stop.
5. **Wi-Fi is gated, and creds are currently ABSENT:** run scan/connect/dhcp/ping ONLY
   when the selected sub-goal explicitly requires that bounded validation. Because
   `workspace/private/secrets/` has no Wi-Fi env, `connect`/`dhcp`/`ping` cannot run —
   device validation is limited to boot + `version`/`status`/`selftest` + `wifi status`/
   `wifi scan`. Never block waiting for creds; never invent or log PSKs; record full Wi-Fi
   functional validation as a parked human checkpoint.
6. **Don't reopen external subsystems:** no SDX50M/eSoC/PCIe/MHI/GDSC/PMIC/GPIO chasing for
   internal `wlan0` unless new on-frontier evidence explicitly reopens them.
7. **Don't commit:** boot images, firmware, ramdisks, compiled binaries, raw logs,
   credentials, DHCP leases, or unredacted MAC/BSSID/IP. Private/large/generated payloads
   live under `workspace/private/`. Redact device identifiers (serial, ap_serial, PARTUUID,
   MAC/BSSID/IP) from anything committed.

## Flash gates (the DEVICE step in detail)

Perform a device step ONLY if the sub-goal needs a new boot artifact. Then, in order:

1. Build via the checked build script; capture and record the artifact **SHA256**. Flash
   only the exact artifact you just built and checksummed.
2. Re-confirm invariant 3 (rollback image + recovery present).
3. Flash via `native_init_flash.py`; reboot.
4. **Health check** over the serial bridge: `a90ctl version`, `status`, `selftest`. The
   device must come back and selftest must not regress.
5. **On failure** (no boot, unreachable, selftest fail): **auto-rollback** to the current
   known-good baseline via `native_init_flash.py`, then re-run the health check.
   - Rollback OK → record the failure, STOP that sub-goal (do not retry-loop), continue
     only with non-device sub-goals if any.
   - Rollback fails or device still unreachable → **STOP the whole loop**, write an
     incident report, do not flash anything else.
6. Only after a clean health check, run the bounded functional validation the sub-goal
   needs (and only the Wi-Fi actions it explicitly requires).

## Versioning (per `docs/operations/VERSIONING_POLICY.md`)

Keep axes separate: Run ID `VNNNN`; native init `MAJOR.MINOR.PATCH` (bump only when the
flashed artifact changes); build tag `vNNNN-purpose`; helper `helper-vNNN`; SHA256 =
artifact identity. A new rollback/test baseline must be promoted under a new run/build
identity. Never use helper numbers as run IDs or boot tags.

## Commit & report hygiene

- One sub-goal per commit. Scoped `git add` of the touched public paths + the report —
  **never `git add -A`/`.`** Inspect `git status --short` before and after.
- Commit only after the sub-goal is implemented, statically validated, and (if a device
  step ran) health-checked. `git diff --check` before commit.
- Every device/analysis iteration gets a redacted, metadata-only report under
  `docs/reports/NATIVE_INIT_VNNNN_*.md`.
- Commit message: imperative subject naming the V-iteration + purpose; body with what /
  why / validation result.

## Development discipline

- Canonical paths only (`workspace/public/src/...`, `workspace/private/...`,
  `docs/...`). Do not recreate old root `stage3/ scripts/ kernel_build/ ...` trees.
- Prefer `rg` for search and `git mv` for tracked moves. Keep patches focused; do not
  repair unrelated historical docs.
- `py_compile` touched Python; cross-compile touched C with `aarch64-linux-gnu-gcc` and
  verify with `file`.
- Web research is allowed during DESIGN; cite sources in the report.

## Stop / escalate

If anything is ambiguous, unsafe, or blocked — or any safety invariant would have to bend
to proceed — STOP and write a note/report. Do not widen scope, fabricate device steps, or
keep retrying. The host-only `tests/GOAL.md` harness is always a safe sub-goal to fall
back to when no device work is safely actionable.
