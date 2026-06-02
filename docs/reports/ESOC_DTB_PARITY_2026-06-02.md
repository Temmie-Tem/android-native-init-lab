# DTB parity — native boot image vs stock/Android modem config (2026-06-02)

**Host-only. No device command, no write.** Closes the "is the modem/PCIe/PMIC
devicetree config native's kernel sees different from Android's?" question.
Verdict: **non-differential (parity).** This is the third and final static/config
layer ruled out as the Android-vs-native differentiator, after bootloader and the
eSoC provider source.

## Why this was asked
`ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md` proved the AP-side eSoC software is
correct and the provider carries no regulator. The remaining host-checkable
hypothesis was: maybe native's flashed boot image carries a different/older DTB,
so the *kernel's* modem/regulator/gpio view differs from Android even though the
bootloader is identical. If true, that WOULD be a real differential (the DTB is
the one low-level thing that can change when only the boot partition is flashed).

## Method
- Native boot image: `stage3/boot_linux_v724.img` (the device's known-good
  native build). Kernel payload already unpacked at
  `tmp/wifi/v1331-esoc-disasm/bootunpack/kernel`.
- Scanned the kernel payload for FDT magic `d00dfeed`. Found **2** full DTB blobs
  (the V775 "third" at off 49827440 leaves only ~173 bytes to EOF — a stray magic
  match, not a DTB). Carved both and parsed with a minimal Python FDT walker.
- Compared node presence/properties against the OSRC source DTS already read for
  the PON analysis (`sm8150-pcie.dtsi`, `sdx5xm-external-soc.dtsi`,
  `sm8150-sdx50m.dtsi`).

## Findings

### Appended DTBs = SM8150 SoC base only (v1 + v2)
- `model = "Qualcomm Technologies, Inc. SM8150 v1 SoC"`, `compatible = qcom,sm8150`.
- The full **SoC power tree is present and matches source**. `qcom,pcie@1c08000`
  (pci-msm, `linux,pci-domain=1` = RC1) carries:
  `gdsc-vdd-supply`, `vreg-1.8-supply`, `vreg-0.9-supply`, `vreg-cx-supply`,
  `perst-gpio`, `wake-gpio`, `qcom,boot-option = <1>` (probe-time enumeration
  intentionally skipped — same value V1523 read; not a native defect),
  `pcie_1_gdsc` node present. PMIC (`pm8150l`) nodes present.

### Board/modem layer is NOT in the appended DTB — and that is normal
- **`qcom,mdm3` / `qcom,ext-sdx50m` / esoc GPIO nodes are absent** from both
  appended DTBs (grep count 0). The eSoC/mdm3 board layer
  (`sdx5xm-external-soc.dtsi`: ap2mdm-status TLMM135, mdm2ap-status TLMM142,
  ap2mdm-soft-reset PM8150L GPIO9, ssctl/sysmon ids) lives in the board overlay,
  delivered via the `dtb`/`dtbo` partitions selected by the bootloader, not via
  the kernel-appended SoC dtb.
- Those partitions are **identical on Android and native** — only the boot
  partition is flashed (`native_init_flash.py --boot-block /dev/block/by-name/boot`).

### The running native kernel DOES have the full correct modem layer — proven live
Independent of which DTB source the bootloader feeds, native's running kernel
demonstrably instantiates the board/modem layer correctly:
- mdm3 reaches OFFLINING and the provider runs `mdm_subsys_powerup` (V849/V902) —
  the mdm3 node + eSoC provider are bound at runtime.
- Pin claims match Android: `pin 135/142 : soc:qcom,mdm3` (V1502/V1506), GPIO9 PON
  steady-state `out/high` identical to Android V919 (V1276). All of these values
  come straight from the board DTB → native's runtime DTB carries them correctly.

## Verdict
**DTB parity = PASS (non-differential).** The modem / PCIe-RC1 / PMIC devicetree
config native's kernel sees is functionally identical to Android's, confirmed two
ways: (1) the appended SoC dtb's pcie1/regulator/PMIC nodes match source, so the
image we flash is not carrying a broken SoC tree; (2) the board/modem layer comes
from the shared dtb/dtbo partitions and is proven live-correct on native
(mdm3 bind, GPIO135/142/9 claim/polarity parity).

## Combined static/config closure (all three layers ruled out)
| layer | differential? | basis |
|---|---|---|
| bootloader (xbl/abl/pmic-config) | NO | only boot partition flashed; identical both sides |
| eSoC provider source | NO (correct) | PON polarity correct, zero regulator code (`ESOC_PON_SOURCE_ANALYSIS`) |
| DTB (modem/PCIe/PMIC config) | NO | appended SoC dtb matches source; board layer shared + live-correct |

Every host-checkable AP/software/config layer is now at parity with Android. The
only remaining unknown is hardware-level: whether the SDX50M main rail is actually
powered so the modem PBL can answer MDM2AP/GPIO142 when native's (correct) PON
pulse lands. That is not on disk and requires bounded read-only LIVE observation
of the natural `__subsystem_get(esoc0)` → `mdm_subsys_powerup` window watching the
GPIO142/MDM2AP IRQ count — not forced RC1, not fake-ONLINE, no PMIC/GPIO write.

## Artifacts / refs
- Carved native DTBs: `tmp/wifi/v1331-esoc-disasm/dtb1.dtb`, `dtb2.dtb`
  (off 48830500 / 49327831 in the kernel payload).
- Cross-refs: `ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md`,
  `ESOC_PMSERVICE_CAUSALITY_HANDOFF_2026-06-02.md`,
  `ESOC_PROVIDER_STATIC_ANALYSIS_2026-06-01.md`,
  V775 (FDT offsets), V1502/V1506 (pin claim parity), V1276 (GPIO9 parity),
  V1523 (boot-option=1), V849/V902 (mdm_subsys_powerup).
