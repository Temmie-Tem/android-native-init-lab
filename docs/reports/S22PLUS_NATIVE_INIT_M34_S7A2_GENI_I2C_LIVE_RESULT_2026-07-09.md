# S22+ M34 S7A2 GENI I2C Live Result

Date: 2026-07-09 KST / 2026-07-08 UTC

Status: PASS for safety/rollback and survival, FAIL for host-visible USB
enumeration. The one-shot S7A2 exception is consumed and retired in
`AGENTS.md`; no active S7A2 live authorization remains.

## Scope

This was the one-shot M34 S7A2 boot-only live gate for:

- adding the missing GENI I2C transport closure:
  `gpi.ko`, `msm-geni-se.ko`, `i2c-msm-geni.ko`
- preserving dep-safe order:
  `msm-geni-se.ko` -> `gpi.ko` -> `i2c-msm-geni.ko`
- keeping `i2c-msm-geni.ko` before `pdic_max77705.ko`
- keeping the S7A max77705/PDIC/altmode producer chain
- using a bounded TypeC role-write discriminator only on
  `/sys/class/typec/port0/data_role=device` and
  `/sys/class/typec/port0/power_role=sink` if no partner is visible
- keeping minimal `ss_acm.0` configfs, `ssusb/mode=peripheral`, final
  `UDC=a600000.dwc3`, no `soft_connect`, no FunctionFS/stock composite, no
  Android/Magisk handoff, no reboot request, no persistent mount, and no block
  writes

Helper:

`workspace/public/src/scripts/revalidation/s22plus_m34_s7a2_geni_i2c_live_gate.py`

Run log:

`workspace/private/runs/s22plus_m34_s7a2_geni_i2c_live_gate_20260708T233149Z/s22plus_m34_s7a2_geni_i2c_live_gate.txt`

## Candidate Pins

- AP.tar.md5 SHA256: `cb89ccf9c8c5481938ddd415930c78a23e1a679d45fdc57f95e6d1b48776bd59`
- padded `boot.img` SHA256: `b9a4d4c2170da2ed6125aa44734005303d81d874b72402513def97b2f8406a54`
- direct `/init` SHA256: `8f8eb4a6f4d94bc552ec61819b9c2b4ea4ec4de7fb7aa097fab7193c6f117e5a`
- template source SHA256: `ce12ea11a6c0f73f5f042801435b419637b473eff6631155f45d4ad382d8a80a`
- module-list SHA256: `c0c35e02fe61a3f6c18c221a9ae2cc1a54aafd38374117fa954dbfa675700998`
- preserved kernel SHA256: `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
- known-booting Magisk boot base SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

## Live Timeline

`timeline.json` uses the standard single `events:[{name,timestamp_utc}]` shape.
Observed events:

- `live_session_start`: `2026-07-08T23:32:00.541577Z`
- `candidate_flash_start`: `2026-07-08T23:32:11.135717Z`
- `candidate_flash_done`: `2026-07-08T23:32:12.681851Z`
- `candidate_boot_ready`: `2026-07-08T23:32:13.961532Z`
- `rollback_flash_start`: `2026-07-08T23:35:21.185185Z`
- `rollback_flash_done`: `2026-07-08T23:35:22.532455Z`
- `rollback_boot_ready`: `2026-07-08T23:35:54.123888Z`
- `live_session_end`: `2026-07-08T23:35:54.464926Z`

Candidate observation lasted the full 90 second survival window. The helper
then requested manual Download mode for rollback. The operator reported RDX
entry followed by Download mode entry.

## Host USB Result

Before flashing, Android baseline was visible as Samsung `04e8:6860`
`SAMSUNG_Android` with CDC ACM present.

After S7A2 candidate flash and across all 18 park snapshots:

- no Samsung `04e8:*`
- no `04e8:6860`
- no CDC ACM
- no `/dev/ttyACM*`
- no ADB
- no Odin endpoint during the observation window
- no Samsung upload/download endpoint during the observation window

Helper result:

`survived-observation-window-manual-download-required`

Interpretation: S7A2 did not create a host-visible USB electrical session or
pullup. Adding GENI I2C transport plus the bounded TypeC role-write
discriminator was not sufficient to make the host see any Samsung USB device.
The result preserves survival and narrows the missing piece beyond S7A's dead
I2C-bus hypothesis.

## Rollback

Rollback used the returned Odin endpoint to flash the pinned Magisk boot-only
rollback AP:

`d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`

Post-rollback Android state:

- `sys.boot_completed=1`
- model `SM-S906N`
- device `g0q`
- bootloader/build `S906NKSS7FYG8`
- verified boot state `orange`
- `boot_recovery=0`
- Magisk root present
- boot partition SHA256 restored to
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

Retained evidence:

- pstore files: empty
- `/proc/last_kmsg`: readable, 2,097,136 bytes
- S7A2 marker found: `0`

## Conclusion

S7A2 closed the GENI I2C transport gap without causing a fast boot loop or
early PMIC/RDX reset, but it still produced no host-visible USB endpoint.
That retires "S7A only failed because the max77705 producer chain lacked
GENI I2C transport" as a sufficient explanation.

The next unit should stay host-only until it explains the complete absence of
host-visible `04e8:*` after S7A2. The most likely next direction is to compare
direct-PID1 ordering against stock Android's USB/TypeC orchestration more
deeply: stock USB HAL/service choreography, TypeC partner creation timing,
PDIC/extcon notifier paths, configfs ownership/service triggers, and whether a
minimal direct PID1 environment is missing a stock userspace participant before
DWC3 can assert pullup.

No S7A2 repeat or downstream descriptor/composition pivot is authorized by this
result.
