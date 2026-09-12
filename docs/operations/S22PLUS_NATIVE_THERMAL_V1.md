# S22+ native thermal development profile V1

Status: **H0 implementation; no grant or live temperature proof.**
Target: **SM-S906N / g0q / S906NKSS7FYG8**, exact G0Q board-id 12.

The bounded task is to add CPU and board battery temperatures to a fresh
experimental E, then qualify the existing admitted-P387 `N -> E -> N` operation.
The [native baseline V2 policy](S22PLUS_NATIVE_BASELINE_V2.md) supplies the complete
authority, one-shot E, finite attended grant and recovery rules. This document
adds no exception or standing device permission. Normal restoration returns the
unchanged admitted P387. An unexplained operation failure retains only the
original exact Android A fallback; it never authorizes a second E or a native
recovery attempt.

## Native changes and measurements

P387's native byte inputs, artifacts and consumed qualification stay unchanged.
The new renderer composes its temperature collector and extended HUD record from
those inputs. Control framing, resident lifetime, private IPC, fixed health
commands and descriptor/return owner remain the existing reviewed paths.
The optional bounded HUD export uses the same fixed command; its new record
dialect additionally carries the displayed battery temperature.
Only E's observer allows three seconds for collector/frame startup immediately
before PID1 freezes that export. This consumes the existing 60-second observation
deadline and never extends the host grant. N and other profiles keep zero settling.

The fresh E's fixed module plan adds the sealed stock `qcom-vadc-common.ko` and
`qcom-spmi-adc5.ko`, followed by `s22plus_thermal_telemetry.ko`. The stock files
already exist in the inherited vendor ramdisk but are absent from the current
native load plan. Their exact bytes are copied into E's boot-only AP under the
existing fixed loader's regular-file, mode, size and module-ABI rules. No module
is loaded into the running P387 during H0 preparation.

CPU source identities remain `cpu-1-0..8` at TSENS0 IDs 5..13 and `cpu-0-0..3`
at TSENS1 IDs 1..4. The provider validates both exact DT resources and every
thermal-zone provider/ID mapping before using them. It reads SROT version and
enable, TM readiness, and one status word joining VALID with signed 12-bit
temperature. It registers no thermal policy, IRQ or workqueue and performs no
TSENS calibration, threshold, enable or reset write. Partial valid coverage
produces a maximum over only those available sensors. Software acquisition time
is bounded; the TSENS hardware conversion age has no timestamp witness.

The board's named `adc-temp` channel is PMIC virtual channel `0x14b`, shared with
`adc-wpc-temp`. The exact DT channel selects ratiometric calibration, 1:1
prescaling, 200-microsecond settling and scale function 5. The processed value
is **microvolts**, despite the stock channel's `IIO_TEMP` metadata. The provider
checks the complete 23-point board table and interpolates signed tenths Celsius.
Out-of-table values, conversion errors and unexpected return formats are invalid;
they never clamp to an endpoint or reuse an earlier successful temperature.
One conversion is a telemetry observation, not stock's five-read trimmed result.
The fuel-gauge temperature register is not used: Android writes its external
temperature input and it is not an independent current battery observation.

## Concrete effects and failure handling

The ADC7 driver writes SID/channel/calibration/averaging/settling configuration
and a conversion request, and owns its EOC IRQ with the existing 501-ms wait.
Those volatile peripheral effects are part of this new F1 payload capability;
this is not described as a wholly read-only hardware operation. The provider
borrows the existing battery platform-device reference and its named IIO channel.
It does not bind a battery driver, which would select unrelated WPC/charger/OVP
pinctrl states before probe. Charger, fuel-gauge configuration and battery
power-supply registration remain outside the new module.

At most one new acquisition is admitted per second. No successful sample cache
is replayed. The collector accepts only an increasing sequence whose BOOTTIME
start follows the current collection start and whose completion is not in the
future. Existing collection-age expiry therefore conservatively expires both
temperature fields. ADC read/format/range failure latches that ADC source stopped
for the rest of the boot, preventing repeated conversion writes after a fault.
Missing IIO provider discovery may retry without a conversion. CPU availability
and command health remain independent. Module/collector uncertainty never
restarts a service or alters the outer owner's recovery rules.

## Completion evidence

H0 requires deterministic AArch64 module/renderer/init/AP outputs, exact
Image/module import CRC closure, actual AP decoding and complete source binding.
Behavioral checks exercise the production kernel wrapper and renderer parser,
invalid/missing/partial readings, signed units, stale/replayed samples, and
native health/return with the new HUD dialect. Retained P387 admission must
rederive with unchanged native identity under the reviewed current host reader.
Independent review covers this hardware surface and the changed reachable
build/catalog/observer/archive closure before a fresh attended request is issued.

The live temperature result requires fresh valid board battery temperature and
at least one correctly mapped CPU sensor, with all 13 coverage bits reported.
Physical visibility, register-observation freshness, feature qualification,
E consumption, normal N restoration and final authenticated N health are separate
claims. Temperature unavailability is a feature `NO_PROOF`, not permission to
repeat E; complete fixed health still permits the policy's normal N restoration.
