# V1184 Vndservice Gate Postmortem — Host-Only Analysis Plan

- **cycle**: V1184
- **date**: 2026-05-28
- **type**: host-only (no device contact)
- **decision**: v1184-gate-design-bug-classified
- **pass**: True
- **prior**: V1183 live FAIL (gate did not prevent per_proxy spawn race)

## Objective

Classify why V1183's vndservice gate failed to prevent the per_proxy/per_mgr race
identified in V1181 and design the corrected V1185 gate placement.

## Findings

### Bug 1 — Gate position (primary, design)

The vndservice gate polling loop in `a90_android_execns_probe.c` is positioned
**after** `composite_spawn_child(&children[PM_OBSERVER_PER_PROXY])` (line 28098).

Flow for `i == PM_OBSERVER_PER_PROXY` in the spawning loop:
1. `composite_spawn_child(&children[PM_OBSERVER_PER_PROXY])` → per_proxy **spawned** (line 28098)
2. `active_child_count++` + `start_order` logged (line 28106–28113)
3. `if (i == PM_OBSERVER_PER_PROXY && cfg->pm_observer_per_proxy_after_vndservice_provider)` →
   gate polling begins (line 28214) — per_proxy **already running**

Comment at line 28276 confirms the design intent was observation-only:
```c
/* continue to per_proxy spawn regardless of gate result (log-only gate) */
```

Evidence from V1183 tracefs (`pm-server-wchan-tracefs-observer.txt`):
- Line 618: `child.per_proxy.start_order=6`  ← per_proxy spawned
- Line 619: `per_proxy_vndservice_gate.begin=1`  ← gate starts **after** spawn
- Lines 354–359: per_proxy PID 3728 has `/dev/vndbinder` mapped at collector index=0

Per_proxy opens vndbinder and calls `pm_client_register("modem")` on per_mgr
during the gate's 5-second poll window — same V1181 race.

### Bug 2 — Infinite recursion in parse_tracefs_output_v1183 (secondary, script)

`patch_defaults()` patches `v1106.parse_tracefs_output = parse_tracefs_output_v1183`
(line 337). `parse_tracefs_output_v1183` calls `v1106.parse_tracefs_output(text)` at
line 113 — which is now itself → infinite recursion → Python RecursionError.

Result: manifest reported `gate_begin=False` / decision `v1183-vndservice-gate-not-activated`
even though the gate actually ran (evidence in raw tracefs output).

**Fix applied** (V1184): added `_ORIG_V1106_PARSE_TRACEFS_OUTPUT` at module level
(before `patch_defaults()`) following the V1179 pattern. `parse_tracefs_output_v1183`
now calls `_ORIG_V1106_PARSE_TRACEFS_OUTPUT(text)` instead of `v1106.parse_tracefs_output(text)`.

### Per_mgr death without vndbinder (V1180 and V1183 identical)

Both V1180 and V1183 show `per_mgr_vndbinder_count=-1` at **all** fd snapshot indices.
Per_mgr never opened `/dev/vndbinder` in either experiment.

| metric | V1180 | V1183 |
|---|---|---|
| `per_mgr_vndbinder_count` | -1 at all polls | -1 at all polls |
| `pm_client_register_entry.count` | 1 | 0 |
| `pm_client_register_ret.count` | 0 | 1 |
| `pm_server_register_entry.count` | 0 | 0 |
| per_mgr exit_code | 0 | 0 |

- V1180: pm_client_register call was **in-flight** when per_mgr died (entry=1, ret=0)
- V1183: per_mgr was **already dead** when pm_client_register returned (dead-object, ret=1, entry=0)

Per_proxy (not pm_proxy_helper) is the caller: per_proxy PID 3728 had `/dev/vndbinder`
mapped at collector index=0 (V1183 line 354–359); pm_proxy_helper vndbinder_count=0
throughout.

`preexec_context_suppressed_reason=pm-service-trigger-observer-ptrace-lite-output-budget`
means per_mgr's actual SELinux domain could not be confirmed from evidence. If the
helper running in `kernel` domain has no `allow kernel vendor_per_mgr:process transition`
rule, per_mgr also runs in `kernel` domain and may fail internal initialization that
requires `vendor_per_mgr` domain capabilities.

## V1185 Corrected Gate Design

Move the vndservice gate block **before** `composite_spawn_child(&children[i])` at
line 28098 in the spawning loop. The restructured flow for `i == PM_OBSERVER_PER_PROXY`:

1. If `cfg->pm_observer_per_proxy_after_vndservice_provider`:
   - Log `per_proxy_vndservice_gate.begin=1`
   - Poll vndservice list at 200ms intervals (5s timeout)
   - If gate opens (per_mgr registered): proceed to spawn per_proxy
   - If gate times out: log `result=timeout`, skip spawn (`continue`), proceed to CNSS
2. `composite_spawn_child(&children[PM_OBSERVER_PER_PROXY])` — only reached if gate opened

Remove or guard the existing gate block at lines 28213–28276 to avoid duplicate execution.

Requires helper v221 (new build, new SHA, updated marker).

## Open Question for V1185

Will per_mgr register with vndservicemanager if per_proxy is not spawned until the
gate opens?

- If per_mgr survives ~1000ms without the early pm_client_register race and registers
  → gate opens → per_proxy spawns safely → V1181 race resolved
- If per_mgr still dies without per_proxy (SELinux domain issue) → gate times out →
  per_mgr's running domain needs capture before the next live attempt

V1185 live output will distinguish these two cases.

## Action Items

1. [DONE] Fix parse bug in `scripts/revalidation/native_wifi_pm_per_proxy_vndservice_gate_v1183.py`
2. [NEXT] V1185: helper v221 source/build-only — move gate before `composite_spawn_child(per_proxy)`
3. [NEXT] V1185: helper v221 deploy + live gate test
