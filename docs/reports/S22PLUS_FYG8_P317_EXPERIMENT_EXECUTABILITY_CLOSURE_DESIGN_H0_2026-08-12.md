# S22+ FYG8 P3.17 experiment-executability closure design

Status: **H0 DESIGN AND IMPLEMENTATION COMPLETE; EXACT TWO-BASE MUTUALLY
RECURSIVE FIXED POINT, RUNTIME WITNESSES, A/B PACKAGE, PROCESS-V2 PROMOTION,
AND CANONICAL OFFLINE BUNDLE PASS; FINAL INDEPENDENT READY-CLOSURE REVIEW
PENDING; NO LIVE AUTHORITY**

Date: 2026-08-12

Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q` /
`S906NKSS7FYG8`) only. This report grants no device authority and changes no
candidate, Image, module, rollback, or A90 state.

## Decision

P3.16 did not suffer an observer failure. Its retained observer correctly
proved that the exact Max77705 parent stayed unbound after synchronous
diagnostic-driver registration, so the MUX experiment never executed. Its
effective campaign class is `NO_PROOF_EXPERIMENT_PRECONDITION`.

That result separates two qualification questions that were previously
conflated:

1. **Can the observer express every admitted terminal?** The existing
   result-contract arming precondition answers this.
2. **Can the candidate satisfy the dependencies needed to execute the
   mechanism?** The new `EXPERIMENT_EXECUTABILITY_CLOSURE` answers this.

Three non-symbol dependency families are now registered. The first,
`FW_DEVLINK_DT_SUPPLIER_CLOSURE`, is derived from the fixed kernel's bounded
property-parser table and exact DT. The second,
`DEVICE_INSTANTIATION_CLOSURE`, covers the parent probe or bus registration
that must create a required device before a supplier graph can even start from
it. The third, `DRIVER_CONSUMED_DT_REFERENCE_CLOSURE`, covers a property that
the exact consumer driver parses and enforces directly even though the fixed
fw_devlink parser table does not recognize it. A `modules.dep` symbol closure
cannot prove any of these relationships.

The general gate is registered as the permanent common qualification boundary
for `UNMODELED_EXPERIMENT_DEPENDENCY_PRECONDITION`, not as a temporary P3.17
hold. Its scope is ordinary Process-v2 causal experiments. False admission or
false blocking, a new non-symbol dependency class, or a change to registered
kernel/firmware/boot/package authority triggers review; retirement requires a
reviewed common-contract replacement proving equivalent closure for every
supported candidate. The independent review of this report is the initial
boundary review.

The prior **INDEPENDENT REVIEW PASS** remains valid for the proof-class split,
the common gate, and the first exact fw_devlink regression. A follow-up review
now also approves the corrected three-root causal authority, all three mutually
recursive relation families, and the exact `+5` module delta. That review does
not qualify runtime witnesses, packaging, a candidate, or live authority.

## Scope and non-goals

This unit does:

- register the new proof class and append-only correction semantics;
- audit P3.10-P3.16 into four observer failures, one experiment-precondition
  failure, and two conclusive results;
- define the general executability gate and its first three relation families;
- implement a host-only exact-source extractor for the parser table and the
  first Max77705 regression case;
- register device instantiation and direct driver-consumed references,
  materialize a reviewable three-root claim-to-consumer authority, and derive
  the exact two-base static fixed point and predecessor module delta; and
- reject global fw_devlink relaxation as a remedy.

The follow-up implementation qualifies and packages the derived
69-early/70-effective module order without changing the fixed P3.10 Image or
the inherited diagnostic module. It builds a boot-only candidate and an
offline Process-v2 bundle, but does not run Full-LTO, read a device, authorize
F1, or satisfy the required final independent changed-closure review.

## Gate contract

### Must-bind consumers

Every experiment design must name the smallest consumer set whose successful
binding is necessary for its causal claim. Only this set forces provider
closure. The complete dependency graph may be inventoried, but a loaded yet
irrelevant DT node does not automatically expand the candidate.

For the Max77705 discriminator, the reviewed authority has three roots:

| Root | Expected driver | Why it must bind |
|---|---|---|
| `platform:9c0000.qcom,qupv3_0_geni_se` | `qupv3_geni_se` | the exact I2C probe consumes `qcom,wrapper-core` and `geni_se_resources_init()` returns `-EPROBE_DEFER` before adapter registration when wrapper driver data is absent |
| `platform:994000.i2c` | `i2c_geni` | its probe registers the adapter; adapter registration calls `of_i2c_register_devices()` and creates the exact DT child at `0x66` |
| exact `maxim,max77705` child at `0x66` beneath that adapter | `s22plus_max77705_mux_diag` | its synchronous probe is the sole producer of the bounded CONTROL1 result |

The exact merged FYG8 DT corrects an earlier source-fragment inference:
`9c0000` and `994000.i2c` are `/soc` siblings created by default OF platform
population. The wrapper's `of_platform_populate()` call therefore does not
create this I2C controller. The dependency is instead a direct driver-consumed
DT reference: the I2C probe parses `qcom,wrapper-core`, resolves the wrapper
platform device, and later requires bound wrapper driver data. Starting only
from the fw_devlink table would still make this dependency structurally
invisible, but attributing it to device instantiation would be equally wrong.
The GPI DMA device remains a derived fw_devlink supplier through the
controller's `dmas` property and is not seeded as a root. P3.17 must still
derive the complete transitive set; this report does not copy the five
post-live localized modules as an expected answer.

The claim authority turns the root judgment into nine explicit
claim-to-consumer counterfactuals. In particular, loss of the controller is no
longer described merely as lost attribution: no adapter is registered,
`of_i2c_register_devices()` does not create the `0x66` client, and the CONTROL1
transaction and both window samples do not occur. Machines enforce membership,
coverage, referential integrity, source seams, and hash drift. Human review,
not the presence of text, decides whether each causal sentence is true.

### Registered relation families

Each family has a source-owned extractor, source identity, count/set/hash
receipt, duplicate policy, and effective enforcement rule. An unknown family
or unresolved required edge blocks packaging.

The first family is:

```text
FW_DEVLINK_DT_SUPPLIER_CLOSURE
  authority = exact fixed drivers/of/property.c + drivers/base/core.c + DT
  consumer scope = experiment must-bind set
  module mapping = exact config + modules.alias + modules.dep + stock order
  live witness = provider presence/binding + consumer bind/probe state
