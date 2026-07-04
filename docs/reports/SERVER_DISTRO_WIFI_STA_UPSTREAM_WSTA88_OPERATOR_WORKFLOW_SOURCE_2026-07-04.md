# WSTA88 Persistent Operator Workflow Source

- Date: 2026-07-04
- Scope: source-only default-off operator UX wrapper after WSTA87
- Decision: `wsta88-persistent-operator-workflow-source-pass`

## Summary

WSTA87 proved the WSTA80 -> WSTA58 live path and the WSTA84 clean-image cache.
WSTA88 turns the previously inline host orchestration into a reusable operator
workflow:

```text
WSTA88 default:
  WSTA72 prepare-to-arm
  -> WSTA73 arming packet
  -> WSTA75 packet inventory
  -> WSTA76 launch brief
  -> WSTA77 launch summary
  -> WSTA78 operator packet
  -> WSTA79 packet status
  -> WSTA80 execute-gate preflight
  -> stop, PUBLIC_OFF
```

The default mode is host-only and does not run WSTA58.  Optional live execution
exists only by passing the existing WSTA80/WSTA58 explicit live stack:

```text
--execute-wsta58-from-status
--allow-operator-live
--allow-native-reboot
--allow-public-live
--ack-credentialed-wifi
--ack-public-exposure
--force-ttl-expiry-proof
--force-manual-stop-proof
--native-confirm-token <private value>
--public-confirm-token <private value>
```

WSTA88 delegates optional live execution to WSTA80; it does not introduce a new
public-exposure mechanism.

## Source Changes

Added:

- `workspace/public/src/scripts/server-distro/run_wsta88_persistent_operator_workflow.py`
- `tests/test_server_distro_wsta88_persistent_operator_workflow.py`

The new runner:

- requires `--prepare-to-execute` before doing any work;
- keeps TTL bounded by the existing short-session maximum;
- requires credentialed Wi-Fi and public-exposure acknowledgements during
  preparation, but still performs no live action by default;
- creates a fresh private WSTA72 -> WSTA80 run tree in one command;
- writes `wsta88_operator_workflow.json` and a redacted markdown summary;
- preserves WSTA80's fail-closed live gate instead of bypassing it;
- passes `--allow-*`, proof flags, and token values to WSTA80 only when the
  operator supplied them to WSTA88;
- keeps public summaries redacted and placeholder-only.

## Safety

- Source-only change; no device command ran for WSTA88.
- No boot image was built or flashed.
- No native reboot, Wi-Fi association, DHCP, public tunnel, public smoke,
  userdata action, switch-root, or non-boot partition write ran.
- Default WSTA88 output is `PUBLIC_OFF` / host-only preflight.
- Optional live execution remains the already-proven WSTA80 -> WSTA58 path and
  remains explicitly gated.
- Public URL values, confirm-token values, raw wireless credentials, network
  identifiers, routable addresses, gateway/DNS values, lease IDs, and device
  serials are not committed here.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest \
  tests.test_server_distro_wsta72_persistent_prepare_to_arm \
  tests.test_server_distro_wsta73_persistent_arming_packet \
  tests.test_server_distro_wsta74_persistent_arming_status \
  tests.test_server_distro_wsta75_persistent_arming_inventory \
  tests.test_server_distro_wsta76_persistent_launch_brief \
  tests.test_server_distro_wsta77_persistent_launch_brief_summary \
  tests.test_server_distro_wsta78_persistent_operator_packet \
  tests.test_server_distro_wsta79_persistent_operator_packet_status \
  tests.test_server_distro_wsta80_persistent_operator_execute_gate \
  tests.test_server_distro_wsta88_persistent_operator_workflow -v
```

Result: `Ran 77 tests ... OK`.

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta72_persistent_prepare_to_arm.py \
  workspace/public/src/scripts/server-distro/run_wsta73_persistent_arming_packet.py \
  workspace/public/src/scripts/server-distro/run_wsta74_persistent_arming_status.py \
  workspace/public/src/scripts/server-distro/run_wsta75_persistent_arming_inventory.py \
  workspace/public/src/scripts/server-distro/run_wsta76_persistent_launch_brief.py \
  workspace/public/src/scripts/server-distro/run_wsta77_persistent_launch_brief_summary.py \
  workspace/public/src/scripts/server-distro/run_wsta78_persistent_operator_packet.py \
  workspace/public/src/scripts/server-distro/run_wsta79_persistent_operator_packet_status.py \
  workspace/public/src/scripts/server-distro/run_wsta80_persistent_operator_execute_gate.py \
  workspace/public/src/scripts/server-distro/run_wsta88_persistent_operator_workflow.py \
  tests/test_server_distro_wsta88_persistent_operator_workflow.py
```

Result: pass.

```text
git diff --check
```

Result: pass.

## Next

The WSTA persistent exposure path now has a one-command default-off operator
workflow around the live-proven WSTA80/WSTA58 path.  Next WSTA work should move
to containment/hardening or the next server-distro persistence rung, rather than
repeating the same live publish proof.
