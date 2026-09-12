# S22+ CPU path defect and SoC/GPU/memory/UFS thermal census

Status: **H0 complete. Exact-input CPU path defect reproduced; 32 TSENS
sensor mappings confirmed. New live temperatures remain unproved.**
Target: **SM-S906N / g0q / S906NKSS7FYG8**, G0Q board revision 12.

This investigation follows the [closed P389 trial](S22PLUS_NATIVE_THERMAL_H0_2026-09-13.md):
battery temperature was observed, CPU coverage was 0/13, and normal restoration
to admitted P387 succeeded. This unit inspected retained firmware, current code
and public primary sources on the host. It made no device contact and changed
none of the 195 reviewed execution inputs. P389 remains consumed.

## Confirmed CPU path defect

The P389 [provider](../../workspace/public/src/kernel-modules/s22plus_thermal_telemetry_v1/s22plus_thermal_telemetry.c)
calls `of_find_node_by_path("/thermal-zones")` in `exact_cpu_map()`. The retained
FYG8 base DTBs and the actual G0Q revision-12 stock overlay instead resolve
`thermal_zones` to **`/soc/thermal-zones`**. `/thermal-zones` does not exist.

All four base DTBs were split from the sealed vendor DTB bundle and independently
merged with the same matching stock overlay using `fdtoverlay`. The actual
merged trees agree on this parent path, both TSENS resources, and all 32
zone/provider/sensor joins. Neither TSENS bank has a disabled status in these
graphs. This checks the final input structure, including the Samsung overlay,
rather than only looking for sensor names in an included DTS fragment.

With these inputs, `exact_cpu_map()` returns `-ENODEV` before CPU MMIO mapping.
The module can still register and provide battery readings: registration does
not require both bank probes to succeed, and battery acquisition is independent.
This is a concrete source defect sufficient to produce the observed
battery-valid/CPU-empty shape. It is **H0 causal reproduction**, not a newly
recovered live `cpu0_error`/`cpu1_error` trace from the consumed P389 boot.

The existing [kernel harness](../../tests/s22plus_thermal_kernel_harness.c)
also supplies a fictional `/thermal-zones` node. The existing source-map test
checks leaf names and sensor IDs but does not resolve their parent node. Those
fixtures therefore missed the same path error.

The production provider body was compiled under the existing C/UBSan harness
with its node lookup backed by the actual merged-tree path. Missing paths return
NULL as the kernel API does. A second, private-only copy changed just the
provider's parent path. Both runs completed:

| Host reproduction | CPU mask | CPU bank errors | Battery |
| --- | --- | --- | --- |
| Unchanged P389 provider + actual parent path | `0` | `-19`, `-19` | Valid |
| Private path-corrected provider + same inputs | `8191` (13/13) | `0`, `0` | Valid |

The register and ADC values in this harness are synthetic. Its success proves
the path correction under the fixture, not real TSENS readiness or temperature.
Production source, old source receipts, candidate images and consumed records
were not modified by the reproduction.

The exact vendor TSENS driver also matters for subsequent qualification:
`init_common()` rejects a cleared `TSENS_EN`; it does not turn that bit on.
Its `get_temp_tsens_valid()` waits without a timeout while VALID is clear, and
does not use P389's additional TRDY precondition on that read path. Loading the
whole stock driver is therefore not an established bounded remedy. After the
path correction, bank binding/error, version, enable, readiness and valid-mask
evidence should remain distinguishable before selecting any hardware change.

## Confirmed TSENS inventory

All rows below are present with these mappings in each of the four reconstructed
stock base-plus-board trees. They describe sensor locations, not CPU-core or GPU
counts. Their live availability is not established by the tree.

| Domain label | Zone names | TSENS bank / IDs | Count |
| --- | --- | --- | ---: |
| CPU | `cpu-1-0..8`, `cpu-0-0..3` | Bank 0: 5–13; bank 1: 1–4 | 13 |
| CPU subsystem | `cpuss-0..3` | Bank 0: 1–4 | 4 |
| GPU subsystem | `gpuss-0..1` | Bank 0: 14–15 | 2 |
| DDR region | `ddr` | Bank 1: 9 | 1 |
| AOSS | `aoss-0..1` | Bank 0: 0; bank 1: 0 | 2 |
| NSP subsystem | `nspss-0..2` | Bank 1: 5–7 | 3 |
| Video | `video` | Bank 1: 8 | 1 |
| Modem subsystem | `mdmss-0..3` | Bank 1: 10–13 | 4 |
| Camera | `camera-0..1` | Bank 1: 14–15 | 2 |

There are **32 unique bank/sensor pairs**, 16 per bank. GPU and DDR observation
can use the same TSENS measurement interface as CPU; their definition does not
require starting a GPU rendering workload. A future “SoC temperature” could be
an explicitly labelled maximum over available TSENS locations, with coverage
reported. It would be a derived aggregate, not a newly discovered single sensor
for the whole chip.

The `ddr` channel belongs to this same SoC-side TSENS interface. It is not a
DRAM mode-register read and does **not** establish the LPDDR package's internal
die temperature. `ddr-cdev` in the vendor driver controls DDR bandwidth/frequency;
a cooling-device state is not a temperature reading.

