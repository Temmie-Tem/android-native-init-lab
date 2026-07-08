# S22+ S7A Loaded the max77705 Producers Onto a Dead I2C Bus — the GENI I2C Transport Was Missing (live read-only, 2026-07-09)

Operator (Claude) read-only pull from the live rooted device after the S7A live
result. No writes, no flash. This report contests the S7A conclusion that "the
max77705/PDIC/altmode producer hypothesis is retired" and shows S7A did not
actually test it.

## Why the S7A conclusion is premature

S7A added `pdic_max77705`, `mfd_max77705`, `max77705_charger`,
`max77705-fuelgauge`, `charger-ulog-glink`, `altmode-glink` and kept
`ssusb/mode=peripheral`, then survived with **no host `04e8:*`**. It concluded
the producer chain is insufficient. But S7A also added TypeC/UDC readback
markers that are **structurally unobservable** on this device (no console,
`pstore` empty, `last_kmsg` is the Android image) — so **S7A never confirmed
whether `/sys/class/typec/port0/data_role` actually resolved to `device`.** The
end state (no pullup) is known; the intermediate link that broke is not.

## The broken link: the max77705 sits on `994000.i2c`, driven by `i2c_msm_geni`

Live stock read:

```text
/sys/class/typec/port0 -> .../soc/994000.i2c/i2c-57/57-0066/max77705-usbc/typec/port0
/sys/bus/platform/devices/994000.i2c/driver -> .../platform/drivers/i2c_geni
```

The PD chip is a discrete I2C device (`57-0066`) on GENI I2C bus `994000.i2c`.
Its bus driver is **`i2c_msm_geni`** (GENI serial-engine I2C), core
**`msm_geni_se`**. `pdic_max77705` reads CC/PD state from the chip **over this
I2C bus**. If the bus driver is absent, the chip is unreachable → no probe → no
`port0-partner` → `data_role` never becomes `device` → no peripheral session →
no D+ pullup → no `04e8:6860`.

## What S7A actually loaded for I2C — the wrong controller

S7A added **`qcom_i2c_pmic`**, which is the **SPMI / PMIC-arbiter** transport
(for the pm8350-class PMICs), a *different* bus than the GENI I2C the discrete
max77705 uses. Checked against the S7A builder tuple (commit `HEAD`), the GENI
I2C transport is **not present**:

```text
MISSING : msm_geni_se        (GENI serial-engine core)
MISSING : i2c_msm_geni       (I2C controller for 994000.i2c — the max77705 bus)
MISSING : gpi                (GPI DMA engine used by geni i2c)
PRESENT : qcom_i2c_pmic      (SPMI/PMIC arbiter — does NOT reach max77705)
```

## The M5 trap, again: probe-time deps are invisible to `modules.dep`

`modules.dep` for the producers does **not** name the bus:

```text
pdic_max77705.ko: mfd_max77705 dwc3-msm usb_f_ss_mon_gadget qc_usb_audio redriver
  if_cb_manager ... usb_typec_manager abc common_muic vbus_notifier
  pdic_notifier_module ... sec_class debug-regulator          # <- no i2c-msm-geni
i2c-msm-geni.ko: gpi msm-geni-se qcom_ipc_logging minidump sec_debug smem
msm-geni-se.ko:  qcom_ipc_logging minidump sec_debug smem
```

A symbol-level `modules.dep` closure of `pdic_max77705` will therefore **never**
pull in `i2c-msm-geni` — the "this device lives on bus 994000.i2c" fact is a
**DT/platform probe-time binding, not a symbol dependency**. This is exactly the
lesson from the original M5 USB-ACM miss (`dwc3-msm` couldn't probe because its
regulators/clocks/PHYs were probe-time platform deps omitted by a symbol walk).
It has recurred one layer down, at the max77705's I2C transport.

## S7A.2 recipe (the actual test of the session hypothesis)

Add the GENI I2C transport **before** the max77705/PDIC producers, dep-ordered:

```text
# substrate already present in the 44-module set: smem, qcom_ipc_logging, minidump,
# sec_debug, pinctrl_msm, clk-qcom, gdsc-regulator, proxy-consumer, debug-regulator
gpi.ko
msm-geni-se.ko          # GENI serial-engine core
i2c-msm-geni.ko         # <-- THE MISSING TRANSPORT: brings 994000.i2c live
# then the producer chain, dep-ordered (mfd -> pdic ...), as in S7A
mfd_max77705.ko ; max77705_charger.ko ; max77705-fuelgauge.ko ; pdic_max77705.ko
common_muic.ko ; vbus_notifier.ko ; pdic_notifier_module.ko ; usb_typec_manager.ko
altmode-glink.ko
# keep ssusb/mode=peripheral, keep minimal ss_acm configfs, keep soft_connect OFF
```

Take exact names/order from stock `modules.load` + `modules.dep`; verify with a
dry-run that `994000.i2c`'s bus driver is in the set and ordered before
`pdic_max77705`.

### Cheap discriminator that survives the blindness

Because on-device markers are unobservable, add ONE host-visible signal: if,
after loading the producers, `port0` still does not show a partner, have the
candidate **directly write the role the HAL itself uses** —
`/sys/class/typec/port0/data_role = device` and `power_role = sink` (both 664,
the exact nodes the stock USB HAL `chown`s to `system`) — then bind UDC. The
host either sees `04e8:6860` (session path works) or not (session genuinely
needs more than role + a reachable chip). Either way it is a real test, unlike
S7A which could not reach the chip at all.

## Do NOT pivot to S7B (descriptors/FunctionFS) yet

The "no device at all" discriminator still holds: descriptor/composite/FFS
parity is downstream and cannot create a pullup. S7B should wait until a
candidate can electrically enumerate. The correct next unit is S7A.2 (add the
GENI I2C bus so the producers can actually probe), not S7B.

## Safety

`i2c-msm-geni`/`msm-geni-se`/`gpi` are bus/DMA controller drivers (standard
platform drivers, clk-framework clocks) — not rail power-writes. `pdic_max77705`
pulls `gdsc-regulator`/`proxy-consumer`/`debug-regulator` in its dep closure;
these are stock power-domain **driver** loads that let devices probe normally,
not manual GDSC/regulator knob writes — flag for explicit operator confirmation
at the S7A.2 gate, but they are the same substrate `dwc3-msm` already needs. The
candidate must still write no charge-current/OTG-boost/rail/GPIO knobs and must
not use `soft_connect`. Read-only pull only; raw dumps (serial) stay in
scratchpad. Any live S7A.2 attempt needs a fresh SHA-pinned boot-only exception.
