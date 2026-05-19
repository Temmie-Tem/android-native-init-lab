# Native Init v294 Android Property Runtime Feasibility

- date: `2026-05-19`
- scope: read-only Android property runtime feasibility inventory
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- plan: `docs/plans/NATIVE_INIT_V294_PROPERTY_RUNTIME_FEASIBILITY_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/wifi_property_runtime_feasibility.py`
- evidence:
  - plan mode: `tmp/wifi/v294-property-runtime-plan/`
  - first live mode: `tmp/wifi/v294-property-runtime-live-20260519-142138/`
  - corrected live mode: `tmp/wifi/v294-property-runtime-live-20260519-142338/`

## Result

- decision: `property-runtime-inputs-visible-runtime-absent`
- pass: `True`
- reason: mounted Android property input files are visible, but native property
  runtime paths are absent.

## Validation

Static validation passed:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_property_runtime_feasibility.py \
  scripts/revalidation/wifi_service_manager_prereq_model.py \
  scripts/revalidation/a90ctl.py
git diff --check
```

Plan mode passed:

```bash
python3 scripts/revalidation/wifi_property_runtime_feasibility.py \
  --out-dir tmp/wifi/v294-property-runtime-plan \
  plan
```

The first live run correctly found runtime absence but used overly narrow
static path candidates for property input files. The tool was corrected to use
the live `find` evidence as well as stat candidates, then the corrected live run
passed:

```bash
python3 scripts/revalidation/wifi_property_runtime_feasibility.py \
  --out-dir tmp/wifi/v294-property-runtime-live-20260519-142338 \
  run
```

## Checks

| Check | Status | Severity | Detail |
| --- | --- | --- | --- |
| v293 property blocker | expected | info | `v293_property_runtime=absent` |
| native version | present | info | `A90 Linux init 0.9.60 (v261)` |
| live property runtime | absent | blocker | `property_socket=False`, `properties_dir=False` |
| mounted property contexts | present | info | `stat_present=1/5`, `find_lines=2` |
| mounted build props | present | info | `stat_present=1/7`, `find_lines=3` |
| `/dev/socket` dir | absent | warning | `/dev/socket` absent |

## Interpretation

The native environment can see Android property input material through the
read-only mounted system tree, but it does not expose Android's live property
runtime:

- no `/dev/socket/property_service`;
- no `/dev/__properties__`;
- no `/dev/socket` directory.

Therefore service-manager execution remains blocked. The next step should be a
read-only property snapshot/shim model, not service-manager execution.

## Guardrails Kept

- no property service creation
- no `/dev/socket` or `/dev/__properties__` writes
- no property value mutation
- no service-manager execution
- no Binder ioctl or Binder devnode creation
- no Wi-Fi daemon execution
- no QMI/QRTR packet
- no Wi-Fi scan/connect/link-up/credential/DHCP/routing
- no Android partition write

## Next

- v295 should model a read-only property snapshot/shim.
- It should answer whether a minimal property view can be provided to Android
  binaries without running Android init's property service.
- Do not start service managers, HALs, `wificond`, supplicant, hostapd, or Wi-Fi
  link-up from v294 alone.
