# S22+ Stop Blind-Flashing the Session Chain — Pivot to a 1-Bit Download-Beacon State Probe (S8) (2026-07-09)

Operator (Claude) strategic pivot after S7A2. Host-only analysis; no live flash
authorized by this report.

## The problem this fixes

S4 → S5 → S6 → S7A → S7A2 are **five attended live flashes**, each testing one
link of a long USB-C peripheral-session chain, every one landing on
`survived-observation-window / no host-visible 04e8:*`:

```text
i2c bus up -> max77705 probe -> CC/BC1.2 detect -> port0-partner ->
data_role=device -> valid session -> dwc3 D+ pullup -> host sees 6860
```

Because native init on this device is **structurally blind** (no console,
`pstore` empty, `last_kmsg` is the Android image, marker count `0` every run),
we cannot see *which* link breaks. So each unit adds one more module/knob and
spends a full flash + manual RDX/Download rollback to test a single blind
hypothesis. That is the observability wall the earlier saga already established
is expensive — and it has now cost five flashes with no localization.

Live stock `dmesg` confirms the chain is a rich cascade we get no view into:
`max77705` CC/BC1.2 detect → `cable=USB_CDP` → `pdic_notifier` → `TCM`
(`usb_typec_manager`) → dwc3. We keep guessing where in that cascade native init
stalls.

## The lever we already have but are not using as a probe

`reboot(download)` is a **proven 1-bit host-visible channel** (M18 P00: a
zero-module candidate reaches the beacon and enters Download mode = HIT; a
parking candidate that never reboots = MISS). The device now **survives** the
whole window (unlike the old ~30 s watchdog hang), so a candidate has time to
read on-device state and then choose beacon-vs-park based on it.

**Convert the blind chain into observable bisection:** have the candidate read
one specific intermediate state and signal it as 1 bit —
`state true -> reboot(download) [HIT]`, `state false -> park [MISS]`.

## S8 beacon-probe ladder (one probed link per flash, in dependency order)

Each candidate is identical up to the probe point, then branches
beacon-vs-park on exactly one predicate:

1. **B1 — did the GENI I2C bus actually probe and reach the chip?**
   Predicate: `/sys/class/typec/port0` exists **OR**
   `/sys/bus/i2c/devices/57-0066` exists (max77705 on `994000.i2c`).
   This directly answers the question S7A2 left blind: did adding
   `gpi`/`msm-geni-se`/`i2c-msm-geni` make the max77705 reachable at all, or is
   the bus still not binding under native init? Highest-value first probe.
2. **B2 — did the cable get detected (CC/PD attach)?**
   Predicate: `/sys/class/typec/port0-partner` exists.
3. **B3 — did the data role resolve to device?**
   Predicate: `data_role` reads `... [device]` (or our forced write took).
4. **B4 — after `UDC=a600000.dwc3`, is the gadget bound + pulled up?**
   Predicate: `/sys/class/udc/a600000.dwc3/state == configured` (and/or
   `current_speed != UNKNOWN`).

The first predicate that reads **false** is the broken link — and now we *know*
it instead of guessing. ~2–4 targeted flashes localize the exact failure, versus
an open-ended blind add-a-module march.

Notes:
- Keep everything else fixed at the S7A2 recipe (i2c bus + producer chain +
  `mode=peripheral` + minimal `ss_acm` configfs, `soft_connect` OFF).
- Order the probes by dependency; a false at B1 makes B2–B4 moot (fix B1 first).
- Encode only ONE predicate per flash (the download beacon is 1 bit; do not try
  to multiplex it fragilely).
- This is not a new electrical hypothesis — it is instrumentation. Do it BEFORE
  any further module additions and BEFORE the S7B descriptor/composition pivot
  (still downstream: no descriptor set can create a pullup).

## Why this is the disciplined path

It is the same observability-first lesson the project already paid for: buy a
channel before bisecting blind. We have a channel (the download beacon); we were
just using it as a "did I reach the end" signal instead of a "what is the
intermediate state" probe. Reusing it as a state probe turns five-flashes-and-
counting of blind guessing into a bounded, decisive bisection.

## Safety / discipline

Read-only host analysis only. Any S8 beacon candidate is a boot-only native-init
flash under a fresh SHA-pinned exception, reads on-device sysfs read-only (except
the already-approved bounded `data_role`/`power_role` write from S7A2), uses only
`reboot(download)` as the beacon, writes no charge/OTG/rail/GPIO knobs, no
persistent partition, and rolls back to the pinned Magisk boot baseline.
