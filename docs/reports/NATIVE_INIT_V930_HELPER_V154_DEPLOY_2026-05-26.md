# Native Init V930 Helper v154 Deploy

## Scope

V930 deploys only `a90_android_execns_probe v154` to `/cache/bin/a90_android_execns_probe` so the next live matrix gate can run on the device. It does not start service-manager, CNSS, Wi-Fi HAL, scan/connect, DHCP, routing, or external ping.

## Evidence

- Deploy tool: `scripts/revalidation/native_wifi_helper_v154_deploy_v930.py`
- Manifest: `tmp/wifi/v930-execns-helper-v154-deploy/manifest.json`
- Summary: `tmp/wifi/v930-execns-helper-v154-deploy/summary.md`
- Serial transcript: `tmp/wifi/v930-execns-helper-v154-deploy/host/serial-install-helper.txt`
- Local helper: `tmp/wifi/v929-execns-helper-v154-build/a90_android_execns_probe`
- Remote helper: `/cache/bin/a90_android_execns_probe`

## Result

- Decision: `execns-helper-v154-deploy-pass`
- Transfer: serial appendfile + uudecode, `837` chunks, safe max cmd line `3890` bytes under limit `3968`.
- Remote sha256: `f87fb6032a4333f4b3dfabc9766b8620bf6e3f2acc9c1081b09738933cc7c9ab`
- Remote marker: `a90_android_execns_probe v154`
- Remote contract: V929 matrix mode, allow flag, order enum, and existing compact CNSS-before-eSoC mode present.

## Postflight

- Native health remained clean: `BOOT OK`, selftest `fail=0`.
- service-manager processes remained clean: no `servicemanager`, `hwservicemanager`, or `vndservicemanager` process was left running.
- Wi-Fi link surface remained clean: no `wlan*`, `swlan*`, `p2p*`, `wiphy*`, or `phy*` link was observed.
- Netservice remained disabled; no NCM/TCP control service was started by this deploy.

## Guardrails

- Device mutation was limited to replacing `/cache/bin/a90_android_execns_probe`.
- No daemon/service-manager live start was performed.
- No Wi-Fi HAL, scan/connect/link-up, credential use, DHCP, route change, or external ping was performed.
- No eSoC ioctl, subsystem open, GPIO/sysfs/debugfs write, boot image write, or partition write was performed.

## Next

V931 should run one bounded matrix order at a time below Wi-Fi HAL and below scan/connect. The first candidate should be `--service-manager-order before-cnss` or `after-mdm-helper-esoc-fd`, depending on whether the goal is to prioritize Binder-clean behavior or preserve the lower `mdm_helper`/CNSS publication window first.