```

The second family is:

```text
DEVICE_INSTANTIATION_CLOSURE
  authority = exact parent/bus driver source + exact DT parent/child/match
  first mechanisms = default OF platform population + SPMI enumeration +
                     parent OF child population + OF I2C child enumeration
  root rule = seed an instantiator only when the dependent device cannot exist
              before that instantiator binds
  live witness = instantiator bind + dependent presence + dependent bind/probe
```

The third family is:

```text
DRIVER_CONSUMED_DT_REFERENCE_CLOSURE
  authority = exact consumer probe/helper + exact DT property and target
  first relation = 994000.i2c qcom,wrapper-core -> QUPv3 wrapper
  failure edge = missing wrapper drvdata -> -EPROBE_DEFER before adapter add
  live witness = referenced device present/bound + consumer probe/bind state
```

The corrected exact FYG8 chain is:

```text
default OF platform population
  -> sibling platform devices 9c0000 wrapper and 994000.i2c
  -> i2c_geni probe parses qcom,wrapper-core
  -> bound wrapper drvdata required by geni_se_resources_init()
  -> i2c_add_adapter()
  -> of_i2c_register_devices()
  -> exact maxim,max77705 client at 0x66
```

The three families are mutually recursive, not root-only passes. With the
reviewed roots as `S[0]`, qualification computes:

```text
S[n+1] = S[n]
       union fw_devlink_suppliers(S[n])
       union device_instantiators(S[n])
       union driver_consumed_dt_dependencies(S[n])
