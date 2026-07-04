# WSTA49 Operator Runbook Source

- Date: 2026-07-04
- Scope: host-only appliance-level operator runbook
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta49-operator-runbook-source-pass`

## Summary

WSTA49 adds a committed operator runbook for the WSTA45 native-uplink D-public publish
path:

- `docs/operations/A90_WSTA_NATIVE_UPLINK_DPUBLIC_OPERATOR_RUNBOOK.md`

The runbook stitches together the proven surfaces:

- pre-run bridge/resident/selftest checks;
- WSTA45 host-only preflight;
- WSTA45 redacted publish-template printing;
- WSTA45 live publish command with explicit native-reboot, credentialed-Wi-Fi, public
  exposure, and confirm-token gates;
- WSTA48 redacted result aggregation;
- independent post-run `status`, `selftest`, and `wifi status`;
- stop conditions and non-goals.

All live command examples use `<native-confirm-token>` and `<public-confirm-token>`
placeholders.  The runbook explicitly keeps aggregate outputs under `workspace/private/`
unless only redacted counts/decisions are copied into a report.

## Safety

- No device command ran.
- No boot image was built or flashed.
- No native reboot, Wi-Fi association, DHCP, public tunnel, public smoke request, or
  external service action ran in this unit.
- The runbook does not authorize persistent public exposure.
- No raw public URL, confirm token, SSID, PSK, BSSID, IP, gateway, or DNS value is
  committed.

## Validation

Focused tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta49_operator_runbook \
  tests.test_server_distro_wsta48_redacted_result_aggregate
```

Result: `Ran 8 tests ... OK`

The runbook tests verify:

- required WSTA45 publish-template/live gate commands are present;
- WSTA48 aggregation is present;
- bridge and post-run health checks are present;
- stop conditions and non-goals are present;
- live values remain placeholder-only;
- actual confirm-token constants, public tunnel domain strings, and obvious Wi-Fi
  credential assignment strings are absent.

```text
git diff --check
```

Result: pass

## Next

The WSTA operator path now has a profile wrapper, redacted publish template, redacted
aggregate helper, and committed runbook.  The next meaningful step should be either
native/HUD/menu integration for this operator flow or a deliberately gated persistent
exposure design.  Do not continue with metadata-only WSTA cleanup.
