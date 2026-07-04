# WSTA79 Persistent Operator Packet Status Source

- Date: 2026-07-04
- Scope: host-only status for WSTA78 operator packets
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta79-persistent-operator-packet-status-pass`

## Summary

WSTA79 consumes a private WSTA78 operator packet, reruns WSTA78 from that
packet's original WSTA77 summary, and reports whether the packet is still
current enough to use as a default-off handoff for an explicit WSTA58 live gate.

This closes the age/drift gap after WSTA78: an operator packet that was fresh
when generated can later become stale, or the fresh selected WSTA76/WSTA73 path
can drift.  WSTA79 classifies that before any live command is considered.

WSTA79 does not replace token placeholders, start a tunnel, touch the device,
connect Wi-Fi, run DHCP, run public smoke, or execute WSTA58.

## Source Change

Added:

- `workspace/public/src/scripts/server-distro/run_wsta79_persistent_operator_packet_status.py`
- `tests/test_server_distro_wsta79_persistent_operator_packet_status.py`

The runner is fail-closed until a private WSTA78 packet is supplied:

```text
python3 workspace/public/src/scripts/server-distro/run_wsta79_persistent_operator_packet_status.py \
  --wsta78-operator-packet-json workspace/private/runs/server-distro/<wsta78-run>/wsta78_operator_packet.json
```

WSTA79 applies the original `selected_ready_index` from the packet unless an
explicit override is supplied.  It compares only logical operator selection
fields, not the new recheck artifact paths that necessarily differ on every
run.

## States

```text
READY_TO_RUN_DEFAULT_OFF
STALE_OR_NOT_READY
DRIFT_RECHECK_REQUIRED
```

`READY_TO_RUN_DEFAULT_OFF` requires the WSTA78 recheck to pass, the selected
WSTA76 brief to match, the selected WSTA73 packet to match, and the WSTA58
command template to match.

`STALE_OR_NOT_READY` means the WSTA78 recheck did not produce a ready packet.

`DRIFT_RECHECK_REQUIRED` means the recheck produced a ready packet, but not the
same logical selected WSTA76/WSTA73/template tuple as the supplied operator
packet.

## Private Smoke

Private smoke directory:

```text
workspace/private/runs/server-distro/wsta79-operator-packet-status-smoke-20260704T113155Z
```

Observed flow:

```text
WSTA72 prepare-to-arm
WSTA73 arming packet
WSTA75 arming inventory
WSTA76 launch brief
WSTA77 launch brief summary
WSTA78 operator packet
WSTA79 operator packet status
```

Observed WSTA79 result:

```text
decision=wsta79-persistent-operator-packet-status-pass
state=READY_TO_RUN_DEFAULT_OFF
ready_for_live=true
wsta78_recheck_decision=wsta78-persistent-operator-packet-pass
selected_wsta73_arming_packet=workspace/private/runs/server-distro/wsta79-operator-packet-status-smoke-20260704T113155Z/packet/wsta73_arming_packet.json
fresh_selected_wsta73_arming_packet=workspace/private/runs/server-distro/wsta79-operator-packet-status-smoke-20260704T113155Z/packet/wsta73_arming_packet.json
selected_wsta76_launch_brief=workspace/private/runs/server-distro/wsta79-operator-packet-status-smoke-20260704T113155Z/brief/wsta76_launch_brief.json
fresh_selected_wsta76_launch_brief=workspace/private/runs/server-distro/wsta79-operator-packet-status-smoke-20260704T113155Z/brief/wsta76_launch_brief.json
initial_seconds_remaining=294
packet_match=true
template_match=true
ack_count=7
guardrail_count=5
live_execution_requested=false
public_url_value_logged=false
secret_values_logged=0
```

Generated status:

```text
workspace/private/runs/server-distro/wsta79-operator-packet-status-smoke-20260704T113155Z/status/wsta79_operator_packet_status.json
workspace/private/runs/server-distro/wsta79-operator-packet-status-smoke-20260704T113155Z/status/wsta79_operator_packet_status.md
```

## Safety

- No boot image was built or flashed.
- No forbidden partition was touched.
- No device command, native reboot, Wi-Fi association, DHCP, public tunnel,
  public smoke, userdata action, switch-root, or external service action ran.
- The runner has no `native_init_flash.py` or `a90ctl.py` call path.
- WSTA79 invokes WSTA78/WSTA77/WSTA76/WSTA75/WSTA74/WSTA73 host-only packet,
  summary, brief, inventory, status, and packet surfaces only.
- WSTA58 live execution remains a separate explicit operator-selected gate.
- Redaction checks are applied to the public summary and generated Markdown.
- The committed report/source/test changes contain no raw public URL, public
  tunnel domain, confirm-token value, Wi-Fi credential, SSID, BSSID, MAC, IP,
  gateway, DNS, lease id value, or device serial.
- Raw private prepare-to-arm outputs, WSTA73 packets, WSTA75 inventories,
  WSTA76 briefs, WSTA77 summaries, WSTA78 packets, and WSTA79 status artifacts
  remain under `workspace/private/`.

## Validation

Compile check:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta79_persistent_operator_packet_status.py \
  tests/test_server_distro_wsta79_persistent_operator_packet_status.py
```

Result: pass

WSTA79 focused tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta79_persistent_operator_packet_status
```

Result: `Ran 8 tests ... OK`

Focused WSTA52-WSTA79 regression:

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
  tests.test_server_distro_wsta76_persistent_launch_brief \
  tests.test_server_distro_wsta77_persistent_launch_brief_summary \
  tests.test_server_distro_wsta78_persistent_operator_packet \
  tests.test_server_distro_wsta79_persistent_operator_packet_status
```

Result: `Ran 168 tests ... OK`

Fresh WSTA72 + WSTA73 + WSTA75 + WSTA76 + WSTA77 + WSTA78 + WSTA79 private
smoke: pass.

## Next

The default-off persistent exposure workflow now has prepare-to-arm, arming
packet, per-packet status, multi-packet inventory, launch brief, multi-brief
operator summary, final operator packet, and a current-time operator packet
status check.  Continue only with explicit operator-selected WSTA58 live proof,
or with a concrete appliance-level integration that does not start public
exposure by default.
