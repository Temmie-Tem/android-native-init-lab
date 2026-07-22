# S22+ FYG8 P2.41 E2 source implementation host pass

Date: 2026-07-23 KST
Tier: H0
Status: `PASS_P241_E2_SOURCE_IMPLEMENTATION_HOST_ONLY`
Device contact: none
Live authority: none

## Result

P2.41 implements the bounded P2.40 E2 contract without building a kernel or
candidate. The new profile repeats the live-proven E1A local runtime and E1B
foundation, then loads the exact 59-module USB closure and observes eight
read-only bind/UDC gates.

The implementation adds:

- one dependency-derived E2 plan whose six-module prefix is
  `qcom_hwspinlock`, `smem`, `minidump`, `qcom-scm`, `qcom_wdt_core`, and
  `gh_virt_wdt`;
- profile 3 in the compact checkpoint model, client, and default-disabled
  kernel patch;
- one static PID 1 runtime with exact module-prefix and read-only gate checks;
- one direct parser for every entry in the exact FYG8 DTBO; and
- one independent checker that composes source, patch, runtime, module bytes,
  DTBO, exhaustive record semantics, and E1A/E1B regression evidence.

No AP, manifest, candidate Image, connected binding, approval, or device
authority was created.

## Exact Contracts

The generated plan contains 59 unique modules and satisfies all 210 metadata
constraints. Its TSV SHA256 is
`fc8169da1036ae8ba76e81ffe6afb17d063d114735a427e858afeeaa82a2218e`.
The generated C header is 4,105 bytes with SHA256
`2223ed333d6288e25b6ce7b7ae3aaa8dc31108dcc8536b9c582a7576953e7647`.

Profile 3 has 76 post-entry stages:

- eight local stages;
- module stages `0x40..0x7a`;
- gate stages `0x7b..0x82`; and
- terminal success `0x8f`.

The kernel patch clean-applies to the source-matched FYG8 tree, remains
default-disabled, and carries the exact same sequence. All 307,201 reachable
E2 slot variants pass CRC, semantics, adjacency, and family-collision checks.
The unchanged E1A/E1B domain still exhausts 90,114 variants.

## Runtime Semantics

For every module the runtime requires exact `openat`,
`finit_module() == 0`, and `close`, then streams `/proc/modules` to EOF and
requires exactly the expected loaded prefix. Missing, duplicate, foreign, or
already-loaded modules fail closed. An unplanned transitive automatic module
load therefore fails as foreign state rather than being silently accepted.

After all modules pass, one global 20-second monotonic deadline covers the
eight gates. The runtime polls at 100 ms, verifies the seven driver paths are
symlinks to the exact device basename, and requires `/sys/class/udc` to contain
one and only one non-dot entry named `a600000.dwc3`. `ENOENT` is normalized to
the bounded not-yet-present state; other errors fail immediately. Every prior
gate is rechecked, and a disappearing gate records that exact gate before the
runtime parks. No sysfs or configfs write exists in this phase.

## Exact DTBO Closure

The direct parser reads the SHA-pinned 8 MiB FYG8 DTBO, parses all 11 embedded
FDT entries, and binds their offset, size, and SHA256 into one entry manifest.
Every entry must contain the parent and child `usb-role-switch` properties,
child `dr_mode = "otg"`, MAX77705 MFD/PDIC, role-swap support, Samsung USB
notifier, and the UCSI fixup. Every entry must contain neither an explicit
`extcon` property nor `role-switch-default-mode`.

This closes P2.40's missing-decompile reproducibility gap without substituting
the source-archive DTS for the exact flashed DTBO.

## Static Validation

The final checker returned
`PASS_P241_E2_SOURCE_IMPLEMENTATION_HOST_ONLY` and reported:

- static AArch64 `/init`: 69,360 bytes, zero undefined symbols, exact run ID
  once, and SHA256
  `01d7205bb60d6f20fcbb8edd37025c1535b1d4a41b4495f6ef1cf57fa81e65b2`;
- static child: 1,384 bytes, QEMU exit 23, exact token, and SHA256
  `3a9b561051f13d07dfb3fa9f75374ac06436e3e98f13cf28a43d80f7f17bef8f`;
- all exact 59 vendor-ramdisk module files present;
- zero selected-module `request_firmware` string hits;
- `sec_log_buf.ko` absent from the selected closure; and
- candidate, kernel build, manifest, device contact, Odin, sysfs/configfs
  write, and live authority all false.

The focused planner, model, P2.33 implementation, P2.34 build-adapter, and
P2.41 implementation suite passed 55 tests after the final review fixes.
Touched Python also passed `py_compile`.

## Independent Review

The independent adversarial review returned `GO-WITH-NITS` with no blocker.
It found one diagnostic issue in the previous-gate regression path and one
missing negative DTBO predicate. The runtime now attributes a disappeared
previous gate to its actual stage/item, and the DTBO contract now rejects
`role-switch-default-mode` in every entry. A focused independent delta review
returned `GO` for both fixes.

The remaining informational risk is deliberate: if a module probe causes an
unplanned transitive module load, the strict `/proc/modules` equality gate
will stop the run. That preserves exact-state semantics and gives a bounded
failure to analyze; it does not justify widening the plan before live data.

## Boundary And Next Unit

P2.41 proves source-level implementation, exact shipped module bytes, DTBO
topology, static linkage, and evidence semantics. It does not prove module
insertion, platform probe, driver bind, DWC3 child creation, UDC publication,
USB enumeration, or host-visible bytes under direct PID 1.

P2.42 may perform the separate reproducible Full-LTO E2 kernel build,
deterministic boot-only packaging, independent artifact reconstruction, and
offline Process v2 evidence promotion. It must not contact the device or
create F1 authority. Connected D0 and a fresh exact F1 approval remain later
steps.
