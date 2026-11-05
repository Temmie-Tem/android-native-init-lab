# ML029 — S22+ mainline UFS wiring and probe order

ML028 closed with a working Debian SSH service cycle in RAM. ML029 moved
toward a resident root by checking the storage wiring that the physical
ML028 image omitted. The host reproduced three proposed device-tree
properties against that exact image and identified a clock-rate mismatch.
The result is `PASS_H0_DISABLED_UFS_DT_REHEARSAL`. The study used retained
files throughout. ML028 is still the latest physical result. [ML028 run](S22PLUS_MAINLINE_ML028_RUN_2026-11-05.md)

Claude and Argon each selected this storage study over another RAM service,
USB NFS root, or enabling the watchdog. Both challenged the proposed
discovery boundary in a second round. One Argon challenge returned an
interrupted-stream error and the replacement call completed. The private
usage ledger records all five attempts. The measured 96.50 seconds from
ML028 control intent to A launch includes host processing and transport.
Timing individual calls would be necessary to attribute that delay.

## What the two trees actually say

The checker follows the closed ML028 task through its qualified physical
init manifest to the DTB and kernel configuration. It also verifies the
same-boot FYG8 capture receipt, compiles the FYG8 r12 OSRC board overlay,
and resolves its fixups against the regulator identities in the captured
tree. Selected mainline sources match members of the pinned Linux 7.2.11
archive. Samsung's Android 15 base sources and the FYG8 differential are
identified separately. [Host checker](../../workspace/public/src/scripts/analysis/s22plus_mainline_ufs_h0.py)

| FYG8 consumer | Resolved supply | FYG8 voltage range | FYG8 maximum load |
| --- | --- | ---: | ---: |
| PHY analog | PM8350 L5 | 880–912 mV | 173,000 µA |
| PHY PLL | PM8350 L6 | 1,200 mV | 24,900 µA |
| Host VCC | PM8350 L7 | 2,504 mV | 1,100,000 µA |
| Host VCCQ | PM8350 L9 | 1,200 mV | 1,200,000 µA |
| Vendor reference-clock supply | PM8350 L9 | 1,200 mV | 100 µA |
| Vendor VCCQ parent vote | PM8350 S12 | 1,224–1,400 mV | 210,000 µA |

The FYG8 and mainline USB2 PHYs already reference L5. ML028 describes it
at 880–888 mV. The SM8450 QMP driver specifies 173,000 and 24,900 µA for
its two PHY supplies and uses a two-lane SM8350-derived table with gear-4
overlays. These declarations establish compatible resource names and a
voltage overlap. Physical load behavior and link lock still need evidence.

Both trees describe a two-lane host at `0x1d84000` and a PHY at
`0x1d87000`. Their PHY windows are respectively `0xe10` and `0x1000`
bytes. Samsung describes separate ICE and HWKM regions starting at
`0x1d88000` and `0x1d90000`, with sizes `0x8000` and `0x9000`.
Mainline references a separate ICE node with a larger `0x18000`-byte
window starting at `0x1d88000`. A mapping establishes address coverage.
Clock, power, firmware and conditional crypto operations require their own
effect analysis. ML028 disables the UFS host and PHY, their kernel drivers,
and the TLMM device-tree node.

## Three properties in a disposable DT

1. **Host reset.** The shipped tree binds active-low GPIO 210. The Samsung
   base pinctrl source and the mainline source use different TLMM bases and
   offsets but arrive at the same control and output addresses,
   `0x0f1de000` and `0x0f1de004`, with output bit 0. The FYG8 source
   differential contains no replacement for those pinctrl files. The
   rehearsal added the matching `reset-gpios` reference to the disabled host.
2. **PHY analog supply.** The rehearsal linked `vdda-phy-supply` to the
   existing mainline L5 regulator. It preserved the USB supply reference,
   voltage constraints and all provider declarations.
3. **Host clock rates.** FYG8 lists nine clocks and gives its separate
   `core_clk_ice` a 75–300 MHz range. ML028 lists eight clocks and declares
   that range on `ref_clk`. The platform driver reads minimum/maximum pairs
   positionally and the core can request the nonzero maximum. The rehearsal
   matched pairs by clock name and restored FYG8's `0/0` pair for `ref_clk`.
   The pair removes the explicit min/max request. Measuring the physical
   reference frequency would require separate evidence.

The host compiled and applied the fragment to a private copy. Removing the
two new properties and restoring the original rate table produced the same
sorted DT bytes as ML028, including reservations and empty nodes. The unit
produced a study DTB, with no boot image, transfer or device access.

## Where storage effects begin

In this kernel, `ufshcd_init` initializes the HBA and its variant. The QCOM
variant requests an optional reset GPIO as `GPIOD_OUT_HIGH`, which can assert
an active-low line. Clock/regulator setup, controller and device reset,
conditional crypto setup, SCSI host registration, and link startup precede
the asynchronous scan. On the regular non-skip path, the host sends a NOP,
sets and polls the device's `fDeviceInit` flag, reads device parameters and
performs post-init work before scheduling that scan. The source retains
the separate `UFSHCD_QUIRK_SKIP_PH_CONFIGURATION` branch.

Later probe work includes a conditional reset/reinitialization path, the
active-ICC-level attribute, and feature-dependent WriteBooster and exception
event settings. Timestamp, reference-clock and power-mode changes have their
own conditions. `ufshcd_add_lus` processes special logical units and queues
RTC work before ordinary SCSI discovery. Manual SCSI scan mode still permits
explicit device addition. Suppressing ordinary scanning or marking a block
device read-only leaves earlier controller and UFS protocol effects in scope.
With a disk registered, the selected kernel also includes the EFI partition
parser, whose GPT implementation reads sectors. These are source-level
paths. ML029 issued zero device or media commands.

## Decision

The next specific board question is the input to the PM8350 regulator group
`vdd-l6-l9-l10` on g0q and the handling of the independent L9 reference-clock
and S12 parent votes over startup, idle and shutdown. The retained FYG8
overlay shows both vendor votes. The physical upstream connection of each LDO and equivalent behavior in
the mainline consumer remain unresolved. QRD/HDK wiring
can guide that investigation but belongs to other boards. No provider or
parent was fabricated in the study tree.

A prospective link experiment also needs a precise stopping point in the
actual QCOM/UFS path and an effect scope covering the power, clocks, GPIO
and controller operations reached before that point. ML028's RAM policy
excludes Linux storage. Its approval was consumed. There is no ML029
physical proposal.

Four focused tests exercise output isolation, source-order and clock parsing,
and a real DT round trip. Twelve changes to copies of the retained inputs were rejected,
including a swap of the two 1.2 V supplies, an incorrect reset polarity,
widened USB voltage, masked clock mismatch and a comment-only initialization
call. The original captures and the first two blocked host analysis attempts
remain in private evidence. The latter exposed a missing mainline PHY lane
property (lane count comes from driver data) and the difference between the
stock USB supply name and mainline's `vdda-pll-supply`. [Tests](../../tests/test_s22plus_mainline_ufs_h0.py)
