# S22+ mainline RAM canary: first H0 build and implementation review

Date: 2026-10-27. Target: SM-S906N / g0q / S906NKSS7FYG8.
Status: **H0 BUILT AND VM-VALIDATED; PHYSICAL ENTRY NOT ADMITTED**.

The operator requested implementation of the selected RAM/USB first unit, then
a Claude review for errors and design problems. This unit produced a pinned
kernel, private g0q DTB, static RAM PID1/initramfs and uniLoader payload. The
actual new kernel/PID1 boots in QEMU and answers its authenticated observation.
Physical g0q boot, USB PHY behavior and recovery remain unproved. No device
command, transfer, host-interface change, activation or new grant occurred.
A90 and S20+ were untouched; the vendor-route journal prototype remains paused.

## Selected implementation

The [H0 tools](../../workspace/public/src/mainline/s22plus_canary_h0/README.md)
use the minimal r0q USB board DTS already in Linux, the public port's broad
configuration and the published loader patch. This retains an existing board
description while avoiding the full-phone port's camera, audio and charging
additions. Generated g0q memory data and all binary artifacts remain private.

| Input | Selected identity |
| --- | --- |
| Linux | 7.2.11; official archive SHA-256 `fd0fc479f983a8c05313f13e9c36330fe6651cf725396748c40d5cd93fa1e6a4` |
| r0q port | `9863baf29b5a9cb30c3df3e466c5de6b04948557` |
| uniLoader | `7781b33c87ccde3e57bb744c5b8bccdbedfa4bc3` plus its pinned public DTB-relocation patch |
| g0q evidence | Retained FYG8 live FDT from the existing ABL analysis; no fresh device read |

