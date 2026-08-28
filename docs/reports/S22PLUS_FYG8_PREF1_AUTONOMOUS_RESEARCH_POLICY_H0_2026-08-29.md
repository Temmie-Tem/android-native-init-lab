# S22+ FYG8 pre-F1 autonomous catalog H0 report

Date: 2026-08-29

Status: **DEFINED / NOT ACTIVE** (`DEFINED_NOT_ACTIVE`)

## Cause

The ordinary S22+ D1 rule requires fresh approval for every transient action.
That is disproportionate for a single-owner personal lab when the objective is
bounded pre-F1 research and the action surface is fixed. The policy change
addresses operator mistakes, stale or wrong target selection, accidental
parallel drift, duplicate or uncertain effects, and missing recovery. It does
not model a malicious same-UID actor replacing state between individual
syscalls; that defense is not added without a concrete incident.

The immediate trigger was D1 V2 ordinal `d1-fresh-baseline-2`. Its exact
approval produced a `773B/86dfc3ef` arm and `1989B/bc438727` typed stop, but no
ADB snapshot, raw directory, start, result, reboot, or device command. The
production P3.18 arm writer emitted indented JSON while the V2 validator
required compact canonical JSON. That host-only composition defect consumed
the approval before any device effect, showing that host preparation and
effect accounting must be separate.

## Change

The normative declaration is
`docs/operations/targets/S22PLUS_FYG8_PREF1_AUTONOMOUS_RESEARCH_POLICY_V1.md`.
It defines one fresh attended session activation and one finite monotonic
campaign for the exact S22+ FYG8 target. The four classes are bounded
raw-first D0 reads, normal Android reboot plus health, payload-free Download
enter/return after automatic-return proof using only descriptor-bound
`/usr/bin/odin4 --reboot -d <bound-endpoint>`, and one fixed privileged
sysfs/configfs USB-role or UDC transient with literal values and restore or
reboot proof.

Activation binds fresh exact target/topology and healthy boot. The declaration
also fixes positive finite budgets and makes durable effect
intent, immediately before the first device command, consume one ordinal. A
pre-intent host failure consumes none; any post-intent cut is uncertain and
never replayed. Exact healthy return precedes the next effect. Each ordinal has
one machine receipt and the campaign one summary. Existing target-selection,
raw-first, journal, and health helpers are reused by one future coordinator;
no per-action runner, manifest, or review ladder is introduced.

## Boundary

The policy remains `DEFINED_NOT_ACTIVE`. It creates no runner, coordinator,
activation manifest, approval token, device command, D0/D1/F1 authority, or
recovery authority. Mechanical activation still requires the exact coordinator,
versioned catalog, hostile tests, independent `PASS_GO`, activation manifest,
fresh attended session approval, exact healthy boot, immutable effect-core
identity, budgets, and expiry. Generic root/su, arbitrary paths or values,
persistent configuration/security changes, packages/shared storage/userdata,
module load/unload, runtime code, panic/crash injection, F1, and partition
payloads remain forbidden. F1 remains attended under Process-v2.

## Validation

This H0 unit uses no device, ADB, USB, Odin, network, root, or private live run.
The policy declaration parses as one JSON block; focused tests cover exact
target binding, inactive state, four-class closure, finite accounting, no
replay, forbidden surfaces, and contract delegation. Existing contract
semantics are preserved, with only the common attendance-list sentence extended
to name this target-specific lane. Policy/contract/taxonomy/S20+ interaction
tests pass `85/85`; the unchanged common Process-v2 modules pass `142/142`.
`AGENTS.md` and the S22+ target contract remain at 260 lines, `GOAL.md` remains
at 900, and Process-v2 remains byte-unchanged. Independent review remains
pending; full-tail review accounting is `62 total / 44 resolved / 18 open`.
