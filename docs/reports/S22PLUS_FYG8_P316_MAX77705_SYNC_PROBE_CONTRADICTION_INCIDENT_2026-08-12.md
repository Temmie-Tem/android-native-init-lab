# S22+ FYG8 P3.16 Max77705 synchronous-probe contradiction

Status: **F1 CLOSED HEALTHY; H0 LOCALIZATION COMPLETE; SUCCESSOR NOT READY**

Date: 2026-08-12

Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q` /
`S906NKSS7FYG8`) only. A90 received zero commands.

## Decision

P3.16 did not measure the Max77705 `CONTROL1` MUX. Its single live attempt
ended in the predeclared fail-closed terminal `0x6708`, decoded as
`exact_parent_unbound_after_sync_return` /
`NO_PROOF_OBSERVER_DIAGNOSTIC_SYNC_CONTRADICTION`.

The retained record proves all of the following in one authoritative vector:

- the exact `maxim,max77705` client existed on the dynamically resolved
  `994000.i2c` adapter before diagnostic loading;
- it was unbound before loading;
- the diagnostic module's synchronous `finit_module()` returned success;
- after that return the same exact parent remained unbound;
- no diagnostic-owned parent and no diagnostic-created `0x25` dummy client
  existed; and
- the result parameter still returned `-EAGAIN`.

Therefore no PMIC identity read, `CONTROL1_R`, `CONTROL1_W(0x09)`, retention
interval, post read, physical-MUX inference, or connector-side causal claim is
permitted. P3.16 is consumed and must never be replayed.

The strongest host-only localization is a missing Max77705 pinctrl-supplier
closure. The exact board DT makes `max77705@66` a consumer of the PM8350C GPIO
provider, while P3.16 omits all five stock modules needed to instantiate and
bind that provider. This mechanism exactly predicts successful I2C-driver
registration followed by pre-probe deferral and an unbound client.

That localization is not promoted to a device-proven unique cause because the
consumed P3.16 record did not retain `waiting_for_supplier` or the unresolved
supplier identity. A successor must close that last attribution gap and be
freshly qualified; adding modules to the plan is not a continuation of this
attempt.

## Live closure

The exact Process-v2 run is private at:

`workspace/private/runs/device-action-f1-live-v2/p316-ready1-prepared-20260812-2`

Its durable facts are:

| Fact | Result |
|---|---|
| exact approval binding | `f5d964deef7cfc36c7b7e6464c04873da1f86fcdc5717058f8bdb66f348a8ad9` |
| candidate transfers | exactly 1 |
| rollback transfers | exactly 1 |
| canonical journal records | 19 |
| candidate observer | ACM endpoint timeout; not accepted |
| retained reads | 2 x 2,097,136 bytes, byte-identical |
| retained SHA-256 | `84d2f8eededdfbdfa16ed96e73ca26006f122b818d5501b74d4bb4d41b06ec71` |
| retained integrity | both Carrier-v2 slots valid; header and envelope CRC valid; no foreign record |
| active pair | generation 106 `0x0da3`, generation 107 terminal `0x6708` |
| runner verdict | `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` |
| outcome | `candidate_not_proven_rollback_verified` |
| terminal state | `CLOSED`, `recovery_required=false` |
| final health | rooted boot-completed FYG8 Android, boot animation stopped, Download absent, rollback and supporting-partition identities verified |

The canonical event order is complete:

```text
live_session_start
candidate_flash_start
candidate_flash_done
candidate_boot_ready
rollback_flash_start
rollback_flash_done
rollback_boot_ready
live_session_end
```

The operator saw a normal candidate boot without a boot loop. That observation
is corroborative only; the formal healthy terminal is the runner's final
health closure after exact rollback.

The live-result identities are:

```text
live-result.json              3c9e9074ba5cb92e8eccc05acbaab828662b576a0cd991cee6e14f7615da9d74
live-state.json               896f88f01ed9ed33c2d7f7a04f4336aa819a6973360a0ca9473639e1eb241c8a
transaction/journal-head.json 3dc4197c723d20b335ca7d52f152d8ef506aad3855550984b1215c2690518ba5
```

No candidate retry, second candidate transfer, non-boot payload, or A90 action
occurred. The recovery invocation resumed the existing durable transaction and
sent only the preapproved exact rollback.

## Exact retained vector

The Max77705 decoder reports:

```text
loader_state                              FINIT_MODULE_RETURNED_SUCCESS (2)
pre_exact_parent_present                  1
pre_exact_parent_driver_state             UNBOUND (1)
pre_matching_unbound_parent_count         1
pre_wrong_address_compatible_parent_count 0
post_exact_parent_driver_state            UNBOUND (1)
post_diagnostic_bound_parent_count        0
post_exact_adapter_muic_0x25_client_count 0
post_foreign_0x25_client_count            0
result                                    unavailable (-EAGAIN)
causal_result_allowed                     false
```

Every listed binding field is authoritative in this terminal. This is not the
earlier P3.13/P3.14 class in which a correct device path was rejected by a bad
count or unpopulated profile array. The P3.16 contract deliberately registered
this row because synchronous driver registration does not prove entry into the
driver's `probe()`.

## Source-localized mechanism

### 1. The exact parent has a mandatory PM8350C pinctrl supplier

The exact g0q revision-12 DT defines:

```text
max77705@66 {
    compatible = "maxim,max77705";
    pinctrl-names = "default";
    pinctrl-0 = <0x7b>;
    max77705,irq-gpio = <0x11 0x05 0x01>;
};
```

Phandle `0x7b` is `if_pmic_irq`, a state below the compatible provider
`qcom,pm8350c-gpio`; phandle `0x11` is that provider itself. The exact source is
`arch/arm64/boot/dts/samsung/rainbow/g0q/g0q_kor_singlex_w00_r12.dts:1476-1524`
and `:11624-11634` in the pinned FYG8 tree.

The fixed common kernel treats `pinctrl-0` and GPIO properties as supplier
bindings (`drivers/of/property.c:1261-1370`). `of_link_to_phandle()` walks from
the state node to its compatible owning ancestor before creating the firmware
link (`:1066-1137`). Driver core checks managed suppliers before pinctrl, DMA,
driver sysfs, or the driver's probe (`drivers/base/dd.c:517-543`). An unavailable
PM8350C GPIO provider can therefore produce exactly the observed state: the
diagnostic I2C driver registers successfully, but `s22plus_max77705_diag_probe()`
never publishes a result and the client remains unbound.

### 2. P3.16 omits the complete stock provider chain

The 64-entry early plan contains none of:

```text
qti-regmap-debugfs.ko
regmap-spmi.ko
qcom-spmi-pmic.ko
spmi-pmic-arb.ko
pinctrl-spmi-gpio.ko
```

The exact stock first-stage `modules.load` contains the latter three at lines
78-80 and the two regmap dependencies at lines 99-100. Exact `modules.dep`
states that `qcom-spmi-pmic.ko` requires both regmap modules; the other two have
no listed module dependency. `modules.alias` maps `qcom,pm8350c-gpio` to
`pinctrl_spmi_gpio`.

The omission is not a missing symbol edge from the diagnostic `.ko`; it is the
same modules.dep-plus-DT-supplier closure distinction documented on 2026-07-09.
P3.16 correctly closed the GENI controller's supplier graph but inherited the
Max77705 client's PMIC-pinctrl supplier as if it were already present.

### 3. Why this is not yet a unique live proof

The terminal does not identify which pre-probe boundary refused the client.
Supplier, pinctrl, DMA, and driver-sysfs setup all precede the diagnostic probe.
The exact DT plus complete five-module omission makes the PM8350C supplier the
dominant source-consistent explanation, but the consumed record lacks:

- the candidate value of `waiting_for_supplier`;
- the candidate `supplier:*` target for the `*-0066` client;
- the presence/binding state of the SPMI arbiter, PMIC parent, and PM8350C GPIO
  provider; and
- a probe-entry witness independent of the result parameter.

Those absences bound the conclusion. They do not justify replaying P3.16.

## Successor boundary

The next H0 unit may start from the fixed P3.16 Image, diagnostic module,
request-v3 envelope, host decoder, sidecar, rollback, and recovery machinery,
but it must treat the module plan and binding evidence as changed execution
closure.

At minimum it must:

1. derive the five-module SPMI/PMIC/GPIO closure from exact `modules.dep`, stock
   order, DT supplier edges, bytes, and linked imports rather than copying this
   list as an expectation;
2. account for the broader stock PMIC-provider binding effects as a changed
   hazard surface and obtain proportional independent review;
3. prove provider presence and binding before diagnostic registration;
4. retain `waiting_for_supplier` and the exact unresolved supplier identity on
   any post-registration unbound result;
5. keep the target-only GENI override fence and reject any competing Max77705
   owner or pre-existing `0x25` client;
6. rerun source-frozen A/B userspace/package qualification and the real
   Process-v2 adapter/persistence closure; and
7. obtain a new clean baseline, immutable binding, attendance, and exact F1
   approval. Nothing in this report grants live authority.

The change is expected to remain userspace/generic-ramdisk-only. It does not by
itself require Full-LTO or a kernel rebuild, but that expectation must be
reproved by the successor's static closure.

## Failed post-live D0 note

After F1 closure, one separate read-only supplier inventory was attempted. The
host could not select exactly one `SM-S906N`/`g0q` ADB endpoint, so the D0 ended
at target selection before sending a device command. It is not retried and
contributes no live supplier evidence. A90 commands remain zero.
