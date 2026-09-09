# S22+ battery data and native-HUD source investigation

Target: SM-S906N/g0q/S906NKSS7FYG8. This is H0 inspection of retained source,
artifacts and prior evidence. No device command, module load, firmware update,
new candidate, or change to the consumed v0.1.1/P377 runtime was performed.

## Findings

The successful P377 Image contains `CONFIG_POWER_SUPPLY=y`, but no Samsung
battery/fuelgauge/MAX77705 provider configuration entries. Its audited package
contains 17 display/return modules and none of `sec-battery.ko`,
`max77705-fuelgauge.ko`, `max77705_charger.ko` or `mfd_max77705.ko`.
The vendor-module build configuration separately selects those providers as
modules, along with `CONFIG_SEC_PD=m` and `CONFIG_QCOM_SPMI_ADC5=m`.
Framework availability therefore does not imply that the `battery` supply exists.
This is a concrete packaging/configuration gap consistent with native N/A;
P377 did not retain a per-attribute failure reason, so it is not proof of the
exact failing syscall or the sole cause of N/A.

The Samsung source registers the supply named `battery` in `sec_battery.c`.
It implements status, capacity, temperature and additional useful properties.
The retained Android D0 observation from the status-HUD preparation already
proved that the four fixed attributes were readable in that Android boot:
Battery / 100 / Full / 262 tenths Celsius. Those observations do not transfer
to native boot or certify the additional attributes listed below.

A retained 2026-08-18 Android module-list capture includes `sec-battery`,
`max77705-fuelgauge`, `max77705_charger`, `sec-direct-charger`, `sec_pd`,
`sb-core`, MAX77705 MFD/PDIC and multiple charger alternatives. Its recorded
list hash was rechecked against the retained raw body:
`8411620a0384d07fed491a2f8f7c146e354d022c8446940fc59f49cb2d98d360`.
This is historical same-firmware evidence, not a fresh loaded-module census.

## Useful display candidates

Paths below are relative to `/sys/class/power_supply/battery/`.
Except for the four previously observed attributes, these are source-supported
candidates, not newly demonstrated live values. Native availability is unproved.

| Display | Attribute | Interpretation in this source | Priority |
| --- | --- | --- | --- |
| Remaining charge | `capacity` | Integer percent; Samsung policy can adjust reported SOC | Main HUD |
| Charging state | `status` | Charging/Discharging/Full/etc.; policy-reported state | Main HUD |
| Battery temperature | `temp` | Tenths Celsius; battery temperature, not CPU temperature | Main HUD |
| Battery voltage | `voltage_now` | Microvolts; divide by 1,000,000 for V; ordinarily cached | First extension |
| Signed battery current | `batt_current_ua_now` | Explicit Samsung microamp selector; divide by 1,000 for mA | First extension |
| Smoothed battery current | `batt_current_ua_avg` | Explicit microamps; averaging includes driver-specific adjustments | Optional |
| Current fault state | `health` | Good/Overheat/etc.; not remaining lifespan or a health percentage | Optional |
| Battery presence | `present` | Presence flag | Diagnostic |
| Charging category | `charge_type` | None/Fast/Trickle/etc.; policy category, not measured watts | Optional |
| Charge completion estimate | `time_to_full_now` | Seconds from the charging model; state-dependent zero/-1 cases | Later |
| Gauge cycles / aging estimate | `fg_cycle`, `fg_asoc` | Vendor-specific gauge-derived diagnostics, with initialization and interpretation requirements | Later |

Keep the main HUD's existing battery percent/state/temperature. Once an exact
provider path is qualified, voltage and signed current are the most useful
additional measurements. Retain N/A for unavailable or invalid data. Validate
current sign against charging state before labeling it as charge/discharge
flow. These readings are battery-side quantities, not automatically the whole
phone's electrical consumption.

## Names that must not be interpreted as standard units

The common sysfs formatter prints the driver's integer without unit conversion.
Samsung's property implementations therefore matter:

- `current_now` and `current_avg` request **mA**, despite the generic power-supply
  convention. The explicit `batt_current_ua_*` attributes request microamps and
  are clearer prospective interfaces. This source conclusion still needs the
  exact running provider/ABI joined before use in a new native candidate.
- `power_now` and `power_avg` request **system current in mA** through
  `SEC_BATTERY_ISYS_MA` / `SEC_BATTERY_ISYS_AVG_MA`. Do not label them W or µW.
