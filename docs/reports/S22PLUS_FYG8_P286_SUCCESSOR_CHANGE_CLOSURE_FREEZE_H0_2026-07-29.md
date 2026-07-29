# S22+ FYG8 P2.86 successor change-closure freeze H0

Date: 2026-07-29 KST

## Verdict

`PASS_P286_PRE_INTENT_CHANGE_CLOSURE_FROZEN_HOST_ONLY`

P2.86 inherits all 60 P2.84 SOURCE_KEYS byte-for-byte. Ten new files that can
affect `boot.img` bytes join the source preimage, producing 70 planned
SOURCE_KEYS. Ten verifier/evidence files that cannot affect those bytes stay
outside SOURCE_KEYS and must instead be bound by the final approval
`bundle.sha256`.

The freeze gate is fail-closed against undeclared tracked changes. It derives
the actual set from committed changes since the reviewed base plus current
tracked/untracked worktree state, then requires exact bidirectional equality
with the declaration frozen in the gate. The old caller-supplied mutation
arguments are removed, so an empty or incomplete CLI declaration cannot hide
a changed file.

This is still not pre-intent readiness. Ten payload sources and eight support
files do not yet exist, so no P2.86 intent or Full-LTO build may begin.
This H0 unit performs no build, package creation, device contact, D0, D1, F1,
reboot, transfer, or partition action and grants no live authority.

## Stage A decision

This unit implements the P2.64 Stage A documentation and change-window gate:

- separate payload identity from non-identity verification/evidence;
- derive tracked mutations from Git instead of trusting caller-supplied path
  lists;
- reject both missing declarations and overdeclarations; and
- keep P2.84 receipts immutable.

P2.64 Stage C, including the wider execution-identity split and independent
execution-critical review, is deferred until after P2.86. It is not a
prerequisite for this successor.

## PM-order correction

P2.84 `0xc18` proves the child-suspend pair used `stop_pid` and was nested
strictly between the actual `dwc3_otg_start_peripheral(..., 0)` entry and
return counters. Stock and bare PID1 therefore selected different runtime-PM
paths because their reference and child-count state differed.

Waiting for exact parent `runtime_status=suspended` remains necessary: PM core
publishes that state after the parent callback returns, so it proves
`dwc3_msm_suspend()` returned and released `suspend_resume_mutex`. It is not an
outer-work completion fence. The enclosing `dwc3_otg_sm_work` can still have
requeue bookkeeping and its return tail after parent state publication.

Accordingly the successor combines the parent-status gate with actual outer
entry/return probes and a closed PERIPHERAL-helper deadline. Parent suspended
removes the callback/mutex portion of the overlap; bounded helper
classification handles the residual tail.

## Frozen candidate requirements

The seven requirements are:

1. wait for exact parent `runtime_status=suspended` on the existing stop
   deadline after child suspended and before PERIPHERAL;
2. replace blocking post-kill `wait4` with publish-before-reap, `WNOHANG`, an
   auxiliary reap deadline, and explicit unreaped-child classification;
3. add `outer_sm_work_in/out` probes attached to actual
   `dwc3_otg_sm_work`;
4. distinguish helper dispatch from helper completion;
5. distinguish flush timeout, completed mode write, start-peripheral entry
   without return, and later role/readback failure;
6. retain a bounded classified PERIPHERAL write for the residual
   requeue-and-return tail after parent suspended; and
7. bind payload-determining inputs in the source preimage and bind
   non-identity verifier/evidence support in `bundle.sha256`.

No existing P2.84 direct path is a permitted mutation target.

## Payload source preimage

The identity partition is:

```text
inherited P2.84 SOURCE_KEYS       60
  inherited direct paths         55
  inherited generated inputs      5
new payload SOURCE_KEYS           10
planned P2.86 SOURCE_KEYS total   70
```

The ten new payload paths are:

```text
workspace/public/src/native-init/s22plus_fyg8_p286_classifier.inc.c
workspace/public/src/native-init/s22plus_fyg8_p286_e3_runtime.inc.c
workspace/public/src/scripts/revalidation/build_s22plus_fyg8_p286_candidate.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_boot_only_packager.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_build.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_candidate_intent.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_contract_spec.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_source_contract.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_trace_contract.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_userspace_build.py
```

These are the only P2.86 additions whose receipts may enter the candidate run
ID preimage.

## Bundle-bound non-identity support