```

Every node emitted by any family re-enters all three. Exact identities are
deduplicated, and the calculation stops only when neither a node nor a required
edge is added. The candidate DT/device-node universe is finite, so the least
fixed point terminates. Historical module-plan membership is checked as an
output; it cannot stand in for a missing relation.

The first supplier-side counterexample is the exact PM8350C GPIO provider.
`pm8350c.dtsi` places `qcom,pm8350c@2` beneath `spmi_bus`, with compatible
`qcom,spmi-pmic`, and places the `qcom,pm8350c-gpio` node beneath that PMIC.
The PMIC-arbiter probe calls `spmi_controller_add()`, the SPMI core enumerates
the PMIC firmware child, and the `qcom-spmi-pmic` probe calls
`devm_of_platform_populate()` to create the GPIO platform child. Thus the GPIO
node emitted by fw_devlink supplier closure must be fed into instantiation
closure; analyzing instantiation only for the three reviewed roots is
fail-open. The exact fixed-point receipt below resolves this dependency rather
than inheriting the 65-module predecessor as an assumption: five required SPMI
and PMIC modules are absent from that predecessor and produce the derived
`65 -> 70` effective-count change.

This registry remains open to future non-symbol relationship classes without
weakening or overloading the observer arming precondition.

### Claim evaluability without root inflation

Each claim carries a non-empty `evaluability_preconditions` field. Four named
preconditions currently cover a complete exact diagnostic result, complete
post1/post2 boundaries, device gadget-path readiness before diagnostic
dispatch, and a Process-v2 USB-sidecar arm receipt covering the candidate
window. The existing materialized runtime source orders UDC bind and the closed
direct fence before diagnostic dispatch; the live Process-v2 runner arms the
sidecar before requesting Download. Those source facts do not make a future
P3.17 run true by declaration: successor qualification must rebind the exact
sources and the live result/arm evidence must satisfy the named preconditions.

DWC3 and the sidecar therefore remain excluded from the dependency-root set
while their absence still makes the MUX-causal host-attach claim unevaluable.
The machine checks that every claim names known preconditions and that none is
orphaned. It deliberately does not machine-assert their causal truth.

### Reviewable must-bind authority receipt

Implementation:

`workspace/public/src/scripts/revalidation/s22plus_fyg8_p317_must_bind_claim_contract.py`

Focused regression:

`tests/test_s22plus_fyg8_p317_must_bind_claim_contract.py`

Private output:

`workspace/private/outputs/s22plus_fyg8_p317/must-bind-claim-contract-20260812-01.json`

```text
receipt size                15,712 bytes
receipt SHA-256             bbb066b0dc8a7492db407a22f9cb1417773ee049a69b232a2ebc02d234418263
claim-authority SHA-256     49859c0957a15ef25cdad98137c5f178eb790f4689ddeb74553971d1a9ce3070
claims / roots / edges      3 / 3 / 9
evaluability preconditions  4
verdict                     PASS_P317_MUST_BIND_FIXED_POINT_AUTHORITY_H0_REVIEWED
human causal review         SATISFIED_2026_08_12
candidate ready             false
```

The receipt pins the materialized P3.16 runtime, diagnostic, result contract,
and Process-v2 live runner plus the fixed QUPv3 wrapper driver, GENI I2C
driver, I2C adapter/OF cores, default OF platform population, Waipio QUPv3 DT,
SPMI PMIC-arbiter driver, SPMI core, SPMI PMIC MFD driver, and PM8350C DT
source. Source mutations that remove the direct wrapper reference, pre-adapter
defer, sibling topology, adapter child enumeration, either SPMI enumeration
stage, gadget-before-diagnostic ordering, or sidecar-before-candidate ordering
fail closed. A root-only or single-family fixed-point mutation also fails.
This is a reviewable input contract for transitive closure, not approval of the
causal sentences and not a candidate qualification.

### Exact mutually recursive fixed-point receipt

Implementation:

`workspace/public/src/scripts/revalidation/s22plus_fyg8_p317_executability_fixed_point.py`

Focused regression:

`tests/test_s22plus_fyg8_p317_executability_fixed_point.py`

Private output:

`workspace/private/outputs/s22plus_fyg8_p317/executability-fixed-point-20260812-01.json`

```text
receipt size                         496,664 bytes
receipt SHA-256                      67042a70a6e023a5ea3382d4fd179fd04b6f0c111ff9430d5e5a1b9410b2a657
applicable vendor bases              2
static fixed-point nodes             23
iterations to convergence            5
raw / deduplicated relation edges    170 / 53
predecessor early/effective          64 / 65
successor early/effective            69 / 70
effective count delta                65 -> 70
verdict                              PASS_P317_EXECUTABILITY_FIXED_POINT_H0_RUNTIME_PENDING
candidate ready                      false
```

The extractor applies the active revision-12 overlay independently to both
applicable pinned Waipio vendor base DTBs and requires byte-independent but
semantically identical closure and module results. Every frontier node is
offered to all three relation families. The working set therefore expands from
the three reviewed roots through the exact GCC, pinctrl, GPI, interconnect,
SMMU, PDC, RPMh, SPMI, PMIC, GPIO, GIC, PSCI, and early fixed-clock nodes. The
Max77705 `pinctrl-0` and `max77705,irq-gpio` reasons still deduplicate to one
PM8350C GPIO owner. Kernel-rejected relationships, including the GIC's
self-reference, are retained as rejected raw evidence rather than incorrectly
treated as created supplier links.

The exact module delta is:

```text
spmi-pmic-arb.ko
pinctrl-spmi-gpio.ko
qti-regmap-debugfs.ko
regmap-spmi.ko
qcom-spmi-pmic.ko
```

The five modules are dependency-ordered before the inherited
`msm-geni-se.ko`; all 64 predecessor modules remain an exact subsequence.
This is a derived result, not a copied localization list. `qcom-spmi-pmic.ko`
pulls the two regmap dependencies from exact `modules.dep`, while the SPMI
arbiter and GPIO modules arise from the recursive instantiation chain.

`69 early / 70 effective` describes two different load domains. The generic
early loop loads the 64 inherited stock modules plus the five derived provider
modules, for 69. The seventieth module is the inherited
`s22plus_max77705_mux_diag.ko`; it is deliberately absent from that loop and is
loaded exactly once through the dedicated synchronous late `finit_module()`
path only after all early modules, gadget-path readiness, and Process-v2
sidecar arming. Thus 70 is the effective complete candidate module count, not
the early-loop capacity.

The static receipt deliberately remains `CANDIDATE_NOT_READY`. Static DT cannot prove
the live `OF_POPULATED`/`FWNODE_FLAG_NOT_DEVICE` early-device gate, and source
defaults cannot substitute for a retained boot-specific `fw_devlink` mode and
strictness witness. The corrected claim authority and changed permanent
relation-family machinery are reviewed; the runtime and packaging authorities
remain unavailable.

## Exact parser authority

The fixed `of_supplier_bindings[]` initializer has exactly 28 non-sentinel
entries:

```text
parse_clocks                 parse_interconnects
parse_iommus                 parse_iommu_maps
parse_mboxes                 parse_io_channels
parse_interrupt_parent       parse_dmas
parse_power_domains          parse_hwlocks
parse_extcon                 parse_nvmem_cells
parse_phys                   parse_wakeup_parent
parse_pinctrl0               parse_pinctrl1
parse_pinctrl2               parse_pinctrl3
parse_pinctrl4               parse_pinctrl5
parse_pinctrl6               parse_pinctrl7
parse_pinctrl8               parse_gpio_compat
parse_interrupts             parse_regulators
parse_gpio                   parse_gpios
```

Only `parse_iommus`, `parse_iommu_maps`, and `parse_dmas` carry
`.optional = true`. That declaration alone does not make them non-blocking.
The actual consumer is:

```c
if (s->optional && !fw_devlink_is_strict())
        continue;
