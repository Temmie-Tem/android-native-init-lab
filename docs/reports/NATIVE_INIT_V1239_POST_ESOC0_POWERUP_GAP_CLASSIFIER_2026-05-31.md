# V1239 Post-esoc0 Powerup Gap Classifier

- report: `docs/reports/NATIVE_INIT_V1239_POST_ESOC0_POWERUP_GAP_CLASSIFIER_2026-05-31.md`
- classifier: `scripts/revalidation/native_wifi_post_esoc0_powerup_gap_classifier_v1239.py`
- evidence: `tmp/wifi/v1239-post-esoc0-powerup-gap-classifier/manifest.json`

- decision: `v1239-gap-is-after-pm-service-esoc0-before-gpio142-pcie-wlfw`
- pass: `True`
- reason: native now reaches the same `pm-service` `/dev/subsys_esoc0` powerup entry as Android, but does not receive the downstream GPIO142/PCIe/SSCTL/WLFW response.
- next_step: design a bounded read-only/cleanup-safe classifier for the SDX50M response inputs around `mdm_subsys_powerup`; do not start Wi-Fi HAL/connect yet.

## Checks

| check | status | detail |
| --- | --- | --- |
| Android positive reference | pass | Android reaches `mdm3=ONLINE`, WLFW/BDF, and `wlan0` |
| Android post-esoc0 chain | pass | GPIO142 IRQ `1`, PCIe RC1 lines `18`, sysmon esoc0 lines `1` |
| Native reaches PM esoc0 | pass | V1238 late `per_proxy` started and actor `/dev/subsys_esoc0` attempt is present |
| Native no lower publication | pass | `mdm3=['OFFLINING']`, WLFW `0`, `wlan0=false` |
| Guardrails | pass | no Wi-Fi HAL/connect/network/flash actions |

## Comparison

| field | Android reference | Native V1238 |
| --- | --- | --- |
| `pm-service` `/dev/subsys_esoc0` entry | present | present |
| Binder `mdm_subsys_powerup` | present | present |
| GPIO142 IRQ | `1` | not observed |
| PCIe RC1 | RC1 reset/L0 present | not observed in lower publication |
| sysmon esoc0 SSCTL | present | absent |
| `ks` / MHI pipe | present | absent |
| WLFW/BDF | present | absent |
| `wlan0` | present | absent |
| `mdm3` state | `ONLINE` | `OFFLINING` |

## Interpretation

V1239 moves the blocker below the userspace PM actor path. V1238 already proved
late `per_proxy` can deliver the request to `pm-service`; V1239 proves the gap is
after `pm-service` enters `/dev/subsys_esoc0` / `mdm_subsys_powerup` and before
the hardware response sequence that Android gets: GPIO142, PCIe RC1, SSCTL, MHI,
WLFW, BDF, and `wlan0`.

The next useful gate is not Wi-Fi HAL or connect. It is a cleanup-safe
classifier for the SDX50M response inputs around `mdm_subsys_powerup`: GPIO142
IRQ, AP2MDM/MDM2AP pin state if safely readable, PCIe RC1 state, PMIC/pinctrl
state, and reboot-required cleanup behavior.

## Safety

Host-only classifier. No device command, Wi-Fi HAL, scan/connect, credentials,
DHCP/routes, external ping, flash, boot image write, or partition write occurred.