These ten files cannot alter `boot.img` bytes and must not enter SOURCE_KEYS:

```text
docs/reports/S22PLUS_FYG8_P286_SUCCESSOR_CHANGE_CLOSURE_FREEZE_H0_2026-07-29.md
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_build_repro_check.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_candidate_contract.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_candidate_static_checker.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_change_freeze.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_e1_decoder.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_e2_stock_closure.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_linked_audit.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_pre_lto_qualification.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_source_contracts.py
```

The selector is deliberately non-identity. A later P2.88 registration must be
able to edit it without changing P2.86's historical run ID or invalidating
P2.86 evidence receipts. The candidate preimage records `source_contract_id`
explicitly, while `p286_source_contract` and `p286_contract_spec` remain
payload-bound and catch a redirected contract implementation.

This follows the P2.82 retirement-guard precedent: a guard or verifier may
remain outside the source preimage while its exact final bytes are still
approval-bound. Fixing one of these files after intent does not invalidate an
otherwise byte-identical A/B pair, but every affected validation must be rerun
and final support bytes must be rebound before approval.

## Git-derived change window

The reviewed base is pinned in the validator with no CLI override:

```text
7929e9f7d7fea1eb99ab43dcd841c5a9c3b6ef94
```

The validator takes the union of:

```text
git diff --name-only -z <base>..HEAD --
git status --porcelain=v1 -z --untracked-files=all
```

It parses rename/copy records without dropping either path. The derived set
must equal the declared set exactly. It then rejects any derived path outside
the frozen payload, support, or Stage A governance sets.

The current Stage A declaration contains exactly:

```text
AGENTS.md
GOAL.md
docs/reports/S22PLUS_FYG8_P284_STOCK_TRACE_PM_ORDER_CORRECTION_H0_2026-07-29.md
docs/reports/S22PLUS_FYG8_P286_SUCCESSOR_CHANGE_CLOSURE_FREEZE_H0_2026-07-29.md
tests/test_s22plus_fyg8_p286_change_freeze.py
workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_change_freeze.py
```

The default command performs the Git derivation; no empty declaration path
exists:

```bash
PYTHONPATH=workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_change_freeze.py
```

## Frozen private D1 runner

The D1 repair list remains separate from candidate identity:

1. parse trace-instance spelling without requiring the absent group prefix;
2. terminate and reap watchdogs immediately on disarm;
3. write `/proc/self/comm` without embedding a newline; and
4. remove the endpoint-count predicate absent from the approved contract.

Only these private paths may implement the repairs:

```text
workspace/private/outputs/s22plus_fyg8_p284_stock_outer_d1_v3/device_runner.sh
workspace/private/outputs/s22plus_fyg8_p284_stock_outer_d1_v3/host_runner.sh
workspace/private/outputs/s22plus_fyg8_p284_stock_outer_d1_v3/control_analyzer.py
workspace/private/outputs/s22plus_fyg8_p284_stock_outer_d1_v3/runner_manifest.json
```

They are deliberately outside the tracked Git set. Their final runner
manifest and approval bundle must bind their bytes. All payload-source paths
and the public P2.84 D1 spec remain forbidden repair targets. This separation
does not authorize another D1.

## Intent and build stop gate

Intent derivation and Full-LTO are forbidden until all of the following hold:

- all 10 payload sources and all ten bundle-bound support files exist;
- the freeze validator reports `pre_intent_ready: true`;
- the successor source contract reports exactly 70 SOURCE_KEYS;
- current P2.84 receipts still match its frozen intent `60/60`;
- Git-derived and declared tracked change sets match exactly;
- focused semantic/fault-injection tests cover all seven requirements;
- the four D1 repair paths remain private with overlap count zero; and
- `git status --short` is clean at intent derivation.

After intent, the 70 source receipts are immutable. Any payload-source byte
change invalidates the A/B pair. Support-file correction does not change
candidate identity, but it remains blocked from approval until validation and
bundle binding are refreshed.

## Static validation

At publication:

- the P2.84 partition is `55 direct + 5 generated = 60`;
- the P2.86 identity plan is `60 inherited + 10 payload = 70`;
- ten non-identity support paths are disjoint from SOURCE_KEYS;
- candidate and private-D1 ancestor/equality overlap count is zero;
- pre-intent readiness is false with `10 + 8 = 18` files missing;
- the Git derivation test covers committed, dirty, and untracked changes;
- bidirectional tests reject omission, overdeclaration, and an unfrozen path;
- rename parsing retains both source and destination; and
- current P2.84 receipts, focused tests, Python compilation, line limits, and
  `git diff --check` pass.

