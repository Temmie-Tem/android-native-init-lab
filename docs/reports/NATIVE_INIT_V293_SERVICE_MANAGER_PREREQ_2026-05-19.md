# Native Init v293 Service-Manager Prerequisite Model

- date: `2026-05-19`
- scope: read-only Android service-manager prerequisite model
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- plan: `docs/plans/NATIVE_INIT_V293_SERVICE_MANAGER_PREREQ_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/wifi_service_manager_prereq_model.py`
- evidence:
  - plan mode: `tmp/wifi/v293-service-manager-prereq-plan/`
  - live mode: `tmp/wifi/v293-service-manager-prereq-live-20260519-141752/`

## Result

- decision: `service-manager-prereq-blockers-mapped`
- pass: `True`
- reason: service-manager execution remains blocked by missing service-manager
  process model and missing Android property runtime.

## Validation

Static validation passed:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_service_manager_prereq_model.py \
  scripts/revalidation/wifi_binder_open_smoke.py \
  scripts/revalidation/a90ctl.py
git diff --check
```

Plan mode passed:

```bash
python3 scripts/revalidation/wifi_service_manager_prereq_model.py \
  --out-dir tmp/wifi/v293-service-manager-prereq-plan \
  plan
```

Live read-only mode passed:

```bash
python3 scripts/revalidation/wifi_service_manager_prereq_model.py \
  --out-dir tmp/wifi/v293-service-manager-prereq-live-20260519-141752 \
  run
```

## Checks

| Check | Status | Severity | Detail |
| --- | --- | --- | --- |
| v292 Binder open | pass | info | `binder-open-only-smoke-pass` |
| v288 boundary | known-blocked | info | `hal-framework-boundary-native-blocked` |
| native version | present | info | `A90 Linux init 0.9.60 (v261)` |
| service-manager binaries | present | info | `present=2/3` |
| service-manager processes | absent | blocker | `process_count=0` |
| property runtime | absent | blocker | property socket/serialized property area absent |
| SELinux surface | present | warning | SELinux path visible, enforce file absent |
| linker runtime | partial | warning | `linker64=True`, linkerconfig not visible |
| runtime library roots | incomplete | warning | `apex=True`, `system_lib64=True`, `vendor_lib64=False` |
| VINTF Wi-Fi metadata | present | info | VINTF evidence remains input only |

## Interpretation

The Binder device layer is no longer the first blocker after v292. v293 shows
that service-manager execution still has unresolved prerequisites:

- no `servicemanager`/`hwservicemanager`/`vndservicemanager` process model;
- missing Android property runtime paths;
- partial linker/runtime namespace visibility;
- SELinux/domain assumptions are not modeled.

Starting a service manager now would mix multiple unknowns at once. The next
work should isolate the property-runtime blocker or produce a dry-run namespace
model, not execute service managers.

## Guardrails Kept

- no service-manager execution
- no Binder ioctl
- no Binder devnode creation
- no Wi-Fi daemon execution
- no QMI/QRTR packet
- no Wi-Fi scan/connect/link-up/credential/DHCP/routing
- no rfkill/ICNSS writes
- no Android partition write

## Next

- v294 should focus on Android property-runtime feasibility.
- Candidate v294 scope:
  - inventory `/dev/socket/property_service`, `/dev/__properties__`, and
    mounted Android property contexts;
  - determine whether a minimal read-only property view is possible;
  - do not create a property service or start service managers yet.
