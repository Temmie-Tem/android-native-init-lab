# ML017: exclude unused TLMM from the RAM/USB2 canary

Status: **H0 qualified, independently reviewed and fixed D0 ready**.
Exact finite attended approval remains pending; no control or partition
transfer has occurred.

After [LA003](S22PLUS_LOADER_PREFIX_LA003_RUN_2026-11-04.md), two rounds of
Claude Opus 5.5 and Gemini 4 Argon High discussion selected a functional
candidate: disable only the TLMM DT node in the bounded mainline RAM/USB2
configuration. The GPIO reservations for 36–39, 50 and 93 remain intact.
V1 loader/entry instrumentation, kernel configuration, USB2, PMIC, clocks,
regulators, memory reservations and original-A recovery are retained.

## Source basis and scope

The exact preceding DTB has no active TLMM GPIO or pin-state consumer, no
direct/inherited/extended TLMM interrupt, no TLMM interrupt-map target, no
GPIO hog and no TLMM self-pinctrl state. The expanded schema-aware scan covers
every pinctrl index and GPIO-range reference, with each consumer's complete
ancestor status. Its four GPIO tuples belong to disabled PCIe nodes.
Integer matches in arbitrary DT cells were not treated as phandle references.

The actual SM8450 driver initializer only registers its OF-matched platform
driver. The ordinary OF platform creation path rejects a disabled node before
device creation and probe. The selected USB controller/PHY use GCC, RPMh,
interconnect, GIC and PDC resources; they declare no TLMM pin state or GPIO.
Generic optional pinctrl handling remains present in the driver core and DWC3
PM code. Missing pin states are permitted. This is a source/DT dependency
argument, not proof of physical electrical independence or future Debian
hardware support.

The common TLMM reset setup registers a handler only for a function named
`ps_hold`; SM8450's table has none. The current RAM PID1 never requests a
reboot or poweroff: success and failure both park. Physical Download and
original-A restoration remain the recovery route.

The compiled DT semantic comparison finds exactly one added property:
`/soc@0/pinctrl@f100000/status = "disabled"`. The resulting DTB hash is
`2274e44acd06f96ef10260c328c49869a9f80ef4eaa65ca8e677685ac1037098`.
Memory/no-map coverage and the existing USB supply checks pass unchanged.
This removes an unused driver probe from this bounded candidate; it does not
identify TLMM as the cause of any historical result.

## Alternatives and evidence limits

A deliberate entry park cannot reach the RAM PID1/USB objective, and either
positive or negative retained records would describe only that new candidate
and recovery. Further returning-prefix or writer-freshness instrumentation
would add observations on the different vendor-return carrier without itself
advancing the full mainline boot. V1 is retained instead of reintroducing the
larger V9 instrumentation alongside the functional DT change.

The discussion's proposed IRQ-mask repair lacked a concrete source defect.
The actual IRQ valid-mask callback is distinct from the GPIO callback, performs
bitmap work without MMIO, and gpiolib's IRQ validity helper checks ordinary
line validity first. No C driver repair or broad peripheral pruning is selected.
Missing historical TLMM return frames do not locate a fault; LA003's prefix
return does not establish the state of an ordinary mainline attempt.

Authenticated USB/RAM PID1 is accepted independently of retained markers by
the existing owner. Static V1 positives establish at-least-once occurrence for
this candidate, without a unique attempt or same-boot join to a USB-absence
window. Zero records do not distinguish pre-entry failure, writer rejection
or later loss. A future functional positive would show that this candidate
works with TLMM excluded, not why earlier candidates failed. Installed Debian
and broader hardware support remain separate objectives.

## Qualification and review scope

Complete fresh kernel production passed without a compiler warning, error or
section mismatch. The source-tree comparison against ML016 differs only in
the generated V1 kernel frame. The configuration and complete ELF symbol
layout match; the entire Image differs only in that 128-byte frame and its
derived 20-byte GNU build ID. Init source/configuration/network inputs remain
unchanged, while candidate identity, key, sealed init and CPIO are fresh.

- 342 actual ARM64 V1 writer cases and six real-EL marker cases pass.
- 20 linked-loader cases, 1,051 aligned-copy cases and three real-EL loader
  entry cases pass, including EL3 refusal.
- The RAM PID1 VM passes in 4.803 seconds; its complete raw evidence rechecks.
- Two boot images and boot-only AP packages are byte-identical.
- The changed DT's complete consumer/semantic checks and 82 relevant
  host/terminal tests pass. Touched Python compiles; compiled init is ARM64.

These checks qualify the exact artifacts in H0. They do not prove physical
boot, USB, retention or automatic recovery. No unchanged diagnostic suite is
being added as another device-approval prerequisite.

The separate mainline capability became stale after LA003's shared target
adoption and loader-only source-list changes. Final independent review returned
`PASS_GO` with no unresolved findings, binding 94 sources and 427 artifact/raw
pins. It independently reproduced both init ELFs and all 342 V1 cases, checked
the embedded payloads and both AP round trips, and revalidated authenticated VM
raw evidence. The exact publication/consumer joins were also reviewed.

The new mainline and backend V26 receipts are published; the unmocked
production image/task consumers pass. The connected ordinary-terminal worker
reports V26 with its two stable source files unchanged. The new task uses
closed LA003's original-A recovery evidence. One fixed preapproval D0 completed,
and all seven complete, successful raw captures rederive exact original-A
health. No experimental operation, approval, grant or unresolved F1 owner
exists. Readiness is a snapshot and is refreshed through the same fixed profile
if required before a later grant.

Old receipts, consumed tasks and grants retain their original pins. The
separate loader-prefix capability is not renewed by this mainline review.

Applicable past-failure rows are ARTIFACT, SEMANTIC, WIRE, ROUTE, PERSIST and
RETURN: exact DT/image/initramfs/package joins, marker proof limits, real raw
consumers, selected capability/entry routing, durable outputs and original-owner
recovery. No new device effect, reset mechanism or evidence-acceptance rule is
introduced. The remaining execution prerequisite is the generated fresh finite
attended approval and usable physical Download recovery; neither H0 checks,
D0 health nor this report supplies that authority.

Private preparation is under
`workspace/private/outputs/s22plus-mainline-ml017-h0-20261104-1/`; discussion and
source checks are under `workspace/private/outputs/s22plus-la003-next-discussion-20261104-1/`.
A90, S20+ and the initial unrelated changes remain untouched.

## External discussion accounting

All four calls completed without fallback or tool use. Claude reported four
uncached input, 59,817 cache-creation input and 18,637 output tokens, including
12,190 thinking tokens. Its five-hour account meter moved from 6% to 12% used.
Argon reported 67,864 input and 32,468 output tokens, including 24,822 thinking
tokens, for 100,332 total; weekly remaining moved from 100% to 96.84%.
These account-wide percentage changes are not exact per-call attribution.
Private before/after records preserve the provider data. Claude's USD 0.851292
list-price equivalent is an estimate, not a subscription charge; Argon cost
was unavailable.
