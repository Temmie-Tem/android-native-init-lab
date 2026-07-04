# WSTA76 Persistent Launch Brief Source

- Date: 2026-07-04
- Scope: host-only launch brief for WSTA75-selected arming packets
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta76-persistent-launch-brief-pass`

## Summary

WSTA76 consumes a private WSTA75 arming inventory, reruns WSTA75 against the
original scan root, selects a fresh READY arming packet, loads the fresh WSTA73
recheck packet, and writes a compact operator launch brief.

This closes the default-off handoff gap between "there is a READY packet" and
"here is the exact still-fresh packet, command template, acknowledgements,
abort conditions, and cleanup expectations to review before a separately chosen
WSTA58 live gate."

WSTA76 does not replace token placeholders, start a tunnel, touch the device,
connect Wi-Fi, or run public smoke.

## Source Change

Added:

- `workspace/public/src/scripts/server-distro/run_wsta76_persistent_launch_brief.py`
- `tests/test_server_distro_wsta76_persistent_launch_brief.py`

The runner is fail-closed until a private WSTA75 inventory is supplied:

```text
python3 workspace/public/src/scripts/server-distro/run_wsta76_persistent_launch_brief.py \
  --wsta75-arming-inventory-json workspace/private/runs/server-distro/<wsta75-run>/wsta75_arming_inventory.json \
  --ready-index 0
```

WSTA76 never trusts the supplied inventory as fresh.  It extracts the inventory
scan root, reruns WSTA75, selects from the fresh READY candidates, and only then
writes the launch brief.

## Private Smoke

Private smoke directory:

```text
workspace/private/runs/server-distro/wsta76-launch-brief-smoke-20260704T111000Z
```

Observed flow:

```text
WSTA72 prepare-to-arm
WSTA73 arming packet
WSTA75 arming inventory
WSTA76 launch brief
```

Observed WSTA76 result:

```text
decision=wsta76-persistent-launch-brief-pass
state=READY_TO_EXECUTE_DEFAULT_OFF
ready_for_live=true
ready_candidate_count=1
selected_wsta73_arming_packet=workspace/private/runs/server-distro/wsta76-launch-brief-smoke-20260704T111000Z/packet/wsta73_arming_packet.json
initial_seconds_remaining=299
ack_count=7
abort_condition_count=5
live_execution_requested=false
public_url_value_logged=false
secret_values_logged=0
```

Generated brief:

```text
workspace/private/runs/server-distro/wsta76-launch-brief-smoke-20260704T111000Z/brief/wsta76_launch_brief.json
workspace/private/runs/server-distro/wsta76-launch-brief-smoke-20260704T111000Z/brief/wsta76_launch_brief.md
```

## Safety

- No boot image was built or flashed.
- No forbidden partition was touched.
- No device command, native reboot, Wi-Fi association, DHCP, public tunnel,
  public smoke, userdata action, switch-root, or external service action ran.
- The runner has no `native_init_flash.py` or `a90ctl.py` call path.
- WSTA76 invokes WSTA75/WSTA74/WSTA73 status and packet rendering surfaces only;
  WSTA58 live execution remains a separate explicit operator-selected gate.
- Redaction checks are applied to the public summary and generated Markdown.
- The committed report/source/test changes contain no raw public URL, public
  tunnel domain, confirm-token value, Wi-Fi credential, SSID, BSSID, MAC, IP,
  gateway, DNS, lease id value, or device serial.
- Raw private prepare-to-arm outputs, WSTA73 packets, WSTA75 inventories, and
  WSTA76 brief artifacts remain under `workspace/private/`.

## Validation

Compile check:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta76_persistent_launch_brief.py
```

Result: pass

WSTA76 focused tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta76_persistent_launch_brief
```

Result: `Ran 8 tests ... OK`

Focused WSTA52-WSTA76 regression:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta52_persistent_exposure_design \
  tests.test_server_distro_wsta53_persistent_exposure_plan \
  tests.test_server_distro_wsta54_private_lease_artifact \
  tests.test_server_distro_wsta55_short_lived_public_proof \
  tests.test_server_distro_wsta58_renewal_manual_stop_proof \
  tests.test_server_distro_wsta63_persistent_session_controller \
  tests.test_server_distro_wsta64_persistent_session_readiness_audit \
  tests.test_server_distro_wsta65_persistent_session_status \
  tests.test_server_distro_wsta66_persistent_session_retire \
  tests.test_server_distro_wsta67_persistent_session_inventory \
  tests.test_server_distro_wsta68_persistent_session_bulk_retire \
  tests.test_server_distro_wsta69_persistent_session_snapshot \
  tests.test_server_distro_wsta70_persistent_session_launch_manifest \
  tests.test_server_distro_wsta71_persistent_launch_readiness_audit \
  tests.test_server_distro_wsta72_persistent_prepare_to_arm \
  tests.test_server_distro_wsta73_persistent_arming_packet \
  tests.test_server_distro_wsta74_persistent_arming_status \
  tests.test_server_distro_wsta75_persistent_arming_inventory \
  tests.test_server_distro_wsta76_persistent_launch_brief
```

Result: `Ran 143 tests ... OK`

Fresh WSTA72 + WSTA73 + WSTA75 + WSTA76 private smoke: pass.

## Next

The default-off persistent exposure workflow now has prepare-to-arm, arming
packet, per-packet status, multi-packet inventory, and a final host-only launch
brief.  Continue only with explicit operator-selected WSTA58 live proof, or
further default-off operator UX/reporting that does not start public exposure.
