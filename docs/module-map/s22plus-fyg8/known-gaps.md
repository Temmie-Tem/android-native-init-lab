# Known Gaps

- Retention and the Max77705-to-DWC3 USB role path now have curated Samsung
  source/ELF/DT review plus stock live bind evidence. Other subsystems remain
  `STATIC_VERIFIED` only.
- ELF imports with no module provider total 19152. They are labeled
  kernel-or-unresolved; this map does not assume every one is a valid built-in
  export for the running kernel.
- Module `__versions` rows describe the shipped consumer side only. Provider
  compatibility remains unproved until a completed Full-LTO build supplies a
  matching `vmlinux.symvers` and module set for comparison.
- Ambiguous ELF imports with multiple module providers total 0.
- Import/export symbol-name overlaps absent from `modules.dep` total
  0; they remain visible in `symbol-overlap-edges.tsv` as
  `CANDIDATE_ONLY`. They are not treated as providers or promoted into load
  order because the same symbol may come from the kernel.
- DT clocks, regulators, interconnects, IOMMUs, reserved-memory regions, device
  links, and deferred-probe causes are not derivable from depmod alone. They
  require subsystem source review and runtime bind gates.
- P2.43 demonstrates that limitation directly: the P2.42 depmod-complete plan
  waited on a display RSC whose DT clock supplier was intentionally outside the
  module set. Exact source and DT now close the static explanation and the
  USB-relevant PSCI -> apps-RSC -> RPMh-provider -> GCC chain, but none of those
  replacement binds is yet observed under direct PID 1.
- Display, GPU, audio, storage, networking, and power subsystem maps are not yet
  curated. Add them one subsystem at a time with a named discriminator.
- This directory is not a live snapshot. A `LIVE_BOUND` claim must cite a report
  and target baseline; it does not automatically carry across a kernel boot.
