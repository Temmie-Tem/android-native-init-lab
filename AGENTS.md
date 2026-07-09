# AGENTS.md — operating contract for autonomous Codex runs

This is the binding contract for Codex working this repo, **including unattended /
bypass runs**. It mirrors `CLAUDE.md`. `GOAL.md` says what to pursue; this file says how.
**Safety invariants and flash gates below are absolute and override any sub-goal.**

The work cycle (STATE → SELECT → DESIGN → IMPLEMENT → STATIC VALIDATE → DEVICE → REPORT →
COMMIT → REPEAT) is defined in `GOAL.md`.

S22+ `S906NKSS7FYG8` full-stock firmware evidence may be either the original
SamFW ZIP SHA256 `f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8`
or the extracted six-file stock firmware set with exact sizes and SHA256 values
documented in
`docs/operations/S22PLUS_FYG8_STOCK_FIRMWARE_EVIDENCE_POLICY_2026-07-08.md`.
This is an evidence/precondition rule only; it does not authorize full firmware,
BL, CP, CSC, userdata, or any non-boot flash.

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
   recovery/vbmeta for S22+ recovery infrastructure, requires S22+
   `S906NKSS7FYG8` full-stock firmware evidence per
   `docs/operations/S22PLUS_FYG8_STOCK_FIRMWARE_EVIDENCE_POLICY_2026-07-08.md`
   to be present,
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
   **Narrow operator-authorized exception (2026-07-08, S22+ sec_debug
   debug_level MID sysrq-panic zero-flash only):**
   **Consumed/retired:** this one-shot exception was consumed by the 2026-07-08
   live run. It proved retained `/proc/last_kmsg` evidence via Samsung
   sec_debug/MID and must not be reused for another sysrq panic under the same
   gate. Future native-init fault-capture work needs a fresh, narrower
   exception for the selected candidate and observation path.
   Before consumption, after the S22+ DTBO+M13 no-hit and the host finding that
   Samsung `sec_debug` gated by `debug_level` is the likely retained-console
   path, Codex could perform one bounded attended zero-flash Android sec_debug
   positive-control run on the Samsung S22+
   `SM-S906N`/`g0q` `S906NKSS7FYG8` (`SM-S906N/g0q/S906NKSS7FYG8`)
   using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py`
   and a now-consumed live ack token. This
   exception authorizes no Odin flash, no partition write, no boot image write,
   no DTBO write, no vendor_boot write, no recovery/vbmeta/BL/CP/CSC/super/
   userdata/EFS/sec_efs/RPMB/keymaster/modem/bootloader write, no raw host `dd`,
   no fastboot, and no Magisk module install. The current boot partition must
   match the known-booting Magisk boot SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
   The operator must first set Samsung SysDump DEBUG LEVEL to MID if available
   (`debug_level=MID`; operator-set SysDump DEBUG LEVEL MID), then pass
   confirmation token `DEBUG_LEVEL_MID_SET_BY_OPERATOR` to the helper. The
   helper may write marker `S22_SECDEBUG_MID_SYSRQ_PANIC_CONTROL` to `/dev/kmsg`
   and `/dev/pmsg0` if present, write `1` to `/proc/sys/kernel/sysrq`, and write
   `c` to `/proc/sysrq-trigger` (`sysrq-trigger-c`) to cause one intentional
   kernel crash. After manual recovery, Codex may collect `/sys/fs/pstore`,
   collect /proc/last_kmsg, and read reset/sec_debug state through ADB root. The
   expected evidence is retained kernel panic/sec_debug/upload/ramdump log
   material or the marker in `/proc/last_kmsg`, pstore, or pmsg-derived retained
   state. If no retained evidence appears, stop and do not keep changing DTBO or
   M22 candidates under this exception. Manual recovery may be required.
   **Narrow operator-authorized exception (2026-07-08, S22+ sec_debug MID M18
   capture boot-only):**
   **Consumed/retired:** this one-shot exception was consumed by the 2026-07-08
   live run. It flashed the pinned M18 boot AP once, observed bootloop/Odin
   return, restored the pinned Magisk boot AP, and collected Samsung sec_debug
   retained `/proc/last_kmsg` evidence. It must not be reused for another M18
   or boot-candidate live flash under the same gate. Future native-init live
   flashes need a fresh, narrower exception for the selected artifact and
   observation path.
   Before consumption, after the S22+ sec_debug/MID sysrq positive control
   proved retained `/proc/last_kmsg` kernel panic evidence, Codex could perform
   one bounded attended S22+ sec_debug MID M18 capture boot-only run on the
   Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_sec_debug_m18_capture_live_gate.py`.
   The consumed live ack token and rollback token are intentionally not listed
   here as active authorization. The run was boot partition only and did not
   authorize DTBO, vendor_boot, vbmeta, recovery, BL, CP, CSC, super, userdata,
   persist, EFS, sec_efs, RPMB, keymaster, modem, bootloader, raw host `dd`,
   fastboot, Magisk modules, multidisabler, format data, additional boot
   candidates, additional debug-level panics, kernel rebuilds, or any A90
   action.
   **Consumed exception (2026-07-08, S22+ EUD Phase-B reversible enable only):**
   this one-shot exception was consumed by the 2026-07-08 live run. It toggled
   `/sys/module/eud/parameters/enable` from 0 to 1 and back to 0 using only
   `workspace/public/src/scripts/revalidation/s22plus_eud_phase_b_enable_live_gate.py`.
   The run restored `enable=0`, observed no host EUD USB hint and no new host
   serial/TTY path, and left the device on the Android/Magisk baseline. The
   consumed live ack token is intentionally not listed here as active
   authorization. Future EUD writes require a fresh operator-approved exception.
   This consumed exception authorizes no flash, no reboot, no partition write,
   no native-init boot candidate, no module insertion, no boot/vendor_boot/dtbo/
   vbmeta/recovery write, no BL, no CP, no CSC, no super, no userdata, no EFS,
   no sec_efs, no RPMB, no keymaster, no modem, no bootloader, no raw host `dd`,
   no fastboot, no Magisk module, no format data, no additional sysfs writes,
   and no A90 action.
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
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` and S22+
   `S906NKSS7FYG8` full-stock firmware evidence per
   `docs/operations/S22PLUS_FYG8_STOCK_FIRMWARE_EVIDENCE_POLICY_2026-07-08.md`
   must be present before flashing. On no boot, unreachable Android, missing Magisk
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
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` and S22+
   `S906NKSS7FYG8` full-stock firmware evidence per
   `docs/operations/S22PLUS_FYG8_STOCK_FIRMWARE_EVIDENCE_POLICY_2026-07-08.md`
   must be present before flashing. After proof collection or on no boot/no marker/no
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
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`, and S22+
   `S906NKSS7FYG8` full-stock firmware evidence per
   `docs/operations/S22PLUS_FYG8_STOCK_FIRMWARE_EVIDENCE_POLICY_2026-07-08.md`
   must be present before flashing. On bad TWRP proof, restore only the pinned stock
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
   **Narrow operator-authorized exception (2026-07-07, S22+ M4T3 raw-reboot
   native-init boot-only live gate):** after M4T2 raw-park stopped the fast
   reboot loop and was rolled back cleanly, Codex may prepare and perform one
   bounded attended boot-partition-only M4T3 live gate on the same Samsung S22+
   `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m4t3_raw_reboot_live_gate.py`
   with live ack token `S22PLUS-M4T3-RAW-REBOOT-LIVE-GATE` and rollback-only
   ack token `S22PLUS-M4T3-ROLLBACK-FROM-DOWNLOAD`. The exact candidate
   AP.tar.md5 SHA256 must be
   `f0a26bb95a091070713f8d736419cbe60974195bb59509cb1fd7cc28a0b1a907`, the
   contained padded `boot.img` SHA256 must be
   `d5e0371c6cb68af8990ce3ac4701ad4e0e487dbe54f4702dae29e21d86f4b92a`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, and the
   raw reboot `/init` SHA256 must be
   `e975a973395fd1bfe2fee0dccb9d47400e6746d62b508cd139b49c551b9aa67c`. The AP
   must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M4T3 candidate may only run as direct PID1, must be constructed by
   `magiskboot unpack/repack` from the known-booting Magisk boot with only the
   ramdisk `/init` entry replaced, must not be built with `mkbootimg` from
   scratch, and its first candidate action is a single direct raw
   `reboot(..., "download")` syscall. If that syscall returns, it must only
   park forever. The raw `/init` must have no libc startup, no marker write, no
   module insertion, no configfs gadget work, no watchdog touch, no persistent
   partition mount, no block-device write, no Android start, no Magisk module
   install, no format data, and no self-rollback path. M4T3 success is
   candidate self-entry to download mode after the original Odin device
   disconnects. Stable no-transport park means the syscall returned or was
   rejected and requires operator manual download-mode entry before rollback.
   Rollback from manual download mode may be performed only through the same
   helper's `--rollback-from-download --ack S22PLUS-M4T3-ROLLBACK-FROM-DOWNLOAD`
   mode, using the exact Magisk boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not
   authorize display/distro candidates, kernel rebuild,
   recovery/vendor_boot/vbmeta/non-boot flash, raw host `dd`, fastboot,
   multidisabler, format data, or any A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M5 USB-ACM
   native-init boot-only live gate):** after M4T3 proved raw custom-PID1
   reboot-to-download and M5 was built host-only, Codex may prepare and perform
   one bounded attended boot-partition-only M5 live gate on the same Samsung
   S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m5_usb_acm_live_gate.py`
   with live ack token `S22PLUS-M5-USB-ACM-LIVE-GATE` and rollback-only ack
   token `S22PLUS-M5-ROLLBACK-FROM-DOWNLOAD`. The exact candidate AP.tar.md5
   SHA256 must be
   `5bce15dede8bcd84b8ead1a7f6db6b09135d38637c983d06965930c40a00159f`, the
   contained padded `boot.img` SHA256 must be
   `3f4e9a514549a2cad2475ef7ef745dfc7e832c910cf1cca25ec4654c9c5522a1`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M5 `/init` SHA256 must be
   `596e4198bbdfece9eb1c227acd19cdca1934a440a544fe43cfdf79976a4fc594`, and
   the M2 USB-first module-bundle manifest SHA256 must be
   `1c22c93496e03a7df6dd74959511797b6d033b74361d3d3733d7be8269a5fa05`. The
   AP must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M5 candidate may only run as direct PID1 with a freestanding raw-syscall
   runtime (`-nostdlib`, no glibc static startup), must be constructed by
   `magiskboot unpack/repack` from the known-booting Magisk boot with ramdisk
   `/init` replaced and the FYG8 USB-first 26-module bundle injected under
   `/lib/modules/s22plus-m5`, must not be built with `mkbootimg` from scratch,
   and may only mount runtime virtual filesystems, insert those 26 ramdisk
   modules, create the configfs `ss_acm.0` gadget, retry UDC binding until
   bound, accept only a host-commanded ACM `download` request as its rollback
   reboot trigger, and park while probing `/dev/ttyGS0`. The M5 `/init` must not start Android or Magisk,
   mount persistent partitions, write block devices, touch watchdog, install
   Magisk modules, format data, or auto-reboot. M5 success is host-visible USB
   ACM enumeration for the M5 gadget, preferably with product id `0x685d`,
   serial `S22M5ACM0001`, or the `S22_NATIVE_INIT_USB_ACM_M5 READY` banner.
   After ACM proof, the helper may send the `download` command over ACM and
   wait for Odin/download mode before rollback. If ACM does not appear or the
   ACM command path fails, rollback requires manual download-mode entry before rollback through the same helper's
   `--rollback-from-download --ack S22PLUS-M5-ROLLBACK-FROM-DOWNLOAD` mode,
   using the exact Magisk boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not
   authorize display/distro candidates, kernel rebuild,
   recovery/vendor_boot/vbmeta/non-boot flash, raw host `dd`, fastboot,
   multidisabler, format data, or any A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M5B mount-reboot
   native-init boot-only live gate):** after M5 v0.4 freestanding USB-ACM
   failed to expose any transport and rolled back cleanly, Codex may prepare
   and perform one bounded attended boot-partition-only M5B live gate on the
   same Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m5b_mount_reboot_live_gate.py`
   with live ack token `S22PLUS-M5B-MOUNT-REBOOT-LIVE-GATE` and rollback-only
   ack token `S22PLUS-M5B-ROLLBACK-FROM-DOWNLOAD`. The exact candidate
   AP.tar.md5 SHA256 must be
   `872de3ee417eebbe8f55c14d226eaefe5e06d5989ffe96176b1bb02994793a59`, the
   contained padded `boot.img` SHA256 must be
   `21a61c84d273390a3681d029977ff6150991036568aa455a0a4879ff24590239`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, and
   the M5B `/init` SHA256 must be
   `accfc6f5e04d7d302ee17c6e4ce93ee14240ebdbb70274424934805e542b9bac`.
   The AP must contain exactly one tar member, `boot.img.lz4`, with no
   recovery, vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super,
   persist, userdata, EFS, RPMB, keymaster, modem, or any other partition
   payload. The M5B candidate may only run as direct PID1 with a freestanding
   raw-syscall runtime, mount only runtime virtual filesystems, emit the
   `S22_NATIVE_INIT_MOUNT_REBOOT_M5B` marker, request
   `reboot(..., "download")`, and park if the reboot syscall returns. It must
   perform no module insertion, no USB gadget setup, no persistent partition
   mount, no block-device write, no watchdog touch, no Android/Magisk start,
   no Magisk module install, no format data, and no self-rollback other than
   the reboot-download request. If candidate self-download does not appear in
   the bounded window, rollback requires manual download-mode entry before
   rollback through the same helper's `--rollback-from-download --ack
   S22PLUS-M5B-ROLLBACK-FROM-DOWNLOAD` mode, using the exact Magisk boot-only
   rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not
   authorize full M5 USB-chain changes, display/distro candidates, kernel
   rebuild, recovery/vendor_boot/vbmeta/non-boot flash, raw host `dd`,
   fastboot, multidisabler, format data, or any A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M6 recovery-replay
   USB-ACM native-init boot-only live gate):** after the M5B no-transport
   incident was manually recovered to rooted Magisk Android with boot hash
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, and
   after the M6 host build report proved the recovery-module replay candidate,
   Codex may prepare and perform one bounded attended boot-partition-only M6
   live gate on the same Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m6_recovery_replay_live_gate.py`
   with live ack token `S22PLUS-M6-RECOVERY-REPLAY-LIVE-GATE` and rollback-only
   ack token `S22PLUS-M6-ROLLBACK-FROM-DOWNLOAD`. The exact candidate AP.tar.md5
   SHA256 must be
   `a12bd8f067375cb14ab9043da5bae37d1f93f82c1d70bccd8fa9cef2f616bee9`, the
   contained padded `boot.img` SHA256 must be
   `7fe85c5973b930d777a670ac5997b0f26a51fa5b97705f5e467b0cecf501ffd2`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M6 `/init` SHA256 must be
   `7aecdf7a2c936b0785d20f5124667a8d682e9eb9678e77d20893889312860295`, and the
   source vendor_boot ramdisk SHA256 must be
   `41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193`.
   The AP must contain exactly one tar member, `boot.img.lz4`, with no
   recovery, vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super,
   persist, userdata, EFS, RPMB, keymaster, modem, or any other partition
   payload. The M6 candidate may only run as direct PID1 with a freestanding
   raw-syscall runtime, mount only runtime virtual filesystems, read the stock
   vendor_boot runtime `/lib/modules/modules.load.recovery`, replay that 446-line
   ordered module list from `/lib/modules`, rely on the stock
   `/lib/modules/modules.softdep` context, force `/sys/class/usb_role/*/role`
   to `device` when available, create only the configfs `ss_acm.0` gadget, bind
   only the real UDC `a600000.dwc3` and never dummy_udc.0, open `/dev/ttyGS0`,
   accept only a host-commanded ACM `download` request as its rollback reboot
   trigger, and park while probing. The M6 `/init` must not start Android or
   Magisk, mount persistent partitions, write block devices, touch watchdog,
   install Magisk modules, format data, auto-reboot, or inject vendor modules
   into the boot ramdisk. If ACM does not appear, ACM command handling fails, or
   candidate download mode does not appear in the bounded window, rollback
   requires manual download-mode rollback through the same helper's
   `--rollback-from-download --ack S22PLUS-M6-ROLLBACK-FROM-DOWNLOAD` mode,
   using the exact Magisk boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not
   authorize display/distro candidates, kernel rebuild, recovery/vendor_boot/
   vbmeta/non-boot flash, raw host `dd`, fastboot, multidisabler, format data,
   or any A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M7 USB-subset
   USB-ACM native-init boot-only live gate):** after the M6 no-transport/
   bootloop incident was manually recovered to rooted Magisk Android with boot
   hash `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`,
   and after the M7 host build report proved the 53-module USB subset candidate,
   Codex may prepare and perform one bounded attended boot-partition-only M7
   live gate on the same Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m7_usb_subset_live_gate.py`
   with live ack token `S22PLUS-M7-USB-SUBSET-LIVE-GATE` and rollback-only ack
   token `S22PLUS-M7-ROLLBACK-FROM-DOWNLOAD`. The exact candidate AP.tar.md5
   SHA256 must be
   `be0e1e34ec9452a14b7cfac66cc7ac57a0b29e92343945c35c1f836282563c4d`, the
   contained padded `boot.img` SHA256 must be
   `7e58de4cfbf50eabef73f62ed1c30a1b4bc83089307cca083c304b9a9b360206`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M7 `/init` SHA256 must be
   `530ff86247270c5a48db22f009e5f659d4403643a90486842938200c8192514d`, the M7
   subset list SHA256 must be
   `b630d318d1a95f596cbd97699d04d2bf60a53e634f35c00bbabc8000fb3315b7`, and the
   source vendor_boot ramdisk SHA256 must be
   `41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193`.
   The AP must contain exactly one tar member, `boot.img.lz4`, with no
   recovery, vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super,
   persist, userdata, EFS, RPMB, keymaster, modem, or any other partition
   payload. The M7 candidate may only run as direct PID1 with a freestanding
   raw-syscall runtime, mount only runtime virtual filesystems, read the boot
   ramdisk `s22plus_m7_usb_subset.modules` 53-module USB subset list, load those
   modules from the stock vendor_boot runtime `/lib/modules`, force
   `/sys/class/usb_role/*/role` to `device` when available, create only the
   configfs `ss_acm.0` gadget, bind only the real UDC `a600000.dwc3` and never
   dummy_udc.0, open `/dev/ttyGS0`, accept only a host-commanded ACM `download`
   request as its rollback reboot trigger, and park while probing. The M7
   subset must keep the watchdog blocklist (`gh_virt_wdt.ko`,
   `qcom_wdt_core.ko`, `qcom_soc_wdt.ko`, `sec_qc_qcom_wdt_core.ko`) out of the
   final load list and must exclude `qc_usb_audio.ko`. The M7 `/init` must not
   start Android or Magisk, mount persistent partitions, write block devices,
   touch watchdog, install Magisk modules, format data, auto-reboot, or inject
   vendor module binaries into the boot ramdisk. If ACM does not appear, ACM
   command handling fails, or candidate download mode does not appear in the
   bounded window, rollback requires manual download-mode rollback through the
   same helper's `--rollback-from-download --ack
   S22PLUS-M7-ROLLBACK-FROM-DOWNLOAD` mode, using the exact Magisk boot-only
   rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not
   authorize display/distro candidates, kernel rebuild, recovery/vendor_boot/
   vbmeta/non-boot flash, raw host `dd`, fastboot, multidisabler, format data,
   or any A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M8
   timed-download module-bisect native-init boot-only live gate):** after the
   M7 USB-subset candidate boot-looped and was manually recovered to rooted
   Magisk Android with boot hash
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, and
   after the M8 host build report proved the timed-download bisect candidate,
   Codex may prepare and perform one bounded attended boot-partition-only M8
   live gate on the same Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m8_timed_download_live_gate.py`
   with live ack token `S22PLUS-M8-TIMED-DOWNLOAD-LIVE-GATE` and rollback-only
   ack token `S22PLUS-M8-ROLLBACK-FROM-DOWNLOAD`. The exact candidate
   AP.tar.md5 SHA256 must be
   `59433518e7bea2d16f5efb62ee226c190f6a3af8673336310a2ef0fff7bee36b`, the
   contained padded `boot.img` SHA256 must be
   `3c10c9232b8579b552d791d24e65b7b4dd8ec3625941766894a08725a7abae52`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M8 `/init` SHA256 must be
   `5c8591023d0ad801155535e9b535993fb3122c4d3e4c86139d36a819ee72c3b2`, the M8
   delta batch list SHA256 must be
   `6831a24ac12ddf0bfdb9b5695dcd3aada7f200aa4a998864874c207efa31bc9d`, and the
   source vendor_boot ramdisk SHA256 must be
   `41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193`.
   The AP must contain exactly one tar member, `boot.img.lz4`, with no
   recovery, vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super,
   persist, userdata, EFS, RPMB, keymaster, modem, or any other partition
   payload. The M8 candidate may only run as direct PID1 with a freestanding
   raw-syscall runtime, mount only runtime virtual filesystems, read the boot
   ramdisk `s22plus_m8_delta_batch.modules` list, load exactly the first 18
   modules from the M7-only delta relative to M5 from the stock vendor_boot
   runtime `/lib/modules`, and then request automatic Samsung download-mode
   return. The helper must wait for the original Odin endpoint to disconnect
   before treating a later Odin endpoint as M8 self-download proof. M8 must use
   no ACM, no configfs, no UDC binding, and no USB role force. The M8 `/init`
   must not start Android or Magisk, mount persistent partitions, write block
   devices, touch watchdog, install Magisk modules, format data, or inject
   vendor module binaries into the boot ramdisk. If automatic download mode
   does not appear in the bounded window, rollback requires manual
   download-mode rollback through the same helper's `--rollback-from-download
   --ack S22PLUS-M8-ROLLBACK-FROM-DOWNLOAD` mode, using the exact Magisk
   boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not
   authorize display/distro candidates, kernel rebuild, recovery/vendor_boot/
   vbmeta/non-boot flash, raw host `dd`, fastboot, multidisabler, format data,
   or any A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M8A
   minimal-fs timed-download native-init boot-only live gate):** after M8 did
   not survive to its timed download request and M8A was built host-only as a
   no-module discriminator, Codex may prepare and perform one bounded attended
   boot-partition-only M8A live gate on the same Samsung S22+ `SM-S906N`/`g0q`
   `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m8a_minfs_download_live_gate.py`
   with live ack token `S22PLUS-M8A-MINFS-DOWNLOAD-LIVE-GATE` and
   rollback-only ack token `S22PLUS-M8A-ROLLBACK-FROM-DOWNLOAD`. The exact
   candidate AP.tar.md5 SHA256 must be
   `c97d29e38fe3293ad145a7743b61ae5fddae8f1b028e619dcd56e2f640de3c19`, the
   contained padded `boot.img` SHA256 must be
   `8a816fb3bf8e644de4bbe0409f6cf94fd06a33d16e672569c130535ce139ad44`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M8A `/init` SHA256 must be
   `aac2a03a2b20e72c3d69cfa3c4d3e5c045c817c293c347ac2aaf81f1bfb029b1`, and
   the M8A source SHA256 must be
   `830f95cc0f4237f10f2e132ead873a69f543134a503816fa2281205d41362538`. The AP
   must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M8A candidate may only run as direct PID1 with a freestanding raw-syscall
   runtime, mount only `/dev`, `/proc`, `/sys`, and `/run`, emit
   `S22_NATIVE_INIT_M8A_MINFS_DOWNLOAD`, sleep briefly, and then request
   automatic Samsung download-mode return. The helper must wait for the
   original Odin endpoint to disconnect before treating a later Odin endpoint
   as M8A self-download proof. M8A must use no module insertion, no configfs,
   no USB gadget, no UDC binding, and no USB role force. The M8A `/init` must
   not start Android or Magisk, mount persistent partitions, write block
   devices, touch watchdog, install Magisk modules, format data, or inject
   vendor module binaries or module-list files into the boot ramdisk. If
   automatic download mode does not appear in the bounded window, rollback
   requires manual download-mode rollback through the same helper's
   `--rollback-from-download --ack S22PLUS-M8A-ROLLBACK-FROM-DOWNLOAD` mode,
   using the exact Magisk boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not
   authorize display/distro candidates, kernel rebuild, recovery/vendor_boot/
   vbmeta/non-boot flash, raw host `dd`, fastboot, multidisabler, format data,
   or any A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M9A C
   first-action reboot native-init boot-only live gate):** after the M8A
   lower-layer postmortem and M9A host build report proved the C first-action
   reboot discriminator, Codex may prepare and perform one bounded attended
   boot-partition-only M9A live gate on the same Samsung S22+ `SM-S906N`/`g0q`
   `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m9a_c_first_reboot_live_gate.py`
   with live ack token `S22PLUS-M9A-C-FIRST-REBOOT-LIVE-GATE` and
   rollback-only ack token `S22PLUS-M9A-ROLLBACK-FROM-DOWNLOAD`. The exact
   candidate AP.tar.md5 SHA256 must be
   `c953f74fe7e3cdc226ebd3e1f0bac2142ee39e14483d87022714ae98e336d6b1`, the
   contained padded `boot.img` SHA256 must be
   `4c998680a1ccdbd5017053d7da58858ab818fc0644f08ef5bb0fc5d0dcc2d981`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M9A `/init` SHA256 must be
   `46dfc4ecf92457260484d38360c70c0a45a1b7aead3a5cac567ec21ab2c7d97f`, and
   the M9A source SHA256 must be
   `6248617a4d2fe077768aef1324937659d33a0c93a453d0ecf9cd8cc3d3ec34a8`. The AP
   must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M9A candidate may only run as direct PID1 with a freestanding C raw-syscall
   runtime, execute one direct `reboot(2)` syscall requesting automatic Samsung
   download-mode return, and then park if that syscall returns. The helper must
   wait for the original Odin endpoint to disconnect before treating a later
   Odin endpoint as M9A self-download proof. M9A must use no marker, no VFS, no
   kmsg, no mount, no sleep, no module insertion, no configfs, no USB gadget,
   no UDC binding, and no USB role force. The M9A `/init` must not start
   Android or Magisk, mount persistent partitions, write block devices, touch
   watchdog, install Magisk modules, format data, or inject vendor module
   binaries or module-list files into the boot ramdisk. If automatic download
   mode does not appear in the bounded window, rollback requires manual
   download-mode rollback through the same helper's `--rollback-from-download
   --ack S22PLUS-M9A-ROLLBACK-FROM-DOWNLOAD` mode, using the exact Magisk
   boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not
   authorize display/distro candidates, kernel rebuild, recovery/vendor_boot/
   vbmeta/non-boot flash, raw host `dd`, fastboot, multidisabler, format data,
   or any A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M10A mkdir-dev
   reboot native-init boot-only live gate):** after the M9A live result proved
   delayed automatic download-mode return from freestanding C first-reboot and
   the M10A host build report proved the mkdir-dev discriminator, Codex may
   prepare and perform one bounded attended boot-partition-only M10A live gate
   on the same Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked
   helper
   `workspace/public/src/scripts/revalidation/s22plus_m10a_mkdir_dev_reboot_live_gate.py`
   with live ack token `S22PLUS-M10A-MKDIR-DEV-REBOOT-LIVE-GATE` and
   rollback-only ack token `S22PLUS-M10A-ROLLBACK-FROM-DOWNLOAD`. The exact
   candidate AP.tar.md5 SHA256 must be
   `d71c8c82d2703892802228dd61ded561a9b4f90c678db15452014f2477170105`, the
   contained padded `boot.img` SHA256 must be
   `c62fce5e444bad47e2b934f6e9e82bc731058a0c9494629f0eb9044ff92e8b24`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M10A `/init` SHA256 must be
   `8f954dfcd5d5887f8c1659e7e658617561627d9c7fecc518972a795ac20422b3`, and
   the M10A source SHA256 must be
   `c12b710f93b957313ad1018de40ebe2dec53883c5de6d018c9d5577b1a426cf0`. The AP
   must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M10A candidate may only run as direct PID1 with a freestanding C raw-syscall
   runtime, execute exactly one `mkdirat("/dev", 0755)` side effect, then one
   direct `reboot(2)` syscall requesting automatic Samsung download-mode
   return, and then park if that syscall returns. The helper must wait for the
   original Odin endpoint to disconnect before treating a later Odin endpoint
   as M10A self-download proof, and its default self-download window must be at
   least 150 seconds. M10A must use no marker, no kmsg, no mknodat, no mount,
   no sleep, no module insertion, no configfs, no USB gadget, no UDC binding,
   and no USB role force. The M10A `/init` must not start Android or Magisk,
   mount persistent partitions, write block devices, touch watchdog, install
   Magisk modules, format data, or inject vendor module binaries or module-list
   files into the boot ramdisk. If automatic download mode does not appear in
   the bounded window, rollback requires manual download-mode rollback through
   the same helper's `--rollback-from-download --ack
   S22PLUS-M10A-ROLLBACK-FROM-DOWNLOAD` mode, using the exact Magisk boot-only
   rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not
   authorize display/distro candidates, kernel rebuild, recovery/vendor_boot/
   vbmeta/non-boot flash, raw host `dd`, fastboot, multidisabler, format data,
   or any A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M10A1 stat-dev
   reboot native-init boot-only live gate):** after the M10A live result was
   operator-corrected to bootloop/manual-download rollback and the M10A1 host
   build report proved the read-only stat-dev discriminator, Codex may prepare
   and perform one bounded attended boot-partition-only M10A1 live gate on the
   same Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m10a1_stat_dev_reboot_live_gate.py`
   with live ack token `S22PLUS-M10A1-STAT-DEV-REBOOT-LIVE-GATE` and
   rollback-only ack token `S22PLUS-M10A1-ROLLBACK-FROM-DOWNLOAD`. The exact
   candidate AP.tar.md5 SHA256 must be
   `68a7f1f5b336a32d882e7cdde73f299815d689b6885b724a6b6c7672bdda00bf`, the
   contained padded `boot.img` SHA256 must be
   `2fe6b3270f7d493f677f126594061eea33d22de7abe98dc2210fe8050961ecb2`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M10A1 `/init` SHA256 must be
   `477583121c6c29f5eb31866c034352abb2f03c8fe97ec71e2f63ecbddd6f1642`, and
   the M10A1 source SHA256 must be
   `a60b66ec5d07f93bb9e29ac96c342e57621815630c29f31653b104e19f7ff86b`. The
   AP must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M10A1 candidate may only run as direct PID1 with a freestanding C raw-syscall
   runtime, execute exactly one `newfstatat(AT_FDCWD, "/dev", ...)` read-only
   pathname VFS probe, then one direct `reboot(2)` syscall requesting Samsung
   download-mode return, and then park if that syscall returns. The helper must
   wait for the original Odin endpoint to disconnect before treating a later
   Odin endpoint as a candidate-or-manual download endpoint. Because of the
   M10A manual-download ambiguity, a later endpoint is not automatic proof
   unless the operator confirms no manual download-mode entry occurred. M10A1
   must use no mkdirat, no marker, no kmsg, no mknodat, no mount, no sleep, no
   module insertion, no configfs, no USB gadget, no UDC binding, and no USB role
   force. The M10A1 `/init` must not start Android or Magisk, mount persistent
   partitions, write block devices, touch watchdog, install Magisk modules,
   format data, or inject vendor module binaries or module-list files into the
   boot ramdisk. If download mode does not appear in the bounded window,
   rollback requires manual download-mode rollback through the same helper's
   `--rollback-from-download --ack S22PLUS-M10A1-ROLLBACK-FROM-DOWNLOAD` mode,
   using the exact Magisk boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not
   authorize display/distro candidates, kernel rebuild, recovery/vendor_boot/
   vbmeta/non-boot flash, raw host `dd`, fastboot, multidisabler, format data,
   or any A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M10A2 getpid
   reboot native-init boot-only live gate):** after the M10A1 live result was
   operator-corrected to bootloop/manual-download rollback and the M10A2 host
   build report proved the non-VFS getpid discriminator, Codex may prepare and
   perform one bounded attended boot-partition-only M10A2 live gate on the same
   Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m10a2_getpid_reboot_live_gate.py`
   with live ack token `S22PLUS-M10A2-GETPID-REBOOT-LIVE-GATE` and
   rollback-only ack token `S22PLUS-M10A2-ROLLBACK-FROM-DOWNLOAD`. The exact
   candidate AP.tar.md5 SHA256 must be
   `108c0a5e2a1fd80efed5ae93ea01b4b98c4990f7d3d8b292ef35ccc0de2fdb60`, the
   contained padded `boot.img` SHA256 must be
   `f0238a82cad63a3d8017a0892a3a85bfe79c8c503848a4ac0fa4a21a77a72c94`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M10A2 `/init` SHA256 must be
   `0839562fbef74328abb17646d957516154ae85ab954667782c809249cf8bde99`, and
   the M10A2 source SHA256 must be
   `5b15166dfc405a7ee1297ac1cd0da3bd844779099748cf98ee3aca8e2e665d9a`. The
   AP must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M10A2 candidate may only run as direct PID1 with a freestanding C raw-syscall
   runtime, execute exactly one `getpid()` non-VFS syscall, then one direct
   `reboot(2)` syscall requesting Samsung download-mode return, and then park
   if that syscall returns. The helper must wait for the original Odin endpoint
   to disconnect before treating a later Odin endpoint as a candidate-or-manual
   download endpoint. Because of the manual-download ambiguity, a later endpoint
   is not automatic proof unless the operator confirms no manual download-mode
   entry occurred. M10A2 must use no pathname access, no VFS, no mkdirat, no
   marker, no kmsg, no mknodat, no mount, no sleep, no module insertion, no
   configfs, no USB gadget, no UDC binding, and no USB role force. The M10A2
   `/init` must not start Android or Magisk, mount persistent partitions, write
   block devices, touch watchdog, install Magisk modules, format data, or
   inject vendor module binaries or module-list files into the boot ramdisk. If
   download mode does not appear in the bounded window, rollback requires manual
   download-mode rollback through the same helper's `--rollback-from-download
   --ack S22PLUS-M10A2-ROLLBACK-FROM-DOWNLOAD` mode, using the exact Magisk
   boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not
   authorize display/distro candidates, kernel rebuild, recovery/vendor_boot/
   vbmeta/non-boot flash, raw host `dd`, fastboot, multidisabler, format data,
   or any A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M10A3 probe reboot
   native-init boot-only live gate):** after the M10A2 live result was
   operator-corrected to bootloop/manual-download rollback and the M10A3 host
   build report proved the no-syscall probe discriminator, Codex may prepare
   and perform one bounded attended boot-partition-only M10A3 live gate on the
   same Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m10a3_probe_reboot_live_gate.py`
   with live ack token `S22PLUS-M10A3-PROBE-REBOOT-LIVE-GATE` and
   rollback-only ack token `S22PLUS-M10A3-ROLLBACK-FROM-DOWNLOAD`. The exact
   candidate AP.tar.md5 SHA256 must be
   `7415538ac9cbfdf4af27f294927c3c81d2656412a7f779fce515138ec28e7e3b`, the
   contained padded `boot.img` SHA256 must be
   `eb2d1cfc278e63cdfe009379f05139e5299b49859a2b247d4e6996be5f24959c`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M10A3 `/init` SHA256 must be
   `4c7908026430658250a0999fad2d47c7e5d99c212dc8daa3ba8fbafb0f4a8371`, and
   the M10A3 source SHA256 must be
   `9b5e3669a7a790a369bf8ed4beb662cb5262189e5d8f22011c731fc827955856`. The
   AP must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M10A3 candidate may only run as direct PID1 with a freestanding C raw-syscall
   runtime, execute one pre-reboot stack-probe helper with no syscall, then one
   direct `reboot(2)` syscall requesting Samsung download-mode return, and then
   park if that syscall returns. The helper must wait for the original Odin
   endpoint to disconnect before treating a later Odin endpoint as a
   candidate-or-manual download endpoint. Because of the manual-download
   ambiguity, a later endpoint is not automatic proof unless the operator
   confirms no manual download-mode entry occurred. M10A3 must use no getpid, no
   pathname access, no VFS, no mkdirat, no marker, no kmsg, no mknodat, no
   mount, no sleep, no module insertion, no configfs, no USB gadget, no UDC
   binding, and no USB role force. The M10A3 `/init` must not start Android or
   Magisk, mount persistent partitions, write block devices, touch watchdog,
   install Magisk modules, format data, or inject vendor module binaries or
   module-list files into the boot ramdisk. If download mode does not appear in
   the bounded window, rollback requires manual download-mode rollback through
   the same helper's `--rollback-from-download --ack
   S22PLUS-M10A3-ROLLBACK-FROM-DOWNLOAD` mode, using the exact Magisk boot-only
   rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not
   authorize display/distro candidates, kernel rebuild, recovery/vendor_boot/
   vbmeta/non-boot flash, raw host `dd`, fastboot, multidisabler, format data,
   or any A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M10A4
   inline-probe reboot native-init boot-only live gate):** after the M10A3 live
   result was operator-corrected to bootloop/manual-download rollback and the
   M10A4 host build report proved the inline-probe discriminator, Codex may
   prepare and perform one bounded attended boot-partition-only M10A4 live gate
   on the same Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked
   helper
   `workspace/public/src/scripts/revalidation/s22plus_m10a4_inline_probe_reboot_live_gate.py`
   with live ack token `S22PLUS-M10A4-INLINE-PROBE-REBOOT-LIVE-GATE` and
   rollback-only ack token `S22PLUS-M10A4-ROLLBACK-FROM-DOWNLOAD`. The exact
   candidate AP.tar.md5 SHA256 must be
   `a4d7c9d05536d22c3f56bd1891a7fbc0c8fa6d3500cf8b1036e11bd0c9569c26`, the
   contained padded `boot.img` SHA256 must be
   `38986a19454d7fd49e8860d025ad4241e2c130b5fc28956bed892c26842fb3a9`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M10A4 `/init` SHA256 must be
   `d70c794979bc16f12917871f5e6e7b2231569f72682a5f6ebcd87f901a11837b`, and
   the M10A4 source SHA256 must be
   `2d168c28dbdef67bedc7d9d39250c7e61c928daf89a2b973616534453a835a84`. The
   AP must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M10A4 candidate may only run as direct PID1 with a freestanding C raw-syscall
   runtime, perform one inline stack probe in `_start`, use no separate
   no-syscall probe helper, then one direct `reboot(2)` syscall requesting
   Samsung download-mode return, and then park if that syscall returns. The
   helper must wait for the original Odin endpoint to disconnect before
   treating a later Odin endpoint as a candidate-or-manual download endpoint.
   Because of the manual-download ambiguity, a later endpoint is not automatic
   proof unless the operator confirms no manual download-mode entry occurred.
   M10A4 must use no getpid, no pathname access, no VFS, no mkdirat, no marker,
   no kmsg, no mknodat, no mount, no sleep, no module insertion, no configfs,
   no USB gadget, no UDC binding, and no USB role force. The M10A4 `/init`
   must not start Android or Magisk, mount persistent partitions, write block
   devices, touch watchdog, install Magisk modules, format data, or inject
   vendor module binaries or module-list files into the boot ramdisk. If
   download mode does not appear in the bounded window, rollback requires
   manual download-mode rollback through the same helper's
   `--rollback-from-download --ack S22PLUS-M10A4-ROLLBACK-FROM-DOWNLOAD`
   mode, using the exact Magisk boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not
   authorize display/distro candidates, kernel rebuild, recovery/vendor_boot/
   vbmeta/non-boot flash, raw host `dd`, fastboot, multidisabler, format data,
   or any A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M11 park-USB
   USB-ACM native-init boot-only live gate):** after the M11 host build report
   proved the park-based USB candidate and `GOAL.md` pivoted away from the
   unreliable reboot-download beacon, Codex may prepare and perform one bounded
   attended boot-partition-only M11 live gate on the same Samsung S22+
   `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m11_park_usb_live_gate.py`
   with live ack token `S22PLUS-M11-PARK-USB-LIVE-GATE` and rollback-only ack
   token `S22PLUS-M11-ROLLBACK-FROM-DOWNLOAD`. The exact candidate AP.tar.md5
   SHA256 must be
   `8b4a4fa6db3bc0b2bf5e4fd1fccf4b671fd2fbd7fbbcc08542c3be816a3f5d43`, the
   contained padded `boot.img` SHA256 must be
   `32f2667c31f05d967529031630e5b004cf5238120ffc6ec7089dcc40a3352a3f`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M11 `/init` SHA256 must be
   `234ded5b6172a3470825a1c616e6537c3de4b2274d8c26525386f8e85d5e8d7e`, the
   M11 module-list SHA256 must be
   `c254be05c91199c4f69380f0488de13c7b2cde987594bc1c5d0a6657a0e8eb58`, the
   M11 source SHA256 must be
   `ff92af817cd4564b6fd811484540e8a217ff19bbe445839981ce7818498561f6`, and
   the vendor ramdisk SHA256 must be
   `41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193`. The AP
   must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M11 candidate may only run as direct PID1 with a freestanding raw-syscall
   runtime, mount only the minimal pseudo filesystems needed for module loading
   and configfs, load the 48 modules in `s22plus_m11_park_usb.modules`, attempt
   `/sys/class/usb_role/*/role=device`, bind only `a600000.dwc3` and never
   `dummy_udc.0`, expose an `ss_acm.0` gadget if possible, and then park. M11
   has no reboot beacon, no arm64 `__NR_reboot=142` path, no `download` string,
   no host-commanded ACM download action, and uses park-vs-loop plus host ACM
   enumeration as the observation model. The final 48 modules must exclude the
   explicitly blocked reset/debug/glink/eud/audio entries including `abc.ko`,
   `icc-debug.ko`, `minidump.ko`, `qc_usb_audio.ko`, and `sec_debug.ko`, plus
   the full explicit blocklist recorded in the manifest. If M11 parks or ACM
   appears, rollback requires operator manual download-mode rollback through
   the same helper's `--rollback-from-download --ack
   S22PLUS-M11-ROLLBACK-FROM-DOWNLOAD` mode, using the exact Magisk boot-only
   rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not
   authorize M10A4 reboot-beacon retry, display/distro candidates, kernel
   rebuild, recovery/vendor_boot/vbmeta/non-boot flash, raw host `dd`,
   fastboot, multidisabler, format data, or any A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M12 M5-floor
   USB-ACM native-init boot-only live gate):** after the M11 live result proved
   the M11 48-module candidate still boot-looped with no ACM and the M12
   host-build report prepared the M5-floor split, Codex may prepare and perform
   one bounded attended boot-partition-only M12 live gate on the same Samsung
   S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m12_m5_floor_live_gate.py`
   with live ack token `S22PLUS-M12-M5-FLOOR-LIVE-GATE` and rollback-only ack
   token `S22PLUS-M12-ROLLBACK-FROM-DOWNLOAD`. The exact candidate AP.tar.md5
   SHA256 must be
   `deece127aa5c85dbf4937459fc528f2cfcd9926fb3556f26ffc9b10fbfe932cb`, the
   contained padded `boot.img` SHA256 must be
   `f211e46c7153df31c458a907f4ac56fe4a3d160d8ded2a13a8e0e31af6f5106c`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M12 `/init` SHA256 must be
   `50ae525230680c495d3c40fc671cb88118e8bd473cef92873266142549a28002`, the
   M12 module-list SHA256 must be
   `c2e44f6f934542f8f7889ef09245294ee342c5ae03a0f6db9988b58b943ddc16`, the
   M12 source SHA256 must be
   `5b43593a24b3b03a667f5515b8a558e40121b4da091efb56adf383ea50240392`, and
   the vendor ramdisk SHA256 must be
   `41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193`. The AP
   must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M12 candidate may only run as direct PID1 with a freestanding raw-syscall
   runtime, mount only the minimal pseudo filesystems needed for module loading
   and configfs, load the 24 modules in `s22plus_m12_m5_floor.modules`, attempt
   `/sys/class/usb_role/*/role=device`, bind only `a600000.dwc3` and never
   `dummy_udc.0`, expose an `ss_acm.0` gadget if possible, and then park. M12
   has no reboot beacon, no arm64 `__NR_reboot=142` path, no `download` string,
   no host-commanded ACM download action, and uses park-vs-loop plus host ACM
   enumeration as the observation model. The 24 modules are the M5/M11 common
   floor in M5 order, loaded from stock vendor_boot `/lib/modules`; the M5-only
   modules `usb_notifier_qcom.ko` and `qc_usb_audio.ko` and all 24 M11-only
   substrate modules are intentionally withheld. If M12 parks or ACM appears,
   rollback requires operator manual download-mode rollback through the same
   helper's `--rollback-from-download --ack
   S22PLUS-M12-ROLLBACK-FROM-DOWNLOAD` mode, using the exact Magisk boot-only
   rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not
   authorize M11 retry, M11-only module add-back, display/distro candidates,
   kernel rebuild, recovery/vendor_boot/vbmeta/non-boot flash, raw host `dd`,
   fastboot, multidisabler, format data, or any A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M13 no-module
   configfs/role-force native-init boot-only live gate):** after the M12 live
   result proved the no-reboot M5-floor candidate still boot-looped with no ACM
   and the M13 host-build report prepared the no-module split, Codex may prepare
   and perform one bounded attended boot-partition-only M13 live gate on the
   same Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m13_nomodule_configfs_live_gate.py`
   with live ack token `S22PLUS-M13-NOMODULE-CONFIGFS-LIVE-GATE` and
   rollback-only ack token `S22PLUS-M13-ROLLBACK-FROM-DOWNLOAD`. The exact
   candidate AP.tar.md5 SHA256 must be
   `5e959f0dd7c55d8e6a9363cde0c0fcc72876639bdc46ccdc826186cfc43134fa`, the
   contained padded `boot.img` SHA256 must be
   `21808217d6cf698217e25cf35caf3a271a7f55451cad85ba576d54a40010441b`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M13 `/init` SHA256 must be
   `6b2d229217d83c7f36032c37291bebbebe7c8c5782d006fedcc538649d99f5d3`, and
   the M13 source SHA256 must be
   `4e3a88336c6a6e0b1ed6e25f572ed0ec26c2e8d177942598a6e32aa1b2a762e8`. The
   AP must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M13 candidate may only run as direct PID1 with a freestanding raw-syscall
   runtime, mount only the minimal pseudo filesystems needed for configfs and
   kmsg logging, perform `module_insertions=false` with no module-list payload
   and no vendor module binaries, attempt `/sys/class/usb_role/*/role=device`,
   bind only `a600000.dwc3` and never `dummy_udc.0`, expose an `ss_acm.0`
   gadget if possible, and then park. M13 has no reboot beacon, no arm64
   `__NR_reboot=142` path, no arm64 `__NR_finit_module=273` path, no
   `download` string, no host-commanded ACM download action, and uses
   park-vs-loop plus host ACM enumeration as the observation model. If M13 parks
   or ACM appears, rollback requires operator manual download-mode rollback
   through the same helper's `--rollback-from-download --ack
   S22PLUS-M13-ROLLBACK-FROM-DOWNLOAD` mode, using the exact Magisk boot-only
   rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not
   authorize M12 retry, module add-back, configfs removal follow-up, display/
   distro candidates, kernel rebuild, recovery/vendor_boot/vbmeta/non-boot
   flash, raw host `dd`, fastboot, multidisabler, format data, or any A90
   action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M14 core-ACM
   add-back native-init boot-only live gate):** after the M13 live result
   recovered a non-looping no-module/no-transport floor and the M14 host-build
   report prepared the first small add-back below M12, Codex may prepare and
   perform one bounded attended boot-partition-only M14 live gate on the same
   Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m14_core_acm_live_gate.py`
   with live ack token `S22PLUS-M14-CORE-ACM-LIVE-GATE` and rollback-only ack
   token `S22PLUS-M14-ROLLBACK-FROM-DOWNLOAD`. The exact candidate AP.tar.md5
   SHA256 must be
   `080fedea35c111020f68b5fb64eb260402dbc45ac4398e282523c94bf9a8922b`, the
   contained padded `boot.img` SHA256 must be
   `dee741af20fb3dbcd347c2fa4d45099018f54f577ddf7ae64ac3dca4a357c2e4`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M14 `/init` SHA256 must be
   `0a144b2ddde32d78b4dfe051e009f5275f2e67c8276b0fa2d1a61e3280b7eed4`, the
   M14 module-list SHA256 must be
   `5b52cd5c1ae26d0bf24e7654b27f254ee478673c9313afdb955a0ec4fcf35f7c`, and
   the M14 source SHA256 must be
   `8acc0bfff03ec3adbde160a7ad6975be4154c8a219e8e59ebe1a6d8b1a19b8a7`. The
   AP must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M14 candidate may only run as direct PID1 with a freestanding raw-syscall
   runtime, mount only the minimal pseudo filesystems needed for module loading,
   configfs, and kmsg logging, load the four core USB/ACM modules in
   `s22plus_m14_core_acm.modules` (`phy-msm-ssusb-qmp.ko`,
   `phy-msm-snps-eusb2.ko`, `dwc3-msm.ko`, `usb_f_ss_acm.ko`) from stock
   vendor_boot `/lib/modules`, include the marker strings `module_group=core_acm`
   and `module_count=4`, attempt `/sys/class/usb_role/*/role=device`, bind only
   `a600000.dwc3` and never `dummy_udc.0`, expose an `ss_acm.0` gadget if
   possible, and then park. M14 has no reboot beacon, no arm64 `__NR_reboot=142`
   path, no `download` string, no host-commanded ACM download action, and uses
   park-vs-loop plus host ACM enumeration as the observation model. The remaining
   20 M12 floor modules are intentionally withheld. If M14 parks or ACM appears,
   rollback requires operator manual download-mode rollback through the same
   helper's `--rollback-from-download --ack S22PLUS-M14-ROLLBACK-FROM-DOWNLOAD`
   mode, using the exact Magisk boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not authorize
   M12/M13 retry, wider module add-back, configfs removal follow-up, display/
   distro candidates, kernel rebuild, recovery/vendor_boot/vbmeta/non-boot
   flash, raw host `dd`, fastboot, multidisabler, format data, or any A90 action.
   **Narrow operator-authorized exception (2026-07-07, S22+ M15 PHY-split
   add-back native-init boot-only live gate):** after the M14 live result
   boot-looped with the four-module core USB/ACM add-back and rollback returned
   Android/Magisk cleanly, Codex may prepare and perform one bounded attended
   boot-partition-only M15 live gate on the same Samsung S22+ `SM-S906N`/`g0q`
   `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m15_phy_split_live_gate.py`
   with live ack token `S22PLUS-M15-PHY-SPLIT-LIVE-GATE` and rollback-only ack
   token `S22PLUS-M15-ROLLBACK-FROM-DOWNLOAD`. The exact candidate AP.tar.md5
   SHA256 must be
   `16a4d526bbc0cb09bc63d61f4743d17dddb26c34047127fe610b1f677bddced2`, the
   contained padded `boot.img` SHA256 must be
   `adaee20d490748aa1be555cdc7aa6828b9bc553185355a60183bd722119b5812`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M15 `/init` SHA256 must be
   `5897fee141921dffc2848fb3eb3515a9b2d75d41e0c286448c4f0add06ab8558`, the
   M15 module-list SHA256 must be
   `f3afe268a05c47492107227b224185c65f7757c004806c4c24d23231bd19e217`, and
   the M15 source SHA256 must be
   `ac57cb1ece2dcc65bf5a8cbfc3fa0a077b006c757a4615298ee00d115b1fdd13`. The
   AP must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M15 candidate may only run as direct PID1 with a freestanding raw-syscall
   runtime, mount only the minimal pseudo filesystems needed for module loading,
   configfs, and kmsg logging, load the two PHY-side modules in
   `s22plus_m15_phy_split.modules` (`phy-msm-ssusb-qmp.ko`,
   `phy-msm-snps-eusb2.ko`) from stock vendor_boot `/lib/modules`, include the
   marker strings `module_group=phy_split` and `module_count=2`, attempt
   `/sys/class/usb_role/*/role=device`, bind only `a600000.dwc3` and never
   `dummy_udc.0`, expose an `ss_acm.0` gadget if possible, and then park. M15
   has no reboot beacon, no arm64 `__NR_reboot=142` path, no `download` string,
   no host-commanded ACM download action, and uses park-vs-loop plus host ACM
   enumeration as the observation model. The remaining two M14 modules
   (`dwc3-msm.ko`, `usb_f_ss_acm.ko`) and the remaining 20 M12 floor modules
   are intentionally withheld. If M15 parks or ACM appears, rollback requires
   operator manual download-mode rollback through the same helper's
   `--rollback-from-download --ack S22PLUS-M15-ROLLBACK-FROM-DOWNLOAD` mode,
   using the exact Magisk boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not authorize
   M12/M13/M14 retry, wider module add-back, configfs removal follow-up,
   display/distro candidates, kernel rebuild, recovery/vendor_boot/vbmeta/
   non-boot flash, raw host `dd`, fastboot, multidisabler, format data, or any
   A90 action.
   **Narrow operator-authorized exception (2026-07-08, S22+ M17 power-QMP
   add-back native-init boot-only live gate):** after the M15 live result
   boot-looped with the naked two-PHY-side module add-back, rollback returned
   Android/Magisk cleanly, and the M17 host-build report corrected the next
   experiment to probe QMP only after its power/clock substrate, Codex may
   prepare and perform one bounded attended boot-partition-only M17 live gate
   on the same Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked
   helper `workspace/public/src/scripts/revalidation/s22plus_m17_power_qmp_live_gate.py`
   with live ack token `S22PLUS-M17-POWER-QMP-LIVE-GATE` and rollback-only ack
   token `S22PLUS-M17-ROLLBACK-FROM-DOWNLOAD`. The exact candidate AP.tar.md5
   SHA256 must be
   `78b2641788a1517f39bdbd50dc425dbaeab0683aa662bcd8bfe9c925a8a50274`, the
   contained padded `boot.img` SHA256 must be
   `090811c8f50aab753ef7f085c3cf5bd73e9d6d43e2ad629e95d2cfe48a0ecac2`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M17 `/init` SHA256 must be
   `34389fc52cd74aa50b2ab2980075183bcde519ffc5d7f9dfb787e1e5b3e2bfe4`, the
   M17 module-list SHA256 must be
   `1e00da43ae2b22c56855a28967201733b66b65ec4e91086faa67a4d9b3177fb8`, and
   the M17 source SHA256 must be
   `561099a8401ea6b5d5642614b6f6a73e225b239556de07c11cf2d99e1d0a6d2f`. The
   AP must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M17 candidate may only run as direct PID1 with a freestanding raw-syscall
   runtime, mount only the minimal pseudo filesystems needed for module loading,
   configfs, and kmsg logging, load the 21-module power/clock substrate
   dependency closure in `s22plus_m17_power_qmp.modules` (`clk-rpmh.ko`,
   `gcc-waipio.ko`, `icc-rpmh.ko`, `qcom_ipc_logging.ko`,
   `rpmh-regulator.ko`, `clk-dummy.ko`, `clk-qcom.ko`, `cmd-db.ko`,
   `debug-regulator.ko`, `gdsc-regulator.ko`, `icc-bcm-voter.ko`,
   `icc-debug.ko`, `minidump.ko`, `qti-fixed-regulator.ko`,
   `proxy-consumer.ko`, `qcom_rpmh.ko`, `qcom-scm.ko`, `sec_debug.ko`,
   `smem.ko`, `socinfo.ko`, `phy-msm-ssusb-qmp.ko`) from stock vendor_boot
   `/lib/modules`, include the marker strings `module_group=power_qmp` and
   `module_count=21`, attempt `/sys/class/usb_role/*/role=device`, bind only
   `a600000.dwc3` and never `dummy_udc.0`, expose an `ss_acm.0` gadget if
   possible, and then park. M17 has no reboot beacon, no arm64
   `__NR_reboot=142` path, no `download` string, no host-commanded ACM
   download action, and uses park-vs-loop plus host ACM enumeration as the
   observation model. The other PHYs (`phy-generic.ko`,
   `phy-msm-snps-hs.ko`, `phy-msm-snps-eusb2.ko`), `dwc3-msm.ko`, USB
   function modules, role/PD/glink stack, and watchdog modules are intentionally
   withheld. If M17 parks or ACM appears, rollback requires operator manual
   download-mode rollback through the same helper's `--rollback-from-download
   --ack S22PLUS-M17-ROLLBACK-FROM-DOWNLOAD` mode, using the exact Magisk
   boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception does not authorize
   M12/M13/M14/M15 retry, naked-QMP M16 live, wider module add-back, display/
   distro candidates, kernel rebuild, recovery/vendor_boot/vbmeta/non-boot
   flash, raw host `dd`, fastboot, multidisabler, format data, or any A90
   action.
   **Narrow operator-authorized exception (2026-07-08, S22+ M18 P00 prefix-download native-init boot-only):**
   **Consumed/retired:** this one-shot exception was consumed by the 2026-07-08
   live run. It flashed the pinned P00 boot AP once, observed the original Odin
   endpoint disconnect, saw no later Odin endpoint during the bounded
   self-download window, required attended manual Download-mode entry, restored
   the pinned Magisk boot AP, and reverified Android/Magisk plus boot and DTBO
   partition hashes. It must not be reused for another P00, P10, M18, or
   prefix-download live flash under the same gate. The consumed live and
   rollback ack tokens are intentionally not listed here as active
   authorization. Before consumption, after the EUD/OpenOCD host path had no
   EUD USB endpoint and the observability frontier audit selected the M18
   prefix-download fallback, Codex could perform one bounded attended S22+
   M18 P00 prefix-download native-init boot-only live gate on the same Samsung
   S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m18_p00_prefix_download_live_gate.py`.
   The consumed P00 candidate AP.tar.md5 SHA256 was
   `b79ac94aac341ab5e4c08cb3c568c20be28bb71ccd4f1b047f712bd1dcf5225b`, the
   contained boot.img SHA256 was
   `f8f362bdd0d0f75ae9ae0ce69d86bcfe47362f246504b02fc6175a4aa0a83133`, the
   base known-booting Magisk boot SHA256 was
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved kernel SHA256 was
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, and the
   P00 `/init` SHA256 was
   `467947f7ba0c4b4088c9a21a19e5202609b833298f2e95256b1f011eb9af034e`. The AP
   contained exactly one tar member, `boot.img.lz4`, and no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, sec_efs, RPMB, keymaster, modem, bootloader, or other
   partition payload. P00 loads no modules and used no ACM, no configfs, no
   module binary injection, no EUD sysfs write, no raw host partition write, and
   no fastboot. The failed proof result means P00 did not demonstrate reaching
   the checkpoint that requests Samsung Download mode. This exception does not
   authorize P10, M18 full-firststage retry, DTBO, vendor_boot, vbmeta,
   recovery, BL, CP, CSC, super, userdata, persist, EFS, sec_efs, RPMB,
   keymaster, modem, bootloader, Magisk modules, multidisabler, format data,
   additional boot candidates, kernel rebuilds, or any A90 action.
   **Narrow operator-authorized exception (2026-07-08, S22+ ramoops DTBO + M18 capture only):**
   after the operator explicitly accepts the non-boot DTBO write risk and the
   patched-DTBO AVB hash-descriptor mismatch under the already-proven
   disabled-vbmeta/orange state, Codex may perform one bounded attended
   S22+ ramoops DTBO + M18 capture run on the Samsung S22+ `SM-S906N`/`g0q`
   `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m18_capture_live_gate.py`
   and live ack token `S22PLUS-RAMOOPS-DTBO-M18-CAPTURE-LIVE-GATE`.
   This exception authorizes exactly two partition classes and no others:
   first flash the patched `dtbo` AP.tar.md5 SHA256
   `4f82663a7c2175a41760ec099c0f662dd04b8932a5ae82ba46b3ecb401a14a00`,
   then flash the M18 boot candidate AP.tar.md5 SHA256
   `9382f91bf2cd3235410368ca08208b9343d8584da48c29b25c46a931b1f42805`;
   after capture, restore the boot partition using the pinned Magisk boot
   rollback AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
   with stock boot fallback AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`,
   then restore stock DTBO using the pinned stock DTBO rollback AP.tar.md5
   SHA256 `6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa`.
   The patched raw DTBO SHA256 must be
   `1c90b54577cbb42e029818a0c4248e85ec3a0e40903b0887648d6556355c85ab`,
   the stock raw DTBO SHA256 must be
   `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`,
   the M18 padded boot.img SHA256 must be
   `a99a09fa062d1aaa848a41037c649a43abc983f177714dfc24c39d0df4d84083`,
   and the M18 base known-booting Magisk boot SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
   The DTBO APs must contain exactly one tar member, `dtbo.img.lz4`; the M18,
   Magisk rollback, and stock boot fallback APs must contain exactly one tar
   member, `boot.img.lz4`. The helper must verify all AP hashes and both
   manifests before live work, verify current Android root and the current boot
   hash, flash patched DTBO first, require Android/root to return, then flash
   M18 for pstore capture. If M18 loops or no transport appears, rollback
   requires operator manual download-mode entry and the helper mode
   `--rollback-boot-from-download --ack S22PLUS-RAMOOPS-M18-ROLLBACK-BOOT-FROM-DOWNLOAD`.
   Stock DTBO restore requires either
   `--restore-dtbo-from-android --ack S22PLUS-RAMOOPS-RESTORE-STOCK-DTBO` or
   `--restore-dtbo-from-download --ack S22PLUS-RAMOOPS-RESTORE-STOCK-DTBO`.
   The capture goal is to read `pstore` / `/sys/fs/pstore` after the M18 boot
   failure, then restore stock DTBO for a clean state. This exception does not
   authorize writing or flashing recovery, vendor_boot, vbmeta, vbmeta_system,
   BL, CP, CSC, super, userdata, persist, EFS, sec_efs, RPMB, keymaster, modem,
   bootloader, raw host `dd`, fastboot, Magisk modules, multidisabler, format
   data, additional boot candidates, additional DTBO candidates, kernel rebuilds,
   or any A90 action.
   **Narrow operator-authorized exception (2026-07-08, S22+ ramoops DTBO status-only):**
   after the active-DTB provenance audit proved that stock DTBO overlays override
   `/proc/device-tree/reserved-memory/ramoops_region/status` to `disabled`, Codex
   may perform one bounded attended S22+ ramoops DTBO status-only live gate on
   the Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_status_live_gate.py`
   and live ack token `S22PLUS-RAMOOPS-DTBO-STATUS-LIVE-GATE`. This exception
   authorizes exactly one partition class and no others: first flash the patched
   `dtbo` AP.tar.md5 SHA256
   `4f82663a7c2175a41760ec099c0f662dd04b8932a5ae82ba46b3ecb401a14a00`, require
   Android/root to return, require current DTBO SHA256
   `1c90b54577cbb42e029818a0c4248e85ec3a0e40903b0887648d6556355c85ab`, require
   live `/proc/device-tree/reserved-memory/ramoops_region/status=okay`, then
   restore stock DTBO using the pinned stock DTBO rollback AP.tar.md5 SHA256
   `6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa`.
   The stock raw DTBO SHA256 must be
   `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`, the
   DTBO APs must contain exactly one tar member, `dtbo.img.lz4`, and the helper
   must verify current Android root, the current known-booting Magisk boot hash,
   current stock DTBO hash, and current live `ramoops_region/status=disabled`
   before any live flash. Stock DTBO restore requires either
   `--restore-dtbo-from-android --ack S22PLUS-RAMOOPS-RESTORE-STOCK-DTBO` or
   `--restore-dtbo-from-download --ack S22PLUS-RAMOOPS-RESTORE-STOCK-DTBO`.
   This exception explicitly has no boot candidate and does not authorize writing
   or flashing boot, recovery, vendor_boot, vbmeta, vbmeta_system, BL, CP, CSC,
   super, userdata, persist, EFS, sec_efs, RPMB, keymaster, modem, bootloader,
   raw host `dd`, fastboot, Magisk modules, multidisabler, format data, M13/M15/
   M18/QMP candidates, additional DTBO candidates, kernel rebuilds, or any A90
   action.
   **Narrow operator-authorized exception (2026-07-08, S22+ ramoops DTBO + M13 positive-control only):**
   **Consumed/retired:** this exception was consumed by the 2026-07-08 live run.
   The patched DTBO enabled live `ramoops_region/status=okay`, and the M13 boot
   candidate was flashed, but the 120s observation saw no ACM/ADB/Odin rollback
   transport and the subsequent attended rollback found no M13 marker in pstore
   or last_kmsg. Boot rollback and stock DTBO restore completed, and the final
   dry-run reverified Android/root, Magisk boot baseline, stock DTBO hash, and
   live `ramoops_region/status=disabled`. This block no longer authorizes a
   default dry-run or live DTBO+M13 rerun. The consumed helper was
   `workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m13_capture_live_gate.py`.
   Before consumption, this exception allowed one bounded attended S22+ ramoops
   DTBO + M13 positive-control capture run on the Samsung S22+ `SM-S906N`/`g0q`
   `S906NKSS7FYG8`.
   The consumed exception authorized exactly two partition classes and no others:
   first flash the patched `dtbo` AP.tar.md5 SHA256
   `4f82663a7c2175a41760ec099c0f662dd04b8932a5ae82ba46b3ecb401a14a00`,
   require Android/root to return, require current DTBO SHA256
   `1c90b54577cbb42e029818a0c4248e85ec3a0e40903b0887648d6556355c85ab`,
   require live `ramoops_region/status=okay`, then flash the M13 boot
   positive-control AP.tar.md5 SHA256
   `5e959f0dd7c55d8e6a9363cde0c0fcc72876639bdc46ccdc826186cfc43134fa`.
   After the M13 observation window, restore the boot partition using the pinned
   Magisk boot rollback AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
   with stock boot fallback AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`,
   collect `pstore`, then restore stock DTBO using the pinned stock DTBO
   rollback AP.tar.md5 SHA256
   `6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa`.
   The stock raw DTBO SHA256 must be
   `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`,
   the M13 padded boot.img SHA256 must be
   `21808217d6cf698217e25cf35caf3a271a7f55451cad85ba576d54a40010441b`,
   the M13 base known-booting Magisk boot SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`,
   the M13 kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`,
   the M13 `/init` SHA256 must be
   `6b2d229217d83c7f36032c37291bebbebe7c8c5782d006fedcc538649d99f5d3`,
   and the M13 source SHA256 must be
   `4e3a88336c6a6e0b1ed6e25f572ed0ec26c2e8d177942598a6e32aa1b2a762e8`.
   The DTBO APs must contain exactly one tar member, `dtbo.img.lz4`; the M13,
   Magisk rollback, and stock boot fallback APs must contain exactly one tar
   member, `boot.img.lz4`. If M13 parks, exposes ACM, or no transport appears,
   rollback requires operator manual download-mode entry and the helper mode
   `--rollback-boot-from-download --ack S22PLUS-RAMOOPS-M13-ROLLBACK-BOOT-FROM-DOWNLOAD`.
   Stock DTBO restore requires either
   `--restore-dtbo-from-android --ack S22PLUS-RAMOOPS-RESTORE-STOCK-DTBO` or
   `--restore-dtbo-from-download --ack S22PLUS-RAMOOPS-RESTORE-STOCK-DTBO`.
   The capture goal is M13 positive-control `pstore` evidence with the live
   ramoops node enabled through DTBO. This path is the DTBO successor to the
   retired vendor_boot-only route: no vendor_boot write is authorized here.
   This exception does not authorize writing or flashing recovery, vendor_boot,
   vbmeta, vbmeta_system, BL, CP, CSC, super, userdata, persist, EFS, sec_efs,
   RPMB, keymaster, modem, bootloader, raw host `dd`, fastboot, Magisk modules,
   multidisabler, format data, M15/M18/QMP candidates, additional boot
   candidates, additional DTBO candidates, kernel rebuilds, or any A90 action.
   **Consumed/retired exception (2026-07-08, S22+ ramoops DTBO + M22
   sysrq-panic retained-console):** this one-shot attended gate was consumed by
   the 2026-07-08 live run. It flashed patched DTBO, verified live
   `ramoops_region/status=okay`, flashed the M22 sysrq-panic positive-control
   boot candidate, observed Download return after operator-attended bootloop,
   restored the Magisk boot baseline, collected pstore and retained last_kmsg,
   restored stock DTBO, and finished with Android/root on the Magisk boot
   baseline and live `ramoops_region/status=disabled`. No retained M22 marker
   appeared in pstore or last_kmsg, so this path is retired as a no-hit. The
   active live/rollback ack strings and M22-specific artifact/source/marker
   strings are intentionally not listed here; future M22 or retained-console
   work needs a fresh SHA-pinned exception and fresh operator approval. This
   retired block authorizes no boot, DTBO, vendor_boot, vbmeta, recovery, BL,
   CP, CSC, super, userdata, EFS/sec_efs, RPMB, keymaster, modem, bootloader,
   raw host `dd`, fastboot, Magisk module, kernel rebuild, or A90 action.
   **Narrow operator-authorized exception (2026-07-08, S22+ ramoops vendor_boot + M13 positive-control only):**
   **Consumed/retired:** this exception was consumed by the 2026-07-08 live run.
   The direct vendor_boot patch booted but live `ramoops_region/status` stayed
   `disabled` because stock DTBO overlays the node, so this block no longer
   authorizes a default dry-run or live `vendor_boot`+M13 attempt. The checked
   helper now rejects the retired default/live path before Android/device access;
   only explicit recovery modes for stock vendor_boot or boot rollback remain.
   The current positive-control route is the separate DTBO-enabled M13 gate.
   After the direct byte-preserving vendor_boot host build proved
   `changed_outside_allowed_count=0` and the gate source prepared the M13
   positive-control flow, Codex previously authorized one bounded attended S22+ ramoops
   vendor_boot + M13 positive-control capture run on the Samsung S22+
   `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_ramoops_vendor_boot_m13_capture_live_gate.py`
   and live ack token `S22PLUS-RAMOOPS-VENDORBOOT-M13-CAPTURE-LIVE-GATE`.
   This exception authorizes exactly two partition classes and no others:
   first flash the direct-patched `vendor_boot` AP.tar.md5 SHA256
   `0af250628c7cd5d7062b53823162f55716d1758d31ff88f65ea1c61dd0da83c3`,
   then, only after Android/root returns and the helper verifies live
   `/proc/device-tree/reserved-memory/ramoops_region/status=okay`, flash the
   known parking M13 boot candidate AP.tar.md5 SHA256
   `5e959f0dd7c55d8e6a9363cde0c0fcc72876639bdc46ccdc826186cfc43134fa`;
   after capture, restore the boot partition using the pinned Magisk boot
   rollback AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
   with stock boot fallback AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`,
   then restore stock vendor_boot using the pinned stock vendor_boot rollback
   AP.tar.md5 SHA256
   `2f9075fe609e7aa66c2ec88a2bd0223d6a9d7ff23d8bab0f7c4eb44633f480bb`.
   The patched vendor_boot image SHA256 must be
   `d62f2da241e1104db9e4b72aa0ba1927c0e85afd22fe380bff62c8df52bd3245`, the
   stock vendor_boot image SHA256 must be
   `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`,
   the source DTB SHA256 must be
   `2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e`, the
   patched DTB SHA256 must be
   `b862359dc65adb1eb9f5f17f1b8be637eb0135e88a681d779f9cbeda3ae5a3ec`, the
   M13 padded boot.img SHA256 must be
   `21808217d6cf698217e25cf35caf3a271a7f55451cad85ba576d54a40010441b`, the
   M13 base known-booting Magisk boot SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   M13 kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M13 `/init` SHA256 must be
   `6b2d229217d83c7f36032c37291bebbebe7c8c5782d006fedcc538649d99f5d3`, and
   the M13 source SHA256 must be
   `4e3a88336c6a6e0b1ed6e25f572ed0ec26c2e8d177942598a6e32aa1b2a762e8`.
   The vendor_boot APs must contain exactly one tar member,
   `vendor_boot.img.lz4`; the M13, Magisk rollback, and stock boot fallback
   APs must contain exactly one tar member, `boot.img.lz4`. The helper must
   verify all AP hashes and both manifests before live work, verify current
   Android root plus the current boot and stock vendor_boot hashes, flash
   patched vendor_boot first, require Android/root to return, verify live
   ramoops status is `okay`, then flash M13 for the M13 positive-control
   pstore capture. If M13 parks or no transport appears, boot rollback requires
   operator manual download-mode entry and the helper mode
   `--rollback-boot-from-download --ack S22PLUS-RAMOOPS-M13-ROLLBACK-BOOT-FROM-DOWNLOAD`.
   Stock vendor_boot restore requires either
   `--restore-vendor-boot-from-android --ack S22PLUS-RAMOOPS-RESTORE-STOCK-VENDOR-BOOT`
   or
   `--restore-vendor-boot-from-download --ack S22PLUS-RAMOOPS-RESTORE-STOCK-VENDOR-BOOT`.
   The capture goal is to read `pstore` / `/sys/fs/pstore` after the M13
   positive-control boot, then restore stock vendor_boot for a clean state. This
   exception does not authorize writing or flashing recovery, dtbo, vbmeta,
   vbmeta_system, BL, CP, CSC, super, userdata, persist, EFS, sec_efs, RPMB,
   keymaster, modem, bootloader, raw host `dd`, fastboot, Magisk modules,
   multidisabler, format data, M15/M18/QMP candidates, additional boot
   candidates, additional vendor_boot candidates, kernel rebuilds, or any A90
   action.
   **Narrow operator-authorized exception (2026-07-08, S22+ M19 C000
   dependency-closed checkpoint/download native-init boot-only):** after the
   M18 capture postmortem showed the same M18 image must not be repeated, the
   operator reported a bootloop/manual-download recovery, and the M19 host-only
   matrix produced a dependency-closed checkpoint set, Codex may prepare and
   perform one bounded attended boot-partition-only C000 live gate on the same
   Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m19_c000_checkpoint_live_gate.py`
   with live ack token `S22PLUS-M19-C000-CHECKPOINT-LIVE-GATE` and rollback-only
   ack token `S22PLUS-M19-C000-ROLLBACK-FROM-DOWNLOAD`. The exact candidate
   AP.tar.md5 SHA256 must be
   `d712840f1aa7d4ef9d07a7be404b29e5f5dd8065701db7f3d39d76c71296b9d4`, the
   contained padded `boot.img` SHA256 must be
   `0ae71d30257dafdc453db252bd77b11b554202f27c458e3b538d13c61df98ebb`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M19 C000 `/init` SHA256 must be
   `7d4f7c8fb30af6aa1e21fe1fe6b24a6597c7385424f5d90e3bf6309a68441135`, the
   M19 closed module-list SHA256 must be
   `c92bb69fd5605cba0ff0aafa44a1ee9f3ac0a66f7e3f1390a19363760e04c94f`, and
   the M19 source SHA256 must be
   `4c83607d102006b045c32edb0dbb58b1ff14822febc01e8a9da281561522e9af`.
   The AP must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M19 C000 candidate may only run as direct PID1 with a freestanding raw-syscall
   runtime, mount only runtime virtual filesystems, read the boot ramdisk
   `s22plus_m19_closed_usb.modules` text file, skip all module loads
   (`prefix_count=0`, `modules_prefix_skipped`), emit
   `S22_NATIVE_INIT_M19_CLOSED_CHECKPOINT`, and then request Samsung download
   mode as a checkpoint-download proof; observation model is host-observed
   self-download means checkpoint reached. It must use no ACM, no configfs, no
   USB role force, no vendor module binary injection, no persistent partition
   mount, no block-device write, no Android/Magisk handoff, no Magisk module
   install, no format data, and no watchdog touch. Success is only
   host-observed self-download after the original Odin endpoint disconnects; no
   later endpoint or bootloop requires operator manual download-mode rollback
   through the same helper's `--rollback-from-download --ack
   S22PLUS-M19-C000-ROLLBACK-FROM-DOWNLOAD` mode, using the exact Magisk
   boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. This exception authorizes only
   C000 from the M19 matrix and does not authorize C129/C135/C137/C140/C144/
   C145/C147/C150, USB/ACM bring-up, display/distro candidates, kernel rebuild,
   recovery/vendor_boot/vbmeta/non-boot flash, raw host `dd`, fastboot,
   multidisabler, format data, or any A90 action.
   **Narrow operator-authorized exception (2026-07-08, S22+ M20A raw-reboot
   floor-split native-init boot-only):** after the M19 C000 live result was
   operator-corrected to bootloop/manual-download/no automatic checkpoint proof,
   and after the M20 host-only floor split built `M20A_RAW`/`M20B_MINFS`/
   `M20C_KMSG` with all variants still `live_flash_authorized=false`, Codex may
   prepare and perform one bounded attended boot-partition-only M20A live gate
   on the same Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked
   helper `workspace/public/src/scripts/revalidation/s22plus_m20a_raw_reboot_live_gate.py`
   with live ack token `S22PLUS-M20A-RAW-REBOOT-LIVE-GATE` and rollback-only
   ack token `S22PLUS-M20A-ROLLBACK-FROM-DOWNLOAD`. The exact candidate
   AP.tar.md5 SHA256 must be
   `795e071107fdd7011a5acdc48ca7415273e5f2a3e19af45386702617292021fc`, the
   contained padded `boot.img` SHA256 must be
   `4fada63c986abc774e2a41eebc590f0635f1f1dcc8a207baa8d02cbfeb20eeb5`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c29967e`, the preserved Magisk-patched
   kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M20A `/init` SHA256 must be
   `4b27b050b11a4f0f28f340172515a397f65e1d151507e149bc9cbe47c6beab17`, and the
   M20A source SHA256 must be
   `ffce971408433acfb9bebb5bef236dab572fc8266d53a6c09e68419039f4abf1`.
   The AP must contain exactly one tar member, `boot.img.lz4`, with no recovery,
   vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super, persist,
   userdata, EFS, RPMB, keymaster, modem, or any other partition payload. The
   M20A_RAW candidate may only run as direct PID1 raw assembly with no libc
   startup, no fs setup, no marker write, no module loading, no configfs, no USB
   role force, no persistent partition mount, no block-device write, no
   Android/Magisk handoff, no Magisk module install, no format data, and no
   watchdog touch. Its first runtime action must be the first-action raw
   `reboot(..., "download")` positive control, and if that syscall returns it
   must only park forever. Success is only host-observed self-download after the
   original Odin endpoint disconnects; no later endpoint or bootloop requires
   operator manual download-mode rollback through the same helper's
   `--rollback-from-download --ack S22PLUS-M20A-ROLLBACK-FROM-DOWNLOAD` mode,
   using the exact Magisk boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. M20B/M20C not authorized by this
   exception. This exception does not authorize M20B, M20C, M19 C129 or wider
   prefixes, USB/ACM bring-up, display/distro candidates, kernel rebuild,
   recovery/vendor_boot/vbmeta/non-boot flash, raw host `dd`, fastboot,
   multidisabler, format data, or any A90 action.
   **Retired unconsumed exception (2026-07-08, S22+ M21A raw
   nanosleep-download floor discriminator native-init boot-only):** the M21A
   floor-discriminator was prepared after the M20A manual-download ambiguity,
   but it was never the primary observability path after the later ramoops
   steer and P00 result. This historical unconsumed authorization is retired so
   it cannot be used accidentally. A later fresh M30/M21A exception may
   independently re-promote a new one-shot gate with fresh active ack tokens,
   but this retired block itself authorizes nothing, so
   `workspace/public/src/scripts/revalidation/s22plus_m21a_raw_nanosleep_download_live_gate.py`
   must fail closed unless that fresh exception is present and complete.
   Historical M21A build/preflight details remain in
   `docs/reports/S22PLUS_NATIVE_INIT_M21A_RAW_NANOSLEEP_DOWNLOAD_HOST_BUILD_2026-07-08.md`
   and
   `docs/reports/S22PLUS_NATIVE_INIT_M21A_RAW_NANOSLEEP_DOWNLOAD_LIVE_GATE_PREFLIGHT_2026-07-08.md`.
   This retired block does not authorize M21A, M20B, M20C, M19 C129 or wider
   prefixes, USB/ACM bring-up, display/distro candidates, kernel rebuild,
   recovery/vendor_boot/vbmeta/non-boot flash, raw host `dd`, fastboot,
   multidisabler, format data, or any A90 action.
   **Consumed/retired exception (2026-07-08, S22+ M23 DTS-exact
   QMP/DWC3 reset_summary capture native-init boot-only):** this one-shot
   exception was consumed by the 2026-07-08 live run. It flashed the pinned M23
   boot AP once, observed no M23 ACM/ADB and an operator manual Download-mode
   return, restored the pinned Magisk boot AP, and captured Samsung reset
   surfaces. It must not be reused for another M23 live flash under the same
   gate. Future native-init live flashes need a fresh, narrower exception for
   the selected artifact and observation path.
   Before consumption, after EUD was closed as TrustZone-gated, the M23 host
   build derived the narrow DTS-exact QMP/DWC3/HS-PHY/provider closure, and the
   reset-summary gate source passed offline/fail-closed validation, Codex could
   prepare and perform one bounded attended boot-partition-only M23 live gate on
   the same Samsung S22+
   `SM-S906N`/`g0q` `S906NKSS7FYG8` using the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m23_dts_exact_qmp_reset_summary_live_gate.py`
   with now-consumed live/rollback ack tokens. The
   exact candidate AP.tar.md5 SHA256 must be
   `558eddb4b78b68c86d65f171072145c63210e9b33b5d0b56f2a3e4a00f0ba2d8`, the
   contained padded `boot.img` SHA256 must be
   `277bf33c0f7cc62fe2b635b83c22b052d35a4e97dfb2e1cadaf60fdcb961184e`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M23 `/init` SHA256 must be
   `745131e23a657905542697cc1c0573a87e484df2e9a06810344d8d4d0be6f357`, the
   M23 `s22plus_m23_dts_exact_qmp.modules` module-list SHA256 must be
   `a542b86aee8d2b09d0ca233e0a81d7deb8919a77657122d91f3b46e0a7933349`, the
   generated source SHA256 must be
   `75610dbd2148017708300aaf5c37b169d12a6a87ec30ed5d96e753708654c9c0`, and
   the stock vendor DTB SHA256 used for derivation must be
   `2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e`.
   The AP must contain exactly one tar member, `boot.img.lz4`, with no
   recovery, vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super,
   persist, userdata, EFS, RPMB, keymaster, modem, or any other partition
   payload. The M23 candidate may only run as direct PID1 with a freestanding
   raw-syscall runtime, load the 43-module DTS-derived QMP/DWC3/HS-PHY/provider
   closure (`module_group=dts_exact_qmp`, `module_count=43`) from
   `s22plus_m23_dts_exact_qmp.modules`, attempt `ss_acm.0` on `a600000.dwc3`,
   force USB role to device if available, and park for bounded host observation.
   It has no reboot beacon and no arm64 reboot syscall path. EUD extcon
   excluded; no EUD sysfs write; no EUD enable/open. Exact module list:
   `clk-rpmh.ko`, `gcc-waipio.ko`, `icc-rpmh.ko`,
   `qcom_ipc_logging.ko`, `rpmh-regulator.ko`, `clk-dummy.ko`,
   `clk-qcom.ko`, `cmd-db.ko`, `debug-regulator.ko`,
   `gdsc-regulator.ko`, `icc-bcm-voter.ko`, `icc-debug.ko`,
   `iommu-logger.ko`, `pinctrl-waipio.ko`, `qnoc-waipio.ko`,
   `phy-generic.ko`, `pinctrl-msm.ko`, `proxy-consumer.ko`,
   `qcom_iommu_util.ko`, `qcom_rpmh.ko`, `qcom-scm.ko`, `qnoc-qos.ko`,
   `sec_class.ko`, `secure_buffer.ko`, `smem.ko`, `socinfo.ko`,
   `arm_smmu.ko`, `phy-msm-ssusb-qmp.ko`, `phy-msm-snps-hs.ko`,
   `phy-msm-snps-eusb2.ko`, `dwc3-msm.ko`, `usb_f_ss_mon_gadget.ko`,
   `usb_f_ss_acm.ko`, `repeater.ko`, `redriver.ko`,
   `usb_notify_layer.ko`, `switch_class.ko`, `common_muic.ko`,
   `vbus_notifier.ko`, `usb_typec_manager.ko`, `if_cb_manager.ko`,
   `pdic_notifier_module.ko`, and `qc_usb_audio.ko`. If M23 loops, exposes ACM
   without rollback transport, or no transport appears, use operator manual
   Download-mode rollback through the same helper's rollback-from-download mode,
   using the exact
   Magisk boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. After rollback, run
   reset_summary/reset_klog post-rollback capture including
   `/proc/reset_summary`, `/proc/reset_klog`, `/proc/reset_history`,
   `/proc/reset_tzlog`, and `/proc/enhanced_boot_stat`. This exception does not
   authorize M21A, M20B, M20C, M19 C129 or wider prefixes, EUD writes, broad
   module permutation, display/distro candidates, kernel rebuild,
   recovery/vendor_boot/vbmeta/non-boot flash, raw host `dd`, fastboot,
   multidisabler, format data, or any A90 action.
   **Consumed/retired exception (2026-07-08, S22+ M24 pmsg-step
   DTS-exact QMP/DWC3 native-init boot-only):** this one-shot exception was
   consumed by the 2026-07-08 live run. It flashed the pinned M24 boot AP once,
   observed no M24 ACM/ADB and an operator manual Download-mode return,
   restored the pinned Magisk boot AP, and captured pmsg/pstore/last_kmsg/reset
   surfaces. No `A90_STEP:M24:` pmsg marker was retained, so this exact M24 path
   is retired as a no-hit. It must not be reused for another M24 live flash
   under the same gate. Future native-init live flashes need a fresh, narrower
   exception for the selected artifact and observation path.
   Before consumption, after the M23 reset-summary live result consumed the M23
   gate and captured no useful reset-summary payload, and after the M24 host
   build plus live-gate source passed offline/fail-closed validation, Codex
   could prepare and perform one bounded attended boot-partition-only M24 live
   gate on the same Samsung S22+
   `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m24_pmsg_steps_live_gate.py`
   with now-consumed live/rollback ack tokens. The exact candidate
   AP.tar.md5 SHA256 must be
   `e09538024abe89585486d54856a5c86bef666da456f314084d4d4d8bb6553fe8`, the
   contained padded `boot.img` SHA256 must be
   `0cccc003687227c4265081fa59d440f4be3e7f40fbb64aca2a3930ca7d5ca3df`, the
   known-booting Magisk boot base SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   preserved Magisk-patched kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, the
   M24 `/init` SHA256 must be
   `4086d18f453980893fa1b8022f93991775b0ee28a6088f1216de82b74cbaf341`, the
   M24 `s22plus_m24_pmsg_steps.modules` module-list SHA256 must be
   `a542b86aee8d2b09d0ca233e0a81d7deb8919a77657122d91f3b46e0a7933349`, the
   generated source SHA256 must be
   `f9a060f7804571c036631c954b3e88c064aa33176d7d8ec6abe9da8b8bf84bdd`, and
   the stock vendor DTB SHA256 used for derivation must be
   `2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e`.
   The AP must contain exactly one tar member, `boot.img.lz4`, with no
   recovery, vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super,
   persist, userdata, EFS, RPMB, keymaster, modem, or any other partition
   payload. The M24 candidate may only run as direct PID1 with a freestanding
   raw-syscall runtime, load the same 43-module DTS-derived
   QMP/DWC3/HS-PHY/provider closure (`module_group=dts_exact_qmp`,
   `module_count=43`) from `s22plus_m24_pmsg_steps.modules`, write pmsg step
   markers to `/dev/pmsg0` using `A90_STEP:M24:`, create only the fallback pmsg
   char-node metadata represented by `fallback_pmsg_major=507`, emit
   `module_prepare` and `module_finit` markers around each module insertion
   attempt, attempt `ss_acm.0` on `a600000.dwc3`, force USB role to device if
   available, and park for bounded host observation. It has no reboot beacon
   and no arm64 reboot syscall path. EUD extcon excluded; no EUD sysfs write;
   no EUD enable/open. Exact module list: `clk-rpmh.ko`, `gcc-waipio.ko`,
   `icc-rpmh.ko`, `qcom_ipc_logging.ko`, `rpmh-regulator.ko`,
   `clk-dummy.ko`, `clk-qcom.ko`, `cmd-db.ko`, `debug-regulator.ko`,
   `gdsc-regulator.ko`, `icc-bcm-voter.ko`, `icc-debug.ko`,
   `iommu-logger.ko`, `pinctrl-waipio.ko`, `qnoc-waipio.ko`,
   `phy-generic.ko`, `pinctrl-msm.ko`, `proxy-consumer.ko`,
   `qcom_iommu_util.ko`, `qcom_rpmh.ko`, `qcom-scm.ko`, `qnoc-qos.ko`,
   `sec_class.ko`, `secure_buffer.ko`, `smem.ko`, `socinfo.ko`,
   `arm_smmu.ko`, `phy-msm-ssusb-qmp.ko`, `phy-msm-snps-hs.ko`,
   `phy-msm-snps-eusb2.ko`, `dwc3-msm.ko`, `usb_f_ss_mon_gadget.ko`,
   `usb_f_ss_acm.ko`, `repeater.ko`, `redriver.ko`,
   `usb_notify_layer.ko`, `switch_class.ko`, `common_muic.ko`,
   `vbus_notifier.ko`, `usb_typec_manager.ko`, `if_cb_manager.ko`,
   `pdic_notifier_module.ko`, and `qc_usb_audio.ko`. If M24 loops, exposes ACM
   without rollback transport, or no transport appears, use operator manual
   Download-mode rollback through the same helper's rollback-from-download mode,
   using the exact Magisk boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   or the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if the
   operator explicitly selects stock rollback. After rollback, run
   pmsg/pstore/last_kmsg/reset-context post-rollback capture including
   `/proc/reset_summary`, `/proc/reset_klog`, `/proc/reset_history`,
   `/proc/reset_tzlog`, and `/proc/enhanced_boot_stat`. This retired exception
   does not authorize M24 repeat, M23 repeat, M21A, M20B, M20C, M19 C129 or
   wider prefixes, EUD writes, broad module permutation, display/distro
   candidates, kernel rebuild, recovery/vendor_boot/vbmeta/non-boot flash, raw
   host `dd`, fastboot, multidisabler, format data, or any A90 action.
   **Consumed exception (2026-07-08, S22+ M25 HS-only USB2 ACM native-init
   boot+DTBO):** this one-shot exception was consumed by the 2026-07-08 live
   run. It flashed the pinned M25 DTBO high-speed cap AP, verified patched
   DTBO after Android/Magisk returned, flashed the pinned M25 boot AP, observed
   no ACM and an Odin/Download return at the bounded observation step, flashed
   the pinned Magisk boot rollback AP, then restored stock DTBO with the pinned
   stock-DTBO AP. Final Android/Magisk baseline hashes matched boot
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, dtbo
   `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`, and
   vendor_boot
   `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`. It must
   not be reused for another M25 live flash under the same gate. Future S22+
   native-init live flashes need a fresh, narrower exception for the selected
   candidate and rollback path.
   Before consumption, after the M24 pmsg-step path was consumed and retired as
   a no-hit, and after the M25 host build plus live-gate source passed
   offline/fail-closed validation, Codex could prepare and perform one bounded
   attended S22+ M25 HS-only USB2 ACM native-init boot+DTBO live gate on the
   same Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked
   helper
   `workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py`
   with live ack token `S22PLUS-M25-HS-ONLY-USB2-ACM-LIVE-GATE`, rollback ack
   token `S22PLUS-M25-HS-ONLY-ROLLBACK-FROM-DOWNLOAD`, and stock-DTBO restore
   ack token `S22PLUS-M25-RESTORE-STOCK-DTBO`. The exact M25 boot AP.tar.md5
   SHA256 must be
   `7f89cfb8ff188190d1d161aee97e3edec2730bfc46efca9df37f2035f7206805`, the
   contained `boot.img` SHA256 must be
   `0ace02ff82be1cb7473879ff52f1c9e8d1491edaa3d9a88b829f901b2c86559f`, the
   M25 `/init` SHA256 must be
   `cc03d95f06b851717d3ccb4fc32fbecac3adfe7109c1a68454f846e3014ecf75`, the
   M25 `s22plus_m25_hs_only_usb2.modules` module-list SHA256 must be
   `00607484b7b777ee5cb54d7657f0cb554b9b66c42fec0e414d0544c0735d6496`, the
   generated source SHA256 must be
   `22350e7de748cf3a2f47236ef984bb224df58ffa7664ced811151c9db189562f`, and
   the stock vendor DTB SHA256 used for derivation must be
   `2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e`. The
   exact M25 DTBO high-speed cap AP.tar.md5 SHA256 must be
   `35afd774444066fd8e2ffe831da11dd73ee47dce3bdd5b1e37675f82344e56b6`, the
   patched raw DTBO SHA256 must be
   `8962cbbded722c85dbdebfbdc2eba5476b9a64e2a2933888b81f947159eddc17`, the
   stock DTBO rollback AP SHA256 must be
   `6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa`, the
   known Magisk boot baseline SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, and the
   stock DTBO raw SHA256 must be
   `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`.
   The M25 boot AP must contain exactly one tar member, `boot.img.lz4`, with no
   recovery, vendor_boot, vbmeta, vbmeta_system, DTBO, BL, CP, CSC, super,
   persist, userdata, EFS, RPMB, keymaster, modem, or any other partition
   payload. The M25 DTBO AP and stock DTBO rollback AP must each contain
   exactly one `dtbo.img.lz4` member, with no boot, recovery, vendor_boot,
   vbmeta, vbmeta_system, BL, CP, CSC, super, persist, userdata, EFS, RPMB,
   keymaster, modem, or any other partition payload.
   The live path is two-stage: first flash exactly the pinned DTBO high-speed
   cap through Odin4, wait for Android/Magisk root to return, and verify the
   patched DTBO hash; only then flash exactly the pinned M25 boot-only AP. M25
   first applies the DTBO high-speed cap by changing equal-length
   `super-speed` maximum-speed values to `high-speed` across all 11 DTBO
   overlay blobs, then runs a direct PID1 freestanding raw-syscall `/init`
   replacement based on the known booting Magisk boot. It uses
   `module_group=hs_only_usb2`, `module_count=40`, and
   `s22plus_m25_hs_only_usb2.modules`, creates only the USB2 HighSpeed ACM path,
   attempts `ss_acm.0` on `a600000.dwc3 only`, forces `bcdUSB=0x0200`, and
   parks for bounded host observation. `phy-msm-ssusb-qmp.ko intentionally
   excluded`; EUD extcon excluded; no EUD sysfs write; no EUD enable/open; no
   QMP/USB3 module loading; no reboot beacon; no arm64 reboot syscall path.
   Exact module list: `clk-rpmh.ko`, `gcc-waipio.ko`, `icc-rpmh.ko`,
   `qcom_ipc_logging.ko`, `rpmh-regulator.ko`, `clk-dummy.ko`, `clk-qcom.ko`,
   `cmd-db.ko`, `debug-regulator.ko`, `gdsc-regulator.ko`,
   `icc-bcm-voter.ko`, `icc-debug.ko`, `iommu-logger.ko`, `qnoc-waipio.ko`,
   `phy-generic.ko`, `proxy-consumer.ko`, `qcom_iommu_util.ko`,
   `qcom_rpmh.ko`, `qcom-scm.ko`, `qnoc-qos.ko`, `sec_class.ko`,
   `secure_buffer.ko`, `smem.ko`, `socinfo.ko`, `arm_smmu.ko`,
   `phy-msm-snps-hs.ko`, `phy-msm-snps-eusb2.ko`, `dwc3-msm.ko`,
   `usb_f_ss_mon_gadget.ko`, `usb_f_ss_acm.ko`, `repeater.ko`, `redriver.ko`,
   `usb_notify_layer.ko`, `switch_class.ko`, `common_muic.ko`,
   `vbus_notifier.ko`, `usb_typec_manager.ko`, `if_cb_manager.ko`,
   `pdic_notifier_module.ko`, and `qc_usb_audio.ko`.
   If M25 loops, exposes ACM without rollback transport, or no rollback
   transport appears, stop and require operator manual download-mode rollback
   through the same helper's `--rollback-from-download` mode. Rollback must use
   the pinned Magisk boot rollback first and then stock DTBO rollback; if the
   DTBO-only step fails before boot candidate flash, use only the stock DTBO
   rollback path. This exception does not authorize M25 repeat, M24 repeat,
   M23 repeat, broad module permutation, display/distro candidates, kernel
   rebuild, recovery/vendor_boot/vbmeta/non-boot/non-DTBO flash other than the
   exact pinned stock-DTBO/M25-DTBO APs above, raw host `dd`, fastboot,
   multidisabler, format data, or any A90 action.
   **Consumed exception (2026-07-09 KST / 2026-07-08 UTC, S22+ M29
   first-rollback retained-log capture boot+DTBO):** this one-shot exception
   was consumed by the 2026-07-09 KST live run. It flashed the pinned M25 DTBO
   high-speed cap AP, captured a pre-candidate retained-log baseline, flashed
   the existing M28 dependency-complete `S24` boot candidate, and then observed
   no clean candidate self-download proof: host polling saw no ADB and no Odin
   for the bounded observation window, the helper logged
   `m29_S24_self_download_seen=0` and
   `m29_S24_result=no-self-download-manual-download-required`, and the operator
   reported bootloop observation plus manual Download-mode entry. This is
   **manual-download contaminated / not a clean self-download proof**.
   Codex then used the checked M29 rollback-from-download mode, flashed the
   pinned Magisk boot rollback AP, collected the first post-M29 rollback
   retained surfaces before stock-DTBO restore, restored stock DTBO, and
   verified the final Android/Magisk baseline. First-capture evidence was
   still not the native candidate: pstore was empty, `/proc/last_kmsg` was
   2,097,136 bytes with SHA256
   `5306bb56ddd5f73f75921dea18c17fa5b07fffba30262b858647e27c302704da`,
   `m29_marker_count=0`, `s22_native_count=0`,
   `android_really_probe_count=49`, `android_reboot_download_count=1`,
   `watchdog_count=30`, `kernel_panic_count=0`, and
   `unknown_symbol_count=0`. Reset surfaces reported NPON /
   `reboot,download` and no retained native marker. Final baseline was
   verified independently: boot
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, dtbo
   `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`, and
   vendor_boot
   `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`.
   This exception must not be reused for M29 repeat, M28 repeat, S24 repeat,
   or F43. Future S22+ native-init live flashes need a fresh, narrower
   exception for the selected candidate and observation path. The now-consumed
   live, rollback, and stock-DTBO ack token strings are intentionally omitted
   here as active authorization. Before consumption, this exception allowed one
   bounded attended first-rollback collection-timing gate on the same Samsung
   S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using only
   `workspace/public/src/scripts/revalidation/s22plus_m29_first_rollback_capture_live_gate.py`
   SHA256
   `d8da7792f9ccc60a16358984636b29a3df27fac6b264f039354ea54770a18bb3`;
   it was limited to `S24 only`, `F43 remains unauthorized`, the existing S24
   AP SHA256
   `c684f6a21bcc9aa50b066b447f4356958fe6d7bfed93edf0ac1b7dcaae8ce75f`, boot
   image SHA256
   `a1459931001bfd6e17593dd329fc682f00ab61f4841b6543791f5349dd012cd0`, `/init`
   SHA256 `5c04a2023b2b56ef98746da6f7168121b62d7859cee81c756b80d1a382c1964e`,
   source marker `S22_NATIVE_INIT_M28_DEP_COMPLETE_DOWNLOAD`, source SHA256
   `0c029dd3de42074c3c942efa23266fb383522750d1ffd9d826c67898db6bde6c`, module
   count `26`, module-list SHA256
   `8c605e2c69aad74f80191bdbc1843b002539d22d49bcffa86bb85bbcb343e5e4`,
   stock `modules.dep` SHA256
   `21eae389f1d8b0a9fc93cec0b12d36e736cfac656d91ae55055c793f2ed67b27`,
   reincluded suppliers `sec_debug.ko` and `minidump.ko`, M25 DTBO AP SHA256
   `35afd774444066fd8e2ffe831da11dd73ee47dce3bdd5b1e37675f82344e56b6`,
   patched raw DTBO SHA256
   `8962cbbded722c85dbdebfbdc2eba5476b9a64e2a2933888b81f947159eddc17`,
   stock-DTBO rollback AP SHA256
   `6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa`,
   Magisk boot rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`, stock
   boot fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`,
   `pre-candidate retained-log baseline capture`, `first rollback boot capture
   before stock DTBO rollback`, `/proc/last_kmsg`, `/proc/reset_summary`,
   `/proc/reset_klog`, `/proc/reset_history`, `/proc/reset_tzlog`,
   `compare pre-candidate and first-rollback last_kmsg sha256`, `Magisk boot
   rollback`, `stock DTBO rollback after first capture`, and `manual Download
   contamination`.
   **Consumed exception (2026-07-08, S22+ M28 dependency-complete
   native-init boot+DTBO batch):** this one-shot exception was consumed by the
   2026-07-08 S24 live run. It flashed the pinned M25 DTBO high-speed cap AP,
   verified patched DTBO, flashed M28 `S24`, and the operator reported
   bootloop observation plus manual Download-mode entry. The helper then saw
   Odin at `m28_S24_self_download_033` and logged
   `m28_S24_result=self-download`, but that is operator-corrected to
   **manual-download contaminated / not a clean self-download proof**. The
   helper flashed the pinned Magisk boot rollback AP, Android/Magisk returned,
   and it restored stock DTBO with the pinned stock-DTBO AP. Final
   Android/Magisk baseline was verified: boot
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, dtbo
   `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`, and
   vendor_boot
   `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`.
   This exception must not be reused for M28 repeat or F43. Future S22+
   native-init live flashes need a fresh, narrower exception for the selected
   candidate and rollback path. The now-consumed live/rollback/stock-DTBO ack
   token strings are intentionally omitted here as active authorization.
   Before consumption, after the M27 prefix-narrow result was corrected to
   manual Download contamination and the stock FYG8 `modules.dep` audit proved
   the prior M25/M26/M27 module closure dependency-incomplete, Codex could
   perform one bounded attended M28 dependency-complete batch on the same
   Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m28_dep_complete_live_gate.py`
   SHA256
   `83521d521c55ceda8c860a940f8eb334e66638561b785231c5a5b007ad791d3b`.
   M28 dependency-complete live batch was limited to S24/F43, had to run S24
   first, had to stop on first no-hit, and could not run F43 if S24 failed or
   required manual Download. The exact S24 AP SHA256 was
   `c684f6a21bcc9aa50b066b447f4356958fe6d7bfed93edf0ac1b7dcaae8ce75f`, boot
   image SHA256 was
   `a1459931001bfd6e17593dd329fc682f00ab61f4841b6543791f5349dd012cd0`, and
   `/init` SHA256 was
   `5c04a2023b2b56ef98746da6f7168121b62d7859cee81c756b80d1a382c1964e`.
   The unrun F43 candidate remains unauthorized after this consumed result.
   **Consumed exception (2026-07-08, S22+ M27 HS prefix-narrow native-init
   boot+DTBO batch):** this one-shot exception was consumed by the 2026-07-08
   live run. It flashed the pinned M25 DTBO high-speed cap AP and then flashed
   M27 `P08`. Host observation showed no ADB/Odin for samples 001-036 after
   the candidate, and the operator reported bootloop observation plus manual
   Download-mode entry. The helper then saw Odin at sample 037 and logged
   `m27_P08_result=self-download`, but that is operator-corrected to
   **manual-download contaminated / not a clean self-download proof**. Codex
   interrupted before any later prefix, the helper had already flashed the
   pinned Magisk boot rollback AP, Android returned, and Codex then restored
   stock DTBO with the pinned stock-DTBO AP. Final Android/Magisk baseline was
   verified: boot
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, dtbo
   `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`, and
   vendor_boot
   `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`.
   This exception must not be reused for M27 repeat or additional prefixes.
   Future S22+ native-init live flashes need a fresh, narrower exception for
   the selected candidate and rollback path.
   Before consumption, after the M27 host build and live-gate source pass
   proved the exact prefix-narrow matrix between M26 `P00` hit and `P24`
   no-hit, Codex could perform one bounded attended M27 prefix-narrow batch on
   the same Samsung S22+ `SM-S906N`/`g0q`
   `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m27_hs_prefix_narrow_live_gate.py`
   with live ack token `S22PLUS-M27-HS-PREFIX-NARROW-LIVE-GATE`, rollback ack
   token `S22PLUS-M27-HS-PREFIX-ROLLBACK-FROM-DOWNLOAD`, and stock-DTBO restore
   ack token `S22PLUS-M27-RESTORE-STOCK-DTBO`. M27 prefix-narrow live batch is
   limited to P08/P12/P16/P20/P22/P23/P24; P00, P25+, broader module
   permutation, and repeated M27 batches require a fresh exception. The helper
   must stop on first no-hit before trying any later prefix.
   The exact M25 DTBO high-speed cap AP.tar.md5 SHA256 must be
   `35afd774444066fd8e2ffe831da11dd73ee47dce3bdd5b1e37675f82344e56b6`, the
   patched raw DTBO SHA256 must be
   `8962cbbded722c85dbdebfbdc2eba5476b9a64e2a2933888b81f947159eddc17`, the
   stock DTBO rollback AP SHA256 must be
   `6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa`, the
   known Magisk boot baseline SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   stock DTBO raw SHA256 must be
   `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`, the
   stock vendor_boot SHA256 must be
   `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`, the
   Magisk boot rollback AP SHA256 must be
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`, and
   the stock boot fallback AP SHA256 must be
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`.
   The M27 generated source SHA256 must be
   `44b3111652cbd64561f4b5eee5413864df44422e28f905ce6dc42aa618f951cd`, the
   marker must be `S22_NATIVE_INIT_M27_HS_PREFIX_DOWNLOAD`, the ramdisk
   module-list file must be `s22plus_m27_hs_only_usb2.modules`, and the
   inherited M25 HS-only module list SHA256 must be
   `00607484b7b777ee5cb54d7657f0cb554b9b66c42fec0e414d0544c0735d6496`.
   Exact M27 candidates:
   P08 count `8`, next `debug-regulator.ko`, AP SHA256
   `60669383e0345dfc5b7f50393ad6aebd3c67307ba32bc107c69eb324d67f499a`,
   boot.img SHA256
   `0ab2daa950bde5932f5651b90e7b32f2a102ccb97fe327fb25698c03c89113ca`, and
   `/init` SHA256
   `7640cd759c1ebfa9c8470a4d1456af9ea81a6415681c8a9715e6963ac3f0cabf`;
   P12 count `12`, next `iommu-logger.ko`, AP SHA256
   `3e0d65386966fb351a108f0c1e03dfdf695d365717e42552e970cfdab16af7ab`,
   boot.img SHA256
   `02cdc8b95209559618e7e2da0caa6124d24b9f25d5d5b41fe3dce2fa4294a9a3`, and
   `/init` SHA256
   `5add362c7479be1435fdb5d0eb9a88d5e7a6e70f202dbaae406eb76953835ace`;
   P16 count `16`, next `qcom_iommu_util.ko`, AP SHA256
   `32b132e30c8f009e161ae0c71a64ed90d4b1ac1560302a17ef1309b03100f61f`,
   boot.img SHA256
   `730b32b44daf3a8c958fda7094ed1b3ac07d00ea116d768a362fabce043bb8bf`, and
   `/init` SHA256
   `7c068bada632fc441d81843e3c70e9743b9e10e4ee3114847cb69051cda1421d`;
   P20 count `20`, next `sec_class.ko`, AP SHA256
   `d4669c932312d2f84ce5982bc2df81a4903c23e7f6fae19bff4129aaba56afba`,
   boot.img SHA256
   `5d2a0faee48bb105fa5c0167daabd8447962896bda646ddcfb9781c8e83be008`, and
   `/init` SHA256
   `01f88c744d59790991a98e74cec9550803c656c28e29c8daeb51dbe5baafc2b0`;
   P22 count `22`, next `smem.ko`, AP SHA256
   `1d7137f60d5743e0cb2145219e8806c6bc1b051a7d8a68749afe5b260cdf3643`,
   boot.img SHA256
   `813016d66fc1f47fda5d7f874563d26feae76f2e98a2eda7c3b8de1ea06973ea`, and
   `/init` SHA256
   `a8fdccb3dbe2bf88ecd9cecf72b008609376b76d74505b22bdb3499ba3cfa99a`;
   P23 count `23`, next `socinfo.ko`, AP SHA256
   `5bc8d767af7794bf7ece761b1d61d080e94b345e99be173556aece49ed40f8fb`,
   boot.img SHA256
   `901459a1f1caeaf0774262108fb728cd4bb05e27b0a61ae57dbdd7b0a2f57b4a`, and
   `/init` SHA256
   `a55243f1ff3bda8b8e82feb502a70714a90bdc159f340163c24ffcf24f06eaff`;
   P24 count `24`, next `arm_smmu.ko`, AP SHA256
   `fff7ecf3ff9233f76ac17f07ecf56a383696d6ecb06b67f84ef39d8f08876180`,
   boot.img SHA256
   `507dc385ac178b2b297cb35f0aeb83b65c81ef07ec2da89ebd51dca1de54c86b`, and
   `/init` SHA256
   `21c63aa298ac362e09eba15b63be20fe1d9c6bb82ef09297e172c5f32c0faa2a`.
   Each M27 boot AP must contain exactly one tar member, `boot.img.lz4`, with
   no recovery, vendor_boot, vbmeta, vbmeta_system, DTBO, BL, CP, CSC, super,
   persist, userdata, EFS, RPMB, keymaster, modem, or any other partition
   payload. The M25 DTBO AP and stock DTBO rollback AP must each contain
   exactly one `dtbo.img.lz4` member, with no boot, recovery, vendor_boot,
   vbmeta, vbmeta_system, BL, CP, CSC, super, persist, userdata, EFS, RPMB,
   keymaster, modem, or any other partition payload.
   The live path is: verify Android/Magisk baseline boot, stock DTBO, and
   vendor_boot; flash exactly the pinned DTBO high-speed cap; verify patched
   DTBO; for each authorized M27 prefix, flash exactly that boot AP, wait for
   the original Odin endpoint to disconnect, count only a later Odin endpoint
   as the candidate self-download proof, then immediately flash the pinned
   Magisk boot rollback before the next prefix. The DTBO high-speed cap may
   remain in place across successful M27 prefixes, but stock DTBO rollback is
   mandatory at session end. M27 is a direct PID1 freestanding raw-syscall
   `/init` replacement using `module_count=40`, `reboot_request=download`, and
   `maximum_speed_dtbo=high-speed`; it has no ACM, no configfs, no module
   binary injection, no EUD sysfs write, no persistent partition mount, no
   block-device write, no Android/Magisk handoff, and no recovery fallback
   inside the candidate.
   If any M27 prefix loops, fails to self-enter Download mode, or no rollback
   transport appears, stop and require operator manual download-mode rollback
   through the same helper's `--rollback-from-download` mode. Rollback must use
   the pinned Magisk boot rollback first and then stock DTBO rollback; if the
   DTBO-only step fails before a boot candidate flash, use only the stock DTBO
   rollback path. This exception does not authorize M27 repeat, P00/P25+ live,
   M26 repeat, M25 repeat, display/distro candidates, kernel rebuild,
   recovery/vendor_boot/vbmeta/non-boot/non-DTBO flash other than the exact
   pinned stock-DTBO/M25-DTBO APs above, raw host `dd`, fastboot,
   multidisabler, format data, or any A90 action.
   **Consumed exception (2026-07-08, S22+ M26 HS prefix-download native-init
   boot+DTBO batch):** this one-shot exception was consumed by the 2026-07-08
   live run. It flashed the pinned M25 DTBO high-speed cap AP, ran M26 `P00`
   and observed a later Odin endpoint proving P00 reached checkpoint
   `reboot(download)`, rolled back boot to the pinned Magisk AP, then ran M26
   `P24` and observed no self-download within the bounded window. The operator
   manually entered Download mode, Codex flashed the pinned Magisk boot rollback
   AP and stock DTBO rollback AP, and final Android/Magisk baseline hashes were
   verified manually with `toybox sha256sum`: boot
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, dtbo
   `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`, and
   vendor_boot
   `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`. The
   helper's final stock-DTBO verify exited false-negative because plain
   `sha256sum` produced no usable block-device output while `toybox sha256sum`
   worked; the shared partition-hash helper was changed to prefer toybox. This
   exception must not be reused for M26 repeat or additional prefixes. Future
   S22+ native-init live flashes need a fresh, narrower exception for the
   selected candidate and rollback path.
   Before consumption, after the M26 host build produced a host-only
   prefix/download discriminator matrix and the operator approved live
   progression, Codex could perform one bounded attended first-live M26 batch
   on the same Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the
   checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m26_hs_prefix_download_live_gate.py`
   with live ack token `S22PLUS-M26-HS-PREFIX-DOWNLOAD-LIVE-GATE`, rollback
   ack token `S22PLUS-M26-HS-PREFIX-ROLLBACK-FROM-DOWNLOAD`, and stock-DTBO
   restore ack token `S22PLUS-M26-RESTORE-STOCK-DTBO`. M26 first live batch is
   limited to P00/P24/P27/P30; P25, P28, P33, P40, broader module permutation,
   and repeated M26 batches require a fresh exception.
   The exact M25 DTBO high-speed cap AP.tar.md5 SHA256 must be
   `35afd774444066fd8e2ffe831da11dd73ee47dce3bdd5b1e37675f82344e56b6`, the
   patched raw DTBO SHA256 must be
   `8962cbbded722c85dbdebfbdc2eba5476b9a64e2a2933888b81f947159eddc17`, the
   stock DTBO rollback AP SHA256 must be
   `6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa`, the
   known Magisk boot baseline SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   stock DTBO raw SHA256 must be
   `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`, the
   stock vendor_boot SHA256 must be
   `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`, the
   Magisk boot rollback AP SHA256 must be
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`, and
   the stock boot fallback AP SHA256 must be
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`.
   The M26 generated source SHA256 must be
   `ba51ec4e8bded43b70d8ae40adafe8b2105aa07f57037457d094f9a1b6b187b7`, the
   marker must be `S22_NATIVE_INIT_M26_HS_PREFIX_DOWNLOAD`, the ramdisk
   module-list file must be `s22plus_m26_hs_only_usb2.modules`, and the
   inherited M25 HS-only module list SHA256 must be
   `00607484b7b777ee5cb54d7657f0cb554b9b66c42fec0e414d0544c0735d6496`.
   Exact M26 first-batch candidates:
   P00 count `0`, next `clk-rpmh.ko`, AP SHA256
   `1f8763c5f08461bb351f1b461898bf568652e292c79aef9e1f46fb9af4bbd79b`,
   boot.img SHA256
   `76a0f5a40dd67db051c60af8fee367594a8580840853b34b3b3e16fe3f47b707`, and
   `/init` SHA256
   `1bd912f2732a975d5ed91e442d4def661e515bed9c87d6bd313d22b898ca08fc`;
   P24 count `24`, next `arm_smmu.ko`, AP SHA256
   `7e9a3fafdbeeda8c92cfab9b4ae73d2c2b2a4821a48d537e6ba5e35b34018029`,
   boot.img SHA256
   `ff231f7fdb410a8fa3489cd63bc8d2f9f539dc823a4086f5917e75a1b24b7af8`, and
   `/init` SHA256
   `7e188e760040073ee28708a17e66b4c7b096f91f4f41319083ae51bf2b98f2da`;
   P27 count `27`, next `dwc3-msm.ko`, AP SHA256
   `19014f494444e3fce3127ac142bc30f622feb96bd08a1f2031e2f14a0a380341`,
   boot.img SHA256
   `38e819de865d0a979446d04521373343f53d3ab8bae461cbb05b94190d2873b3`, and
   `/init` SHA256
   `5289ef3bdb344fa09e8a18d0183b8d7d4ce5c98d4eb83fe0f68813d5bf444a22`;
   P30 count `30`, next `repeater.ko`, AP SHA256
   `a4510148c14652ffd87c8c0c6dd2ec1b127a36136ed1d28849bba04028ea8c9c`,
   boot.img SHA256
   `3f952b45b8d339112fe6c25acc94f83257c21520c370559a37ad1a80f1016990`, and
   `/init` SHA256
   `fc99836944f0ac3373b45e8dc0523bc475ecd77cb5661dff77fbaf885a32aedf`.
   Each M26 boot AP must contain exactly one tar member, `boot.img.lz4`, with
   no recovery, vendor_boot, vbmeta, vbmeta_system, DTBO, BL, CP, CSC, super,
   persist, userdata, EFS, RPMB, keymaster, modem, or any other partition
   payload. The M25 DTBO AP and stock DTBO rollback AP must each contain
   exactly one `dtbo.img.lz4` member, with no boot, recovery, vendor_boot,
   vbmeta, vbmeta_system, BL, CP, CSC, super, persist, userdata, EFS, RPMB,
   keymaster, modem, or any other partition payload.
   The live path is: verify Android/Magisk baseline boot, stock DTBO, and
   vendor_boot; flash exactly the pinned DTBO high-speed cap; verify patched
   DTBO; for each authorized M26 prefix, flash exactly that boot AP, wait for
   the original Odin endpoint to disconnect, count only a later Odin endpoint
   as the candidate self-download proof, then immediately flash the pinned
   Magisk boot rollback before the next prefix. The DTBO high-speed cap may
   remain in place across the M26 batch, but stock DTBO rollback is mandatory
   at session end. M26 is a direct PID1 freestanding raw-syscall `/init`
   replacement using `module_count=40`, `reboot_request=download`, and
   `maximum_speed_dtbo=high-speed`; it has no ACM, no configfs, no module
   binary injection, no EUD sysfs write, no persistent partition mount, no
   block-device write, no Android/Magisk handoff, and no recovery fallback
   inside the candidate.
   If any M26 prefix loops, fails to self-enter Download mode, or no rollback
   transport appears, stop and require operator manual download-mode rollback
   through the same helper's `--rollback-from-download` mode. Rollback must use
   the pinned Magisk boot rollback first and then stock DTBO rollback; if the
   DTBO-only step fails before a boot candidate flash, use only the stock DTBO
   rollback path. This exception does not authorize M26 repeat, P25/P28/P33/P40
   live, M25 repeat, display/distro candidates, kernel rebuild,
   recovery/vendor_boot/vbmeta/non-boot/non-DTBO flash other than the exact
   pinned stock-DTBO/M25-DTBO APs above, raw host `dd`, fastboot,
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
   **Narrow operator-authorized exception (2026-07-07, S22+ M4T3 raw-reboot
   native-init boot-only Odin path):** the S22+ M4T3 live gate above may use
   `/usr/bin/odin4 --reboot -a` through
   `workspace/public/src/scripts/revalidation/s22plus_m4t3_raw_reboot_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `f0a26bb95a091070713f8d736419cbe60974195bb59509cb1fd7cc28a0b1a907`, and
   the same helper may use `/usr/bin/odin4 --reboot -a` in
   `--rollback-from-download` mode with the exact single-member Magisk
   boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, or partition is
   authorized by this exception.
   **Narrow operator-authorized exception (2026-07-07, S22+ M5 USB-ACM
   native-init boot-only Odin path):** the S22+ M5 live gate above may use
   `/usr/bin/odin4 --reboot -a` through
   `workspace/public/src/scripts/revalidation/s22plus_m5_usb_acm_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `5bce15dede8bcd84b8ead1a7f6db6b09135d38637c983d06965930c40a00159f`, and
   the same helper may use `/usr/bin/odin4 --reboot -a` in
   `--rollback-from-download` mode with the exact single-member Magisk
   boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, or partition is
   authorized by this exception.
   **Narrow operator-authorized exception (2026-07-07, S22+ M5B mount-reboot
   native-init boot-only Odin path):** the S22+ M5B live gate above may use
   `/usr/bin/odin4 --reboot -a` through
   `workspace/public/src/scripts/revalidation/s22plus_m5b_mount_reboot_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `872de3ee417eebbe8f55c14d226eaefe5e06d5989ffe96176b1bb02994793a59`, and
   the same helper may use `/usr/bin/odin4 --reboot -a` in
   `--rollback-from-download` mode with the exact single-member Magisk
   boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, or partition is
   authorized by this exception.
   **Narrow operator-authorized exception (2026-07-07, S22+ M6 recovery-replay
   USB-ACM native-init boot-only Odin path):** the S22+ M6 live gate above may
   use `/usr/bin/odin4 --reboot -a` through
   `workspace/public/src/scripts/revalidation/s22plus_m6_recovery_replay_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `a12bd8f067375cb14ab9043da5bae37d1f93f82c1d70bccd8fa9cef2f616bee9`, and
   the same helper may use `/usr/bin/odin4 --reboot -a` in
   `--rollback-from-download` mode with the exact single-member Magisk
   boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, or partition is
   authorized by this exception.
   **Narrow operator-authorized exception (2026-07-07, S22+ M7 USB-subset
   USB-ACM native-init boot-only Odin path):** the S22+ M7 live gate above may
   use `/usr/bin/odin4 --reboot -a` through
   `workspace/public/src/scripts/revalidation/s22plus_m7_usb_subset_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `be0e1e34ec9452a14b7cfac66cc7ac57a0b29e92343945c35c1f836282563c4d`, and
   the same helper may use `/usr/bin/odin4 --reboot -a` in
   `--rollback-from-download` mode with the exact single-member Magisk
   boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, or partition is
   authorized by this exception.
   **Narrow operator-authorized exception (2026-07-07, S22+ M8 timed-download
   module-bisect native-init boot-only Odin path):** the S22+ M8 live gate above
   may use `/usr/bin/odin4 --reboot -a` through
   `workspace/public/src/scripts/revalidation/s22plus_m8_timed_download_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `59433518e7bea2d16f5efb62ee226c190f6a3af8673336310a2ef0fff7bee36b`, and
   the same helper may use `/usr/bin/odin4 --reboot -a` in
   `--rollback-from-download` mode with the exact single-member Magisk
   boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, or partition is
   authorized by this exception.
   **Narrow operator-authorized exception (2026-07-07, S22+ M8A minimal-fs
   timed-download native-init boot-only Odin path):** the S22+ M8A live gate
   above may use `/usr/bin/odin4 --reboot -a` through
   `workspace/public/src/scripts/revalidation/s22plus_m8a_minfs_download_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `c97d29e38fe3293ad145a7743b61ae5fddae8f1b028e619dcd56e2f640de3c19`, and
   the same helper may use `/usr/bin/odin4 --reboot -a` in
   `--rollback-from-download` mode with the exact single-member Magisk
   boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, or partition is
   authorized by this exception.
   **Narrow operator-authorized exception (2026-07-07, S22+ M9A C
   first-action reboot native-init boot-only Odin path):** the S22+ M9A live
   gate above may use `/usr/bin/odin4 --reboot -a` through
   `workspace/public/src/scripts/revalidation/s22plus_m9a_c_first_reboot_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `c953f74fe7e3cdc226ebd3e1f0bac2142ee39e14483d87022714ae98e336d6b1`, and
   the same helper may use `/usr/bin/odin4 --reboot -a` in
   `--rollback-from-download` mode with the exact single-member Magisk
   boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, or partition is
   authorized by this exception.
   **Narrow operator-authorized exception (2026-07-07, S22+ M10A mkdir-dev
   reboot native-init boot-only Odin path):** the S22+ M10A live gate above may
   use `/usr/bin/odin4 --reboot -a` through
   `workspace/public/src/scripts/revalidation/s22plus_m10a_mkdir_dev_reboot_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `d71c8c82d2703892802228dd61ded561a9b4f90c678db15452014f2477170105`, and
   the same helper may use `/usr/bin/odin4 --reboot -a` in
   `--rollback-from-download` mode with the exact single-member Magisk
   boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, or partition is
   authorized by this exception.
   **Narrow operator-authorized exception (2026-07-08, S22+ M19 C000
   checkpoint/download native-init boot-only Odin path):** the S22+ M19 C000
   live gate above may use `/usr/bin/odin4 --reboot -a` through
   `workspace/public/src/scripts/revalidation/s22plus_m19_c000_checkpoint_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `d712840f1aa7d4ef9d07a7be404b29e5f5dd8065701db7f3d39d76c71296b9d4`, and
   the same helper may use `/usr/bin/odin4 --reboot -a` in
   `--rollback-from-download` mode with the exact single-member Magisk
   boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, M19 prefix, or
   partition is authorized by this exception.
   **Narrow operator-authorized exception (2026-07-08, S22+ M20A raw-reboot
   floor-split native-init boot-only Odin path):** the S22+ M20A live gate
   above may use `/usr/bin/odin4 --reboot -a` through
   `workspace/public/src/scripts/revalidation/s22plus_m20a_raw_reboot_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `795e071107fdd7011a5acdc48ca7415273e5f2a3e19af45386702617292021fc`, and
   the same helper may use `/usr/bin/odin4 --reboot -a` in
   `--rollback-from-download` mode with the exact single-member Magisk
   boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, M20 variant, M19
   prefix, or partition is authorized by this exception.
   **Consumed/retired exception (2026-07-08, S22+ M23 DTS-exact
   QMP/DWC3 reset-summary native-init boot-only Odin path):** the S22+ M23 live
   gate above consumed this Odin path. No current exception authorizes another
   M23 Odin transfer or M23 rollback transfer under this helper. Before
   consumption, the gate could use `/usr/bin/odin4 --reboot -a` through
   `workspace/public/src/scripts/revalidation/s22plus_m23_dts_exact_qmp_reset_summary_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `558eddb4b78b68c86d65f171072145c63210e9b33b5d0b56f2a3e4a00f0ba2d8`, and
   the same helper may use `/usr/bin/odin4 --reboot -a` in
   `--rollback-from-download` mode with the exact single-member Magisk
   boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, M23 variant, M20
   variant, M19 prefix, or partition is authorized by this exception.
   **Consumed/retired exception (2026-07-08, S22+ M24 pmsg-step
   native-init boot-only Odin path):** the S22+ M24 live gate above consumed
   this Odin path. No current exception authorizes another M24 Odin transfer or
   M24 rollback transfer under this helper. Before consumption, paired only
   with the M24 pmsg-step gate above, `/usr/bin/odin4 --reboot -a` could be
   used through
   `workspace/public/src/scripts/revalidation/s22plus_m24_pmsg_steps_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `e09538024abe89585486d54856a5c86bef666da456f314084d4d4d8bb6553fe8`, and
   the same helper could use `/usr/bin/odin4 --reboot -a` in
   `--rollback-from-download` mode with the exact single-member Magisk
   boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, M24 variant, M23
   variant, M20 variant, M19 prefix, or partition is authorized by this
   exception.
   **Consumed exception (2026-07-09, S22+ M30/M21A raw nanosleep-download floor
   re-anchor boot-only live gate):** this one-shot exception was consumed by
   the 2026-07-09 KST live run. It flashed the pinned M21A boot-only candidate
   once, observed no host ADB/Odin through the 90 second dwell plus 30 second
   grace window (`m21a_download_seen=0`,
   `m21a_result=no-download-after-dwell-grace`), and the operator observed an
   RDX screen with `PMIC abnormal reset`. The host did not observe automatic
   Download mode. The operator then manually entered Download mode; Codex used
   the checked M21A rollback-from-download mode to flash the pinned Magisk boot
   rollback AP, and Android/Magisk returned cleanly. Final baseline was
   verified independently: boot
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, dtbo
   `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`,
   vendor_boot
   `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`,
   Android boot complete, vbstate orange, and Magisk root present. Post-rollback
   pstore was empty and retained `/proc/last_kmsg` did not contain the M21A
   marker (`S22_NATIVE=0`, `M21A=0`), though the operator photo captured the
   `PMIC abnormal reset` RDX screen. This exception must not be reused for
   M30/M21A repeat, M28/M29/S24 repeat, F43, USB/ACM bring-up, DTBO/vendor_boot/
   recovery/vbmeta/non-boot flash, kernel rebuild, raw host `dd`, fastboot,
   multidisabler, format data, EUD writes, or any A90 action. Future S22+
   native-init live flashes need a fresh, narrower exception for the selected
   candidate and observation path. The now-consumed live and rollback ack token
   strings are intentionally omitted here as active authorization. Before
   consumption, this exception allowed one bounded attended run using only
   `workspace/public/src/scripts/revalidation/s22plus_m21a_raw_nanosleep_download_live_gate.py`
   and the exact candidate AP.tar.md5 SHA256
   `d1949a56c60c71498d68753d2ffd6064719fafce1ad0e3959ebb8a4255bb6c79`, padded
   `boot.img` SHA256
   `61d7dc9818b79c810b30370edfe4df2b55ec451588defb48458fefae9c6c00a5`, raw
   `/init` SHA256
   `10f525760b170cba4ec55d7fd4955c466601253258371cb571eb45515bd9cf30`, source
   SHA256 `300ed990c8ea476c3744e18327ae08277c0d27dc443e99245aeecba457968c4f`,
   preserved kernel SHA256
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`, and
   boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` first,
   with stock boot-only fallback SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`.
   **Consumed exception (2026-07-09, S22+ M34 S10C0 direct-finit loader-audit boot-only live gate):**
   this one-shot exception was consumed by the 2026-07-09 KST live run. It
   proved `download-beacon-hit` / `finit_cmd_db_accepted`, then failed to
   complete a clean Magisk rollback and was recovered with the S10C0 stock
   boot-only fallback. It must not be reused for another S10C0 or native-init
   candidate flash under the same gate.
   Before consumption, Codex could run
   one bounded attended boot-partition-only M34 S10C0 live gate on the Samsung
   S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s10c0_direct_finit_loader_audit_live_gate.py`.
   Live ack token: `S22PLUS-M34-S10C0-DIRECT-FINIT-LOADER-AUDIT-LIVE-GATE`. Rollback ack token:
   `S22PLUS-M34-S10C0-DIRECT-FINIT-LOADER-AUDIT-ROLLBACK-FROM-DOWNLOAD`.

   The exact candidate AP.tar.md5 SHA256 must be
   `9221cfa3ea3ce0776860a5041981e23a84d0be9b833203401dab771897266c6f`; contained padded `boot.img` SHA256 must be
   `8d77e1434cd47fe47f4723c948e4ff6db759cbe4bf75dd21e9e0c265d928c6df`; direct `/init` SHA256 must be
   `cd80d5923c94f8a423821bc6dee4547f22763e177fbcc637d1bcb101c4b8c39b`; template source SHA256 must be
   `e7c8e62487701d6af31b5e7bc060a12091a5f55737aec67c4b45be484f67666b`; module-list SHA256 must be
   `c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26`; preserved kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`; and known-booting base Magisk boot SHA256
   must be `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`. The AP must contain exactly one
   tar member, `boot.img.lz4`, and must not carry recovery, vendor_boot, dtbo,
   vbmeta, vbmeta_system, BL, CP, CSC, super, persist, userdata, EFS,
   sec_efs, RPMB, keymaster, modem, bootloader, or any other partition payload.
   Before live flash, the helper must verify the pinned Magisk boot-only
   rollback AP SHA256 `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` and the S10C0-specific
   FYG8 stock boot-only fallback AP SHA256 `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`
   generated from stock raw boot SHA256 `4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae`.

   The candidate is limited to freestanding direct PID1 M34 S10C0 behavior:
   `S22+ M34 S10C0 direct-finit loader-audit download-beacon native-init boot-only`,
   `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S10C0`, `S10C0 starts from the S9/S10A/S10B 89-module recipe`,
   and `S10C0 separates direct cmd-db.ko finit_module rc from /proc/modules observation failure`. It remains
   driver-load-only: `both_graphs_closure=1`, `devlink_supplier_closure=1`,
   `substrate_load_set=waipio_devlink`, `driver_load_only=1`,
   `manual_power_write=0`, `module_count=89`, `session_producer_parity=1`,
   `max77705_session=1`, `geni_i2c_transport=1`, `i2c_msm_geni=1`,
   `gpi_dma=1`, `msm_geni_se=1`, `functionfs=0`, `stock_composite=0`,
   `configfs_gadget=0`, `udc_bind=0`, `role_write_discriminator=0`, and
   `typec_readback=0`.

   S10C0 intentionally performs no downstream USB gadget work: no configfs
   gadget setup, no UDC bind, no TypeC role write, no ssusb role write, no
   FunctionFS, and no stock composite. Its only observation is
   `s10c_loader_audit=1`, `module_load_probe=finit_cmd_db_accepted`,
   `predicate=cmd_db_finit_accepted`, `phase=s10c_module_loader_audit_probe`,
   `proc_modules=0`, `direct_finit_rc=1`, `probe_module=cmd-db.ko`,
   `probe_proc_name=cmd_db`, `cmd_db_file=cmd-db.ko`,
   `cmd_db_seen=`, `cmd_db_rc=`, `modules_open_rc=`, `modules_read_rc=`,
   `attempted=`, `ok=`, `eexist=`, `fail=`, `first_fail_index=`,
   `first_fail_rc=`, and `first_fail_name=`. Predicate true requests
   `reboot_request=download` with `download_beacon=1` and records
   `true_action=reboot_download`; predicate false records `false_action=park`
   and parks. The host-visible HIT is `download-beacon-hit`, where a new Odin
   Download endpoint appears after the original Download endpoint disconnects.
   MISS is `download-beacon-miss-parked-manual-download-required`; manual
   Download rollback is required and is recovery-only. S10C0 HIT means
   cmd-db.ko finit_module returned 0 or -EEXIST under native-init. S10C0 MISS
   means cmd-db.ko was not attempted or direct finit_module failed.

   The candidate must have no Android/Magisk handoff, no persistent partition
   mount, no block write, no module binary injection into boot ramdisk, no raw
   host `dd`, no fastboot, no Magisk modules, no multidisabler, no format data,
   no DTBO/vendor_boot/recovery/vbmeta/non-boot flash, and no A90 action. It
   must not write charge current, OTG/VBUS boost, regulator, GDSC, GPIO,
   display, raw PMIC knobs, EUD sysfs, TypeC role nodes, configfs, UDC, or
   ssusb role nodes. PMIC/RDX abnormal reset before the observation window is
   FAIL. This exception does not authorize S10B1/S10B2/S10B3/S10B4/S10B5/
   S10B6, S10A/S9 repeat, B2/B3/B4, descriptor/composition pivots,
   FunctionFS/conn_gadget parity, display/distro candidates, kernel rebuilds,
   RDX PC dump retrieval, or any non-boot partition action.

   Required policy marker coverage:
   `S22+ M34 S10C0 direct-finit loader-audit download-beacon native-init boot-only`
   `workspace/public/src/scripts/revalidation/s22plus_m34_s10c0_direct_finit_loader_audit_live_gate.py`
   `S22PLUS-M34-S10C0-DIRECT-FINIT-LOADER-AUDIT-LIVE-GATE`
   `S22PLUS-M34-S10C0-DIRECT-FINIT-LOADER-AUDIT-ROLLBACK-FROM-DOWNLOAD`
   `SM-S906N/g0q/S906NKSS7FYG8`
   `S10C0`
   `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S10C0`
   `9221cfa3ea3ce0776860a5041981e23a84d0be9b833203401dab771897266c6f`
   `8d77e1434cd47fe47f4723c948e4ff6db759cbe4bf75dd21e9e0c265d928c6df`
   `cd80d5923c94f8a423821bc6dee4547f22763e177fbcc637d1bcb101c4b8c39b`
   `c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26`
   `e7c8e62487701d6af31b5e7bc060a12091a5f55737aec67c4b45be484f67666b`
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
   `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`
   `4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae`
   `S10C0 starts from the S9/S10A/S10B 89-module recipe`
   `S10C0 separates direct cmd-db.ko finit_module rc from /proc/modules observation failure`
   `s10c_loader_audit=1`
   `module_load_probe=finit_cmd_db_accepted`
   `predicate=cmd_db_finit_accepted`
   `phase=s10c_module_loader_audit_probe`
   `proc_modules=0`
   `direct_finit_rc=1`
   `probe_module=cmd-db.ko`
   `probe_proc_name=cmd_db`
   `cmd_db_file=cmd-db.ko`
   `cmd_db=1`
   `cmd_db_seen=`
   `cmd_db_rc=`
   `modules_open_rc=`
   `modules_read_rc=`
   `attempted=`
   `ok=`
   `eexist=`
   `fail=`
   `first_fail_index=`
   `first_fail_rc=`
   `first_fail_name=`
   `both_graphs_closure=1`
   `devlink_supplier_closure=1`
   `substrate_load_set=waipio_devlink`
   `driver_load_only=1`
   `manual_power_write=0`
   `module_count=89`
   `session_producer_parity=1`
   `max77705_session=1`
   `geni_i2c_transport=1`
   `i2c_msm_geni=1`
   `gpi_dma=1`
   `msm_geni_se=1`
   `functionfs=0`
   `stock_composite=0`
   `configfs_gadget=0`
   `udc_bind=0`
   `role_write_discriminator=0`
   `typec_readback=0`
   `reboot_request=download`
   `download_beacon=1`
   `true_action=reboot_download`
   `false_action=park`
   `download-beacon-hit`
   `download-beacon-miss-parked-manual-download-required`
   `host-visible HIT = new Odin Download endpoint appears`
   `MISS = no new Odin endpoint during bounded observation; manual Download rollback required`
   `no configfs gadget setup`
   `no UDC bind`
   `no TypeC role write`
   `no ssusb role write`
   `no FunctionFS`
   `no stock composite`
   `no Android/Magisk handoff`
   `no persistent partition mount`
   `no block write`
   `no charge-current write`
   `no OTG/VBUS boost write`
   `no regulator/GDSC/GPIO/raw PMIC write`
   `manual Download rollback is recovery-only`
   `PMIC/RDX abnormal reset before the observation window is FAIL`
   `S10C0 HIT means cmd-db.ko finit_module returned 0 or -EEXIST under native-init`
   `S10C0 MISS means cmd-db.ko was not attempted or direct finit_module failed`
   `cmd-db.ko`
   `cmd_db`
   `cmd_db`
   `qcom_rpmh`
   `gcc_waipio`
   `pinctrl_waipio`
   `qcom_pdc`
   `i2c_msm_geni`
   `mfd_max77705`
   `pdic_max77705`

   **Consumed exception (2026-07-10, S22+ O3 direct-PID1 minimal generic-ACM boot-only live gate):**
   this one-shot exception was consumed by the 2026-07-10 KST O3 live run.
   The exact candidate AP transferred and left the original Odin endpoint, and
   the operator observed no bootloop, but no O3 ACM device appeared during the
   bounded 120-second wait. Continuous host USB evidence contains no candidate
   USB enumeration between the candidate Odin disconnect and attended manual
   Download entry. The checked helper therefore recorded
   `candidate-proof-failed`/`rc=9`, with no `candidate_boot_ready`, roundtrip, or
   `O3 STATUS` proof. After manual Download entry it restored the pinned Magisk
   boot-only AP and verified Android/root, exact baseline boot SHA, and four
   stability samples. It collected 2,097,136 bytes from `/proc/last_kmsg`, but
   no O3 marker; the exact candidate phase remains `UNVERIFIABLE`. This
   exception must not be reused for O3 repeat, a freestanding rewrite, O4, or
   any other candidate. A new candidate requires a fresh narrower exception.

   after V3412 built and reproducibly verified the exact O3 artifact, the
   checked live helper passed its offline artifact gate and connected read-only
   Android/Magisk preflight, and the operator explicitly approved live work,
   Codex may perform one bounded attended boot-partition-only O3 run on the
   Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_o3_minimal_acm_live_gate.py`.
   The authorized candidate is exactly `S22+ O3 direct-PID1 minimal generic-ACM boot-only`.
   Exact target marker: `SM-S906N/g0q/S906NKSS7FYG8`.
   Live ack token: `S22PLUS-O3-MINIMAL-ACM-LIVE-GATE`.
   Mandatory rollback ack token:
   `S22PLUS-O3-MINIMAL-ACM-ROLLBACK-FROM-DOWNLOAD`.

   The exact candidate AP.tar.md5 SHA256 must be
   `41b7e32424a809cec6ac7bded281b9ac355a9f3d2d0a3727f8b02de6d1e757f7`;
   contained padded `boot.img` SHA256 must be
   `4f4a073f79b47c0a6a3924fabf09b2389c62bb731ed3355ebb83e48c53868609`;
   `boot.img.lz4` SHA256 must be
   `5421281a463cbca00a2a1fcec00af96f21f827af30f3b107ae326c364d9264fb`.
   The direct PID1 `/init` SHA256 must be
   `7b2785687482971e4358575d555e49af402ceac2ee72136afdfeff3ece4b95cc`;
   static O3 control daemon SHA256 must be
   `2cb881f420dccd909610c4e3822adf6439fbe443460ee61644178f38509e5570`;
   module-plan TSV SHA256 must be
   `a34ebbad3b5d770f133e37a450cc3007e4a84ab831788484680e88aad6b3d534`;
   generated plan-header SHA256 must be
   `45727cff30952096d9604682a3ba3d284807a75e6622ed4c8ae57bc153d5b863`.
   The known-booting base Magisk boot SHA256 must remain
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`;
   preserved kernel SHA256 must remain
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`.
   The AP must contain exactly one tar member, `boot.img.lz4`, and must not
   contain recovery, vendor_boot, dtbo, vbmeta, vbmeta_system, BL, CP, CSC,
   super, persist, userdata, EFS, sec_efs, RPMB, keymaster, modem, bootloader,
   or any other partition payload. There is `no non-boot partition write`.

   Candidate behavior is limited to direct PID1 mounting volatile proc, sysfs,
   devtmpfs, and configfs; loading the exact pinned 59-module stock
   hard+soft-dependency plan from stock vendor_boot `/lib/modules`; consuming
   `/proc/modules` through EOF; requiring all eight ordered bind gates; creating
   one generic built-in `acm.usb0` function; writing only
   `a600000.ssusb/mode=peripheral`; binding only `a600000.dwc3`; and exposing
   the bounded framed control daemon on `/dev/ttyGS0`. The plan's exact single
   tolerated unavailable softdep remains
   `pinctrl-waipio.ko -> pre:qcom_tlmm_vm_irqchip`. Risk modules `abc`,
   `sec_debug`, `minidump`, `eud`, `qc_usb_audio`, `qcom_wdt_core`, and
   `gh_virt_wdt` may only be inserted as pinned dependency/survival inputs.
   The candidate must not enable EUD, trigger sec_debug/sysrq, configure audio,
   write Type-C/charger/PMIC/OTG/VBUS/regulator/GDSC/GPIO state, create Samsung
   `ss_acm`, FunctionFS, MTP, ADB, NCM, or a stock composite, mount persistent
   partitions, write block devices, start Android/Magisk, or request reboot.

   Before candidate flash the helper must verify the exact candidate and
   manifest hashes, the normal rooted Android identity, exact current Magisk
   boot SHA, one target transport, the active exception, the pinned Magisk
   boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`,
   and the FYG8 stock boot-only fallback AP SHA256
   `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`
   derived from stock raw boot SHA256
   `4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae`.
   Continuous host USB observers must cover the candidate window. O3 PASS
   requires the exact `S22O3ACM01` serial, the `128-request framed O0 protocol`
   with sequence/payload equality and host close/reopen, and an `O3 STATUS`
   response proving all 59 modules, EOF registration, gate mask `0xff`, exact
   mode and UDC readbacks, generic `acm.usb0`, and zero protocol invalid/CRC/
   sequence errors. Enumeration, survival, or source intent alone is not PASS.

   A `mandatory boot-only rollback` follows both PASS and FAIL. Because the
   candidate deliberately has no reboot command, attended `manual Download-mode entry`
   is expected after observation; the helper may wait up to its bounded timeout
   and then flash only the pinned Magisk boot AP. The pinned stock boot AP is
   fallback only if Magisk rollback transfer fails while one Download endpoint
   remains available. After rollback the helper must verify Android/root,
   exact baseline boot SHA and stability, and collect `/sys/fs/pstore` plus
   `/proc/last_kmsg`. If Download mode does not appear, stop and preserve the
   recovery command; do not widen behavior or flash another candidate. The
   exception is consumed once `candidate_flash_start` is recorded and must be
   rewritten as consumed after the run. It does not authorize O3 repeat, O4,
   NCM, Debian handoff, another module plan, kernel rebuild, Magisk module,
   multidisabler, format data, raw host `dd`, fastboot, full firmware flash,
   RDX retrieval, any non-boot flash, or any A90 action. Recoverable-envelope,
   single-target, fail-closed, and fails-twice-stop rules remain binding.

   **Consumed exception (2026-07-10, S22+ O1.1 SELinux-domain USB control boot-only live gate):**
   this one-shot exception was consumed by the 2026-07-10 KST O1.1 live run.
   The exact candidate booted with its pinned boot SHA, reached the bounded O1.1
   daemon while stock `DR-daemon` had released ttyGS0, completed all 128 framed
   request/response payloads with sequence continuity and the host close/reopen,
   restored stock tty ownership, and reported `daemon_rc=0`/`restore_rc=0`.
   The checked helper then restored the pinned Magisk boot-only AP, collected
   retained `/proc/last_kmsg`, and verified Android/root, exact baseline boot
   SHA, stability, and stock tty ownership. Retained init logs show
   `s22plus_o1_control` started and exited status 0; the O1 `no domain transition`
   rejection did not recur. This exception must not be reused for O1.1 repeat,
   O2/O3, or any other candidate.

   after the V3406 O1 retained-log result isolated the service-domain transition
   failure, V3407 built the single-delta O1.1 candidate, the checked O1.1 live
   helper passed its host gates, and the operator explicitly approved live work,
   Codex may perform one bounded attended boot-partition-only O1.1 run on the
   Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_o11_stock_first_stage_control_live_gate.py`.
   Exact target marker: `SM-S906N/g0q/S906NKSS7FYG8`.
   Live ack token: `S22PLUS-O11-SECLABEL-CONTROL-LIVE-GATE`.
   Mandatory rollback ack token:
   `S22PLUS-O11-SECLABEL-CONTROL-ROLLBACK`.

   The exact candidate AP.tar.md5 SHA256 must be
   `c43eeb83cedb2db3e0758de71050ef2960765740face7378fcc285a5b8188730`;
   contained padded `boot.img` SHA256 must be
   `1e59b172edda0d2c717a93021c9084af1393c0c4db7d28eeb10e06c0b1787b0d`;
   `boot.img.lz4` SHA256 must be
   `afef7ff56c7efd54cbb094b1a36bc8068cb3c780ccc8e2667baee9493c6ca6e6`.
   The known-booting base Magisk boot SHA256 must remain
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`;
   preserved kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`;
   preserved Magisk `/init` SHA256 must be
   `383670a7ba3a6a4b79e5f3467e1da4b66a5df66a9b356ab9f70916854dd6b468`.
   Overlay source SHA256 values must be rc
   `36363a0c6aedbd901310ac5de7bcdd9b85c2a2f985f92a0d78d86daefef8503b`,
   service
   `3e5c000308acaa52495c1b235b9f3e777123e3ddeb1e51f01b7461a38593be93`,
   and O0 daemon
   `a82cd32f83afc20d40fc74a9402896ae07378811f259913ed6df7cbc540f858c`.
   The AP must contain exactly one tar member, `boot.img.lz4`, and must not
   contain recovery, vendor_boot, dtbo, vbmeta, vbmeta_system, BL, CP, CSC,
   super, persist, userdata, EFS, sec_efs, RPMB, keymaster, modem, bootloader,
   or any other partition payload.

   The candidate is limited to `S22+ O1.1 SELinux-domain USB control boot-only`
   behavior. It preserves the O1 kernel, Magisk `/init`, stock first-stage
   module loader, stock Android USB gadget, wrapper, daemon, trigger, protocol,
   and timeouts. Its only executable behavior delta from O1 is the service
   option `seclabel u:r:magisk:s0`; it carries no SELinux policy file. After
   `sys.usb.configured=configured`, the bounded wrapper may require stock
   `DR-daemon`/`ddexe` ttyGS0 ownership, stop only `DR-daemon`, run the
   `128-request framed O0 protocol` with one host tty close/reopen, restore and
   revalidate `DR-daemon`, and write only volatile marker/status evidence under
   `/dev`, including `/dev/.s22plus_o1_status`. The candidate and helper perform
   `no configfs/sysfs write`, no active gadget change, `no module insertion`,
   `no persistent partition mount`, no block-device write, and no
   candidate-side reboot request.

   Before candidate flash the helper must verify the normal rooted Android
   identity, exact current Magisk boot SHA, single Samsung ACM tty, stock
   `DR-daemon` ownership, exact candidate/manifest hashes, the active exception,
   the pinned Magisk boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`,
   and the FYG8 stock boot-only fallback AP SHA256
   `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`
   derived from stock raw boot SHA256
   `4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae`.
   The helper may use a `bounded two-attempt ADB Download retry`: a nonzero ADB
   result is retried only after it proves the same Android target is again
   reachable, while an already observed single Odin endpoint counts only as
   transition acceptance and is not retried. Continuous host USB observers
   must cover the candidate window. O1.1 PASS requires candidate boot readback,
   service domain readiness before host tty open, all 128 framed payloads with
   sequence continuity, host tty reopen completion, volatile
   `result=pass`/`daemon_rc=0`/`restore_rc=0`, and restored stock tty ownership.

   A `mandatory boot-only rollback` to the pinned Magisk AP follows both PASS
   and FAIL. The pinned stock boot-only AP is fallback only if the Magisk
   rollback transfer fails while Download remains available. After successful
   rollback the helper must perform `automatic postrollback retained-log collection`
   from both `/sys/fs/pstore` and `/proc/last_kmsg`, then verify Android/root,
   boot SHA, stability, and stock tty ownership. If Android/ACM does not return,
   the helper may wait for attended manual Download entry and perform only that
   rollback. Absence of protocol/status is FAIL and must not be rounded up to
   source-intended execution. The exception is consumed once
   `candidate_flash_start` is recorded and must then be rewritten as consumed.
   This exception does not authorize O1.1 repeat, O2/O3, direct PID1, native
   module loading, USB role/Type-C/PMIC/EUD writes, Magisk modules,
   multidisabler, format data, raw host `dd`, fastboot, non-boot flash, full
   firmware flash, RDX dump retrieval, or any A90 action. Recoverable-envelope,
   single-target, fail-closed, and mandatory rollback gates remain binding.

   **Consumed exception (2026-07-10, S22+ O1 stock-first-stage USB control boot-only live gate):**
   this one-shot exception was consumed by the 2026-07-10 KST O1 live run. The
   exact candidate booted normal Android with its pinned boot SHA, but the first
   host frame failed with tty `EIO`. Retained `/proc/last_kmsg` proved the O1 rc
   was injected and its property trigger ran, while Android init rejected the
   service because `/debug_ramdisk/s22plus_o1_service.sh` had `system_file`
   labeling and no transition from `u:r:init:s0`. A software Download retry made
   after the operator explicitly requested it let the checked helper restore the
   pinned Magisk boot-only AP. Android/root, boot SHA, and stock `DR-daemon`
   ownership passed postflight. This exception must not be reused for O1.1 or
   any other candidate.

   Before consumption, after the V3403 O0 live PASS and V3404 host-build report
   pinned the exact O1 artifact, and after the operator explicitly approved live
   work, Codex could perform one bounded attended boot-partition-only O1 run on the Samsung S22+
   `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_o1_stock_first_stage_control_live_gate.py`.
   Exact target marker: `SM-S906N/g0q/S906NKSS7FYG8`.
   Live ack token: `S22PLUS-O1-STOCK-FIRST-STAGE-CONTROL-LIVE-GATE`.
   Mandatory rollback ack token:
   `S22PLUS-O1-STOCK-FIRST-STAGE-CONTROL-ROLLBACK`.

   The exact candidate AP.tar.md5 SHA256 must be
   `388d35c12e9f5024f053837444da46254db6a6177c046400549148e24eaeec29`;
   contained padded `boot.img` SHA256 must be
   `df7a166752f78aa07bea10aef53de1ba2737abf43bb041fe01738cce36113070`;
   `boot.img.lz4` SHA256 must be
   `26af084cca0cf23525e8786a50a49b270d60ae7b2fa7f4ed8d652bc9e102bb21`.
   The known-booting base Magisk boot SHA256 must remain
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`;
   preserved kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`;
   preserved Magisk `/init` SHA256 must be
   `383670a7ba3a6a4b79e5f3467e1da4b66a5df66a9b356ab9f70916854dd6b468`.
   Overlay source SHA256 values must be rc
   `9bd6732aacd55e2eb929bd0eb52fdbdff33613e5ac0931c1ea1ca67ad7cf32fe`,
   service
   `3e5c000308acaa52495c1b235b9f3e777123e3ddeb1e51f01b7461a38593be93`,
   and O0 daemon
   `a82cd32f83afc20d40fc74a9402896ae07378811f259913ed6df7cbc540f858c`.
   The AP must contain exactly one tar member, `boot.img.lz4`, and must not
   contain recovery, vendor_boot, dtbo, vbmeta, vbmeta_system, BL, CP, CSC,
   super, persist, userdata, EFS, sec_efs, RPMB, keymaster, modem, bootloader,
   or any other partition payload.

   The candidate is limited to `S22+ O1 stock-first-stage USB control boot-only`
   behavior. It preserves the stock kernel, Magisk `/init`, stock first-stage
   module loader, and stock Android USB gadget, and adds exactly
   `overlay.d/s22plus_o1_control.rc`,
   `overlay.d/sbin/s22plus_o1_service.sh`, and
   `overlay.d/sbin/s22plus_o1_tty_echo`. After
   `sys.usb.configured=configured`, the bounded wrapper may require stock
   `DR-daemon`/`ddexe` ttyGS0 ownership, stop only `DR-daemon`, run the
   `128-request framed O0 protocol` with one host tty close/reopen, restore and
   revalidate `DR-daemon`, and write only volatile marker/status evidence under
   `/dev`, including `/dev/.s22plus_o1_status`. The candidate and helper perform
   no configfs/sysfs write, no active gadget change, no module insertion, no
   persistent partition mount, no block-device write, and no candidate-side
   reboot request.

   Before candidate flash the helper must verify the normal rooted Android
   identity, exact current Magisk boot SHA, single Samsung ACM tty, stock
   `DR-daemon` ownership, exact candidate/manifest hashes, the pinned Magisk
   boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`,
   and the FYG8 stock boot-only fallback AP SHA256
   `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`
   derived from stock raw boot SHA256
   `4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae`.
   Continuous host USB observers must cover the candidate window. O1 PASS
   requires all 128 framed request/response payloads and sequence continuity,
   host tty reopen completion, candidate boot readback hash, volatile
   `result=pass`/`daemon_rc=0`/`restore_rc=0`, and restored stock tty ownership.

   A mandatory boot-only rollback to the pinned Magisk AP follows both PASS and
   FAIL. The pinned stock boot-only AP is fallback only if the Magisk rollback
   transfer fails while Download remains available. If Android/ACM does not
   return, the helper may wait for attended manual Download entry and perform
   only that rollback. Absence of O1 protocol/status is FAIL and must not be
   rounded up to source-intended execution. The exception is consumed once
   `candidate_flash_start` is recorded and must then be rewritten as consumed.
   This exception does not authorize a second O1 candidate, O2/O3, direct PID1,
   native module loading, USB role/Type-C/PMIC/EUD writes, Magisk modules,
   multidisabler, format data, raw host `dd`, fastboot, non-boot flash, full
   firmware flash, RDX dump retrieval, or any A90 action. `mandatory boot-only
   rollback`, recoverable-envelope, single-target, and fail-closed gates remain
   binding.

   **Consumed exception (2026-07-10, S22+ M34 S11P1 timed loader-result boot-only live gate):**
   this one-shot exception was consumed by the 2026-07-10 KST live S11P1 run.
   It flashed only the pinned single-member M34 S11P1 boot-only AP.tar.md5,
   observed no self-Download timed beacon inside the bounded 180s observation
   window, then restored the pinned Magisk boot-only AP after manual Download
   entry. Android/Magisk baseline and boot SHA were verified after rollback.
   The exception must not be reused for another S11P1/S11P0/S10 repeat or any
   other boot candidate.

   Before consumption, after the M34 S11P1 host-build report pinned the exact artifact hashes and
   the operator provided live approval, Codex could run one bounded attended
   boot-partition-only M34 S11P1 live gate on the Samsung S22+
   `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s11p1_timed_loader_result_live_gate.py`.
   Live ack token: `S22PLUS-M34-S11P1-TIMED-LOADER-RESULT-LIVE-GATE`. Rollback ack token:
   `S22PLUS-M34-S11P1-TIMED-LOADER-RESULT-ROLLBACK-FROM-DOWNLOAD`.

   The exact candidate AP.tar.md5 SHA256 must be
   `1bc209674aa6b496bcc4132eae4343c1311de06143164771994cc8b1df945b56`; contained padded `boot.img` SHA256 must be
   `874c312b4ce1b95388c158a686f22e56d7a5278dd09cfab13c0c853ab688c61e`; `boot.img.lz4` SHA256 must be
   `cb4234a257a91b4b7b43343f97c1c9f90049a2daca59cc28f19da5159567605a`; direct `/init` SHA256 must be
   `af4eb75a8bcdcbbe8bd4fe81e1100cbc34ef786c1c2e64b09b111582c727c3d1`; template source SHA256 must be
   `4d6688c2961eb58e5a86ddf2c6372943c0e50faf1c50298ac4a3e783ade44fca`; module-list SHA256 must be
   `c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26`; preserved kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`; and known-booting base Magisk boot SHA256
   must be `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`. The AP must contain exactly one
   tar member, `boot.img.lz4`, and must not carry recovery, vendor_boot, dtbo,
   vbmeta, vbmeta_system, BL, CP, CSC, super, persist, userdata, EFS,
   sec_efs, RPMB, keymaster, modem, bootloader, or any other partition payload.
   Before live flash, the helper must verify the pinned Magisk boot-only
   rollback AP SHA256 `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` and the S10C0-specific
   FYG8 stock boot-only fallback AP SHA256 `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`
   generated from stock raw boot SHA256 `4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae`.

   The candidate is limited to freestanding direct PID1 M34 S11P1 behavior:
   `S22+ M34 S11P1 timed loader-result native-init boot-only`,
   `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S11P1`, `S11P1 keeps the S9/S10C0/S11P0 isolated module
   recipe`, and `S11P1 always returns to Download after a bounded timed result
   delay`. It remains driver-load-only: `both_graphs_closure=1`,
   `devlink_supplier_closure=1`, `substrate_load_set=waipio_devlink`,
   `driver_load_only=1`, `manual_power_write=0`, `module_count=89`,
   `configfs_gadget=0`, `udc_bind=0`, `role_write_discriminator=0`, and
   `typec_readback=0`.

   S11P1 intentionally performs no downstream USB gadget work: no configfs
   gadget setup, no UDC bind, no TypeC role write, no ssusb role write, no
   FunctionFS, and no stock composite. Its observation is
   `s11p1_timed_loader_result=1`,
   `module_load_probe=timed_first_failure_or_proc_modules_result`,
   `predicate=timed_first_failure_or_proc_modules_result`,
   `phase=s11p1_timed_loader_result_probe`, `proc_modules=1`,
   `timed_download_beacon=1`, `always_reboot_download=1`,
   `download_delay_model=first_fail_index_or_proc_result`,
   `direct_finit_rc=1`, `probe_module=cmd-db.ko`,
   `probe_proc_name=cmd_db`,
   `positive_control=watchdog_proc_visible`,
   `positive_control_proc_names=qcom_wdt_core,gh_virt_wdt`,
   `positive_control_modules=qcom_wdt_core.ko,gh_virt_wdt.ko`,
   `result_code=`, `result=`, `download_delay_sec=`,
   `modules_open_rc=`, `modules_read_rc=`, `attempted=`, `ok=`, `eexist=`,
   `fail=`, `first_fail_index=`, `first_fail_rc=`, `first_fail_name=`,
   `cmd_db_seen=`, `cmd_db_rc=`, `cmd_db_proc_seen=`,
   `qcom_wdt_core_proc_seen=`, `gh_virt_wdt_proc_seen=`, and
   `watchdog_proc_seen=`.

   The timing contract is: `6` seconds for `modules_open_or_read_fail`, `12`
   seconds for `cmd_db_not_attempted`, `18` seconds for `cmd_db_rc_fail`,
   `20 + first_fail_index` seconds for `first_module_failure`, `116` seconds
   for `proc_watchdog_missing`, `122` seconds for
   `watchdog_visible_cmd_db_proc_missing`, and `128` seconds for
   `proc_watchdog_and_cmd_db_visible`. Both true and false paths record
   `true_action=timed_reboot_download` and
   `false_action=timed_reboot_download` semantics and request
   `reboot_request=download` with `download_beacon=1`. The host-visible result
   is `download-beacon-hit-timed`, where a new Odin Download endpoint appears
   after the original Download endpoint disconnects. If no new Download appears
   within the bounded observation window, the result is
   `download-beacon-miss-manual-download-required`; manual Download rollback is
   recovery-only.

   The candidate must have no Android/Magisk handoff, no persistent partition
   mount, no block write, no module binary injection into boot ramdisk, no raw
   host `dd`, no fastboot, no Magisk modules, no multidisabler, no format data,
   no DTBO/vendor_boot/recovery/vbmeta/non-boot flash, and no A90 action. It
   must not write charge current, OTG/VBUS boost, regulator, GDSC, GPIO,
   display, raw PMIC knobs, EUD sysfs, TypeC role nodes, configfs, UDC, or
   ssusb role nodes. PMIC/RDX abnormal reset before the observation window is
   FAIL. This exception does not authorize S11P0 repeat, S10C0 repeat, S10B
   repeat, B2/B3/B4, descriptor/composition pivots, FunctionFS/conn_gadget
   parity, display/distro candidates, kernel rebuilds, RDX PC dump retrieval,
   or any non-boot partition action.

   Required policy marker coverage:
   `S22+ M34 S11P1 timed loader-result native-init boot-only`
   `workspace/public/src/scripts/revalidation/s22plus_m34_s11p1_timed_loader_result_live_gate.py`
   `S22PLUS-M34-S11P1-TIMED-LOADER-RESULT-LIVE-GATE`
   `S22PLUS-M34-S11P1-TIMED-LOADER-RESULT-ROLLBACK-FROM-DOWNLOAD`
   `SM-S906N/g0q/S906NKSS7FYG8`
   `S11P1`
   `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S11P1`
   `1bc209674aa6b496bcc4132eae4343c1311de06143164771994cc8b1df945b56`
   `874c312b4ce1b95388c158a686f22e56d7a5278dd09cfab13c0c853ab688c61e`
   `cb4234a257a91b4b7b43343f97c1c9f90049a2daca59cc28f19da5159567605a`
   `af4eb75a8bcdcbbe8bd4fe81e1100cbc34ef786c1c2e64b09b111582c727c3d1`
   `c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26`
   `4d6688c2961eb58e5a86ddf2c6372943c0e50faf1c50298ac4a3e783ade44fca`
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
   `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`
   `4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae`
   `S11P1 keeps the S9/S10C0/S11P0 isolated module recipe`
   `S11P1 always returns to Download after a bounded timed result delay`
   `module_load_probe=timed_first_failure_or_proc_modules_result`
   `s11p1_timed_loader_result=1`
   `timed_download_beacon=1`
   `always_reboot_download=1`
   `download_delay_model=first_fail_index_or_proc_result`
   `phase=s11p1_timed_loader_result_probe`
   `predicate=timed_first_failure_or_proc_modules_result`
   `result_code=`
   `result=`
   `download_delay_sec=`
   `modules_open_or_read_fail`
   `cmd_db_not_attempted`
   `cmd_db_rc_fail`
   `first_module_failure`
   `proc_watchdog_missing`
   `watchdog_visible_cmd_db_proc_missing`
   `proc_watchdog_and_cmd_db_visible`
   `6`
   `12`
   `18`
   `20 + first_fail_index`
   `116`
   `122`
   `128`
   `proc_modules=1`
   `direct_finit_rc=1`
   `probe_module=cmd-db.ko`
   `probe_proc_name=cmd_db`
   `positive_control=watchdog_proc_visible`
   `positive_control_proc_names=qcom_wdt_core,gh_virt_wdt`
   `positive_control_modules=qcom_wdt_core.ko,gh_virt_wdt.ko`
   `cmd_db_proc_seen=`
   `qcom_wdt_core_proc_seen=`
   `gh_virt_wdt_proc_seen=`
   `watchdog_proc_seen=`
   `cmd_db_seen=`
   `cmd_db_rc=`
   `modules_open_rc=`
   `modules_read_rc=`
   `attempted=`
   `ok=`
   `eexist=`
   `fail=`
   `first_fail_index=`
   `first_fail_rc=`
   `first_fail_name=`
   `both_graphs_closure=1`
   `devlink_supplier_closure=1`
   `substrate_load_set=waipio_devlink`
   `driver_load_only=1`
   `manual_power_write=0`
   `module_count=89`
   `configfs_gadget=0`
   `udc_bind=0`
   `role_write_discriminator=0`
   `typec_readback=0`
   `reboot_request=download`
   `download_beacon=1`
   `true_action=timed_reboot_download`
   `false_action=timed_reboot_download`
   `download-beacon-hit-timed`
   `download-beacon-miss-manual-download-required`
   `no configfs gadget setup`
   `no UDC bind`
   `no TypeC role write`
   `no ssusb role write`
   `no Android/Magisk handoff`
   `no persistent partition mount`
   `no block write`
   `manual Download rollback is recovery-only`


   **Consumed exception (2026-07-10, S22+ M34 S11P0 proc-modules positive-control boot-only live gate):**
   this one-shot exception was consumed by the 2026-07-10 KST live S11P0 run.
   It flashed only the pinned single-member M34 S11P0 boot-only AP.tar.md5
   SHA256 `dacb20dc0466487e6ad30f7ad5ebcb053a9593966922464eba4b3ed60e5f3b45`,
   observed a Download-beacon MISS, and then recovered the rooted Magisk
   measurement baseline through the rollback paths documented in
   `docs/reports/S22PLUS_NATIVE_INIT_M34_S11P0_LIVE_RESULT_2026-07-10.md`.
   The live and rollback ack tokens below are retained as historical evidence
   only and are not active authorization for another S11P0/S11P1/S10 repeat or
   any other boot candidate.

   Before consumption, after the Magisk boot baseline was restored and the M34
   S11P0 host-build report pinned the exact artifact hashes, Codex could run
   one bounded attended boot-partition-only M34 S11P0 live gate on the Samsung S22+
   `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s11p0_proc_modules_positive_control_live_gate.py`.
   Live ack token: `S22PLUS-M34-S11P0-PROC-MODULES-POSITIVE-CONTROL-LIVE-GATE`. Rollback ack token:
   `S22PLUS-M34-S11P0-PROC-MODULES-POSITIVE-CONTROL-ROLLBACK-FROM-DOWNLOAD`.

   The exact candidate AP.tar.md5 SHA256 must be
   `dacb20dc0466487e6ad30f7ad5ebcb053a9593966922464eba4b3ed60e5f3b45`; contained padded `boot.img` SHA256 must be
   `3ac8b8a5dde2ef6c3f7170c258a4dc6f3a3f9a4bb4575b5af5cf3380952d7881`; direct `/init` SHA256 must be
   `efd8141e8c552b4e30f0052186b801d36420476d155e7c489c0a8644718dd5f6`; template source SHA256 must be
   `70f4326294da2f27c7736f5119c7c9ad32f10e02e066fd2f2530ca91a8e4078b`; module-list SHA256 must be
   `c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26`; preserved kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`; and known-booting base Magisk boot SHA256
   must be `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`. The AP must contain exactly one
   tar member, `boot.img.lz4`, and must not carry recovery, vendor_boot, dtbo,
   vbmeta, vbmeta_system, BL, CP, CSC, super, persist, userdata, EFS,
   sec_efs, RPMB, keymaster, modem, bootloader, or any other partition payload.
   Before live flash, the helper must verify the pinned Magisk boot-only
   rollback AP SHA256 `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` and the S10C0-specific
   FYG8 stock boot-only fallback AP SHA256 `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`
   generated from stock raw boot SHA256 `4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae`.

   The candidate is limited to freestanding direct PID1 M34 S11P0 behavior:
   `S22+ M34 S11P0 proc-modules positive-control native-init boot-only`,
   `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S11P0`, `S11P0 keeps the S10C0/S9 module recipe`, and
   `S11P0 positive-controls native-init /proc/modules with watchdog modules`.
   It remains driver-load-only: `both_graphs_closure=1`,
   `devlink_supplier_closure=1`, `substrate_load_set=waipio_devlink`,
   `driver_load_only=1`, `manual_power_write=0`, `module_count=89`,
   `configfs_gadget=0`, `udc_bind=0`, `role_write_discriminator=0`, and
   `typec_readback=0`.

   S11P0 intentionally performs no downstream USB gadget work: no configfs
   gadget setup, no UDC bind, no TypeC role write, no ssusb role write, no
   FunctionFS, and no stock composite. Its observation is
   `s11_proc_modules_positive_control=1`,
   `module_load_probe=finit_cmd_db_accepted_and_watchdog_proc_visible`,
   `predicate=cmd_db_finit_accepted_and_watchdog_proc_visible`,
   `phase=s11_proc_modules_positive_control_probe`, `proc_modules=1`,
   `direct_finit_rc=1`, `probe_module=cmd-db.ko`,
   `probe_proc_name=cmd_db`,
   `positive_control=watchdog_proc_visible`,
   `positive_control_proc_names=qcom_wdt_core,gh_virt_wdt`,
   `positive_control_modules=qcom_wdt_core.ko,gh_virt_wdt.ko`,
   `cmd_db_proc_seen=`, `qcom_wdt_core_proc_seen=`,
   `gh_virt_wdt_proc_seen=`, `watchdog_proc_seen=`, `cmd_db_seen=`,
   `cmd_db_rc=`, `modules_open_rc=`, `modules_read_rc=`, `attempted=`,
   `ok=`, `eexist=`, `fail=`, `first_fail_index=`, `first_fail_rc=`, and
   `first_fail_name=`. Predicate true requests `reboot_request=download` with
   `download_beacon=1` and records `true_action=reboot_download`; predicate
   false records `false_action=park` and parks. The host-visible HIT is
   `download-beacon-hit`, where a new Odin Download endpoint appears after the
   original Download endpoint disconnects. MISS is
   `download-beacon-miss-parked-manual-download-required`; manual Download
   rollback is required and is recovery-only. HIT means native-init
   /proc/modules can see a watchdog positive control. MISS means watchdog
   positive-control visibility failed or the loader did not reach the expected
   state.

   The candidate must have no Android/Magisk handoff, no persistent partition
   mount, no block write, no module binary injection into boot ramdisk, no raw
   host `dd`, no fastboot, no Magisk modules, no multidisabler, no format data,
   no DTBO/vendor_boot/recovery/vbmeta/non-boot flash, and no A90 action. It
   must not write charge current, OTG/VBUS boost, regulator, GDSC, GPIO,
   display, raw PMIC knobs, EUD sysfs, TypeC role nodes, configfs, UDC, or
   ssusb role nodes. PMIC/RDX abnormal reset before the observation window is
   FAIL. This exception does not authorize S11P1, S10C0 repeat, S10B repeat,
   B2/B3/B4, descriptor/composition pivots, FunctionFS/conn_gadget parity,
   display/distro candidates, kernel rebuilds, RDX PC dump retrieval, or any
   non-boot partition action.

   Required policy marker coverage:
   `S22+ M34 S11P0 proc-modules positive-control native-init boot-only`
   `workspace/public/src/scripts/revalidation/s22plus_m34_s11p0_proc_modules_positive_control_live_gate.py`
   `S22PLUS-M34-S11P0-PROC-MODULES-POSITIVE-CONTROL-LIVE-GATE`
   `S22PLUS-M34-S11P0-PROC-MODULES-POSITIVE-CONTROL-ROLLBACK-FROM-DOWNLOAD`
   `SM-S906N/g0q/S906NKSS7FYG8`
   `S11P0`
   `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S11P0`
   `dacb20dc0466487e6ad30f7ad5ebcb053a9593966922464eba4b3ed60e5f3b45`
   `3ac8b8a5dde2ef6c3f7170c258a4dc6f3a3f9a4bb4575b5af5cf3380952d7881`
   `efd8141e8c552b4e30f0052186b801d36420476d155e7c489c0a8644718dd5f6`
   `c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26`
   `70f4326294da2f27c7736f5119c7c9ad32f10e02e066fd2f2530ca91a8e4078b`
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
   `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`
   `4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae`
   `S11P0 keeps the S10C0/S9 module recipe`
   `S11P0 positive-controls native-init /proc/modules with watchdog modules`
   `module_load_probe=finit_cmd_db_accepted_and_watchdog_proc_visible`
   `predicate=cmd_db_finit_accepted_and_watchdog_proc_visible`
   `phase=s11_proc_modules_positive_control_probe`
   `s11_proc_modules_positive_control=1`
   `proc_modules=1`
   `direct_finit_rc=1`
   `probe_module=cmd-db.ko`
   `probe_proc_name=cmd_db`
   `positive_control=watchdog_proc_visible`
   `positive_control_proc_names=qcom_wdt_core,gh_virt_wdt`
   `positive_control_modules=qcom_wdt_core.ko,gh_virt_wdt.ko`
   `cmd_db_proc_seen=`
   `qcom_wdt_core_proc_seen=`
   `gh_virt_wdt_proc_seen=`
   `watchdog_proc_seen=`
   `cmd_db_seen=`
   `cmd_db_rc=`
   `modules_open_rc=`
   `modules_read_rc=`
   `attempted=`
   `ok=`
   `eexist=`
   `fail=`
   `first_fail_index=`
   `first_fail_rc=`
   `first_fail_name=`
   `both_graphs_closure=1`
   `devlink_supplier_closure=1`
   `substrate_load_set=waipio_devlink`
   `driver_load_only=1`
   `manual_power_write=0`
   `module_count=89`
   `configfs_gadget=0`
   `udc_bind=0`
   `role_write_discriminator=0`
   `typec_readback=0`
   `reboot_request=download`
   `download_beacon=1`
   `true_action=reboot_download`
   `false_action=park`
   `download-beacon-hit`
   `download-beacon-miss-parked-manual-download-required`
   `HIT means native-init /proc/modules can see a watchdog positive control`
   `MISS means watchdog positive-control visibility failed or the loader did not reach the expected state`
   `no configfs gadget setup`
   `no UDC bind`
   `no TypeC role write`
   `no ssusb role write`
   `no Android/Magisk handoff`
   `no persistent partition mount`
   `no block write`
   `manual Download rollback is recovery-only`

   **Consumed exception (2026-07-10, S22+ Magisk boot-baseline restore boot-only gate):**
   this one-shot exception was consumed by the 2026-07-10 KST live restore run.
   It flashed only the pinned single-member Magisk boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` through
   `workspace/public/src/scripts/revalidation/s22plus_magisk_boot_baseline_restore_gate.py`
   after explicit operator flash approval. The AP contained exactly
   `boot.img.lz4` with member SHA256
   `b33b63d9d2c56cbe10170820e88cf136be8fe9ad621a21752da19fdd9b642d31`.
   The run completed with `result=magisk-baseline-restored`, Android
   `SM-S906N`/`g0q`/`S906NKSS7FYG8`, `vbstate=orange`,
   `/debug_ramdisk/su` Magisk root, and restored boot partition SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
   The consumed live ack token string is intentionally omitted here as active
   authorization. This consumed exception must not be reused for another
   Magisk restore, native-init candidate, kernel rebuild, recovery/vendor_boot/
   vbmeta/dtbo/BL/CP/CSC/super/userdata/EFS/sec_efs/RPMB/keymaster/modem/
   bootloader write, raw host `dd`, fastboot, Magisk module, multidisabler,
   format data, or any A90 action.

   **Consumed exception (2026-07-09, S22+ M34 S10B0 module-load prefix
   boot-only live gate):** this one-shot exception was consumed by the
   2026-07-09 KST live run. It flashed the pinned M34 S10B0 boot-only
   candidate once on the Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s10b0_module_load_prefix_live_gate.py`.
   The consumed live and rollback ack token strings are intentionally omitted
   here as active authorization. The run returned
   `download-beacon-miss-parked-manual-download-required`, then restored the
   pinned Magisk boot baseline through manual Download rollback after the
   operator reported RDX then Download entry. The helper's live rc was `5`
   because the old post-rollback verifier only accepted PATH `su`; a follow-up
   dry-run proved Magisk root through `/debug_ramdisk/su`, boot partition
   SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, and
   Android baseline clean. The Android `/data` storage-full side effect was
   traced to `/data/log/core` ART core dumps and cleaned after preserving
   triage samples; runtime `core_pattern=/dev/null` suppressed immediate
   regeneration.

   The exact candidate AP.tar.md5 SHA256 must be
   `c117d8789b4ed990afd047ef3a6bb8d32f0b7b5d76bdce58eecf8ae98725d47c`; contained padded `boot.img` SHA256 must be
   `a30120d094d3484b6b4234e0a285f6c26e95120f032ed9ec3671fd287661b610`; direct `/init` SHA256 must be
   `50bd942c92d6aad3b143e1f215c0e7a313819994f5dbfa580c11666d32d5f761`; template source SHA256 must be
   `6ac888ddf29e559a9a9b7522eda4edd54c5a38264782dddd2bd5c80d6d8e21a6`; module-list SHA256 must be
   `c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26`; preserved kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`; and known-booting base Magisk boot SHA256
   must be `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`. The AP must contain exactly one
   tar member, `boot.img.lz4`, and must not carry recovery, vendor_boot, dtbo,
   vbmeta, vbmeta_system, BL, CP, CSC, super, persist, userdata, EFS,
   sec_efs, RPMB, keymaster, modem, bootloader, or any other partition payload.

   The candidate is limited to freestanding direct PID1 M34 S10B0 behavior:
   `S22+ M34 S10B0 module-load prefix download-beacon native-init boot-only`,
   `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S10B0`, `S10B0 starts from the S9/S10A 89-module recipe`,
   and `S10B0 bisects the S10A all-core /proc/modules MISS`. It remains
   driver-load-only: `both_graphs_closure=1`, `devlink_supplier_closure=1`,
   `substrate_load_set=waipio_devlink`, `driver_load_only=1`,
   `manual_power_write=0`, `module_count=89`, `session_producer_parity=1`,
   `max77705_session=1`, `geni_i2c_transport=1`, `i2c_msm_geni=1`,
   `gpi_dma=1`, `msm_geni_se=1`, `functionfs=0`, `stock_composite=0`,
   `configfs_gadget=0`, `udc_bind=0`, `role_write_discriminator=0`, and
   `typec_readback=0`.

   S10B0 intentionally performs no downstream USB gadget work: no configfs
   gadget setup, no UDC bind, no TypeC role write, no ssusb role write, no
   FunctionFS, and no stock composite. Its only observation is
   `s10b_ladder=1`, `s10b_module_load_prefix_probe=1`,
   `module_load_probe=proc_modules_prefix_1`, `predicate=proc_modules_prefix`,
   `proc_modules=1`, `prefix_index=0`, `prefix_expected=1`, and
   `prefix_modules=cmd_db`. Predicate true requests
   `reboot_request=download` with `download_beacon=1` and records
   `true_action=reboot_download`; predicate false records `false_action=park`
   and parks. The host-visible HIT is `download-beacon-hit`, where a new Odin
   Download endpoint appears after the original Download endpoint disconnects.
   MISS is `download-beacon-miss-parked-manual-download-required`; manual
   Download rollback is required and is recovery-only. S10B0 HIT means cmd_db
   appears in /proc/modules under native-init. S10B0 MISS means cmd_db never
   appears or /proc/modules cannot be trusted there.

   The candidate must have no Android/Magisk handoff, no persistent partition
   mount, no block write, no module binary injection into boot ramdisk, no raw
   host `dd`, no fastboot, no Magisk modules, no multidisabler, no format data,
   no DTBO/vendor_boot/recovery/vbmeta/non-boot flash, and no A90 action. It
   must not write charge current, OTG/VBUS boost, regulator, GDSC, GPIO,
   display, raw PMIC knobs, EUD sysfs, TypeC role nodes, configfs, UDC, or
   ssusb role nodes. PMIC/RDX abnormal reset before the observation window is
   FAIL. This consumed exception must not be reused and does not authorize
   S10B1/S10B2/S10B3/S10B4/S10B5/
   S10B6, S10A/S9 repeat, B2/B3/B4, descriptor/composition pivots,
   FunctionFS/conn_gadget parity, display/distro candidates, kernel rebuilds,
   RDX PC dump retrieval, or any non-boot partition action.
   **Consumed exception (2026-07-09, S22+ M34 S10A module-load
   download-beacon boot-only live gate):** this one-shot exception was consumed
   by the 2026-07-09 KST live run. It flashed the pinned M34 S10A boot-only
   candidate once on the Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s10a_module_load_beacon_live_gate.py`.
   The consumed live and rollback ack token strings are intentionally omitted
   here as active authorization. The run returned
   `download-beacon-miss-parked-manual-download-required`, then restored the
   pinned Magisk boot baseline through manual Download rollback after the
   operator reported RDX then Download entry; `result.json` and `timeline.json`
   live in
   `workspace/private/runs/s22plus_m34_s10a_module_load_beacon_live_gate_live_20260709T095435Z/`.

   The exact candidate AP.tar.md5 SHA256 must be
   `064cc0431e649eb78bc8c8d1d89fcd16d09426f898120edb3c31c375275e3182`;
   contained padded `boot.img` SHA256 must be
   `a1ca7a4bf64ec8ecfc56d28d3f5e8511e6045bb1b2513fbafdb4249f75e15217`;
   direct `/init` SHA256 must be
   `f8ad5df4ef3ff5db7229b3c7f55f2453bc8fe5a72260ca539534e9cddbbdc4e8`;
   template source SHA256 must be
   `f5e116e65f7e0075a304c8ef36610fc1604055310ca28d7fad97eb1b5457b772`;
   module-list SHA256 must be
   `c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26`;
   preserved kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`;
   known-booting base Magisk boot SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`;
   and the pinned Magisk boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
   plus stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`
   must be present. The AP must contain exactly one tar member,
   `boot.img.lz4`, and must not carry recovery, vendor_boot, dtbo, vbmeta,
   vbmeta_system, BL, CP, CSC, super, persist, userdata, EFS, sec_efs, RPMB,
   keymaster, modem, bootloader, or any other partition payload.

   The candidate is limited to freestanding direct PID1 M34 S10A behavior:
   `S22+ M34 S10A module-load download-beacon native-init boot-only`,
   `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S10A`,
   `module_load_probe=proc_modules_core_loaded`, `s10a_module_load_probe=1`,
   `proc_modules=1`, `core_module_count=8`, `both_graphs_closure=1`,
   `devlink_supplier_closure=1`, `substrate_load_set=waipio_devlink`,
   `driver_load_only=1`, `manual_power_write=0`, `module_count=89`,
   `session_producer_parity=1`, `max77705_session=1`,
   `geni_i2c_transport=1`, `i2c_msm_geni=1`, `gpi_dma=1`,
   `msm_geni_se=1`, `functionfs=0`, `stock_composite=0`,
   `configfs_gadget=0`, `udc_bind=0`, `role_write_discriminator=0`, and
   `typec_readback=0`. Its core `/proc/modules` names are `cmd_db`,
   `qcom_rpmh`, `gcc_waipio`, `pinctrl_waipio`, `qcom_pdc`,
   `i2c_msm_geni`, `mfd_max77705`, and `pdic_max77705`.

   Predicate true requests `reboot_request=download` with
   `download_beacon=1` and records `true_action=reboot_download`; predicate
   false records `false_action=park` and parks. The host-visible HIT is
   `download-beacon-hit`, where a new Odin Download endpoint appears after
   the original Download endpoint disconnects. MISS is
   `download-beacon-miss-parked-manual-download-required` and requires manual
   Download rollback. The candidate must have no Android/Magisk handoff, no
   persistent partition mount, no block write, no module binary injection into
   boot ramdisk, no raw host `dd`, no fastboot, no Magisk modules, no
   multidisabler, no format data, no DTBO/vendor_boot/recovery/vbmeta/
   non-boot flash, and no A90 action. It must not write charge current,
   OTG/VBUS boost, regulator, GDSC, GPIO, display, raw PMIC knobs, EUD sysfs,
   TypeC role nodes, configfs, UDC, or ssusb role nodes. This exception does
   not authorize S9 repeat, B2/B3/B4, descriptor/composition pivots,
   FunctionFS/conn_gadget parity, display/distro candidates, kernel rebuilds,
   RDX PC dump retrieval, or any non-boot partition action.
   **Consumed exception (2026-07-09, S22+ M34 S9 download-beacon
   state-probe boot-only live gate):** this one-shot exception was consumed by
   the 2026-07-09 KST live run. It flashed the pinned M34 S9 boot-only
   candidate once on the Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s9_devlink_substrate_beacon_live_gate.py`.
   The consumed live and rollback ack token strings are intentionally omitted
   here as active authorization. The run returned
   `download-beacon-miss-parked-manual-download-required`, then restored the
   pinned Magisk boot baseline through manual Download rollback; `result.json`
   and `timeline.json` live in
   `workspace/private/runs/s22plus_m34_s9_devlink_substrate_beacon_live_gate_20260709T091154Z/`.

   The exact candidate AP.tar.md5 SHA256 must be
   `41a76ac1404c99273e9ec3aeae591dbfc94e1aa83daf97de9a7068e3c155022f`; contained padded `boot.img` SHA256 must be
   `509a05e4ff97dad39ca52eae6c57169e20d3ddbf1524d292e8c91b9286a80414`; direct `/init` SHA256 must be
   `9f231faff6154dc08b6b4d1b6cd169e82c81bfdc1e8d02cc92d1ea5a02dbd390`; template source SHA256 must be
   `8364aca94582fc325f89855b5cfd4e47ff8e41d2f18c341c99bd750ea3ebe3ae`; module-list SHA256 must be
   `c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26`; preserved kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`; and known-booting base Magisk boot SHA256
   must be `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`. The AP must contain exactly one
   tar member, `boot.img.lz4`, and must not carry recovery, vendor_boot, dtbo,
   vbmeta, vbmeta_system, BL, CP, CSC, super, persist, userdata, EFS,
   sec_efs, RPMB, keymaster, modem, bootloader, or any other partition payload.

   The candidate is limited to freestanding direct PID1 M34 S9 behavior.
   S9 starts from the S8B1A wide B1 recipe, closes the Waipio devlink supplier
   substrate load-set, and remains driver-load-only:
   `devlink_supplier_closure=1`, `substrate_load_set=waipio_devlink`,
   `driver_load_only=1`, `manual_power_write=0`, GENI I2C transport closure,
   stock max77705 PDIC altmode session-producer closure, `module_count=89`,
   `session_producer_parity=1`, `max77705_session=1`,
   `geni_i2c_transport=1`, `i2c_msm_geni=1`, `gpi_dma=1`,
   `msm_geni_se=1`, `functionfs=0`, `stock_composite=0`,
   `sec_debug_region.ko present due stock charger dependency`, and
   `requires_s7a_specific_live_risk_review`.

   S9 intentionally performs no downstream USB gadget work:
   `configfs_gadget=0`, `udc_bind=0`, `ssusb_mode_peripheral=0`,
   `typec_readback=0`, `role_write_discriminator=0`, no configfs gadget setup,
   no UDC bind, no TypeC role write, no ssusb role write, no FunctionFS, and
   no stock composite. Its only observation is
   `s8_beacon_probe=typec_port_or_i2c_any_0066` / `predicate=typec_port_or_i2c_any_0066`,
   reading `/sys/class/typec/port0` and any `/sys/bus/i2c/devices/*-0066`.
   Predicate true requests `reboot_request=download` with `download_beacon=1`
   and records `true_action=reboot_download`; predicate false records
   `false_action=park` and parks. The host-visible HIT is that a new Odin
   Download endpoint appears after the original Download endpoint disconnects.
   MISS means no new Odin endpoint during bounded observation; manual Download
   rollback is required and is recovery-only.

   The candidate must have no Android/Magisk handoff, no persistent partition
   mount, no block write, no module binary injection into boot ramdisk, no raw
   host `dd`, no fastboot, no Magisk modules, no multidisabler, no format data,
   no DTBO/vendor_boot/recovery/vbmeta/non-boot flash, and no A90 action. It
   must not write charge current, OTG/VBUS boost, regulator, GDSC, GPIO,
   display, raw PMIC knobs, EUD sysfs, TypeC role nodes, configfs, UDC, or
   ssusb role nodes. PMIC/RDX abnormal reset before the observation window is
   FAIL. This exception does not authorize S1/S2/S3/S4/S5/S6/S7A/S7A2/S8B1/
   S8B1A repeat, B2/B3/B4, descriptor/composition pivots,
   FunctionFS/conn_gadget parity, display/distro candidates, kernel rebuilds,
   RDX PC dump retrieval, or any non-boot partition action.

   Required policy marker coverage:
   `S22+ M34 S9 download-beacon state-probe native-init boot-only`
   `workspace/public/src/scripts/revalidation/s22plus_m34_s9_devlink_substrate_beacon_live_gate.py`
   `SM-S906N/g0q/S906NKSS7FYG8`
   `S9`
   `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S9`
   `41a76ac1404c99273e9ec3aeae591dbfc94e1aa83daf97de9a7068e3c155022f`
   `509a05e4ff97dad39ca52eae6c57169e20d3ddbf1524d292e8c91b9286a80414`
   `9f231faff6154dc08b6b4d1b6cd169e82c81bfdc1e8d02cc92d1ea5a02dbd390`
   `c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26`
   `8364aca94582fc325f89855b5cfd4e47ff8e41d2f18c341c99bd750ea3ebe3ae`
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
   `S9 starts from the S8B1A wide B1 recipe`
   `Waipio devlink supplier substrate load-set`
   `devlink_supplier_closure=1`
   `substrate_load_set=waipio_devlink`
   `driver_load_only=1`
   `manual_power_write=0`
   `GENI I2C transport closure`
   `stock max77705 PDIC altmode session-producer closure`
   `module_count=89`
   `session_producer_parity=1`
   `max77705_session=1`
   `geni_i2c_transport=1`
   `i2c_msm_geni=1`
   `gpi_dma=1`
   `msm_geni_se=1`
   `typec_readback=0`
   `role_write_discriminator=0`
   `configfs_gadget=0`
   `udc_bind=0`
   `ssusb_mode_peripheral=0`
   `functionfs=0`
   `stock_composite=0`
   `s8_beacon_probe=typec_port_or_i2c_any_0066`
   `predicate=typec_port_or_i2c_any_0066`
   `/sys/class/typec/port0`
   `/sys/bus/i2c/devices/*-0066`
   `reboot_request=download`
   `download_beacon=1`
   `true_action=reboot_download`
   `false_action=park`
   `download-beacon-hit`
   `download-beacon-miss-parked-manual-download-required`
   `host-visible HIT = new Odin Download endpoint appears`
   `MISS = no new Odin endpoint during bounded observation; manual Download rollback required`
   `no configfs gadget setup`
   `no UDC bind`
   `no TypeC role write`
   `no ssusb role write`
   `no FunctionFS`
   `no stock composite`
   `no Android/Magisk handoff`
   `no persistent partition mount`
   `no block write`
   `no charge-current write`
   `no OTG/VBUS boost write`
   `no regulator/GDSC/GPIO/raw PMIC write`
   `manual Download rollback is recovery-only`
   `PMIC/RDX abnormal reset before the observation window is FAIL`
   `sec_debug_region.ko present due stock charger dependency`
   `requires_s7a_specific_live_risk_review`
   `clk-qcom.ko`
   `pinctrl-msm.ko`
   `qcom_rpmh.ko`
   `icc-rpmh.ko`
   `icc-bcm-voter.ko`
   `gcc-waipio.ko`
   `pinctrl-waipio.ko`
   `clk-rpmh.ko`
   `rpmh-regulator.ko`
   `gdsc-regulator.ko`
   `qnoc-waipio.ko`
   `arm_smmu.ko`
   `qcom-pdc.ko`
   `qcom-pdc.ko`
   `pinctrl-msm.ko`
   `pinctrl-waipio.ko`
   `gpi.ko`
   `msm-geni-se.ko`
   `i2c-msm-geni.ko`
   `qcom-i2c-pmic.ko`
   `mfd_max77705.ko`
   `max77705_charger.ko`
   `max77705-fuelgauge.ko`
   `pdic_max77705.ko`
   `charger-ulog-glink.ko`
   `altmode-glink.ko`
   `msm-geni-se.ko`
   `gpi.ko`
   `charger-ulog-glink.ko`
   `altmode-glink.ko`
   `qti-regmap-debugfs.ko`
   `qcom-i2c-pmic.ko`
   `i2c-msm-geni.ko`
   `sec_pm_log.ko`
   `qcom-cpufreq-hw.ko`
   `sched-walt.ko`
   `kryo_arm64_edac.ko`
   `memory_dump_v2.ko`
   `sec_key_notifier.ko`
   `sec_crashkey_long.ko`
   `sec_debug_region.ko`
   `sec_param.ko`
   `sec_qc_dbg_partition.ko`
   `sec_qc_summary.ko`
   `sec_upload_cause.ko`
   `sec_qc_upload_cause.ko`
   `sec_qc_user_reset.ko`
   `sec_qc_smem.ko`
   `sec_qc_hw_param.ko`
   `sb-core.ko`
   `sec_pd.ko`
   `sec-battery.ko`
   `mfd_max77705.ko`
   `spu_verify.ko`
   `pdic_max77705.ko`
   `max77705_charger.ko`
   `max77705-fuelgauge.ko`
   `memory_dump_v2.ko`
   `sec_debug_region.ko`
   `sec_param.ko`
   `sec_qc_dbg_partition.ko`
   `sec_qc_summary.ko`
   `sec_upload_cause.ko`
   `sec_qc_upload_cause.ko`
   `sec_qc_user_reset.ko`

   **Consumed exception (2026-07-09, S22+ M34 S8B1 download-beacon
   state-probe boot-only live gate):** this one-shot exception was consumed by
   the 2026-07-09 KST live run. It flashed the pinned M34 S8B1 boot-only
   candidate once on the Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py`.
   The consumed live and rollback ack token strings are intentionally omitted
   here as active authorization. The run returned
   `download-beacon-miss-parked-manual-download-required`, then restored the
   pinned Magisk boot baseline through manual Download rollback; `result.json`
   and `timeline.json` live in
   `workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T042547Z_live/`.

   The exact candidate AP.tar.md5 SHA256 must be
   `0bf313cdf24a5f5babc3d0073a1e90686f1b734b6dafdfa548154ef3eac6c2c8`; contained padded `boot.img` SHA256 must be
   `4e599087f242fdf2ae6bee1465e0725b60057bad893b665a178bcf87b88b9a20`; direct `/init` SHA256 must be
   `a1cbc9828a24a7e302bd569de93b4f41e2ceb159130ea373d2ea9c9572f5a20d`; template source SHA256 must be
   `35978182a80e0502a0aec89ec66e35ca378ebbb3b7c58c573ad0e8ff55cc248d`; module-list SHA256 must be
   `c0c35e02fe61a3f6c18c221a9ae2cc1a54aafd38374117fa954dbfa675700998`; preserved kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`; and known-booting base Magisk boot SHA256
   must be `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`. The AP must contain exactly one
   tar member, `boot.img.lz4`, and must not carry recovery, vendor_boot, dtbo,
   vbmeta, vbmeta_system, BL, CP, CSC, super, persist, userdata, EFS,
   sec_efs, RPMB, keymaster, modem, bootloader, or any other partition payload.

   The candidate is limited to freestanding direct PID1 M34 S8B1 behavior.
   S8B1 keeps the S7A2 module recipe fixed: GENI I2C transport closure,
   stock max77705 PDIC altmode session-producer closure, `module_count=86`,
   `session_producer_parity=1`, `max77705_session=1`,
   `geni_i2c_transport=1`, `i2c_msm_geni=1`, `gpi_dma=1`,
   `msm_geni_se=1`, `functionfs=0`, `stock_composite=0`,
   `sec_debug_region.ko present due stock charger dependency`, and
   `requires_s7a_specific_live_risk_review`.

   S8B1 intentionally performs no downstream USB gadget work:
   `configfs_gadget=0`, `udc_bind=0`, `ssusb_mode_peripheral=0`,
   `typec_readback=0`, `role_write_discriminator=0`, no configfs gadget setup,
   no UDC bind, no TypeC role write, no ssusb role write, no FunctionFS, and
   no stock composite. Its only observation is
   `s8_beacon_probe=typec_port_or_i2c_device` / `predicate=typec_port_or_i2c_device`,
   reading `/sys/class/typec/port0` and `/sys/bus/i2c/devices/57-0066`.
   Predicate true requests `reboot_request=download` with `download_beacon=1`
   and records `true_action=reboot_download`; predicate false records
   `false_action=park` and parks. The host-visible HIT is that a new Odin
   Download endpoint appears after the original Download endpoint disconnects.
   MISS means no new Odin endpoint during bounded observation; manual Download
   rollback is required and is recovery-only.

   The candidate must have no Android/Magisk handoff, no persistent partition
   mount, no block write, no module binary injection into boot ramdisk, no raw
   host `dd`, no fastboot, no Magisk modules, no multidisabler, no format data,
   no DTBO/vendor_boot/recovery/vbmeta/non-boot flash, and no A90 action. It
   must not write charge current, OTG/VBUS boost, regulator, GDSC, GPIO,
   display, raw PMIC knobs, EUD sysfs, TypeC role nodes, configfs, UDC, or
   ssusb role nodes. PMIC/RDX abnormal reset before the observation window is
   FAIL. This exception does not authorize S1/S2/S3/S4/S5/S6/S7A/S7A2 repeat,
   B2/B3/B4, descriptor/composition pivots, FunctionFS/conn_gadget parity,
   display/distro candidates, kernel rebuilds, RDX PC dump retrieval, or any
   non-boot partition action.

   Required policy marker coverage:
   `S22+ M34 S8B1 download-beacon state-probe native-init boot-only`
   `workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py`
   `SM-S906N/g0q/S906NKSS7FYG8`
   `S8B1`
   `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S8B1`
   `0bf313cdf24a5f5babc3d0073a1e90686f1b734b6dafdfa548154ef3eac6c2c8`
   `4e599087f242fdf2ae6bee1465e0725b60057bad893b665a178bcf87b88b9a20`
   `a1cbc9828a24a7e302bd569de93b4f41e2ceb159130ea373d2ea9c9572f5a20d`
   `c0c35e02fe61a3f6c18c221a9ae2cc1a54aafd38374117fa954dbfa675700998`
   `35978182a80e0502a0aec89ec66e35ca378ebbb3b7c58c573ad0e8ff55cc248d`
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
   `S8B1 keeps the S7A2 module recipe fixed`
   `GENI I2C transport closure`
   `stock max77705 PDIC altmode session-producer closure`
   `module_count=86`
   `session_producer_parity=1`
   `max77705_session=1`
   `geni_i2c_transport=1`
   `i2c_msm_geni=1`
   `gpi_dma=1`
   `msm_geni_se=1`
   `typec_readback=0`
   `role_write_discriminator=0`
   `configfs_gadget=0`
   `udc_bind=0`
   `ssusb_mode_peripheral=0`
   `functionfs=0`
   `stock_composite=0`
   `s8_beacon_probe=typec_port_or_i2c_device`
   `predicate=typec_port_or_i2c_device`
   `/sys/class/typec/port0`
   `/sys/bus/i2c/devices/57-0066`
   `reboot_request=download`
   `download_beacon=1`
   `true_action=reboot_download`
   `false_action=park`
   `download-beacon-hit`
   `download-beacon-miss-parked-manual-download-required`
   `host-visible HIT = new Odin Download endpoint appears`
   `MISS = no new Odin endpoint during bounded observation; manual Download rollback required`
   `no configfs gadget setup`
   `no UDC bind`
   `no TypeC role write`
   `no ssusb role write`
   `no FunctionFS`
   `no stock composite`
   `no Android/Magisk handoff`
   `no persistent partition mount`
   `no block write`
   `no charge-current write`
   `no OTG/VBUS boost write`
   `no regulator/GDSC/GPIO/raw PMIC write`
   `manual Download rollback is recovery-only`
   `PMIC/RDX abnormal reset before the observation window is FAIL`
   `sec_debug_region.ko present due stock charger dependency`
   `requires_s7a_specific_live_risk_review`
   `gpi.ko`
   `msm-geni-se.ko`
   `i2c-msm-geni.ko`
   `qcom-i2c-pmic.ko`
   `mfd_max77705.ko`
   `max77705_charger.ko`
   `max77705-fuelgauge.ko`
   `pdic_max77705.ko`
   `charger-ulog-glink.ko`
   `altmode-glink.ko`
   `msm-geni-se.ko`
   `gpi.ko`
   `charger-ulog-glink.ko`
   `altmode-glink.ko`
   `qti-regmap-debugfs.ko`
   `qcom-i2c-pmic.ko`
   `i2c-msm-geni.ko`
   `sec_pm_log.ko`
   `qcom-cpufreq-hw.ko`
   `sched-walt.ko`
   `kryo_arm64_edac.ko`
   `memory_dump_v2.ko`
   `sec_key_notifier.ko`
   `sec_crashkey_long.ko`
   `sec_debug_region.ko`
   `sec_param.ko`
   `sec_qc_dbg_partition.ko`
   `sec_qc_summary.ko`
   `sec_upload_cause.ko`
   `sec_qc_upload_cause.ko`
   `sec_qc_user_reset.ko`
   `sec_qc_smem.ko`
   `sec_qc_hw_param.ko`
   `sb-core.ko`
   `sec_pd.ko`
   `sec-battery.ko`
   `mfd_max77705.ko`
   `spu_verify.ko`
   `pdic_max77705.ko`
   `max77705_charger.ko`
   `max77705-fuelgauge.ko`
   `memory_dump_v2.ko`
   `sec_debug_region.ko`
   `sec_param.ko`
   `sec_qc_dbg_partition.ko`
   `sec_qc_summary.ko`
   `sec_upload_cause.ko`
   `sec_qc_upload_cause.ko`
   `sec_qc_user_reset.ko`
   `smem.ko`
   `minidump.ko`
   `sec_debug.ko`
   `qcom_ipc_logging.ko`
   `cmd-db.ko`
   `qcom_rpmh.ko`
   `clk-rpmh.ko`
   `debug-regulator.ko`
   `proxy-consumer.ko`
   `gdsc-regulator.ko`
   `clk-qcom.ko`
   `clk-dummy.ko`
   `gcc-waipio.ko`
   `icc-bcm-voter.ko`
   `icc-debug.ko`
   `socinfo.ko`
   `icc-rpmh.ko`
   `rpmh-regulator.ko`
   `qcom-scm.ko`
   `qcom_wdt_core.ko`
   `gh_virt_wdt.ko`
   `iommu-logger.ko`
   `qnoc-qos.ko`
   `qnoc-waipio.ko`
   `phy-generic.ko`
   `qcom_iommu_util.ko`
   `sec_class.ko`
   `secure_buffer.ko`
   `arm_smmu.ko`
   `msm-geni-se.ko`
   `gpi.ko`
   `qmi_helpers.ko`
   `qcom_glink.ko`
   `qcom_glink_smem.ko`
   `qcom_smd.ko`
   `rproc_qcom_common.ko`
   `pdr_interface.ko`
   `pmic_glink.ko`
   `charger-ulog-glink.ko`
   `altmode-glink.ko`
   `eud.ko`
   `qti-regmap-debugfs.ko`
   `qcom-i2c-pmic.ko`
   `phy-msm-ssusb-qmp.ko`
   `abc.ko`
   `usb_notify_layer.ko`
   `switch_class.ko`
   `common_muic.ko`
   `vbus_notifier.ko`
   `pdic_notifier_module.ko`
   `usb_typec_manager.ko`
   `usb_f_ss_mon_gadget.ko`
   `phy-msm-snps-hs.ko`
   `repeater.ko`
   `phy-msm-snps-eusb2.ko`
   `redriver.ko`
   `if_cb_manager.ko`
   `qc_usb_audio.ko`
   `dwc3-msm.ko`
   `usb_f_ss_acm.ko`
   `ucsi_glink.ko`
   `i2c-msm-geni.ko`
   `sec_pm_log.ko`
   `qcom-cpufreq-hw.ko`
   `sched-walt.ko`
   `kryo_arm64_edac.ko`
   `memory_dump_v2.ko`
   `sec_key_notifier.ko`
   `sec_crashkey_long.ko`
   `sec_debug_region.ko`
   `sec_param.ko`
   `sec_qc_dbg_partition.ko`
   `sec_qc_summary.ko`
   `sec_upload_cause.ko`
   `sec_qc_upload_cause.ko`
   `sec_qc_user_reset.ko`
   `sec_qc_smem.ko`
   `sec_qc_hw_param.ko`
   `sb-core.ko`
   `sec_pd.ko`
   `sec-battery.ko`
   `mfd_max77705.ko`
   `spu_verify.ko`
   `pdic_max77705.ko`
   `max77705_charger.ko`
   `max77705-fuelgauge.ko`

   **Consumed exception (2026-07-09, S22+ M34 S7A2 GENI I2C
   runtime-gadget boot-only live gate):** this one-shot exception was consumed
   by the 2026-07-09 KST live run. It flashed the pinned M34 S7A2 boot-only
   candidate once on the Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s7a2_geni_i2c_live_gate.py`.
   The consumed live and rollback ack token strings are intentionally omitted
   here as active authorization.

   The exact candidate AP.tar.md5 SHA256 must be
   `cb89ccf9c8c5481938ddd415930c78a23e1a679d45fdc57f95e6d1b48776bd59`; contained padded `boot.img` SHA256 must be
   `b9a4d4c2170da2ed6125aa44734005303d81d874b72402513def97b2f8406a54`; direct `/init` SHA256 must be
   `8f8eb4a6f4d94bc552ec61819b9c2b4ea4ec4de7fb7aa097fab7193c6f117e5a`; template source SHA256 must be
   `ce12ea11a6c0f73f5f042801435b419637b473eff6631155f45d4ad382d8a80a`; module-list SHA256 must be
   `c0c35e02fe61a3f6c18c221a9ae2cc1a54aafd38374117fa954dbfa675700998`; preserved kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`; and known-booting base Magisk boot SHA256
   must be `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`. The AP must contain exactly one
   tar member, `boot.img.lz4`, and must not carry recovery, vendor_boot, dtbo,
   vbmeta, vbmeta_system, BL, CP, CSC, super, persist, userdata, EFS,
   sec_efs, RPMB, keymaster, modem, bootloader, or any other partition payload.

   The candidate is limited to freestanding direct PID1 M34 S7A2 behavior.
   It starts from S7A, adds only the missing GENI I2C transport closure
   (`gpi.ko included`, `msm-geni-se.ko included`, `i2c-msm-geni.ko included`),
   keeps stock-ordered configfs gadget/function/config, `UDC=none`, stock IDs
   `0x04E8:0x6860`, `ss_acm.0 link`, no `g1/max_speed=high-speed`, no
   `/sys/class/usb_role`, no `ssusb/speed` high-speed write, read-only
   `ssusb/speed` marker, `ssusb/mode=peripheral`, final UDC bind,
   `UDC=a600000.dwc3`, no `soft_connect`, and no
   `/sys/class/udc/a600000.dwc3/soft_connect`.
   It must keep the stock max77705 PDIC altmode session-producer closure:
   `session_producer_parity=1`, `max77705_session=1`, `typec_readback=1`,
   `geni_i2c_transport=1`, `i2c_msm_geni=1`, `gpi_dma=1`, `msm_geni_se=1`,
   `functionfs=0`, `stock_composite=0`, `qmp_module=1`, `eud_module=1`,
   `ucsi_glink=1`, `phy-msm-ssusb-qmp.ko included`, `eud.ko included without
   EUD sysfs write`, `ucsi_glink.ko included`, `qcom-i2c-pmic.ko included`,
   `mfd_max77705.ko included`, `pdic_max77705.ko included`,
   `max77705_charger.ko included`, `max77705-fuelgauge.ko included`,
   `charger-ulog-glink.ko included`, and `altmode-glink.ko included`.
   The helper must treat `sec_debug_region.ko present due stock charger
   dependency`, `requires_s7a_specific_live_risk_review`, and
   `stage_s7a2_no_charge_otg_rail_gpio_writes` as explicit policy markers.
   S7A2 may read TypeC/UDC state through
   `/sys/class/typec/port0/data_role`, `/sys/class/typec/port0/power_role`,
   `/sys/class/typec/port0/port_type`, `/sys/class/typec/port0-partner/uevent`,
   `/sys/class/udc/a600000.dwc3/state`,
   `/sys/class/udc/a600000.dwc3/current_speed`, and
   `/sys/class/udc/a600000.dwc3/function`. Its only sysfs writes outside the
   prior S7A recipe are the bounded role-write discriminator after
   `phase=typec_partner_check`: if no partner is visible, write
   `data_role=device` only to `/sys/class/typec/port0/data_role` and
   `power_role=sink` only to `/sys/class/typec/port0/power_role`, record
   `phase=typec_role_write`, `role_device_rc=`, and `role_sink_rc=`, then bind
   UDC. It must not write charge current, OTG/VBUS boost, regulator, GDSC,
   GPIO, display, raw PMIC knobs, or EUD sysfs.
   It must make no descriptor or companion-function change, no FunctionFS
   change, and no `usb_f_conn_gadget.ko`/stock composite parity change. It must
   have no reboot syscall, no Download beacon, no Android/Magisk handoff, no
   persistent partition mount, no block write, no module binary injection into
   boot ramdisk, no raw host `dd`, no fastboot, no Magisk modules, no
   multidisabler, no format data, no DTBO/vendor_boot/recovery/vbmeta/non-boot
   flash, and no A90 action. Manual Download rollback is recovery-only after
   the helper requests it. Survival proof requires it survives past 60-90
   seconds; PMIC/RDX abnormal reset before the observation window is FAIL. The
   helper must collect enhanced host USB observation including
   `lsusb -d 04e8:6860 -v`, `usb-devices`, udev properties, and host dmesg
   delta. This exception does not authorize S1/S2/S3/S4/S5/S6 repeat,
   post-pullup command channels, DTBO surgery, M32 repeat, display/distro
   candidates, kernel rebuilds, RDX PC dump retrieval, EUD sysfs writes, or any
   non-boot partition action.

   Live result: candidate Odin flash succeeded, the original Download endpoint
   disconnected, and the candidate survived the full 90 s observation window.
   The operator observed no boot loop, then RDX/PMIC and manual Download entry
   for rollback. Across 18 candidate park snapshots, the host observed no
   Samsung `04e8:*` device, no `04e8:6860`, no CDC ACM, no `/dev/ttyACM*`, no
   ADB, no Odin endpoint, and no Samsung upload/download endpoint. The result
   was `survived-observation-window-manual-download-required`.

   Rollback used the returned Odin endpoint to flash the pinned Magisk
   boot-only rollback AP and restored the rooted Android baseline:
   `sys.boot_completed=1`, model `SM-S906N`, device `g0q`, bootloader/build
   `S906NKSS7FYG8`, vbstate `orange`, `boot_recovery=0`, Magisk root present,
   and boot partition SHA256 restored to
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
   Retained evidence did not contain the S7A2 marker: pstore was empty and
   `/proc/last_kmsg` was readable but marker-absent.

   This consumed exception authorizes no additional S7A2 run, no S1/S2/S3/S4/
   S5/S6/S7A repeat, no post-pullup command channel, no descriptor/composition
   pivot, no DTBO surgery, no M32 repeat, no display/distro candidate, no
   kernel rebuild, no RDX PC dump retrieval, no EUD sysfs write, no non-boot
   flash, no raw host `dd`, no fastboot, no Magisk module, no multidisabler,
   no format data, and no A90 action. Future S22+ native-init live flashes
   require a fresh, narrower exception for the selected artifact and observation
   path.

   Historical policy marker coverage for the consumed run:
   `S22+ M34 S7A2 GENI I2C runtime-gadget native-init boot-only`
   `workspace/public/src/scripts/revalidation/s22plus_m34_s7a2_geni_i2c_live_gate.py`
   `consumed-live-ack-token-omitted`
   `consumed-rollback-ack-token-omitted`
   `SM-S906N/g0q/S906NKSS7FYG8`
   `S7A2`
   `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S7A2`
   `cb89ccf9c8c5481938ddd415930c78a23e1a679d45fdc57f95e6d1b48776bd59`
   `b9a4d4c2170da2ed6125aa44734005303d81d874b72402513def97b2f8406a54`
   `8f8eb4a6f4d94bc552ec61819b9c2b4ea4ec4de7fb7aa097fab7193c6f117e5a`
   `c0c35e02fe61a3f6c18c221a9ae2cc1a54aafd38374117fa954dbfa675700998`
   `ce12ea11a6c0f73f5f042801435b419637b473eff6631155f45d4ad382d8a80a`
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
   `stock-ordered configfs gadget/function/config`
   `UDC=none`
   `0x04E8:0x6860`
   `ss_acm.0 link`
   `no g1/max_speed=high-speed`
   `no /sys/class/usb_role`
   `no ssusb/speed high-speed write`
   `read-only ssusb speed marker`
   `ssusb/mode=peripheral`
   `final UDC bind`
   `UDC=a600000.dwc3`
   `no soft_connect`
   `no /sys/class/udc/a600000.dwc3/soft_connect`
   `stock max77705 PDIC altmode session-producer closure`
   `GENI I2C transport closure`
   `session_producer_parity=1`
   `max77705_session=1`
   `typec_readback=1`
   `geni_i2c_transport=1`
   `i2c_msm_geni=1`
   `gpi_dma=1`
   `msm_geni_se=1`
   `role_write_discriminator=1`
   `phase=typec_partner_check`
   `phase=typec_role_write`
   `role_device_rc=`
   `role_sink_rc=`
   `data_role=device`
   `power_role=sink`
   `functionfs=0`
   `stock_composite=0`
   `/sys/class/typec/port0/data_role`
   `/sys/class/typec/port0/power_role`
   `/sys/class/typec/port0/port_type`
   `/sys/class/typec/port0-partner/uevent`
   `/sys/class/udc/a600000.dwc3/state`
   `/sys/class/udc/a600000.dwc3/current_speed`
   `/sys/class/udc/a600000.dwc3/function`
   `qmp_module=1`
   `eud_module=1`
   `ucsi_glink=1`
   `phy-msm-ssusb-qmp.ko included`
   `eud.ko included without EUD sysfs write`
   `ucsi_glink.ko included`
   `qcom-i2c-pmic.ko included`
   `gpi.ko included`
   `msm-geni-se.ko included`
   `i2c-msm-geni.ko included`
   `mfd_max77705.ko included`
   `pdic_max77705.ko included`
   `max77705_charger.ko included`
   `max77705-fuelgauge.ko included`
   `charger-ulog-glink.ko included`
   `altmode-glink.ko included`
   `sec_debug_region.ko present due stock charger dependency`
   `requires_s7a_specific_live_risk_review`
   `stage_s7a2_no_charge_otg_rail_gpio_writes`
   `no descriptor or companion-function change`
   `enhanced host USB observation`
   `lsusb -d 04e8:6860 -v`
   `usb-devices`
   `udev properties`
   `host dmesg delta`
   `no reboot syscall`
   `no Download beacon`
   `no Android/Magisk handoff`
   `no persistent partition mount`
   `no block write`
   `manual Download rollback is recovery-only`
   `survives past 60-90 seconds`
   `PMIC/RDX abnormal reset before the observation window is FAIL`
   `no EUD sysfs write`
   `no charge-current write`
   `no OTG/VBUS boost write`
   `no regulator/GDSC/GPIO/raw PMIC write`
   `gpi.ko`
   `msm-geni-se.ko`
   `i2c-msm-geni.ko`
   `gpi.ko`
   `msm-geni-se.ko`
   `i2c-msm-geni.ko`
   `qcom-i2c-pmic.ko`
   `mfd_max77705.ko`
   `max77705_charger.ko`
   `max77705-fuelgauge.ko`
   `pdic_max77705.ko`
   `charger-ulog-glink.ko`
   `altmode-glink.ko`
   `msm-geni-se.ko`
   `gpi.ko`
   `charger-ulog-glink.ko`
   `altmode-glink.ko`
   `qti-regmap-debugfs.ko`
   `qcom-i2c-pmic.ko`
   `i2c-msm-geni.ko`
   `sec_pm_log.ko`
   `qcom-cpufreq-hw.ko`
   `sched-walt.ko`
   `kryo_arm64_edac.ko`
   `memory_dump_v2.ko`
   `sec_key_notifier.ko`
   `sec_crashkey_long.ko`
   `sec_debug_region.ko`
   `sec_param.ko`
   `sec_qc_dbg_partition.ko`
   `sec_qc_summary.ko`
   `sec_upload_cause.ko`
   `sec_qc_upload_cause.ko`
   `sec_qc_user_reset.ko`
   `sec_qc_smem.ko`
   `sec_qc_hw_param.ko`
   `sb-core.ko`
   `sec_pd.ko`
   `sec-battery.ko`
   `mfd_max77705.ko`
   `spu_verify.ko`
   `pdic_max77705.ko`
   `max77705_charger.ko`
   `max77705-fuelgauge.ko`
   `memory_dump_v2.ko`
   `sec_debug_region.ko`
   `sec_param.ko`
   `sec_qc_dbg_partition.ko`
   `sec_qc_summary.ko`
   `sec_upload_cause.ko`
   `sec_qc_upload_cause.ko`
   `sec_qc_user_reset.ko`
   `smem.ko`
   `minidump.ko`
   `sec_debug.ko`
   `qcom_ipc_logging.ko`
   `cmd-db.ko`
   `qcom_rpmh.ko`
   `clk-rpmh.ko`
   `debug-regulator.ko`
   `proxy-consumer.ko`
   `gdsc-regulator.ko`
   `clk-qcom.ko`
   `clk-dummy.ko`
   `gcc-waipio.ko`
   `icc-bcm-voter.ko`
   `icc-debug.ko`
   `socinfo.ko`
   `icc-rpmh.ko`
   `rpmh-regulator.ko`
   `qcom-scm.ko`
   `qcom_wdt_core.ko`
   `gh_virt_wdt.ko`
   `iommu-logger.ko`
   `qnoc-qos.ko`
   `qnoc-waipio.ko`
   `phy-generic.ko`
   `qcom_iommu_util.ko`
   `sec_class.ko`
   `secure_buffer.ko`
   `arm_smmu.ko`
   `msm-geni-se.ko`
   `gpi.ko`
   `qmi_helpers.ko`
   `qcom_glink.ko`
   `qcom_glink_smem.ko`
   `qcom_smd.ko`
   `rproc_qcom_common.ko`
   `pdr_interface.ko`
   `pmic_glink.ko`
   `charger-ulog-glink.ko`
   `altmode-glink.ko`
   `eud.ko`
   `qti-regmap-debugfs.ko`
   `qcom-i2c-pmic.ko`
   `phy-msm-ssusb-qmp.ko`
   `abc.ko`
   `usb_notify_layer.ko`
   `switch_class.ko`
   `common_muic.ko`
   `vbus_notifier.ko`
   `pdic_notifier_module.ko`
   `usb_typec_manager.ko`
   `usb_f_ss_mon_gadget.ko`
   `phy-msm-snps-hs.ko`
   `repeater.ko`
   `phy-msm-snps-eusb2.ko`
   `redriver.ko`
   `if_cb_manager.ko`
   `qc_usb_audio.ko`
   `dwc3-msm.ko`
   `usb_f_ss_acm.ko`
   `ucsi_glink.ko`
   `i2c-msm-geni.ko`
   `sec_pm_log.ko`
   `qcom-cpufreq-hw.ko`
   `sched-walt.ko`
   `kryo_arm64_edac.ko`
   `memory_dump_v2.ko`
   `sec_key_notifier.ko`
   `sec_crashkey_long.ko`
   `sec_debug_region.ko`
   `sec_param.ko`
   `sec_qc_dbg_partition.ko`
   `sec_qc_summary.ko`
   `sec_upload_cause.ko`
   `sec_qc_upload_cause.ko`
   `sec_qc_user_reset.ko`
   `sec_qc_smem.ko`
   `sec_qc_hw_param.ko`
   `sb-core.ko`
   `sec_pd.ko`
   `sec-battery.ko`
   `mfd_max77705.ko`
   `spu_verify.ko`
   `pdic_max77705.ko`
   `max77705_charger.ko`
   `max77705-fuelgauge.ko`
   **Consumed exception (2026-07-09, S22+ M34 S7A session-producer
   runtime-gadget boot-only live gate):** this one-shot exception was consumed
   by the 2026-07-09 KST live run. It flashed the pinned M34 S7A boot-only
   candidate once on the Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s7a_session_producer_live_gate.py`.
   The consumed live and rollback ack token strings are intentionally omitted
   here as active authorization.

   The exact target was `SM-S906N/g0q/S906NKSS7FYG8`; stage `S7A`; AP marker
   `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S7A`; exact candidate AP.tar.md5
   SHA256 `b533d8e218aa4842c941f86075ce770cf60a67a179939dd4d552d22767376267`;
   contained padded `boot.img` SHA256
   `5e1a0758008651eb5a22b82fd91d4c2549ba756a4ed885779a0934688e129e49`;
   direct `/init` SHA256
   `22e1f7e9346c61c876253a6e194d64d55adc3e24571ed2b10d76e4c09cef1914`;
   template source SHA256
   `388d9f187bb1dfa1877c99cc2f8481bb2f191aec2ac66131785e9d70e17e71ad`;
   module-list SHA256
   `eb1ddfe7ac9a481b9dacae696c72b876e82d6e8ac4681772df825995a162001c`;
   preserved kernel SHA256
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`;
   and known-booting base Magisk boot SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
   The AP contained exactly one tar member, `boot.img.lz4`, and did not carry
   recovery, vendor_boot, dtbo, vbmeta, vbmeta_system, BL, CP, CSC, super,
   persist, userdata, EFS, sec_efs, RPMB, keymaster, modem, bootloader, or any
   other partition payload.

   Live result: candidate Odin flash succeeded, the original Download endpoint
   disconnected, and the candidate survived the full 90 s observation window.
   The operator observed no boot loop, then RDX/PMIC and manual Download entry
   for rollback. Across 18 candidate park snapshots, the host observed no
   Samsung `04e8:*` device, no `04e8:6860`, no CDC ACM, no `/dev/ttyACM*`, no
   ADB, no Odin endpoint, and no Samsung upload/download endpoint. The result
   was `survived-observation-window-manual-download-required`.

   Rollback used the returned Odin endpoint to flash the pinned Magisk
   boot-only rollback AP and restored the rooted Android baseline:
   `sys.boot_completed=1`, model `SM-S906N`, device `g0q`, bootloader/build
   `S906NKSS7FYG8`, vbstate `orange`, `boot_recovery=0`, Magisk root present,
   and boot partition SHA256 restored to
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
   Retained evidence did not contain the S7A marker: pstore was empty and
   `/proc/last_kmsg` was readable but marker-absent.

   This consumed exception authorizes no additional S7A run, no S1/S2/S3/S4/S5/S6
   repeat, no post-pullup command channel, no DTBO surgery, no M32 repeat, no
   display/distro candidate, no kernel rebuild, no RDX PC dump retrieval, no
   EUD sysfs write, no non-boot flash, no raw host `dd`, no fastboot, no Magisk
   module, no multidisabler, no format data, and no A90 action. Future S22+
   native-init live flashes require a fresh, narrower exception for the selected
   artifact and observation path.
   **Consumed exception (2026-07-09, S22+ M34 S6 stock-speed softdep
   runtime-gadget boot-only live gate):** this one-shot exception was consumed
   by the 2026-07-09 KST live run. It flashed the pinned M34 S6 boot-only
   candidate once on the Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s6_stock_softdep_live_gate.py`.
   The consumed live and rollback ack token strings are intentionally omitted
   here as active authorization.

   The exact target was `SM-S906N/g0q/S906NKSS7FYG8`; stage `S6`; AP marker
   `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S6`; exact candidate AP.tar.md5
   SHA256 `f1ff77b7df434536029db417291689bff8b3a7dcdf4fda38fef5322475daad39`;
   contained padded `boot.img` SHA256
   `b1bfc4ece7ece60af752bc570e0ae4ce76230d13b129b1c58d4e840cd92225f6`;
   direct `/init` SHA256
   `ca3eb2b5a0fedff73cfb0aaa249d42f4b92fcb99b360e9ec5a041649dcd7dd8c`;
   template source SHA256
   `ce023ba98006e49839433ce16ec8321bd9003b74151f39879fcecb682fef9ecc`;
   module-list SHA256
   `51ba77aeed1966a2de8c78d307ca3d6fe5440daa2b96488679446f6056142515`;
   preserved kernel SHA256
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`;
   and known-booting base Magisk boot SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
   The AP contained exactly one tar member, `boot.img.lz4`, and did not carry
   recovery, vendor_boot, dtbo, vbmeta, vbmeta_system, BL, CP, CSC, super,
   persist, userdata, EFS, sec_efs, RPMB, keymaster, modem, bootloader, or any
   other partition payload.

   Live result: candidate Odin flash succeeded, the original Download endpoint
   disconnected, and the candidate survived the full 90 s observation window.
   The operator observed no boot loop, then RDX/PMIC and manual Download entry
   for rollback. Across 17 candidate park snapshots, the host observed no
   Samsung `04e8:*` device, no `04e8:6860`, no CDC ACM, no `/dev/ttyACM*`, no
   ADB, no Odin endpoint, and no Samsung upload/download endpoint. The result
   was `survived-observation-window-manual-download-required`.

   Rollback used the returned Odin endpoint to flash the pinned Magisk boot-only
   rollback AP and restored the rooted Android baseline: `sys.boot_completed=1`,
   model `SM-S906N`, device `g0q`, bootloader/build `S906NKSS7FYG8`, vbstate
   `orange`, `boot_recovery=0`, Magisk root present, and boot partition SHA256
   restored to
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
   Retained evidence did not contain the S6 marker: pstore was empty and
   `/proc/last_kmsg` was readable but marker-absent.

   This consumed exception authorizes no additional S6 run, no S1/S2/S3/S4/S5
   repeat, no post-pullup command channel, no DTBO surgery, no M32 repeat, no
   display/distro candidate, no kernel rebuild, no RDX PC dump retrieval, no
   EUD sysfs write, no non-boot flash, no raw host `dd`, no fastboot, no Magisk
   module, no multidisabler, no format data, and no A90 action. Future S22+
   native-init live flashes require a fresh, narrower exception for the selected
   artifact and observation path.
   **Consumed exception (2026-07-09, S22+ M34 S5 soft-connect
   runtime-gadget boot-only live gate):** this one-shot exception was consumed by
   the 2026-07-09 KST live run. It flashed the pinned M34 S5 boot-only
   candidate once on the Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s5_soft_connect_live_gate.py`.
   The consumed live and rollback ack token strings are intentionally omitted
   here as active authorization. The exact target was
   `SM-S906N/g0q/S906NKSS7FYG8`; stage `S5`; AP marker
   `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S5`; exact candidate AP.tar.md5
   SHA256 `3a63dc339577d4aaf550159743b81edd9c1318ef5c6c4b745ed363f171d30d5e`;
   contained padded `boot.img` SHA256
   `09751f5fce9f25be3ce7b814f00c04cafd22ae9a96d8c69ab9d52b6274951a95`;
   direct `/init` SHA256
   `efecaf1842aff95907b2f2780dc12531b0980acff6cbe64f789e9ad4b6c3c55c`;
   template source SHA256
   `bf90fbadbaf72bb9287150d769104b97ec8faaae0ce1c0591aaafdeb88004fb8`;
   module-list SHA256
   `2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`;
   preserved kernel SHA256
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`;
   and base Magisk boot SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`. The AP
   contained exactly one tar member, `boot.img.lz4`, and did not carry recovery,
   vendor_boot, dtbo, vbmeta, vbmeta_system, BL, CP, CSC, super, persist,
   userdata, EFS, sec_efs, RPMB, keymaster, modem, bootloader, or any other
   partition payload.

   Live result: candidate flash succeeded, original Download endpoint
   disconnected, and S5 parked long enough for 15 host snapshots through
   73.950 seconds. During all candidate snapshots, Samsung `04e8:6860`, CDC
   ACM, `/dev/ttyACM*`, and ADB stayed absent. At 73.950 seconds a normal Odin
   endpoint appeared before the 90 second survival window, so the result was
   `unexpected_odin_before_survival_window`, not ACM enumeration and not a
   survival pass. The checked helper immediately flashed the pinned Magisk
   boot-only rollback AP from that Odin endpoint. Final baseline returned clean:
   Android `sys.boot_completed=1`, build/bootloader `S906NKSS7FYG8`, vbstate
   `orange`, Magisk root present, and boot partition SHA256 restored to
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
   (confirmed by helper and post-live independent `dd | sha256sum`). Retained
   evidence had no M34 S5 marker: pstore empty, `/proc/last_kmsg` readable at
   2,097,136 bytes, marker absent. This exception must not be reused for S5
   repeat, S1/S2/S3/S4 repeat, DTBO surgery, descriptor/function parity live
   work, post-pullup command channels, M32 repeat, display/distro candidates,
   kernel rebuilds, RDX PC dump retrieval, EUD writes, non-boot flash, raw host
   `dd`, fastboot, Magisk modules, multidisabler, format data, or any A90
   action. Future S22+ native-init live flashes need a fresh, narrower
   exception for the selected artifact and observation path.
   **Consumed exception (2026-07-09, S22+ M34 S4 ssusb role-lever
   runtime-gadget boot-only live gate):** this one-shot exception was consumed by
   the 2026-07-09 KST live run. It flashed the pinned M34 S4 boot-only
   candidate once on the Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s4_role_lever_live_gate.py`.
   The consumed live and rollback ack token strings are intentionally omitted
   here as active authorization. The exact target was
   `SM-S906N/g0q/S906NKSS7FYG8`; stage `S4`; AP marker
   `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S4`; exact candidate AP.tar.md5
   SHA256 `9d93eb5c3c4fec3c02c920b2c80435a76b7c161079d906940a3279fc77495cc9`;
   contained padded `boot.img` SHA256
   `153ceff9877351d55448de7839ec52f7631485c006a68971ca7ea14fc9dd11c5`;
   direct `/init` SHA256
   `ee73a26d65649346e8cae830ee9bb229152d0a8001c2bc8fc48e536fdc08fb96`;
   template source SHA256
   `51ec34f669f35f81a41411c82613ece65924c3a16b4bc5619e670e05b3231065`;
   module-list SHA256
   `2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`;
   preserved kernel SHA256
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`;
   and base Magisk boot SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`. The AP
   contained exactly one tar member, `boot.img.lz4`, and did not carry recovery,
   vendor_boot, dtbo, vbmeta, vbmeta_system, BL, CP, CSC, super, persist,
   userdata, EFS, sec_efs, RPMB, keymaster, modem, bootloader, or any other
   partition payload.

   Live result: candidate flash succeeded, original Download endpoint
   disconnected, S4 survived the full 90 second observation window, and across
   17 enhanced host USB snapshots no Samsung `04e8:6860`, CDC ACM, `/dev/ttyACM*`,
   ADB, or Odin endpoint appeared during the park window. The result is
   `survived-observation-window-manual-download-required`: the stock-kernel
   `ssusb/speed=high-speed` plus `ssusb/mode=peripheral` role lever is not the
   reset boundary, but it also did not make the ACM endpoint enumerate. Manual
   Download rollback was then performed through the checked helper, the pinned
   Magisk boot-only rollback AP flashed successfully, Android returned with
   `sys.boot_completed=1`, build/bootloader `S906NKSS7FYG8`, vbstate `orange`,
   Magisk root present, and boot partition SHA256 restored to
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`. Retained
   evidence collection found empty pstore and readable `/proc/last_kmsg`
   (2,097,136 bytes) but did not contain the M34 S4 marker. This exception must
   not be reused for another S4 flash, S1/S2/S3 repeat, DTBO surgery, post-pullup
   command channels, RDX PC dump retrieval, EUD writes, kernel rebuilds,
   non-boot flash, raw host `dd`, fastboot, Magisk modules, format data, or any
   A90 action. Future live work needs a fresh, narrower exception for the
   selected next candidate and observation path.

   **Consumed exception (2026-07-09, S22+ M34 S3 UDC-pullup runtime-gadget
   native-init boot-only live gate):** this one-shot exception was consumed by
   the 2026-07-09 KST live run. It flashed the pinned M34 S3 boot-only
   candidate once on the Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s3_runtime_gadget_live_gate.py`.
   The consumed live and rollback ack token strings are intentionally omitted
   here as active authorization. The exact target was
   `SM-S906N/g0q/S906NKSS7FYG8`; stage `S3`; AP marker
   `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S3`; exact candidate AP.tar.md5
   SHA256 `0ef55db2d38bec3df83cb77cd83f8ee6644054447ae7da10f8ecaecc8faa2957`;
   contained padded `boot.img` SHA256
   `87351f4955740aa4d83567406567c1ef4d6fcfa217d9ee5b0d7c446f2db09142`;
   direct `/init` SHA256
   `2f391e50ff271b2dfe14dce31dbfdd0f0fb2b6d353ae89a2079acad5b46e668f`;
   template source SHA256
   `ac20dcf724cf6864540d65958332d561d45409e7e85785a8c014882b37e29193`;
   module-list SHA256
   `2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`;
   preserved kernel SHA256
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`;
   and base Magisk boot SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`. The AP
   contained exactly one tar member, `boot.img.lz4`, and did not carry recovery,
   vendor_boot, dtbo, vbmeta, vbmeta_system, BL, CP, CSC, super, persist,
   userdata, EFS, sec_efs, RPMB, keymaster, modem, bootloader, or any other
   partition payload.

   The candidate was limited to freestanding direct PID1
   `S22+ M34 S3 UDC-pullup runtime-gadget native-init boot-only` behavior:
   stock-ordered configfs gadget/function/config, `UDC=none`, stock IDs
   `0x04E8:0x6860`, `ss_acm.0 link`, `max_speed=high-speed`,
   `usb_role=device`, final UDC bind, and `UDC=a600000.dwc3`; with no reboot
   syscall, no Download beacon, no Android/Magisk handoff, no persistent
   partition mount, no block write, no module binary injection into boot
   ramdisk, no raw host `dd`, no fastboot, no Magisk modules, no multidisabler,
   no format data, no DTBO/vendor_boot/recovery/vbmeta/non-boot flash, and no
   A90 action. `phy-msm-ssusb-qmp.ko intentionally excluded`; `EUD excluded`.

   Live result: the original Download endpoint disconnected after candidate
   flash, and M34 S3 survived the full 90 second observation window with no
   ADB/Odin/ACM endpoint returning across 18 host snapshots. This proves final
   `UDC=a600000.dwc3` bind/pullup, when applied after the S2-proven configfs
   plus pullup-knob setup, is not the observed reset boundary. It does not prove
   ACM transport usability, because no host `/dev/ttyACM*` endpoint appeared.
   Manual rollback was then required; the operator observed RDX while entering
   manual rollback, a normal Download endpoint later appeared, and the checked
   helper flashed the pinned Magisk boot rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
   successfully. Final baseline was clean: Android boot complete, bootanim
   stopped, vbstate orange, Magisk root present, bootloader/build
   `S906NKSS7FYG8`, and boot partition SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
   Post-rollback pstore was empty and `/proc/last_kmsg` was readable at
   2,097,136 bytes but did not contain the M34 S3 marker. This exception must
   not be reused and does not authorize S3 repeat, post-pullup command channels,
   DTBO surgery, M32 repeat, display/distro candidates, kernel rebuilds, RDX PC
   dump retrieval, EUD writes, raw host `dd`, fastboot, multidisabler, format
   data, non-boot partition action, or any A90 action.
   **Consumed exception (2026-07-09, S22+ M34 S2 pullup-knobs runtime-gadget
   native-init boot-only live gate):** this one-shot exception was consumed by
   the 2026-07-09 KST live run. It flashed the pinned M34 S2 boot-only
   candidate once on the Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s2_runtime_gadget_live_gate.py`.
   The consumed live and rollback ack token strings are intentionally omitted
   here as active authorization. The exact target was
   `SM-S906N/g0q/S906NKSS7FYG8`; stage `S2`; AP marker
   `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S2`; exact candidate AP.tar.md5
   SHA256 `d235e6fd7c77c9fc2b63bd7280dcbf430783c9b62b5f361f43441c24687c38b3`;
   contained padded `boot.img` SHA256
   `f8838867e0b0fab5ffe5aa8717565d9304f635ef04487596a0baeb03b2dd7a70`;
   direct `/init` SHA256
   `fba33555bcc73d834a7dbfe87dc5e6fe3b622184d163ae72d478e18a0ce653b8`;
   template source SHA256
   `ac20dcf724cf6864540d65958332d561d45409e7e85785a8c014882b37e29193`;
   module-list SHA256
   `2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`;
   preserved kernel SHA256
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`;
   and base Magisk boot SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`. The AP
   contained exactly one tar member, `boot.img.lz4`, and did not carry recovery,
   vendor_boot, dtbo, vbmeta, vbmeta_system, BL, CP, CSC, super, persist,
   userdata, EFS, sec_efs, RPMB, keymaster, modem, bootloader, or any other
   partition payload.

   The candidate was limited to freestanding direct PID1
   `S22+ M34 S2 pullup-knobs runtime-gadget native-init boot-only` behavior:
   stock-ordered configfs gadget/function/config, `UDC=none`, stock IDs
   `0x04E8:0x6860`, `ss_acm.0 link`, `max_speed=high-speed`, and
   `usb_role=device`; with no final UDC bind, no `UDC=a600000.dwc3`, no reboot
   syscall, no Download beacon, no Android/Magisk handoff, no persistent
   partition mount, no block write, no module binary injection into boot
   ramdisk, no raw host `dd`, no fastboot, no Magisk modules, no multidisabler,
   no format data, no DTBO/vendor_boot/recovery/vbmeta/non-boot flash, and no
   A90 action. `phy-msm-ssusb-qmp.ko intentionally excluded`; `EUD excluded`.

   Live result: the original Download endpoint disconnected after candidate
   flash, and M34 S2 survived the full 90 second observation window without
   ADB/Odin returning. This proves `max_speed=high-speed` plus
   `usb_role=device`, when applied after the S1-proven stock configfs setup but
   before final UDC bind, are not the observed reset boundary. Manual rollback
   was then required; the operator observed RDX while entering manual rollback,
   a normal Download endpoint later appeared, and the checked helper flashed
   the pinned Magisk boot rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
   successfully. Final baseline was clean: Android boot complete, bootanim
   stopped, vbstate orange, Magisk root present, bootloader/build
   `S906NKSS7FYG8`, and boot partition SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
   Post-rollback pstore was empty and `/proc/last_kmsg` was readable at
   2,097,136 bytes but did not contain the M34 S2 marker. This exception must
   not be reused and does not authorize S2 repeat, S3 live, final UDC pullup,
   DTBO surgery, M32 repeat, display/distro candidates, kernel rebuilds, RDX PC
   dump retrieval, EUD writes, raw host `dd`, fastboot, multidisabler, format
   data, non-boot partition action, or any A90 action.
   **Consumed exception (2026-07-09, S22+ M34 S1 stock configfs runtime-gadget
   native-init boot-only live gate):** this one-shot exception was consumed by
   the 2026-07-09 KST live run. It flashed the pinned M34 S1 boot-only
   candidate once on the Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s1_runtime_gadget_live_gate.py`.
   The consumed live and rollback ack token strings are intentionally omitted
   here as active authorization. The exact target was
   `SM-S906N/g0q/S906NKSS7FYG8`; stage `S1`; AP marker
   `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S1`; exact candidate AP.tar.md5
   SHA256 `77e8858ea6becc3e988232d464f97827f55594f16ed6edebd23c3529c972d237`;
   contained padded `boot.img` SHA256
   `bb46233068890bb6849c63b4dab845ca48b65a9ffeac9e24ad08e81416b63f85`;
   direct `/init` SHA256
   `5339170f3138843a8f8da6cfd5f20f85696d3a9d18ae22bda439e21d0dd259cd`;
   template source SHA256
   `ac20dcf724cf6864540d65958332d561d45409e7e85785a8c014882b37e29193`;
   module-list SHA256
   `2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`;
   preserved kernel SHA256
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`;
   and base Magisk boot SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`. The AP
   contained exactly one tar member, `boot.img.lz4`, and did not carry recovery,
   vendor_boot, dtbo, vbmeta, vbmeta_system, BL, CP, CSC, super, persist,
   userdata, EFS, sec_efs, RPMB, keymaster, modem, bootloader, or any other
   partition payload.

   The candidate was limited to freestanding direct PID1
   `S22+ M34 S1 stock configfs runtime-gadget native-init boot-only` behavior:
   stock-ordered configfs gadget/function/config, `UDC=none`, stock IDs
   `0x04E8:0x6860`, and `ss_acm.0 link`; with no `max_speed=high-speed`, no
   `usb_role=device`, no final UDC bind, no `UDC=a600000.dwc3`, no reboot
   syscall, no Download beacon, no Android/Magisk handoff, no persistent
   partition mount, no block write, no module binary injection into boot
   ramdisk, no raw host `dd`, no fastboot, no Magisk modules, no multidisabler,
   no format data, no DTBO/vendor_boot/recovery/vbmeta/non-boot flash, and no
   A90 action. `phy-msm-ssusb-qmp.ko intentionally excluded`; `EUD excluded`.

   Live result: the original Download endpoint disconnected after candidate
   flash, and M34 S1 survived the full 90 second observation window without
   ADB/Odin returning. This proves stock-ordered configfs gadget/function/
   config creation, `UDC=none`, and the `ss_acm.0` link are not the observed
   35 second reset boundary when max-speed, role forcing, and final UDC pullup
   are absent. Manual rollback was then required; the operator observed RDX
   while entering manual rollback, a normal Download endpoint later appeared,
   and the checked helper flashed the pinned Magisk boot rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
   successfully. Final baseline was clean: Android boot complete, bootanim
   stopped, vbstate orange, Magisk root present, bootloader/build
   `S906NKSS7FYG8`, and boot partition SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
   Post-rollback pstore was empty and `/proc/last_kmsg` was readable at
   2,097,136 bytes but did not contain the M34 S1 marker. This exception must
   not be reused and does not authorize S1 repeat, S2/S3 live, final UDC
   pullup, DTBO surgery, M32 repeat, display/distro candidates, kernel rebuilds,
   RDX PC dump retrieval, EUD writes, raw host `dd`, fastboot, multidisabler,
   format data, non-boot partition action, or any A90 action.
   **Consumed exception (2026-07-09, S22+ M33 P30 watchdog-prefix park
   native-init boot-only live gate):** this one-shot exception was consumed by
   the 2026-07-09 KST live run. It flashed the pinned M33 P30 boot-only
   candidate once on the Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m33_p30_wdt_prefix_park_live_gate.py`.
   The consumed live and rollback ack token strings are intentionally omitted
   here as active authorization. The exact target was
   `SM-S906N/g0q/S906NKSS7FYG8`; selected variant `P30`; AP marker
   `S22_NATIVE_INIT_M33_WDT_PREFIX_PARK_P30`; exact candidate AP.tar.md5
   SHA256 `e7cadd856da852e577adf32e088c0fee668904f265cdad1e9309072ccb2b18fd`;
   contained padded `boot.img` SHA256
   `0a972bcb4af2b75d5177ae9767e34a4caa8b8c94237afa708bb4a577b2ba7bfe`;
   direct `/init` SHA256
   `48afc2af4fc1bdbfa7724cbff02d68249fc75a62005da073d5092e6c12dd4baa`;
   module-list SHA256
   `2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`;
   generated source SHA256
   `88d05498dc8956c95799cd0e6edb3b7080a8cd5d12b662a17545a7de7ffadf68`;
   preserved kernel SHA256
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`;
   and base Magisk boot SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`. The AP
   contained exactly one tar member, `boot.img.lz4`, and did not carry recovery,
   vendor_boot, dtbo, vbmeta, vbmeta_system, BL, CP, CSC, super, persist,
   userdata, EFS, sec_efs, RPMB, keymaster, modem, bootloader, or any other
   partition payload. The candidate was limited to freestanding direct PID1
   watchdog-managed prefix park behavior with `prefix_targets=30` and
   `module_load_only=1`: it loaded the full-ACM-module-without-configfs prefix,
   including `usb_f_ss_acm.ko`, emitted kmsg phase markers, and parked with no
   runtime ACM/configfs binding.
   It had no runtime USB/configfs/ACM, no reboot syscall, no Download beacon,
   no Android/Magisk handoff, no persistent partition mount, no block write, no
   module binary injection into boot ramdisk, no raw host `dd`, no fastboot, no
   Magisk modules, no multidisabler, no format data, no DTBO/vendor_boot/
   recovery/vbmeta/non-boot flash, and no A90 action. Live result: the original
   Download endpoint disconnected after candidate flash, and P30 survived the
   full 90 second observation window without ADB/Odin returning. The operator
   then observed an RDX screen while entering manual rollback; a normal Download
   endpoint later appeared and the checked helper flashed the pinned Magisk
   boot rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
   successfully. Final baseline was clean: Android boot complete, bootanim
   stopped, vbstate orange, Magisk root present, bootloader/build
   `S906NKSS7FYG8`, and boot partition SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
   Post-rollback pstore was empty and `/proc/last_kmsg` was readable at
   2,097,136 bytes but did not contain the M33 P30 marker. The retained log did
   contain `collect_rr_data : upload_cause = PMIC abnormal reset`, `RDX is
   locked`, `PonReason.HARD_RESET = 1`, and XBL/PMIC abnormal reset material,
   matching the operator's RDX observation during manual rollback. This
   exception must not be reused and does not authorize P30 repeat, P40 live,
   M34 S1/S2/S3 live, M32 repeat, ACM/configfs runtime binding beyond this
   no-binding candidate, display/distro candidates, kernel rebuilds, recovery/
   vendor_boot/dtbo/vbmeta/non-boot flashes, RDX PC dump retrieval, EUD writes,
   raw host `dd`, fastboot, multidisabler, format data, or any A90 action.
   **Consumed exception (2026-07-09, S22+ M33 P28 watchdog-prefix park
   native-init boot-only live gate):** this one-shot exception was consumed by
   the 2026-07-09 KST live run. It flashed the pinned M33 P28 boot-only
   candidate once on the Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m33_p28_wdt_prefix_park_live_gate.py`.
   The consumed live and rollback ack token strings are intentionally omitted
   here as active authorization.
   The exact target string is `SM-S906N/g0q/S906NKSS7FYG8`; variant `P28`;
   marker `S22_NATIVE_INIT_M33_WDT_PREFIX_PARK_P28`; candidate AP.tar.md5
   SHA256 `4c76ef4df814356a7acfa9ce9a00c2fe003208ff8289c2874535e26b7e1c3f07`;
   contained padded `boot.img` SHA256
   `3bc59d6df58b5c7130e6ca531a6a6cd3a4d35e14ff7fd6667da72e2bd40e9e29`;
   direct `/init` SHA256
   `2ef661b9e5a1496674b6cc457c9b0e84c60ae7af01914c2403db602c6ebe84b1`;
   module-list SHA256
   `ef57a00fbef4b9c89936b30fc5c001974fbe9c2ece590c6a6984cb4695318a8f`;
   generated source SHA256
   `8d752ade0ee5100b5f91cb7fb15c09d24652a97e03721fb8c4d784d1f419f289`;
   preserved kernel SHA256
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`; and
   known booting base Magisk boot SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
   P28 is a `watchdog-managed prefix park`, `prefix_targets=28`,
   `module_load_only=1`, `DWC3-without-ACM prefix`. It has `no ACM function`,
   `no reboot syscall`, `no Download beacon`, and `no runtime USB/configfs/ACM`.
   The survival proof is `survives past 60-90 seconds` with no returned ADB or
   Odin endpoint; `PMIC/RDX abnormal reset before the observation window is
   FAIL`. `manual Download rollback is recovery-only` and must use the pinned
   Magisk boot-only AP first, with stock boot-only fallback only if Magisk
   rollback fails and Download mode remains available.
   The P28 module list is exactly: `smem.ko`, `minidump.ko`, `sec_debug.ko`,
   `qcom_ipc_logging.ko`, `cmd-db.ko`, `qcom_rpmh.ko`, `clk-rpmh.ko`,
   `debug-regulator.ko`, `proxy-consumer.ko`, `gdsc-regulator.ko`,
   `clk-qcom.ko`, `clk-dummy.ko`, `gcc-waipio.ko`, `icc-bcm-voter.ko`,
   `icc-debug.ko`, `socinfo.ko`, `icc-rpmh.ko`, `rpmh-regulator.ko`,
   `qcom-scm.ko`, `qcom_wdt_core.ko`, `gh_virt_wdt.ko`, `iommu-logger.ko`,
   `qnoc-qos.ko`, `qnoc-waipio.ko`, `phy-generic.ko`, `qcom_iommu_util.ko`,
   `sec_class.ko`, `secure_buffer.ko`, `arm_smmu.ko`, `abc.ko`,
   `usb_notify_layer.ko`, `switch_class.ko`, `common_muic.ko`,
   `vbus_notifier.ko`, `pdic_notifier_module.ko`, `usb_typec_manager.ko`,
   `usb_f_ss_mon_gadget.ko`, `phy-msm-snps-hs.ko`, `repeater.ko`,
   `phy-msm-snps-eusb2.ko`, `redriver.ko`, `if_cb_manager.ko`,
   `qc_usb_audio.ko`, and `dwc3-msm.ko`. `phy-msm-ssusb-qmp.ko intentionally
   excluded`; `EUD excluded`.
   The candidate did not expose ACM, run configfs gadget setup, start
   Android/Magisk, mount persistent partitions, write block devices, inject
   module binaries into the boot ramdisk, write DTBO/vendor_boot/recovery/
   vbmeta/non-boot partitions, use raw host `dd`, use fastboot, install
   Magisk modules, run multidisabler, or format data. The AP contained exactly
   one tar member, `boot.img.lz4`.
   Live result: the candidate flashed successfully, left the original Download
   endpoint, and survived the full 90 second observation window with no host
   ADB/Odin endpoint returning. After survival proof, the operator reported
   RDX/PMIC while entering manual recovery; a normal Odin/Download endpoint
   later appeared and the checked helper flashed the pinned Magisk boot
   rollback AP successfully. Final baseline was clean: Android boot complete,
   bootanim stopped, vbstate orange, Magisk root present, and boot partition
   SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
   Retained evidence had no M33 P28 marker: pstore empty, `/proc/last_kmsg`
   readable at 2,097,136 bytes, marker absent. The retained log did contain
   `collect_rr_data : upload_cause = PMIC abnormal reset`, `RDX is locked`,
   `PonReason.HARD_RESET = 1`, and XBL/PMIC
   `boot_update_abnormal_reset_status` material, matching the operator's RDX/
   PMIC observation, but not the P28 marker.
   Before consumption, the helper had to verify normal Android identity,
   vbstate orange, Magisk root, current boot partition SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   exact P28 candidate hashes, the exact Magisk boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`, and
   the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`.
   This exception must not be reused and does not authorize P28 repeat,
   P25/P30/P40 live, M33 matrix rebuild, M32 repeat,
   display/distro candidates, kernel rebuild, recovery/vendor_boot/vbmeta/
   DTBO/non-boot flash, raw host `dd`, fastboot, multidisabler, format data,
   EUD writes, or any A90 action.
   **Consumed exception (2026-07-09, S22+ M33 P27 watchdog-prefix park
   native-init boot-only live gate):** this one-shot exception was consumed by
   the 2026-07-09 KST live run. It flashed the pinned M33 P27 boot-only
   candidate once on the Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m33_p27_wdt_prefix_park_live_gate.py`.
   The consumed live and rollback ack token strings are intentionally omitted
   here as active authorization.
   The exact candidate AP.tar.md5 SHA256 must be
   `9110e793f5cc812c856dedf35aaa4cc2f2c692f8561bba9dbe10c7b1e8a29371`; the
   contained padded `boot.img` SHA256 must be
   `16efd35b4bb340b2c8d5d5b99e3e3d3e19d4c01a60e87f6ed3cf60acc90386ea`; direct
   `/init` SHA256 must be
   `4ce13d65264c2e887aadeefe66c812e4079340b14745bfb277b37a9fde7e8785`;
   module-list SHA256 must be
   `11f8ccac67944d689d327d0157eb2f504e794d205df91c480506a3247d9c830e`;
   generated source SHA256 must be
   `b57c37678ec5b145d3b1c6208c6ee685ba40401512115e08e4f92afa63627f33`;
   preserved kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`; and
   the known booting base Magisk boot SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
   The marker is `S22_NATIVE_INIT_M33_WDT_PREFIX_PARK_P27`, variant `P27`,
   `watchdog-managed prefix park`, `prefix_targets=27`, `module_load_only=1`,
   and `SMMU and HS/eUSB2 PHY prefix`. The P27 module list is exactly:
   `smem.ko`, `minidump.ko`, `sec_debug.ko`, `qcom_ipc_logging.ko`,
   `cmd-db.ko`, `qcom_rpmh.ko`, `clk-rpmh.ko`, `debug-regulator.ko`,
   `proxy-consumer.ko`, `gdsc-regulator.ko`, `clk-qcom.ko`, `clk-dummy.ko`,
   `gcc-waipio.ko`, `icc-bcm-voter.ko`, `icc-debug.ko`, `socinfo.ko`,
   `icc-rpmh.ko`, `rpmh-regulator.ko`, `qcom-scm.ko`, `qcom_wdt_core.ko`,
   `gh_virt_wdt.ko`, `iommu-logger.ko`, `qnoc-qos.ko`, `qnoc-waipio.ko`,
   `phy-generic.ko`, `qcom_iommu_util.ko`, `sec_class.ko`,
   `secure_buffer.ko`, `arm_smmu.ko`, `abc.ko`, `usb_notify_layer.ko`,
   `switch_class.ko`, `common_muic.ko`, `vbus_notifier.ko`,
   `pdic_notifier_module.ko`, `usb_typec_manager.ko`,
   `usb_f_ss_mon_gadget.ko`, `phy-msm-snps-hs.ko`, `repeater.ko`, and
   `phy-msm-snps-eusb2.ko`.
   P27 must keep `phy-msm-ssusb-qmp.ko intentionally excluded` and
   `EUD excluded`; it has no DWC3, no ACM function, no reboot syscall, no
   Download beacon, and no runtime USB/configfs/ACM. It must not start
   Android/Magisk, mount persistent partitions, write block devices, inject
   module binaries into the boot ramdisk, write DTBO/vendor_boot/recovery/
   vbmeta/non-boot partitions, use raw host `dd`, use fastboot, install
   Magisk modules, run multidisabler, or format data. The AP must contain
   exactly one tar member, `boot.img.lz4`.
   Live result: the candidate flashed successfully, left the original Download
   endpoint, and survived the full 90 second observation window with no host
   ADB/Odin endpoint returning. The operator reported no bootloop during the
   observation window. After survival proof, the operator reported a PMIC/RDX
   screen while entering manual recovery; a normal Odin/Download endpoint later
   appeared and the checked helper flashed the pinned Magisk boot rollback AP
   successfully. Final baseline was clean: Android boot complete, bootanim
   stopped, vbstate orange, Magisk root present, and boot partition SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
   Retained evidence had no M33 P27 marker: pstore empty, `/proc/last_kmsg`
   readable at 2,097,136 bytes, marker absent. The retained log did contain
   XBL/PMIC `boot_update_abnormal_reset_status` material, matching the
   operator's RDX observation, but not the P27 marker.
   Before consumption, the helper had to verify normal Android identity,
   vbstate orange, Magisk root, current boot partition SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, the
   exact P27 candidate hashes, the exact Magisk boot-only rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`, and
   the exact stock boot-only fallback AP SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`.
   The live path was: reboot Android to Download, flash exactly the pinned P27
   boot AP, wait for the original Odin endpoint to disconnect, observe for the
   bounded survival window, and treat `survives past 60-90 seconds` with no
   returned ADB/Odin endpoint as the survival proof. Manual Download rollback
   is recovery-only and should be used after survival proof or after a
   pre-proof stop when the helper requires it. `PMIC/RDX abnormal reset before
   the observation window is FAIL`. Rollback must use the pinned Magisk
   boot-only AP first, with the pinned stock boot-only AP only as fallback if
   Magisk rollback failed and Download mode remained available. This exception
   must not be reused and does not authorize P27 repeat, P25/P28/P30/P40 live,
   M33 matrix rebuild, M32 repeat, display/distro candidates, kernel rebuild,
   recovery/vendor_boot/vbmeta/DTBO/non-boot flash, raw host `dd`, fastboot,
   multidisabler, format data, EUD writes, or any A90 action.
   **Consumed exception (2026-07-09, S22+ M33 P12 watchdog-prefix park
   native-init boot-only live gate):** this one-shot exception was consumed by
   the 2026-07-09 KST live run. It flashed the pinned M33 P12 boot-only
   candidate once on the Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using
   only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m33_p12_wdt_prefix_park_live_gate.py`.
   The consumed live and rollback ack token strings are intentionally omitted
   here as active authorization. The exact candidate AP.tar.md5 SHA256 was
   `47a7acd9f953de4464848aa02413b629064c512e2250356da0e33df5c46a3ce0`;
   contained padded `boot.img` SHA256 was
   `72afa113caf0bd8fc2f3c4d2a27108f3be94dd00f405071d3b7e609af8d8a2f2`;
   direct `/init` SHA256 was
   `8ce2d3aea3008b476fbc8113f8c5712abd120f0dc90cb158956b9ba1a6962405`;
   module-list SHA256 was
   `b44e23aa5e38c1327bc3286f3b722558b56daa3198982434a474b4bff8c6d052`;
   generated source SHA256 was
   `a7d0f6cf2bd0ca217a92478a8f03c977d3e3d23e40383a050f1215853fa6d3b4`;
   preserved kernel SHA256 was
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`; and
   base Magisk boot SHA256 was
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`. The AP
   marker string is `S22_NATIVE_INIT_M33_WDT_PREFIX_PARK_P12`. The selected
   variant is `P12`, its runtime marker must include `prefix_targets=12` and
   `module_load_only=1`, and the behavior class is `watchdog-managed prefix
   park`. The AP must contain exactly one tar member, `boot.img.lz4`, and must
   not carry recovery, vendor_boot, dtbo, vbmeta, vbmeta_system, BL, CP, CSC,
   super, persist, userdata, EFS, sec_efs, RPMB, keymaster, modem, bootloader,
   or any other partition payload. The candidate may only run as freestanding
   direct PID1, create a minimal tmpfs/dev/proc/sys runtime, load the P12
   dependency-complete watchdog-managed prefix, emit kmsg phase markers, and
   park. It must have no reboot syscall, no Download beacon, no USB/configfs/ACM,
   no Android/Magisk handoff, no persistent partition mount, no block write, no
   module binary injection into boot ramdisk, no raw host `dd`, no fastboot, no
   Magisk modules, no multidisabler, no format data, no DTBO/vendor_boot/
   recovery/vbmeta/non-boot flash, and no A90 action. Expected proof is that it
   survives past 60-90 seconds without ADB/Odin returning; `PMIC/RDX abnormal
   reset before the observation window is FAIL`. `manual Download rollback is
   recovery-only` and must not be reported as self-Download proof. The module
   closure is `smem.ko`, `minidump.ko`, `sec_debug.ko`,
   `qcom_ipc_logging.ko`, `cmd-db.ko`, `qcom_rpmh.ko`, `clk-rpmh.ko`,
   `debug-regulator.ko`, `proxy-consumer.ko`, `gdsc-regulator.ko`,
   `clk-qcom.ko`, `clk-dummy.ko`, `gcc-waipio.ko`, `icc-bcm-voter.ko`,
   `icc-debug.ko`, `socinfo.ko`, `icc-rpmh.ko`, `rpmh-regulator.ko`,
   `qcom-scm.ko`, `qcom_wdt_core.ko`, and `gh_virt_wdt.ko`;
   `phy-msm-ssusb-qmp.ko intentionally excluded` and `EUD excluded`. Before
   live flash, the helper must verify Android identity, current boot hash,
   rollback APs, exact candidate hashes, AP member list, P12 closure, and the
   active `AGENTS.md` markers above. Rollback is required after the observation
   window: primary rollback is the pinned Magisk boot-only AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`, with
   pinned stock boot-only fallback SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if
   Magisk rollback transfer fails and Download mode remains available. This
   live result: P12 survived the full 90 second observation window with no host
   ADB/Odin endpoint returning, and the operator reported no bootloop during
   that window. The helper recorded
   `m33_p12_survival_window_pass=1` and
   `m33_p12_result=survived-observation-window-manual-download-required`.
   During manual rollback, the operator first observed an RDX screen; the first
   detected endpoint `/dev/bus/usb/003/027` failed both Magisk and stock fallback
   Odin attempts with `ioctl bulk write Fail : Protocol error 71`, consistent
   with RDX rather than normal Odin/Download protocol. After the operator entered
   normal Download mode, Codex used the checked helper's rollback-from-download
   mode to flash the pinned Magisk boot rollback AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`; rollback
   completed with rc=0. Final baseline was verified independently: Android boot
   complete, bootanim stopped, vbstate orange, Magisk root present, and boot
   partition SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
   Post-rollback pstore was empty and `/proc/last_kmsg` was readable at
   2,097,136 bytes but did not contain the M33 P12 marker. This exception must
   not be reused and does not authorize any other M33 variant, M33 P12 repeat,
   M32 repeat, M31B repeat, ACM/configfs candidate, kernel rebuild, recovery/
   vendor_boot/dtbo/vbmeta/non-boot flash, RDX PC dump retrieval, EUD writes, or
   any A90 action.
   **Consumed exception (2026-07-09, S22+ M32 watchdog-managed HS ACM
   native-init boot-only live gate):** this one-shot exception was consumed by
   the 2026-07-09 KST live run. It flashed the pinned M32 boot-only candidate
   once on the Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the
   checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m32_wdt_hs_acm_live_gate.py`.
   The consumed live and rollback ack token strings are intentionally omitted
   here as active authorization. The candidate AP.tar.md5 SHA256 was
   `b2dee88862cbbfa8e9da799978c10134a07f41e4d144c23b2db1d0b8e00adbd4`;
   contained padded `boot.img` SHA256 was
   `8001809f9f0d7b2d6615bdec97843680a0c20721d679dde74a76bbe6d95bb9ca`;
   direct `/init` SHA256 was
   `0595a0e932fa0ca7240192e2438d134ca8e4338a48e68a17edb8d9b023dc8f77`;
   module-list SHA256 was
   `2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`;
   generated source SHA256 was
   `ad1b94c144faa3ba3dd232110a07a7680ce5aa7c796061158e0cd75c3edd37b2`;
   preserved kernel SHA256 was
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`; and
   base Magisk boot SHA256 was
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`. The AP
   marker string is `S22_NATIVE_INIT_USB_ACM_M32_WDT_HS`, and its runtime status
   marker must include `role_force=device`. The AP
   must contain exactly one tar member, `boot.img.lz4`, and must not carry
   recovery, vendor_boot, dtbo, vbmeta, vbmeta_system, BL, CP, CSC, super,
   persist, userdata, EFS, sec_efs, RPMB, keymaster, modem, bootloader, or any
   other partition payload. The candidate may only run as freestanding direct
   PID1, load the dependency-complete HS-only USB/ACM closure while keeping the
   M31B watchdog-managed closure, force USB role=device, create the runtime
   `ss_acm.0` configfs ACM gadget, expose `ttyGS0` with USB serial
   `S22M32WDTHS01`, and park. Expected proof is that the candidate survives
   observation window and exposes ACM. `PMIC/RDX abnormal reset before ACM
   survival proof is FAIL`. `manual Download rollback is recovery-only` and must
   not be reported as a self-Download pass. The closure is
   `smem.ko`, `minidump.ko`, `sec_debug.ko`, `qcom_ipc_logging.ko`,
   `cmd-db.ko`, `qcom_rpmh.ko`, `clk-rpmh.ko`, `debug-regulator.ko`,
   `proxy-consumer.ko`, `gdsc-regulator.ko`, `clk-qcom.ko`, `clk-dummy.ko`,
   `gcc-waipio.ko`, `icc-bcm-voter.ko`, `icc-debug.ko`, `socinfo.ko`,
   `icc-rpmh.ko`, `rpmh-regulator.ko`, `qcom-scm.ko`, `qcom_wdt_core.ko`,
   `gh_virt_wdt.ko`, `iommu-logger.ko`, `qnoc-qos.ko`, `qnoc-waipio.ko`,
   `phy-generic.ko`, `qcom_iommu_util.ko`, `sec_class.ko`, `secure_buffer.ko`,
   `arm_smmu.ko`, `abc.ko`, `usb_notify_layer.ko`, `switch_class.ko`,
   `common_muic.ko`, `vbus_notifier.ko`, `pdic_notifier_module.ko`,
   `usb_typec_manager.ko`, `usb_f_ss_mon_gadget.ko`, `phy-msm-snps-hs.ko`,
   `repeater.ko`, `phy-msm-snps-eusb2.ko`, `redriver.ko`, `if_cb_manager.ko`,
   `qc_usb_audio.ko`, `dwc3-msm.ko`, and `usb_f_ss_acm.ko`. This is a
   watchdog-managed HS ACM dependency-complete HS-only USB/ACM closure with
   `phy-msm-ssusb-qmp.ko intentionally excluded` and `EUD excluded`; it must
   have no reboot syscall, no Download beacon, no Android/Magisk handoff, no
   persistent partition mount, no block write, no module binary injection into
   boot ramdisk, no raw host `dd`, no fastboot, no Magisk modules, no
   multidisabler, no format data, no DTBO/vendor_boot/recovery/vbmeta/non-boot
   flash, and no A90 action. Before live flash, the helper must verify Android
   identity, current boot hash, rollback APs, exact candidate hashes, AP member
   list, and that no baseline M32 ACM device is already present. Rollback is
   required after the observation window: primary rollback is the pinned Magisk
   boot-only AP SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`, with
   pinned stock boot-only fallback SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e` if
   Magisk rollback transfer fails and Download mode remains available. Live
   result: ACM never appeared; the operator reported bootloop; the host observed
   unexpected Odin/Download endpoint return at ~35.6 s, then the helper rolled
   back with the pinned Magisk boot-only AP. Final baseline was verified:
   Android boot complete, vbstate orange, Magisk root present, and boot
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`. This
   exception must not be reused and does not authorize repeat M32, repeat M31B,
   M30/M21A, M28/M29/S24, F43, RDX PC dump retrieval, EUD writes, kernel
   rebuilds, recovery/vendor_boot/dtbo/vbmeta/non-boot flashes, or any A90
   action.
   **Consumed exception (2026-07-09, S22+ M31B watchdog-managed park
   native-init boot-only live gate):** this one-shot exception was consumed by
   the 2026-07-09 KST live run. It flashed the pinned M31B boot-only candidate
   once using
   `workspace/public/src/scripts/revalidation/s22plus_m31b_wdt_managed_park_live_gate.py`.
   The candidate AP.tar.md5 SHA256 was
   `06d1c149c7c09a284062826f21ac848220e99d552d6b91762abbfb80f3679527`;
   contained padded `boot.img` SHA256
   `206fbb40df69a496f7fbe67e32cf862049d9258ef518db6949e1b5db2f4afdc4`;
   direct `/init` SHA256
   `b01e52d3762e3cbdcba3501b00bb1dc9f9084899550ea23b92df43884bed23d0`;
   watchdog module-list SHA256
   `80da959311e4a0f6bedb40da3c6f74c7fd5918017e40e0787b3e17c153cfe937`;
   source SHA256
   `32d85b4aeb64e5e1615b175b93fde166795598bfa0614934a9dcfb1bb165230d`;
   preserved kernel SHA256
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`; and
   base Magisk boot SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`. The
   AP contained exactly one tar member, `boot.img.lz4`. The candidate loaded
   only the stock watchdog dependency closure `smem.ko`, `minidump.ko`,
   `qcom-scm.ko`, `qcom_wdt_core.ko`, and `gh_virt_wdt.ko`, then parked with
   no reboot syscall, no Download beacon, no USB/configfs/ACM, no Android/
   Magisk handoff, no persistent partition mount, and no block write. Host
   observation recorded `m31b_survival_window_pass=1` and
   `m31b_result=survived-observation-window-manual-download-required` after a
   120 second window with no host ADB/Odin endpoint. The operator reported no
   bootloop during that window. While attempting manual Download rollback after
   the helper asked, the operator observed the RDX `PMIC abnormal reset` screen;
   the first detected endpoint then failed both Magisk and stock fallback Odin
   rollback attempts with `ioctl bulk write Fail : Protocol error 71`. After
   re-entering normal Download mode, Codex used the same checked helper's
   rollback-from-download mode to flash the pinned Magisk boot rollback AP
   SHA256 `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`,
   and Android/Magisk returned cleanly. Final baseline was verified
   independently: boot
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, dtbo
   `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`,
   vendor_boot
   `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`,
   Android boot complete, vbstate orange, and Magisk root present. Post-rollback
   pstore was empty and retained `/proc/last_kmsg` did not contain the M31B
   marker (`post_m31b_manual_rollback_retained_marker_found=0`). This exception
   must not be reused for a second M31B run, M31A short-dwell, M30/M21A repeat,
   M28/M29/S24 repeat, F43, USB/ACM bring-up, DTBO/vendor_boot/recovery/vbmeta/
   non-boot flash, kernel rebuild, raw host `dd`, fastboot, multidisabler,
   format data, EUD writes, or any A90 action. Future S22+ native-init live
   flashes need a fresh, narrower exception for the selected candidate and
   observation path. The now-consumed live and rollback ack token strings are
   intentionally omitted here as active authorization.
   **Retired unconsumed exception (2026-07-08, S22+ M21A Odin path):** the
   M21A-specific Odin path that paired with the retired 2026-07-08 M21A live
   gate above is no longer active. It does not independently authorize an M21A
   Odin transfer or M21A rollback transfer; the later M30/M21A exception above
   is also now consumed. This retired block authorizes no Odin slot, tar member,
   candidate hash, rollback hash, M21 variant, M20 variant, M19 prefix, or
   partition.
   **Retired consumed exception (2026-07-08, S22+ ramoops DTBO + M22
   sysrq-panic Odin path):** the Odin path paired with the consumed M22 gate
   above is no longer active. No current exception authorizes another M22 Odin
   transfer, DTBO transfer, or rollback transfer under that helper. Future work
   needs a fresh SHA-pinned exception and fresh operator approval; this retired
   block authorizes no Odin slot, tar member, candidate hash, rollback hash,
   boot candidate, DTBO candidate, or partition.
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
- **Strip device serials before committing.** Never paste raw `adb devices -l`,
  `adb -s <serial>`, `fastboot devices`, or Odin/heimdall device-listing output
  verbatim into a tracked report — it embeds the S22+ serial (DID) and the A90
  serial, both on the never-commit list. Redact any serial to
  `<S22_SERIAL_REDACTED>` / `<A90_SERIAL_REDACTED>`; keep the public product
  identifiers (`ro.product.model`/`device`/`ro.boot.bootloader`). Before commit,
  grep the staged diff for the recorded device serials and the generic
  `adb: <alnum> device usb:` device-listing pattern; both must return nothing.
  Same rule for
  SSID/PSK/BSSID/MAC/DHCP-lease/routable-IP/KASLR slides/tunnel URLs.
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
