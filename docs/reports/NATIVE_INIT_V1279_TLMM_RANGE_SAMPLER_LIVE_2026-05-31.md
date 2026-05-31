# Native Init V1279 TLMM Range Sampler Live

- generated: 2026-05-31
- cycle: V1279
- command: bounded live observation
- decision: `v1279-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required`
- pass: true
- helper: `a90_android_execns_probe v267`

## Result

V1279 reran the bounded PM-service `/dev/subsys_esoc0` response sampler with
helper v267 deployed by V1278.

| field | value |
| --- | --- |
| sample count | `14` |
| PM-service `/dev/subsys_esoc0` attempt | true |
| late `per_proxy` started | `1` |
| TLMM GPIO135 range block | visible |
| TLMM GPIO142 range block | visible |
| TLMM range window | `0-174` |
| TLMM GPIO135 exact debugfs line | absent |
| TLMM GPIO142 exact debugfs line | absent |
| GPIO135 pinmux | `soc:qcom,mdm3 3000000.pinctrl:135 function gpio group gpio135` |
| GPIO142 pinmux | `soc:qcom,mdm3 3000000.pinctrl:142 function gpio group gpio142` |
| GPIO142 IRQ count | `0` |
| PCI devices | `0` |
| MHI bus devices | `0` |
| MHI pipe | absent |
| `wlan0` | absent |
| debugfs cleanup | mounted by cycle, absent after cleanup |
| post-run health | v724 selftest `pass=11 warn=1 fail=0` |

Evidence:

- `tmp/wifi/v1279-tlmm-range-sampler-live/manifest.json`
- `tmp/wifi/v1279-tlmm-range-sampler-live/summary.md`

## Interpretation

V1279 separates the previous ambiguity:

1. The TLMM controller/range is visible (`gpiochip0: GPIOs 0-174`).
2. GPIO135/GPIO142 pinmux ownership is visible and belongs to `soc:qcom,mdm3`.
3. Exact line-value entries for GPIO135/GPIO142 are still absent from
   `/sys/kernel/debug/gpio`.
4. The downstream response remains silent: no GPIO142 IRQ, PCIe RC1
   enumeration, MHI device, MHI pipe, or `wlan0`.

This means the next blocker is no longer "is the TLMM controller visible?". The
remaining gap is why the ext-mdm/SDX50M power-up path reaches
`mdm_subsys_powerup` without enabling the PCIe/GPIO142/MHI response path that
Android reaches.

## Safety

No Wi-Fi HAL start, scan/connect, credential use, DHCP/route change, external
ping, flash, boot image write, partition write, PMIC write, GPIO line request,
or direct eSoC ioctl was executed. The live actor remained the existing bounded
PM-service response path.

## Next

V1280 should be host-only: compare V1279 native evidence with existing Android
positive evidence (especially Android GPIO135/GPIO142 debugfs line values and
PCIe RC1 timing) and classify whether the next safe live gate should target
PCIe/GDSC enablement evidence, AP2MDM/MDM2AP line transition timing, or an
Android-side early sampler gap.