## Other board and PMIC paths

The selected board overlay declares these ADC routes and conversion metadata:

| Item | Declared route | Evidence status |
| --- | --- | --- |
| AP board thermistor | `sec-ap-thermistor`, `ap_therm`, ADC `0x144` | Board table and route confirmed; live value unproved |
| CF / WF board thermistors | `cf_therm` `0x14c`, `wf_therm` `0x14a` | Routes/tables confirmed; physical placement beyond the names unproved |
| USB / charger thermistors | `usb_thm` `0x145`, `chg_thm` `0x148` | Routes/tables confirmed; live values unproved |
| Battery / WPC route | `wpc_thm` `0x14b`, shared by board `adc-temp` and `adc-wpc-temp` | P389 battery observation proved through this route |
| PMIC die sensors | PMK8350 `0x003`, PM8350 `0x103`, PM8350B `0x303`, PMR735A `0x403`, PMR735B `0x503` | ADC die-temperature channels declared; live values unproved |

The AP thermistor is separate from the on-chip CPU/GPU TSENS channels. Its name
does not make it a CPU junction-temperature measurement. The board thermistors
use processed microvolts plus their individual tables, while the PMIC die
channels select the stock PM7 die-temperature scaler. Units and conversions
must be bound per channel. Additional ADC acquisitions retain their concrete
conversion/configuration effects and are not described as pure memory reads.

## RAM die and UFS temperature

**RAM die:** no exact SM8450/G0Q path exporting a RAM-package temperature was
established in the selected Qualcomm thermal, memory, SoC or vendor sources.
MR4 is a separate DRAM thermal/refresh-status mechanism; an official
[Intel MR4 description](https://edc.intel.com/content/www/us/en/design/publications/12th-generation-core-processor-datasheet-volume-2-of-2/mr4-rank-temperature-mr4-rank-temperature-0-0-0-mchbar-offset-e424/?language=en)
illustrates that distinction and technology-dependent encoding. It is background
evidence, not a Qualcomm register map or proof about this installed RAM part.
The exact part, supported reporting and a bounded target read path remain
unproved. The TSENS `ddr` result must keep a different label.

**UFS:** a device-case rough-temperature facility exists in the upstream UFS
interface. Linux v6.6 defines attributes `0x18` for case rough temperature and
`0x19`/`0x1a` for high/low bounds. Its
[hwmon reader](https://github.com/torvalds/linux/blob/v6.6/drivers/ufs/core/ufs-hwmon.c)
uses a READ_ATTR query, rejects zero as no data, and converts the encoded value
to Celsius by subtracting 80. Its
[probe](https://github.com/torvalds/linux/blob/v6.6/drivers/ufs/core/ufshcd.c)
also checks host capability, UFS version and the device's temperature-notification
feature bits; setup includes exception-event configuration.

The retained FYG8 `drivers/scsi/ufs/ufs.h` skips these temperature attribute IDs,
and its UFS source/sysfs files do not provide that upstream hwmon temperature
path. Its `ufs-qcom` thermal callbacks report mitigation levels and control
hibernation/autosuspend behavior; those values are not UFS temperature.
The actual P389 Image's embedded configuration has HWMON disabled and no built-in
Qualcomm UFS selection. This describes that kernel image, not every possible
external vendor module. Presence in the inherited vendor archive is also
separate from the selected native load plan.

Thus **UFS temperature is possible in the interface, but support by this exact
UFS part and an available native read path remain unproved**. No UFS query,
controller initialization or notification-enable operation occurred here.

## Next bounded implementation direction

First correct the CPU parent path and make the fixture derive it from the exact
merged tree; preserve the existing bank diagnostics in the retained output.
Then qualify the same TSENS path for the named GPU and DDR locations, with
separate values and availability masks. AP/PMIC ADC channels can be considered
as separate labelled additions. RAM-internal reporting and UFS support remain
separate research questions, not prerequisites for a useful CPU/GPU/SoC display.

Any implementation uses a fresh E and its normal qualification/review/finite
authority. This census creates no approval or replay exception. Current P387,
the closed P389 result, and A90/S20+ remain unchanged.

## Input and evidence identities

| Retained input | Bytes | SHA-256 |
| --- | ---: | --- |
| Stock vendor DTB bundle | 1,721,428 | `2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e` |
| Stock DTBO image | 8,388,608 | `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c` |
| Matching G0Q r12 overlay, entry 10 | 708,337 | `79eeb405f8eae4c31329183cee1a39dc9103234ed4676450869a8a023fe7429f` |
| Actual P389 Image | 41,490,944 | `fe8dfd63799efba54387e9071a5394a80e6758293c673d59f5f1c7bc55370f05` |

Host source commit: `c731e9cdfb6bb6573dec1b74da6b39e712724e04`.
Private evidence is under
`workspace/private/outputs/s22plus-temperature-census-h0-20260913-1/`:
stock/merged DT inspections, `tsens-census.json`, both C reproductions,
`path-defect-reproduction.json`, actual Image configuration, public-source
receipts, and `census-close-result.json` binding 16 local source inputs.
These reconstructed DTs are host evidence; no fresh on-device FDT was collected.
