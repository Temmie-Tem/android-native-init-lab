# Native Init V1758 WLAN-PD Provider Visibility Contract Classifier

## Summary

- Cycle: `V1758`
- Type: host-only provider visibility contract classifier
- Decision: `v1758-provider-positive-contract-not-composed-with-wlfw-route-host-pass`
- Label: `compose-provider-positive-vndservice-gate-before-cnss-pm-register`
- Result: PASS
- Reason: V1757 proves V1736 sees a null PeripheralManager service object; V1092/V1087 prove the provider requires policy-load plus explicit vndservicemanager readiness/query; V1101 proves provider-positive PM register can reach pm-service; V1736 reaches WLFW without that provider-positive contract, while V1686's broad actor march regresses WLFW
- Evidence: `tmp/wifi/v1758-wlan-pd-provider-visibility-contract-classifier`

## Inputs

| Input | Decision / State | Key Facts |
| --- | --- | --- |
| V1757 | `v1757-peripheral-manager-service-get-null-host-pass` | label `peripheral-manager-service-object-null`: V1736 `getService("vendor.qcom.PeripheralManager")` returns null |
| V1092 | `v1092-pm-provider-registration-observed` | provider_seen=`True`, vndservicemanager_ready=`True`, query=`True` |
| V1087 | `v1087-addservice-readiness-policy-delta-classified` | addService failure without readiness/policy, provider-positive with V490 + readiness |
| V1101 | `v1101-cnss-server-register-no-return-at-pm_server_register_entry` | provider_seen=`True`, CNSS client/server register entries `1`/`1` |
| V1736 | `v1736-wlfw-start-reached-downstream-block-rollback-pass` | WLFW request hits `1`, provider enabled/query/readiness `0`/`0`/`0` |
| V1686 | `v1686-pm-trio-child-failed-rollback-pass` | PM actors running `1`/`1`, WLFW request `0`, query `0` |

## pm-service Static Surface

- Path: `tmp/wifi/v1073-host-only/vendor-extract/files/pm-service`
- Exists/size: `True` / `54888`

| Literal / Dependency | Present |
| --- | ---: |
| `vendor_qcom_peripheral_manager` | `True` |
| `dev_vndbinder` | `True` |
| `libbinder` | `True` |
| `libperipheral_client` | `True` |
| `qmi_service_start` | `True` |
| `vendor_peripheral_prefix` | `True` |

## Interpretation

- The missing object in V1757 is not an unknown `libperipheral_client.so` branch anymore. It is a missing visible provider object.
- V1092 proves `pm-service` can register `vendor.qcom.PeripheralManager` when V490 policy-load and explicit `vndservicemanager_ready`/`vndservice list` gating are present.
- V1087 explains why earlier attempts failed: `addService` was sensitive to the policy/readiness preconditions.
- V1101 proves a provider-positive namespace can carry CNSS PM register traffic into `pm-service`.
- V1736 is the route that reaches `wlfw_start`/`wlfw_service_request`, but it explicitly has `peripheral_manager.enabled=0`, `vndservice_query.enabled=0`, and `vndservicemanager_readiness.enabled=0`.
- V1686 proves that simply adding PM actors is not enough; that broad actor march regresses the WLFW worker and still does not request `wlanmdsp.mbn`.

## Next Candidate

- V1759 should be source/build-only first: compose the V1092 provider-positive contract into the V1736 internal-modem/WLFW route.
- Minimum intended order: service managers -> explicit `vndservicemanager_ready` -> `pm_proxy_helper`/`per_mgr` -> `vndservice list` provider proof -> internal modem firmware/tftp/CNSS route -> CNSS PM register/WLFW observer.
- Success criterion for the next live gate is not actor presence. It must observe non-null PeripheralManager lookup or PM register/transaction progress, then measure whether `wlanmdsp.mbn` is requested.
- Keep blocked: broad PM actor march, eSoC/RC1, `/dev/subsys_esoc0`, `boot_wlan`, restart-PD, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping until `wlanmdsp.mbn` request or WLFW service 69 appears.

## Safety Scope

This classifier is host-only. It reads retained manifests, retained helper transcripts, and a staged `pm-service` binary. It performs no device contact, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware/partition write, or new actor start.
