# Native Init V923 CNSS-before-eSoC Live Gate Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| V923 bounded live gate | `tmp/wifi/v923-mdm-helper-cnss-before-esoc-capture-live/manifest.json` | `v923-wlfw-precondition-missing-no-open` |

V923 passed as an intermediate blocker classification. It started the native
`mdm_helper` plus CNSS/WLFW request path, but no WLFW precondition appeared, so
the helper did not open `/dev/subsys_esoc0`.

## Runner

- Added `scripts/revalidation/native_wifi_mdm_helper_cnss_before_esoc_capture_v923.py`.
- The runner executes helper `v152` mode
  `wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture`.
- The live gate permits only:
  - read-only system/vendor setup and private property shim;
  - selinuxfs mount/unmount for runtime parity;
  - `/vendor/bin/pm-service`;
  - `/vendor/bin/mdm_helper`;
  - `/vendor/bin/cnss_diag`;
  - `/vendor/bin/cnss-daemon -n -l`;
  - `/dev/subsys_esoc0` child open only if a WLFW precondition marker appears.

## Findings

| Field | Value |
| --- | --- |
| `per_mgr_light_start_executed` | `true` |
| `mdm_helper_start_executed` | `true` |
| `cnss_diag_start_executed` | `true` |
| `cnss_daemon_start_executed` | `true` |
| `wlfw_precondition_observed` | `false` |
| `subsys_esoc0_open_attempted` | `false` |
| `subsys_esoc0_controller_open_attempted` | `false` |
| `cleanup_needed` | `false` |
| `cleanup_reboot_executed` | `false` |

The helper observed `mdm_helper` holding `/dev/esoc-0`, then started CNSS
diagnostic and daemon actors. Across `25` WLFW-precondition polls, no
`cnss-daemon wlfw_start`-equivalent marker appeared. Because the precondition
remained absent, the fail-closed gate kept `/dev/subsys_esoc0` closed.

The helper stdout exceeded the 1 MiB command transcript cap before the final
result keys. The runner treats this exact shape as a fail-closed derived result
only when all of these are true:

- execns returned `rc=0`;
- stdout truncation is explicit in the transcript;
- `wlfw_precondition_observed=0`;
- no `subsys_trigger.*` or open-attempt marker exists;
- post-surface actor/helper checks are clean.

## Guardrails

- No service-manager start.
- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credential use.
- No DHCP/route mutation.
- No external ping.
- No controller `ESOC_NOTIFY`, `BOOT_DONE`, or subsystem controller open.
- No boot image, partition, firmware, GPIO, sysfs, debugfs, module, bind, or
  unbind mutation.

## Device Health

Post-run checks passed:

```text
boot: BOOT OK shell 4.2s
selftest: pass=11 warn=1 fail=0
exposure: guard=ok warn=0 fail=0 ncm=absent tcpctl=stopped boundary=usb-local
```

No actor or helper process remained in the post-run surface.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_mdm_helper_cnss_before_esoc_capture_v923.py
python3 scripts/revalidation/native_wifi_mdm_helper_cnss_before_esoc_capture_v923.py \
  --out-dir tmp/wifi/v923-mdm-helper-cnss-before-esoc-capture-plan \
  plan
python3 scripts/revalidation/native_wifi_mdm_helper_cnss_before_esoc_capture_v923.py \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-mdm-helper-cnss-before-subsys-trigger-capture \
  --allow-cleanup-reboot \
  --assume-yes \
  run
python3 scripts/revalidation/a90ctl.py bootstatus
python3 scripts/revalidation/a90ctl.py selftest
```

## Interpretation

The V918 soft-reset blocker was avoided: V923 did not repeat the D-state
`/dev/subsys_esoc0` open because CNSS/WLFW did not reach the required
precondition. The remaining blocker is earlier than the eSoC trigger: native
CNSS start-only under the current private runtime still does not emit the WLFW
request marker that Android shows before `__subsystem_get(esoc0)`.

## Next

V924 should classify the missing CNSS/WLFW precondition before any further
subsystem-open live gate. The most useful candidates are:

1. reduce helper output volume so final result keys are not transcript-truncated;
2. compare `cnss-daemon` stderr/property access failures against Android
   property contexts;
3. inspect whether missing linkerconfig/APEX/VNDK/property namespace inputs
   prevent `cnss-daemon wlfw_start`;
4. keep service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and
   external ping blocked until WLFW/BDF/wlan0 progression is proven.