The archive checksum was compared with the official checksum list; this run
did not verify its PGP signature. Source and artifact pins are in the private
run and public `sources.json`. References: [Linux archive checksums](https://cdn.kernel.org/pub/linux/kernel/v7.x/sha256sums.asc),
[pinned r0q port](https://github.com/cammo1997/SM-S901E-Linux-Part-Working/tree/9863baf29b5a9cb30c3df3e466c5de6b04948557),
[pinned uniLoader](https://github.com/ivoszbg/uniLoader/tree/7781b33c87ccde3e57bb744c5b8bccdbedfa4bc3).

BLOCK and SMP remain enabled, with one initial online CPU. UFS/MMC, selected
unused peripherals, charger control and watchdog driver control are excluded.
The embedded r0q userspace path is cleared and the canary command line is
forced. The RAM PID1 has no child/shell/exec, module loader, installed-root
mount or reset command. It creates one NCM gadget and serves one fixed HMAC
observation before parking. Omitting drivers does not establish that inherited
firmware charging or watchdog activity is disabled.

The generated DT preserves five RAM banks and the union of fixed retained/base
reservations. Coverage requires enabled, non-reusable, no-map candidate nodes;
disabled live reservations are retained conservatively. Addressless CMA
requests are recorded separately. The compiled USB node must use the enabled,
audited USB2 PHY. Its PMIC family, RPMh LDO resource and voltage range are joined
to the retained g0q supply references. All actual selected rails passed.

## Findings and corrections

One tools-disabled Claude Opus 5.5 review examined a frozen source snapshot and
sanitized results. Independent local reviews also examined actual kernel and
loader consumers. Advice was checked against current bytes; it is not a
capability approval. The private dispositions distinguish actual defects from
missing assertions where the selected artifact was already correct.

| Finding | Resolution and evidence |
| --- | --- |
| Published loader staging overlaps retained ADSP/SLPI/CDSP memory | Move staging to a free retained interval and use a 2 MiB-aligned kernel destination. Verify actual ELF/runtime/copy extents; the initial ABL source remains unresolved below. |
| Addressing `usb0` before UDC bind fails | Linux `f_ncm` registers its netdev during bind. Bind once, then address it. The actual production function passed a same-kernel dummy-UDC test. |
| Producer relative deadline disagreed with host absolute uptime limit | Both use the absolute boot-time limit. Fresh complete VM observation and rejection tests passed. |
| DT node/property comparison omitted the header reservation map | Compare the bounded header map, version and boot CPU too. The formerly accepted counterexample and malformed variants reject. |
| Private network masks could parse differently in Python and C | Normalize address/mask strings before sealing, record their input digest, and require private unicast endpoint geometry. |
| Build records could be mixed across preparations | Join prepared config, kernel build receipt, initramfs input config, DTB, initrd address and kernel release. Four mutated records reject before a build begins. |
| Reservation and supply checks did not fully join candidate semantics | Require effective no-map coverage and actual enabled USB/PHY/resource/voltage joins. The selected artifact was already correct; mutated reservation, role, voltage and PHY inputs reject. |
| READY preceded socket listen | Emit READY only after listen succeeds; remove the VM's fixed sleep workaround. Clock failure parks and unavailable console falls back to `/dev/null`. |

The source questions about fixed-peripheral property placement and PMK8350
were resolved against the selected kernel. USB uses the flattened
`qcom,snps-dwc3` node. PMK8350's input variants have no pull-up bit and disable
debounce/PS_HOLD configuration; the older reset-configuration callbacks are not
registered for them. The parent PON reboot-mode write is an explicit reboot
callback, which this PID1 does not invoke. This does not claim that IRQ setup
or every PMIC-related operation is write-free, nor qualify physical recovery.

## Artifact and test evidence

| Final member | Size | SHA-256 |
| --- | ---: | --- |
| ARM64 Image | 43,969,024 bytes | `7eafd4a9b43ea35ff7851f7cb8a71dfa68ac31781bebafaa04c0497b4d44654b` |
| RAM initramfs | 300,849 bytes | `bc66cd26949a5d7625a58cf3bc519121385b38957358a1464ad0407d899aa486` |
| uniLoader payload | 44,461,944 bytes | `466f9f00636f5c9a348ea701c1d80d6c4d05ae0759eae33600f5e7874a27d28a` |

The static production PID1 is 709,080 bytes. The kernel's declared runtime
extent is 44,826,624 bytes; its configuration remained unchanged after build.
Later explicit fragment assertions resolve to those same bytes, so the kernel
was reused. Earlier loader builds with identical members reproduced identical
raw bytes; that comparison does not assert whole-toolchain reproducibility.

- Fresh actual-kernel ARM64 VM: PID1, executable/FDT measurement, HMAC response,
  one CPU, no block devices and memory/timer check passed. Wrong-key input
  produced no response and the expected terminal rejection. VM Ethernet and
  its explicit variant cannot be accepted as a physical artifact.
- Real configfs/NCM producer test: a separate H0 harness includes `usb()`
  unchanged and loads `dummy_hcd` in the same kernel. `usb0` is absent before
  bind and exists with the exact address and UP flag afterward. Its test seal
  names the dummy UDC; physical UDC identity and PHY behavior remain untested.
- Actual compiled loader handler and libfdt objects: ARM64 execution expanded
  this DTB to the effective 500,000-byte buffer with exact initrd bounds and
  unchanged remaining properties/reservations. Bad magic and insufficient
  buffer reject. Embedded DTB alignment and all three ELF member byte ranges
  were checked against their inputs.
- Seven focused tests exercise real ARM64 C/Python protocol agreement,
  authenticated wrong fields, truncation/tampering/duplicate data, VM separation,
  reserve-map/header changes and effective reservation coverage. Additional
  mutations of real DTB and artifact records reject.

DTC compilation succeeded with inherited SoC warnings; this is not a claim of
a full DT schema-validation pass. Initial H0 failures remain recorded: Kconfig
selected PSTORE through ACPI APEI, the VM marker had CRLF, and the first loader
qualifier assumed the wrong ELF filename and `_start` location. Corrections
used actual consumers/linker symbols. Earlier artifacts were retained and were
not relabelled as the final source closure.

## Remaining pre-device issue and next unit

The retained FYG8 ABL reads 64-bit EFI `KernelBaseAddr`/`KernelSize`, then adds
the Image offset and a randomized displacement. Its fallback defaults do not
prove the successful EFI path's actual address, and the retained observations
do not expose it. uniLoader's relocation copy is forward-only. A free final
staging interval alone does not prove disjointness from the initial source,
executing stub or source tail.

The final ELF also places `_start` after the relocation/header stub; copying
`_reloc_size` from there extends beyond `_stack_end`. The H0 checks include
that full destination extent and record the loader Image header, but **initial
source/stub overlap remains unresolved**. These artifacts are not admitted for
physical use. No Odin AP, candidate registration or active owner was published.

Next: resolve that loader entry/copy condition, then qualify the boot-v4
container and exact attended execution/recovery path. The first physical
criterion remains an identified mainline g0q RAM PID1, authenticated USB
observation, and original-A return with health. Charging, thermal/watchdog
qualification, storage admission and resident operation remain later units.

Private evidence is under
`workspace/private/outputs/s22plus-mainline-canary-h0-20261027-1/`: `prepare-4`,
`init-final-2`, `init-vm-final-2`, `loader-final-3`, `vm-final-2`,
`vm-final-wrong-key-2`, `final-validation-1`, `review` and `claude-review`.
