# Native Init V800 Provider-first ICNSS Edge v124 Replay Plan

## Goal

Run the next bounded live gate selected by V799: replay the service `74`
positive, PeripheralManager-confirmed provider-first CNSS tail on the current
stock v724 native image using the already deployed helper v124.

## Scope

- Target scripts:
  - `scripts/revalidation/native_wifi_provider_first_icnss_edge_v800.py`
  - `scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v800.py`
- Target helper:
  - `/cache/bin/a90_android_execns_probe`
  - marker: `a90_android_execns_probe v124`
  - sha256: `d44cbb538db11a280aa789ccafb008476ac541ec08bb96f549670ae28db7cec6`
- Expected native image:
  - `A90 Linux init 0.9.68 (v724)`

## Live Gate

The live path is inherited from the proven V712/V700 provider-first contract:

```text
V641 clean-DSP reboot
  -> V401 SELinuxfs mount surface
  -> V490 SELinux policy-load proof
  -> service74-gated provider-first CNSS retry
  -> PeripheralManager vndservice query
  -> ICNSS/QCA edge capture
  -> reboot cleanup
```

## Hard Gates

- No Wi-Fi HAL, `wificond`, supplicant, or hostapd start.
- No scan/connect/link-up, credential use, DHCP, route change, or external ping.
- No `esoc0` open/hold, subsystem state write, bind/unbind, module load/unload,
  boot image write, or partition write.
- No Wi-Fi secret material in tracked output.

## Success Criteria

- V800 plan and runner compile.
- Live run uses helper v124 on native v724.
- Current-boot prep completes and service `180/74` opens.
- PeripheralManager registration is queried before CNSS retry interpretation.
- ICNSS edge capture is present.
- WLFW/service `69`, BDF, wiphy, or `wlan0` progression is classified if it
  appears; otherwise the pre-WLFW blocker is preserved without widening to
  connection-level behavior.
- Reboot cleanup returns native v724 to healthy status.

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_provider_first_icnss_edge_v800.py \
  scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v800.py

python3 scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v800.py \
  --out-dir tmp/wifi/v800-provider-first-icnss-edge-v124-plan-check \
  plan

python3 scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v800.py \
  --out-dir tmp/wifi/v800-provider-first-icnss-edge-v124-live \
  --arm-companion-runtime-sec 30 \
  --apply --assume-yes \
  run

git diff --check
```
