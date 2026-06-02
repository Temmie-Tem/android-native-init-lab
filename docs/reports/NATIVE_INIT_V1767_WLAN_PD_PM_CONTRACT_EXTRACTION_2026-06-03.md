# Native Init V1767 WLAN-PD PM Contract Extraction

## Summary

- Cycle: `V1767`
- Type: host-only PeripheralManager contract extraction
- Decision: `v1767-pm-contract-extracted-live-suspended-host-pass`
- Label: `pm-contract-extracted-live-suspended`
- Result: PASS
- Reason: narrow PM contract extracted; live service-object/register discriminator remains suspended by current stop directive
- Evidence: `tmp/wifi/v1767-wlan-pd-pm-contract-extraction`

## Extracted Contract

The next narrow live discriminator, if explicitly reopened, must prove this ordered contract before any Wi-Fi connection work:

1. Current-boot SELinux/policy-load and service-manager namespace are valid for `vendor_per_mgr`.
2. `vndservicemanager` is started and explicitly ready.
3. `/vendor/bin/pm-service` registers `vendor.qcom.PeripheralManager`.
4. `/vendor/bin/vndservice list` sees `vendor.qcom.PeripheralManager` in the same namespace used by `cnss-daemon`.
5. `cnss-daemon` `libperipheral_client.so` lookup returns a non-null service object.
6. `IPeripheralManager::asInterface` and manager-register transaction are reached.
7. PM register/vote returns or reaches the server-side post-entry checkpoints.
8. Only then measure `requested_wlanmdsp`, WLFW service 69, and `wlan0`.

## Facts

- V1087 policy/readiness delta classified: `True`
- V1092 provider registration observed: `True`
- V1092 `vndservicemanager` readiness observed: `True`
- V1095 provider-positive CNSS window observed: `True`
- V1101 CNSS server register entry observed: `True`
- V1101 server register entry only: `True`
- V1757 static null-service branch proven: `True`
- Native PM null branch / `asInterface` / register TX: `True` / `False` / `False`
- Android PM vote before request / request seen: `True` / `True`
- Native requested `wlanmdsp`: `False`
- V1764 dormant artifact available: `True`
- Active stop suspends live PM helper gate: `True`

## Classification

- `provider_seen` alone is insufficient; V1095/V1101 show provider-positive windows can still leave `wlanmdsp.mbn` unrequested.
- The decisive pre-request milestones are non-null service object, `asInterface`, manager-register TX/return, and PM vote/register success.
- A future live gate should include labels that distinguish `provider-not-visible`, `service-object-null`, `register-tx-no-return`, `register-return-still-no-request`, and `request-progress`.
- The current directive still suspends that live gate, so this unit stops at host/source-only contract extraction.

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PM actor start, QCACLD load, eSoC/RC1 action, restart-PD request, firmware write, partition write, PMIC/GPIO/GDSC write, PCI rescan, platform bind/unbind, or tracefs write.

## Next

- If the stop directive remains active: continue only host/source-only analysis of the PM register server-side branch after entry.
- If the narrow live gate is explicitly reopened: deploy the dormant V1764-style helper only after adding the refined output labels above.
- Do not proceed to Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping until `wlan0` exists and the user explicitly opens the active connection gate.