- `charge_now` returns the Samsung charging-mode enum, not remaining charge.
- `charge_full` and `charge_full_design` both use the same configured full
  capacity. Their ratio does not measure degradation.
- `battery/online` is a Samsung cable-type value, not a generic Boolean USB
  connection indicator. A separately verified USB/AC supply would be preferable
  for an external-power indicator.
- `charge_counter` is calculated from raw SOC and configured gauge capacity;
  it is not by itself proof of independently integrated consumed charge.

A future `voltage × current` display could be labeled an approximate battery
power flow only after unit/sign/freshness validation. It must not reuse
`power_now` under an assumed standard meaning.

## Provider and initialization constraints

The g0q source describes a `max77705-fuelgauge` and charger providers, with
`sec-direct-charger` and hardware-dependent wireless/direct charger alternatives.
The inspected r10 DTS is a source example; this investigation did not prove the
currently selected live overlay or select a particular optional charger.
The battery's temperature path also includes named IIO channels such as
`adc-temp` and table-based ADC conversion. Raw IIO numbers cannot simply be
labeled Celsius without the correct source and calibration table.

The retained dependency metadata for `max77705-fuelgauge.ko` includes the
MAX77705 MFD, `sec-battery`, `usb_typec_manager`, MUIC/VBUS/PDIC notifier support,
`switch_class`, `usb_notify_layer`, Samsung parameter/SMEM/reset support,
`sb-core` and `sec_pd`. It is not a demonstrated standalone two-module loader.
Reintroducing that stack must account for the existing native USB/control owner.

Loading a provider is not equivalent to reading an already active sysfs file:

- `max77705_fuelgauge_probe()` calls `max77705_fg_init()` and V-empty setup.
  The initializer writes CONFIG/CONFIG2 under its declared conditions.
- `sec_bat_dev_init_work()` waits for FG/main/direct/wireless initialization,
  initializes policy state and starts further work. The wait has a 20-second
  timeout; reaching the timeout is not proof that providers are ready.
- With wireless support and firmware-update configuration enabled, it schedules
  wireless firmware initialization. The vendor build enables that configuration.
  Whether a hardware update would actually occur is conditional and was not
  established here; loading the entire stack merely to expose readings is not
  a qualified read-only operation.

The smallest next implementation unit is a source-bound provider/dependency and
probe-effect qualification for the desired percent/voltage/current/temperature
path, followed by a separate fresh candidate if appropriate. Additional Android
attribute reads, if needed to settle ABI/unit questions, should use a reviewed
fixed D0 profile. No broad sysfs dump, register access, or provider activation
is necessary to complete this source investigation.

## Reproducible evidence

Private `workspace/private/outputs/s22plus-battery-research-20260909/source-findings.json`
records hashes for 13 inspected inputs, extracted Image/vendor config facts,
actual P377 package module names and the retained module-list/dependency subset.
The findings record is 5,728 bytes, SHA-256
`865c5d04a6d80d4e7b4cde9771e465e3f8840f489cb33410dfb6997b13cffc73`.
No firmware, raw device output, identifiers or binaries are committed.

Source root:
`workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel/`.

| Source within root | Relevant locations |
| --- | --- |
| `drivers/battery/common/sec_battery.c` | Properties 67–89; getter 5406–5577; device init 7440 onward; named supply 7585 onward |
| `drivers/battery/common/sec_battery_sysfs.c` | Explicit µA reads 339–360; gauge cycle conversion 741–750 |
| `drivers/power/supply/power_supply_sysfs.c` | Generic formatting 263–307 |
| `drivers/battery/fuelgauge/max77705_fuelgauge/max77705_fuelgauge.c` | Current conversion 602–688; initialization 1224–1290; charge counter/ISYS 2019–2055; probe 2694 onward |
| `drivers/battery/common/sec_charging_modprobe.c` | Required provider mask and timeout 16–52 |
| `drivers/battery/common/sec_adc.c` | Named IIO channels 28 onward; table interpolation 164–216 |
| `drivers/battery/common/sec_battery_ttf.c` | State-dependent completion estimate 346–357 |
| `arch/arm64/boot/dts/samsung/rainbow/g0q/g0q_kor_singlex_w00_r10.dts` | Example battery provider names 29–35; IIO channels 173–174 |

A90 and S20+ were not contacted or changed. The current functional version
remains v0.1.1; this research creates no new firmware version or live authority.
