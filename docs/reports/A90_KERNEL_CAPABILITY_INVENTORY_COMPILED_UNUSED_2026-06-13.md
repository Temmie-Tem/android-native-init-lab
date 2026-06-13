# A90 Kernel Capability Inventory — Compiled-in but Unused (2026-06-13)

What the stock A90 kernel **compiles in** that native init does **not yet use** —
the surface for the peripheral-breadth / "phone as a multitool" direction. Native
init drives the device by consuming kernel interfaces directly (no Android
HAL/framework), so "compiled in" + "node reachable" = drivable from our PID1.

Metadata-only: CONFIG flag states + sysfs/dev paths. No firmware/secrets.

## Provenance & caveat

- Source: vendor defconfig
  `…/kernel_source/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/configs/r3q_kor_single_defconfig`,
  cross-checked against the device `/proc/config.gz` matrix
  (`tmp/kernel-config/v202-kernel-config.md`, different/complementary areas:
  netfilter, cgroup, bpf, pstore, tracefs, wifi, namespaces).
- Platform: `ro.board.platform=msmnile` → **Snapdragon 855 / SM8150**.
- **`compiled-in` is necessary, not sufficient.** Native init has no `ueventd`, so a
  node may not materialize (cf. KGSL `/dev/kgsl-3d0` open-block). **Confirm the node
  exists live under native init before committing a unit.** See the TWRP node map
  (`TWRP_RECOVERY_TEARDOWN_DEVICE_REFERENCE_2026-06-13.md` §3) for canonical paths.

## "Unlocked Arduino" primitive mapping

The classic Arduino I/O primitives are all compiled in and exposed via sysfs/chardev
— normally gated by Android HAL/SELinux, opened up by native-init PID1 + permissive
SELinux.

| Arduino | A90 path | CONFIG |
| --- | --- | --- |
| `digitalWrite/Read` | `/sys/class/gpio/export` | `GPIOLIB=y` `GPIO_SYSFS=y` |
| `Wire` (I2C) | `/dev/i2c-*` | `I2C_CHARDEV=y` |
| `SPI` | `/dev/spidev*` | `SPI_SPIDEV=y` |
| `analogWrite` (PWM) | `/sys/class/pwm` | `PWM=y` `PWM_SYSFS=y` `PWM_QTI_LPG=y` |
| `analogRead` | IIO / PMIC VADC channels | `IIO=y` `QTI_ADC_TM=y` `QCOM_VADC_COMMON=y` |
| USB HID | `/dev/hidg*` | `USB_F_HID=y` `USB_CONFIGFS_F_HID=y` |

## Tier 1 — drivable now (no bring-up wall; chardev/sysfs)

| Capability | CONFIG (compiled in) | Drive path |
| --- | --- | --- |
| **USB HID gadget (BadUSB)** | `USB_F_HID` + `USB_CONFIGFS_F_HID` | add `functions/hid.0` to gadget (see TWRP §1) → `/dev/hidgN` |
| **USB mass_storage gadget** | `USB_F_MASS_STORAGE` + `USB_CONFIGFS_MASS_STORAGE` | gadget function → host sees a USB disk |
| **GPIO** | `GPIOLIB` `GPIO_SYSFS` | `/sys/class/gpio` (read/designated only — see safety) |
| **I2C raw** | `I2C_CHARDEV` | `/dev/i2c-*` (read/probe; **no PMIC writes**) |
| **SPI raw** | `SPI_SPIDEV` | `/dev/spidev*` |
| **uinput / uhid / hidraw** | `INPUT_UINPUT` `UHID` `HIDRAW` | synthesize input / create HID dev / raw HID |
| **PWM** | `PWM_SYSFS` `PWM_QTI_LPG` | `/sys/class/pwm` |
| **ADC / IIO** | `IIO` `QTI_ADC_TM` `QCOM_VADC_COMMON` | PMIC voltage/thermal reads |
| **Flashlight / torch** | `LEDS_QPNP_FLASH_V2` `LEDS_CLASS` | `/sys/class/leds/...` |
| **Haptics / vibration** | `INPUT_QTI_HAPTICS` `SS_VIBRATOR` `INPUT_FF_MEMLESS` | sysfs / evdev FF |
| **Battery telemetry** | `POWER_SUPPLY` `OF_BATTERYDATA` | `/sys/class/power_supply/battery/*` |
| **HW RNG / crypto** | `HW_RANDOM` `CRYPTO_DEV_QCEDEV` `CRYPTO_DEV_QCRYPTO` | `/dev/hwrng`, qcedev |
| **Networking toolkit** | `TUN` `L2TP`(+V3/IP/ETH) `BRIDGE` + iptables `IP_NF_NAT` | hotspot NAT, VPN, tunnels, bridging |
| **Backlight** | (panel driver) | `/sys/class/backlight/panel0-backlight/brightness` |

## Tier 2 — medium wall

- **NFC:** standard stack **off** (`CONFIG_NFC` not set), but `SAMSUNG_NFC=y` +
  `NFC_PN547=y` — NXP PN547 controller via Samsung's **non-standard char driver**
  (not the mainline `nfc` genl interface). Reachable only by reverse-engineering the
  sec-nfc protocol. Hardware present, interface non-standard.
- **Sound:** `SND=y` `SND_PCM=y` `SND_USB_AUDIO=y` (ALSA core on), but Qualcomm
  mixer routing + ADSP bring-up is the wall (needs `mixer_paths*` from the vendor
  partition — not in recovery image).

## Tier 3 — big wall (Wi-Fi-class bring-up)

- **Camera:** `VIDEO_V4L2=y` `VIDEO_DEV=y` **`SPECTRA_CAMERA=y`** (Qualcomm Spectra
  ISP; `MSM_CAMERA`/`QCOM_CAMSS` not set). Driver present but CAMSS/ISP/CSI/sensor
  power pipeline bring-up is a multi-week subsystem. Defer.

## Safety — the brick zone

The Arduino freedom has a real cost the $3-board metaphor lacks: **GPIO/I2C/SPI
*writes* to the PMIC / regulators / power rails can damage or permanently brick the
phone.** This is exactly the project invariant *"no PMIC/GPIO/GDSC/regulator
writes."* Line: **reads + driving designated peripherals via their own drivers
(haptics/flash/backlight) = safe; raw register writes to power-management buses =
forbidden.**

## Relation to current plan

Foundation/reference for a future **peripheral-breadth track**, not a queued item.
The active queued epic remains E1/E2 (WLAN nl80211 / rtnetlink events) per
`GOAL.md`. When breadth opens, the fact-based order is: **BadUSB (HID gadget) →
i2c/spi read-probing → flashlight/vibration/battery** (all Tier 1, no wall), each
gated by a live node-existence recon first. Sound/NFC/camera are separate, walled
chapters.
