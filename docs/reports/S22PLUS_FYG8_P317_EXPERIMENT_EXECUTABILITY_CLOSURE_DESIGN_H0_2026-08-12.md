# S22+ FYG8 P3.17 experiment-executability closure design

Status: **H0 DESIGN AND FIRST FW_DEVLINK REGRESSION IMPLEMENTED; INDEPENDENT
REVIEW PASS; P3.17 CANDIDATE NOT READY**

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

The first registered non-symbol dependency family is
`FW_DEVLINK_DT_SUPPLIER_CLOSURE`. A `modules.dep` symbol closure cannot prove
it. The exact fixed kernel derives these dependencies from a bounded property
parser table and the exact DT, then blocks probing while required fwnode
suppliers remain unresolved.

The general gate is registered as the permanent common qualification boundary
for `UNMODELED_EXPERIMENT_DEPENDENCY_PRECONDITION`, not as a temporary P3.17
hold. Its scope is ordinary Process-v2 causal experiments. False admission or
false blocking, a new non-symbol dependency class, or a change to registered
kernel/firmware/boot/package authority triggers review; retirement requires a
reviewed common-contract replacement proving equivalent closure for every
supported candidate. The independent review of this report is the initial
boundary review.

## Scope and non-goals

This unit does:

- register the new proof class and append-only correction semantics;
- audit P3.10-P3.16 into four observer failures, one experiment-precondition
  failure, and two conclusive results;
- define the general executability gate and its first relation family;
- implement a host-only exact-source extractor for the parser table and the
  first Max77705 regression case; and
- reject global fw_devlink relaxation as a remedy.

It does not derive or package the final P3.17 module plan, change the P3.16
diagnostic module, build a candidate, run Full-LTO, read a device, or authorize
F1.

## Gate contract

### Must-bind consumers

Every experiment design must name the smallest consumer set whose successful
binding is necessary for its causal claim. Only this set forces provider
closure. The complete dependency graph may be inventoried, but a loaded yet
irrelevant DT node does not automatically expand the candidate.

For the Max77705 discriminator, the minimum set begins with the dynamically
resolved `994000.i2c` transport chain and the exact `maxim,max77705` client at
address `0x66`. P3.17 must derive the complete transitive set; this report does
not copy the five post-live localized modules as an expected answer.

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

This is intentionally open to future non-symbol relationship classes without
weakening or overloading the observer arming precondition.

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

The focused extractor and Process-v2 documentation suites pass 40/40. The
independent review reproduced and closed fail-open mutations for parser-table
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

## Successor boundary

P3.17 remains H0 and not ready. Before any candidate qualification it must:

1. derive the complete must-bind consumer set;
2. reprove effective fw_devlink mode/strict from candidate boot authorities;
3. run the 28-row parser over every must-bind consumer and its transitive
   compatible owners;
4. map each effective owner to exact built-in/module bytes and source-derived
   order without using the five-module H0 localization as an expected answer;
5. account for the broader binding effects of every added provider;
6. define a non-ambiguous retained supplier/bind/probe-entry vector;
7. run actual encoder, Carrier, decoder, persistence, and negative terminal
   fixtures;
8. run source-frozen A/B userspace/package/static qualification; and
9. obtain proportional independent review before any ready-manifest, D0, or
   approval work.

No P3.16 artifact or approval may be reused as live authority. The fixed Image
and diagnostic module may be inherited only after the future static closure
proves their exact bytes; no Full-LTO expectation is itself proof.
