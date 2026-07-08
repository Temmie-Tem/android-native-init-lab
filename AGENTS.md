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
   steer and P00 result. This unconsumed authorization is retired so it cannot
   be used accidentally. The active M21A live and rollback ack token strings
   are intentionally omitted from this file, so
   `workspace/public/src/scripts/revalidation/s22plus_m21a_raw_nanosleep_download_live_gate.py`
   must fail closed at its AGENTS marker check. Historical M21A build/preflight
   details remain in
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
   **Narrow operator-authorized exception (2026-07-08, S22+ M24 pmsg-step
   DTS-exact QMP/DWC3 native-init boot-only):** after the M23 reset-summary
   live result consumed the M23 gate and captured no useful reset-summary
   payload, and after the M24 host build plus live-gate source passed
   offline/fail-closed validation, Codex may prepare and perform one bounded
   attended boot-partition-only M24 live gate on the same Samsung S22+
   `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m24_pmsg_steps_live_gate.py`
   with live ack token `S22PLUS-M24-PMSG-STEPS-LIVE-GATE` and rollback-only ack
   token `S22PLUS-M24-PMSG-STEPS-ROLLBACK-FROM-DOWNLOAD`. The exact candidate
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
   `/proc/reset_tzlog`, and `/proc/enhanced_boot_stat`. This exception does
   not authorize M23 repeat, M21A, M20B, M20C, M19 C129 or wider prefixes, EUD
   writes, broad module permutation, display/distro candidates, kernel rebuild,
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
   **Narrow operator-authorized exception (2026-07-08, S22+ M24 pmsg-step
   native-init boot-only Odin path):** paired only with the active M24 pmsg-step
   gate above, `/usr/bin/odin4 --reboot -a` may be used through
   `workspace/public/src/scripts/revalidation/s22plus_m24_pmsg_steps_live_gate.py`
   for the exact single-member `boot.img.lz4` candidate AP.tar.md5 SHA256
   `e09538024abe89585486d54856a5c86bef666da456f314084d4d4d8bb6553fe8`, and
   the same helper may use `/usr/bin/odin4 --reboot -a` in
   `--rollback-from-download` mode with the exact single-member Magisk
   boot-only AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` or the
   exact single-member stock boot-only AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`. No other
   Odin slot, tar member, candidate hash, rollback hash, M24 variant, M23
   variant, M20 variant, M19 prefix, or partition is authorized by this
   exception.
   **Retired unconsumed exception (2026-07-08, S22+ M21A Odin path):** the
   M21A-specific Odin path that paired with the retired M21A live gate above is
   no longer active. No current exception authorizes an M21A Odin transfer or
   M21A rollback transfer. A future M21A run would need a fresh SHA-pinned
   exception and a fresh operator approval; this retired block authorizes no
   Odin slot, tar member, candidate hash, rollback hash, M21 variant, M20
   variant, M19 prefix, or partition.
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
