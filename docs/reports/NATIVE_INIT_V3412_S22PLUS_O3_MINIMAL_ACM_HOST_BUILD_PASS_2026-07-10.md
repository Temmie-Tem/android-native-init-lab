# V3412 S22+ O3 Minimal-ACM Host Build

## Verdict

`HOST BUILD PASS`. The V3411 59-module stock-loader-parity design is now a
reproducible direct-PID1 boot-only artifact with a generic configfs ACM control
daemon. No device command, reboot, flash, module insertion, sysfs/configfs
write, or partition write occurred. The manifest remains
`live_flash_authorized=false`; no active O3 live exception exists in this unit.

## Runtime Contract

The candidate performs only this bounded sequence:

1. Mount volatile proc, sysfs, devtmpfs, and configfs views.
2. Execute the pinned 59-module hard+soft dependency plan with fail-stop
   `finit_module` handling.
3. Stream `/proc/modules` through EOF and require all 59 runtime names.
4. Require the eight ordered O2 bind gates.
5. Create one generic `acm.usb0` function and one configuration.
6. Write only `a600000.ssusb/mode=peripheral`, verify it, bind only
   `a600000.dwc3`, and verify the bind.
7. Require `/dev/ttyGS0`, then exec the static O3 control daemon as PID1.
8. Serve O0-compatible framed echo plus `O3 STATUS`; on failure emit retained
   kmsg/pmsg state and park.

The new gadget starts unbound. An early draft attempted to write `none` to its
empty `UDC` attribute; review rejected that as an invalid configfs assumption.
The final source performs exactly one UDC write, the final
`a600000.dwc3` bind.

The runtime contains no Samsung `ss_acm`, FunctionFS, MTP/ADB, NCM,
max77705/charger/altmode control, EUD enable, sec_debug/sysrq trigger,
reboot request, persistent mount, block write, or Android/Magisk handoff.

## Pinned Plan And Vendor Proof

```text
module_count=59
module_plan_tsv_sha256=a34ebbad3b5d770f133e37a450cc3007e4a84ab831788484680e88aad6b3d534
generated_header_sha256=45727cff30952096d9604682a3ba3d284807a75e6622ed4c8ae57bc153d5b863
tolerated_missing_softdep=pinctrl-waipio.ko -> pre:qcom_tlmm_vm_irqchip
vendor_boot_ko_count=441
all_59_plan_modules_present_in_vendor_boot=true
```

The builder independently verifies the FYG8 planner metadata pins and compares
the overlapping `modules.dep`, `modules.softdep`, `modules.load`,
`modules.load.recovery`, and `modules.alias` hashes against the actual stock
vendor_boot ramdisk. Module binaries remain in stock vendor_boot
`/lib/modules`; none are copied into the boot ramdisk.

## Exact Artifacts

Output:

```text
workspace/private/outputs/s22plus_native_init/o3_minimal_acm_v0_1
```

```text
o3_init_sha256=7b2785687482971e4358575d555e49af402ceac2ee72136afdfeff3ece4b95cc
o3_control_sha256=2cb881f420dccd909610c4e3822adf6439fbe443460ee61644178f38509e5570
boot_img_sha256=4f4a073f79b47c0a6a3924fabf09b2389c62bb731ed3355ebb83e48c53868609
boot_img_lz4_sha256=5421281a463cbca00a2a1fcec00af96f21f827af30f3b107ae326c364d9264fb
ap_tar_sha256=b06a34f90eb834a281e63608801dd02e5cfe197005b081920c14a6eaa9094050
ap_tar_md5_sha256=41b7e32424a809cec6ac7bded281b9ac355a9f3d2d0a3727f8b02de6d1e757f7
tar_members=boot.img.lz4
```

Both binaries are stripped, static AArch64 executables with no `PT_INTERP`.
The 100663296-byte boot image preserves the known Magisk base kernel. A
no-change MagiskBoot unpack/repack remains byte-identical to the base boot.

## Reproducibility And Tests

An independent rebuild under `/tmp/s22plus_o3_repro` reproduced all of these
hashes exactly: init, daemon, plan TSV/header, patched ramdisk, boot image,
LZ4 payload, tar, and AP.tar.md5.

The host-compiled daemon was attached to a PTY and passed an initial device
status query, 128/128 CRC-framed echo requests with continuous sequence
numbers, and a final status query reporting:

```text
protocol_result=pass
protocol_handled=128
protocol_invalid=0
protocol_crc_errors=0
protocol_seq_errors=0
```

The combined O0, O1, O1.1, O2, and O3 focused suite passed 58 tests. Static
source tests also pin generic ACM, the exact mode/UDC paths, fail-stop loader
usage, and absence of the prohibited behavior above.

## Next Gate

Before any live action, add a fresh one-shot O3 exception and a checked helper
that pins the exact AP/boot/init/daemon/plan hashes, known Magisk and stock
boot-only rollback APs, normal Android preflight, one target transport,
continuous USB observation, framed status+128-request proof, and mandatory
rollback. Because O3 deliberately contains no reboot command, failure or proof
completion may require attended manual Download-mode entry before rollback.
