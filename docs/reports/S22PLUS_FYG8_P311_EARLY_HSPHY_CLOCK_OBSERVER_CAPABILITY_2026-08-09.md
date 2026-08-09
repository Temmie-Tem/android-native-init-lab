# S22+ FYG8 P3.11 Early HS-PHY Clock Observer Capability

Date: 2026-08-09

Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q` / `S906NKSS7FYG8`)

Verdict: `PASS_GO_EARLY_HSPHY_CLOCK_OBSERVER_CAPABILITY`

## Outcome

P3.11 is qualified as the next distinct boot-only observation candidate. It
keeps the fixed P3.10 Image and measures the previously discarded HS-PHY clock
return values without a system-wide clock probe or a new hazard class.

The canonical Process-v2 manifest is
`s22plus-fyg8-p311-process-v2-ready-1`. A fresh connected read-only preparation
bound the exact candidate, rollback, clean retained baseline, USB observer, and
execution closure. That preparation performed no reboot, write, Odin
invocation, partition transfer, or F1 action. The candidate remains unarmed.

## Capability

The observer registers one pending module-local trace instance before the
HS-PHY module load. The kernel module `COMING` notification arms the enabled
symbol-plus-offset probes before module initialization. Thirty trace events
cover six caller entry/return records and 24 exact post-call clock sites:

- six in `msm_hsphy_probe`;
- twelve in `msm_hsphy_init`; and
- six in `msm_hsphy_set_suspend`.

Because the clock helper is inlined into those callers, every return value is
attributed by construction to its exact module-local callsite. P3.11 therefore
does not use the rejected global `clk_prepare` or `clk_enable` design and does
not inherit its foreign-call, record-capacity, or hazard-class concerns.

## Validation

- Exact linked A/B callsite audit: `PASS_P311_24_EXACT_POST_BL_CALLSITES_HOST_ONLY`.
- Pending-module arm-before-init QEMU control: `PASS_P311_DELAYED_MODULE_KPROBE_QEMU_HOST_ONLY`.
- Tracefs descriptor and ABI audit: `PASS_P311_TRACEFS_ABI_AND_EARLY_DESCRIPTOR_HOST_ONLY`.
- Actual encoder outputs through all applicable gates: `PASS_P311_ACTUAL_ENCODER_OUTPUTS_SUBSET_ALL_GATES_HOST_ONLY`.
- Materialized runtime fixtures: `PASS_P311_MATERIALIZED_RUNTIME_FIXTURES_HOST_ONLY`.
- Independent artifact closure: `PASS_P311_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY`.
- Focused independent review of the final execution-critical closure: `PASS_GO`.

The final source closure contains 24 frozen `SOURCE_KEYS`. Candidate A/B
artifacts are byte-identical. The runner binds both the inherited P3.10 decoder
preimage and the exact P3.11 replacement, so the overlay cannot silently
substitute an unbound execution decoder.

## Authority State

P3.11 is ready only for the fresh exact legacy-runner approval and attended
S22+ F1 transaction. This capability record is not approval, does not replay
P3.08 or P3.10, and grants no authority to any other target. A90 was untouched.