```

The fixed source defaults to `fw_devlink=on` and
`fw_devlink.strict=true`. With no boot-argument override, all 28 rows are
parsed. P3.17 qualification must reprove the effective mode and strict value
from every boot cmdline/bootconfig authority; source defaults alone are not a
candidate result.

A raw scan of every phandle is forbidden. The exact parser table recognizes a
bounded set of property forms and some arbitrary phandle-bearing properties do
not create fw_devlink edges.

## Kernel-equivalent edge derivation

For each must-bind consumer, the extractor records:

1. parser row, order, source identity, and optional bit;
2. effective mode and strict value plus boot-source authority;
3. property name and raw referenced phandle;
4. referenced DT node;
5. the first compatible owning ancestor selected by `of_link_to_phandle()`;
6. raw consumer/property edges;
7. consumer-to-owner edges after `fwnode_link_add()`-equivalent duplicate
   elimination; and
8. must-bind status, provider implementation, module/built-in identity, order,
   runtime witness, and final probe-blocking decision.

The effective equations are:

```text
parse_edge =
    fw_devlink != off
    && property matches exact of_supplier_bindings[]
    && (!optional || fw_devlink.strict)

blocks_probe =
    parse_edge
    && fw_devlink != permissive
    && unresolved supplier remains
```

The implementation must model the fixed source rather than trust these prose
equations alone.

## First regression: Max77705 pinctrl and IRQ GPIO

The host extractor parsed exact source instead of copying the post-live H0
answer. It found:

| Property | Raw phandle | Referenced node | Compatible owner |
|---|---:|---|---|
| `pinctrl-0` | `0x7b` | `if_pmic_irq` state | `qcom,pm8350c-gpio` at `pinctrl@8800` |
| `max77705,irq-gpio` | `0x11` | `pinctrl@8800` | the same `qcom,pm8350c-gpio` node |

`max77705,irq-gpio` matches the fixed `-gpio` suffix parser despite its vendor
prefix. The two properties are two raw reasons for one consumer-to-owner
relationship. `fwnode_link_add()` rejects a duplicate pair, so the exact result
is:

```text
raw property edges                         2
deduplicated consumer -> supplier edges    1
supplier compatible                        qcom,pm8350c-gpio
```

The regression mutates the IRQ GPIO phandle to a different compatible owner
and requires the audit to fail rather than silently preserve the one-edge
answer.

## Host-only extractor and receipt

Implementation:

`workspace/public/src/scripts/revalidation/s22plus_fyg8_p317_fw_devlink_contract.py`

Focused regression:

`tests/test_s22plus_fyg8_p317_fw_devlink_contract.py`

Private output:

`workspace/private/outputs/s22plus_fyg8_p317/fw-devlink-contract-20260812-01.json`

Receipt:

```text
size       14,680 bytes
SHA-256    88b8247e48a1945c8a5f31544336f942c32f9604787e0cd46de0ba5f70f17609
verdict    PASS_P317_FW_DEVLINK_DT_SUPPLIER_CLOSURE_CONTRACT_H0
```

Pinned source identities inside that receipt:

| Source | Size | SHA-256 |
|---|---:|---|
| tracked extractor | 33,188 | `6bc514ee8696226faa088b4f4222d79b02f3ed96ed5bd135679cc3e1e212ae16` |
| fixed `drivers/of/property.c` | 42,408 | `78ddae866197962692d77657817b35013b87929c0e2bc3d475665dfd3d5e8530` |
| fixed `drivers/base/core.c` | 129,453 | `dc6a5633c0d7dc05e4280af835b00e05cd9bb5c6d754d1befff9bd23da336e28` |
| fixed `drivers/of/base.c` | 61,960 | `119d007edc40b95a29129d967e172a955fc2c0903c892db6ed0e53d8f689f7e9` |
| exact g0q revision-12 DTS | 1,086,127 | `aff997ab764b7be8ff66d57b0633fa11c881a108f8fabea186cf5a4216844822` |

The receipt preserves all eight `off`/`permissive`/`on`/`rpm` by strict-false/
strict-true evaluations, source-binds the mode producer and exact property
parser helpers, and proves source-default semantics and the exact two-to-one
Max77705 statically eligible edge. Runtime `OF_POPULATED`/
`FWNODE_FLAG_NOT_DEVICE` early-device state is explicitly unavailable from
static DT and remains a future package/runtime witness rather than a claimed
final device-link count. The receipt deliberately says
`candidate_boot_arguments_must_reprove_effective_policy=true`; it is not yet a
P3.17 package receipt.

The first fw_devlink extractor and Process-v2 documentation suites pass 40/40.
The corrected must-bind and mutually recursive fixed-point suites add 34/34,
for 74/74 focused host tests in the current tree. Machine tests establish
coverage and source binding, not causal truth. The follow-up human review
approves the corrected causal authority, mutual recursion, direct-reference
family, and exact `+5` delta. The earlier independent review reproduced and
closed fail-open mutations for parser-table
substitution, unmodeled consumer properties, disabled consumer/supplier paths,
self/descendant suppliers, malformed GPIO arguments, mode/strict producers,
and receipt/source separation. It independently regenerated the exact private
receipt byte-for-byte. This review qualifies only the H0 design and first
regression; it does not qualify a P3.17 candidate or grant device authority.

## `waiting_for_supplier` evidence contract

The fixed sysfs attribute prints one boolean based on whether the consumer's
fwnode supplier list is empty. Its three admissible retained states are:

| Retained state | Meaning |
|---|---|
| attribute absent | this device/kernel path did not expose the authority |
| present, value `0` | no unresolved fwnode supplier at that sample |
| present, value `1` | one or more unresolved fwnode suppliers at that sample |

Absence is never decoded as zero. The file never names the supplier.
`supplier:*` links can identify realized device links, but may not represent an
uninstantiated fwnode supplier. P3.17 must therefore keep separate fields for:

- attribute presence and boolean value;
- existing `supplier:*` link targets;
- source-derived required supplier mask;
- provider device presence and driver binding;
- exact consumer binding; and
- an independent diagnostic probe-entry witness.

If the retained channel cannot encode those authorities without ambiguity,
P3.17 remains unimplemented rather than collapsing unknown into absent.

## Rejected remedies

The following are rejected before implementation:

- `fw_devlink=off`;
- `fw_devlink=permissive`;
- disabling strict dependency parsing to skip optional rows; and
- treating an absent `waiting_for_supplier` file as `0`.

The fw_devlink command-line changes are global. They allow unrelated consumers
to probe without declared suppliers, conceal rather than satisfy the missing
closure, change the fixed boot execution contract, and destroy the causal
authority of a successful MUX result. They are more invasive and less
informative than deriving the exact must-bind provider closure.

## Proof-class audit

The adjacent live cohort is fixed as:

```text
P3.10  NO_PROOF_OBSERVER
P3.11  NO_PROOF_OBSERVER
P3.12  REFUTED
P3.13  NO_PROOF_OBSERVER
P3.14  NO_PROOF_OBSERVER
P3.15  REFUTED
P3.16  NO_PROOF_EXPERIMENT_PRECONDITION
```

This is derived from the existing post-live cause rows, not from current
terminal spelling. The original append-only P3.16 F1 row remains unchanged; a
new H0 row carries the effective classification correction for metrics.

## Runtime, packaging, and Process-v2 closure

The successor implementation closes items 1-6 of the original boundary:

- the materialized runtime reads complete `/proc/cmdline`, rejects either
  `fw_devlink` override token, and retains the effective default mode/strict
  witness separately from `waiting_for_supplier`;
- three provider devices, provider binding, `of_node`, `supplier:*`, the
  three-state waiting attribute, exact consumer binding, and diagnostic probe
  entry are sampled with field-level authority masks;
- the actual materialized runtime and immediate callers execute under host
  fixtures, and the late-loader lifecycle preserves the bounded reap/error
  rules inherited from P3.16;
- native Envelope-v3 and the real Process-v2 adapter round-trip 105 unique
  rows: 84 observer site/error rows, 15 terminal rows, five MUX rows, and one
  overflow no-proof row;
- the generic early loop contains exactly 69 modules and the unchanged
  diagnostic remains one dedicated late-only module, for 70 effective;
- two userspace builds and two boot-only packages are byte-identical. Both use
  fixed Image SHA-256 `71f573eb77e67c82b9191bfe0926153f6c8dd5fefe3bba01f884c9beb0c4bae8`,
  candidate boot SHA-256
  `068aa5337acdbe4c2a0dcf80241b7aa543600fdfdfc84bb0e74111542b76d18d`,
  and candidate AP SHA-256
  `ac0db3172cdc4dc9fe7991bf034e872f0d377a3fb175e61ff8cba0eb136c9f22`;
- final qualification, independent static reconstruction, and Process-v2
  promotion pass with candidate-static `90ab95c9248ee6f3a5e506bc61ab7d973cf815de5e711d105aaa503c8b42628a`,
  run-manifest `857b6d0710a4b54ce2f2bc02b4110e8d6ea0c3570936011fee578cf382254c9b`,
  and static-check `fc28637f63aecd996fb37bb509c42acd55df8844130595efcb274d9ea87ce346`;
  and
- non-creating ready rehearsal and canonical creation both pass. The manifest
  is 2,777 bytes, SHA-256
  `47b5e3c61d5a262ac6f00481210ef85f695d7d3793f456be8cbf0de28d2843b6`,
  binds the exact rollback `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`,
  and records a 300-second candidate window under the 1,200-second guard.

The common Process-v2 limits remain fail-closed: the 5 MiB candidate-static
allowance applies only to the P3.17 overlay, while the P3.16 allowance remains
2 MiB; the 2 MiB execution-source allowance applies only to the named P3.17
overlay intent, while every other source retains the 1 MiB default.

## Remaining boundary

P3.17 is canonical **offline-bundle ready but not independently PASS_GO**.
Item 7 remains: independently review the changed runtime/schema/Process-v2
closure and reproduce the source-frozen artifacts before D0 preparation or a
fresh exact F1 approval. The ready manifest itself creates no device authority.
No P3.16 artifact or approval may be reused, and no device command, Full-LTO,
kernel rebuild, flash, or A90 action occurred in this H0 implementation.