## Post-intent HSPHY source-comparison addendum

This addendum is non-identity H0 analysis. It does not change the selected
P2.86 contract, any of its 70 `SOURCE_KEYS`, or the already-derived intent.
The report remains bundle-bound support. P2.86 stays selected; P2.88 is only a
conditional paper design below and has not been implemented.

### Source provenance and fixed FYG8 correspondence

The reconstructed FYG8 source file
`kernel_platform/msm-kernel/drivers/usb/phy/phy-msm-snps-hs.c` is 50,240 bytes
and has SHA256
`7823f9efd310b350169d84ba824e715b31ef3065e6a280ffc502dac6985124eb`.
Extracting the same member directly from
`SM-S906N_15_base_osrc/Kernel.tar.gz` produces that exact hash. The FYG8 delta
archive contains zero members ending in
`drivers/usb/phy/phy-msm-snps-hs.c`; therefore the fixed reconstruction uses
the byte-identical base-source implementation for this driver.

The shipped FYG8 `phy-msm-snps-hs.ko` independently retains real local symbols
at `msm_hsphy_enable_power=0xd80`, `msm_hsphy_init=0x11f4`, and
`msm_hsphy_set_suspend=0x19d4`. These addresses and the offsets below describe
that exact stock module, not a source-name assumption.

### Cold-init comparison and SIDDQ dependency

The independent Qualcomm femto-v2 cold-init implementation performs the same
essential sequence as vendor `msm_hsphy_init`: enable supplies, enable clocks,
assert/deassert `phy_reset`, program the UTMI/HS-PHY registers, release POR,
and release the override. Its explicit write clearing `SIDDQ` in
`HS_PHY_CTRL_COMMON0` is absent from the vendor implementation; the vendor
file does not define `SIDDQ`.

The vendor sequence instead depends on `msm_hsphy_reset()` asserting the PHY
reset for 100 microseconds and then deasserting it before the register writes.
This is a recorded reset/default-state dependency, not evidence that the
vendor sequence is defective. Comparison references are the U-Boot Qualcomm
USB support series and the upstream
[`phy-qcom-snps-femto-v2.c`](https://android.googlesource.com/kernel/common/+/4c75bf7e4a0e5472bd8f0bf0a4a418ac717a9b70/drivers/phy/qualcomm/phy-qcom-snps-femto-v2.c).

### Suspend/resume asymmetry and P2.86 relevance

Vendor `msm_hsphy_set_suspend(..., 1)` has two materially different paths:

- with a connected cable or host mode, it disables clocks only;
- on cable disconnect, subject to the DPDM and EUD guards, it disables clocks
  and calls `msm_hsphy_enable_power(..., false)`.

`msm_hsphy_set_suspend(..., 0)` only enables clocks and clears the software
`suspended` flag. It neither restores power nor calls `msm_hsphy_init`.
Consequently the relevant PHY reinitialization comes from
`dwc3_core_init -> usb_phy_init -> msm_hsphy_init`, not from the PHY driver's
resume half of `set_suspend`.

This source fact raises confidence in the already-selected P2.80 through P2.86
strategy: a completed deep suspend followed by the DWC3 core restart is the
driver-supported route that can re-run PHY initialization. It does not change
P2.86's success criteria and does not prove that a physical rail changed.

### Idempotent guard and the optional deep-off boundary

`msm_hsphy_enable_power()` first returns zero when
`phy->power_enabled == on`. Therefore an entry/return pair alone cannot
distinguish the idempotent guard from execution of the regulator-disable
sequence.

In the exact FYG8 module, the comparison is at function offset `+0x58`, its
equal branch reaches the guard return, and the subsequent `tbz` selects the
`!on` path at `msm_hsphy_enable_power+0x14c`. The `+0x14c` instruction is
four-byte aligned, follows the idempotent guard, and precedes the regulator
disable chain. A probe there would prove entry into the driver's real
disable sequence.

That probe would still not prove electrical rail collapse. The vendor source
explicitly documents targets where the 3.3 V EUD supply is shared with eMMC
and remains on after this driver removes its vote. Other consumers can
similarly keep a regulator enabled. The software boundary is therefore
diagnostic insurance only.

### Conditional P2.88 paper design

P2.88 is not selected and no source, contract, probe table, decoder, or
packager implementation is authorized by this section. Preserve the following
design only for the specific trigger `0x90 passed and 0x91 failed
ambiguously`:

1. confirm the exact FYG8 `msm_hsphy_enable_power` symbol and disassembly
   receipt again;
2. retain the existing function entry/return observation;
3. add one instruction-aligned attachment at the exact `+0x14c` deep-off
   boundary and require the attachment-name positive/negative controls;
4. classify guard-return separately from disable-sequence entry and return;
5. state explicitly that neither class proves electrical rail collapse.

The decision rule is:

- a failure before or at `0x90` does not activate this design;
- `0x90` success plus an ambiguous `0x91` failure may activate a fresh P2.88
  design/review/intent cycle;
- a complete P2.86 pass retires the need for this probe.

The diagnostic branch is estimated to matter only in the latter ambiguous
case. It does not improve P2.86's chance of crossing the current `0x90`
boundary, so reopening the reviewed identity closure before that evidence
would add contract risk without changing the selected behavior.

## Regulator D0 no-proof and runtime-predicate design

### Connected read-only result

An attended D0 contacted one boot-complete FYG8 `g0q`. Operator-enabled
Android wireless debugging produced an authorized TCP ADB transport; its
device serial, product, and boot-complete values matched the existing USB
transport. No endpoint or raw device identifier is recorded in tracked
evidence.

The HSPHY consumer links resolved:

| Supply | Runtime class | RPMh provider |
| --- | --- | --- |
| `vdda33` | `regulator.27` | `ldob2` |
| `vdd` | `regulator.29` | `ldob5` |
| `vdda18` | `regulator.39` | `ldoc1` |

No `88e3000.hsphy-refgen` consumer link exists. This matches the source's
optional `refgen` handling and is recorded as target configuration, not a
defect.

Each mapped class device contains `state`, `num_users`, `microvolts`,
`requested_microamps`, and `opmode`, but both Android `shell` and Magisk UID 0
received `EACCES` when reading them. The files are mode `0444`, Android is
enforcing, the Magisk process is in `u:r:magisk:s0`, and no relevant AVC was
visible; a dontaudit rule may suppress it. Exact FYG8
`regulator_state_show()` and `num_users_show()` contain no capability check,
so this is an Android MAC boundary rather than absence of the attributes.

Debugfs is not mounted and there is no existing read-only regulator summary
mirror. Tracefs contains regulator tracepoint definitions but no historical
state; enabling them would be a write. The physical cable was therefore not
disconnected: the post-disconnect predicates would remain unreadable, so the
second half could not add evidence.

The structured private verdict is
`NO_PROOF_P286_REGULATOR_SYSFS_READ_DENIED_D0`. No device setting, mount,
SELinux rule, trace enable, reboot, or payload action was performed by the
agent.

### Exact DT and environment-transfer limits

The exact Waipio USB DT assigns `vdd=pm8350_l5`, `vdda18=pm8350c_l1`, and
`vdda33=pm8350_l2`. Those regulator definitions contain neither
`regulator-always-on` nor `regulator-boot-on`; an off request is therefore not
excluded by their static constraints.

The stock `vdda33` provider also exposes a DP consumer, while `vdd` exposes
UFS, PCIe, camera, display, and other consumers. Their live stock votes are
not a transferable invariant for bare PID1: the fixed P2.86 60-module plan
does not load those stock consumer driver sets. Thus a stock disconnected
`disabled/use_count=0` result would be useful positive evidence, but a stock
`enabled/use_count>0` result would not by itself prove that bare PID1 retains
the same vote.

Likewise, a retained rail would disprove a literal full-power-cycle claim but
would not invalidate the whole restart strategy. The selected mechanism also
re-enters `dwc3_core_init -> usb_phy_init -> msm_hsphy_init`, including the
PHY reset and register-init sequence.

### Bare-PID1 predicate feasibility

The candidate does not load Android SELinux policy. Its already-proven
tracefs kprobe registration and SSUSB sysfs access are consistent with this
environment distinction. It can therefore use the existing freestanding
`getdents64`, `readlinkat`, and newline-normalizing `p260_read_value`
primitives to observe regulator sysfs without an Android policy workaround.

A correct resolver must not freeze `regulator.N`. It must:

1. enumerate `/sys/class/regulator/regulator.*`;
2. require exactly one directory containing the exact consumer-link basename
   `88e3000.hsphy-vdda33`;
3. verify that link resolves to the exact HSPHY platform device;
4. construct `state` and `num_users` paths under that class device;
5. parse exactly `disabled`, `enabled`, or `unknown` plus a bounded decimal
   `num_users`; and
6. classify zero matches, multiple matches, malformed values, and read errors
   separately.

One stock reboot is not needed to make this resolver safe and would not prove
bare enumeration stability. Dynamic exact-link resolution removes that
assumption directly.

`state` is still a software/provider fact. Exact RPMh
`rpmh_regulator_is_enabled()` returns the cached aggregate enable request.
The debugfs summary similarly reports framework counts and
`regulator_get_voltage_rdev()` output; that voltage is provider-reported, not
an ADC measurement.

The three rails must not share one pass predicate. Their consumer profiles
differ:

- `vdda33/ldob2` has the HSPHY and a stock DP consumer;
- `vdda18/ldoc1` has no other enumerated stock consumer; and
- `vdd/ldob5` has UFS, PCIe, camera, display, and other stock consumers.

Bare PID1 removes many stock consumers, but storage-related activity can still
make `vdd` remain enabled after the HSPHY correctly removes its own vote.
Therefore `vdd=disabled` must never be a success requirement. A complete-off
observation is most informative for the narrower `vdda33` and `vdda18`
providers, and even those values must remain rail-specific facts rather than a
single all-rails invariant.

`num_users` is also aggregate `rdev->use_count`. It cannot identify whether
the HSPHY's individual regulator handle decremented its own `enable_count`
when another consumer remains. Per-consumer `enable_count` is present only in
the debugfs `regulator_summary`, not in the regulator class sysfs attributes.
The exact sysfs proof boundary is consequently:

- `state=disabled` (especially for `vdda33` or `vdda18`) strongly proves that
  the provider/framework considers the entire rail off; but
- `state=enabled` or nonzero `num_users` cannot prove that the HSPHY failed to
  remove its own vote.

No refined checkpoint may label the second case as a failed HSPHY disable.

### Checkpoint and identity consequence

Adding a third progress write would damage two-slot retention. The useful
placement is to refine the existing suspended-stage `0x8f` classification:

- exact resolver/read failure;
- rail-specific provider `unknown`;
- rail-specific provider `enabled`, with aggregate `num_users`;
- `vdda33` or `vdda18` provider `disabled`; or
- `vdd` provider state as non-gating telemetry.

That preserves the load-bearing pair: refined `0x8f` followed by the existing
`0x90/restart-trace-cleanup-pending` marker if cleanup blocks. On later
restart failures, the regulator class must be folded into the restart
classification rather than relying on a third retained slot.

This is feasible, but it changes the runtime include, classifier, detail ABI,
contract, tests, and generated payload. The P2.86 intent has already fixed all
70 `SOURCE_KEYS`; implementing this design in P2.86 would invalidate its
identity and require a new intent plus a new Full-LTO A/B pair. It is therefore
paper design only under the current P2.86 decision.

### Exact `+0x14c` control-flow position

The shipped FYG8 module places the proposed boundary before the refgen choice,
not inside only one disable leg:

```text
+0x058  cmp   power_enabled, on
+0x05c  b.eq  idempotent-return
+0x060  tbz   on, #0, +0x14c
+0x14c  ldr   refgen
+0x150  cbz   refgen, +0x180
+0x154  bl    regulator_disable(refgen)
...
+0x180  bl    regulator_disable(vdda33)
```

Thus `+0x14c` is the first instruction after the `!on` selection and fires
for both refgen-present and refgen-absent executions. On this target the live
consumer mapping and exact DT show no refgen; the `cbz` therefore takes the
`+0x180` `disable_vdda33` leg. The offset remains a disable-sequence-entry
fact, not an electrical or per-consumer-vote proof.

`magiskpolicy --live` is not an available D1 workaround under the active risk
tier: even when RAM-only it changes SELinux security state, which ordinary D1
explicitly forbids. A separately approved plain debugfs
mount/read/unmount could be designed as transient D1, but no forced
`context=` relabel is selected. If the ordinary mount remains unreadable, that
D1 must end no-proof rather than modify MAC policy.
