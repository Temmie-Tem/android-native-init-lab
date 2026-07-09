# Known Gaps

- Retention and the Max77705-to-DWC3 USB role path now have curated Samsung
  source/ELF/DT review plus stock live bind evidence. Other subsystems remain
  `STATIC_VERIFIED` only.
- ELF imports with no module provider total 19086. They are labeled
  kernel-or-unresolved; this map does not assume every one is a valid built-in
  export for the running kernel.
- Ambiguous ELF imports with multiple module providers total 0.
- Import/export symbol-name overlaps absent from `modules.dep` total
  66; they remain visible in `symbol-overlap-edges.tsv` as
  `CANDIDATE_ONLY`. They are not treated as providers or promoted into load
  order because the same symbol may come from the kernel.
- DT clocks, regulators, interconnects, IOMMUs, reserved-memory regions, device
  links, and deferred-probe causes are not derivable from depmod alone. They
  require subsystem source review and runtime bind gates.
- Display, GPU, audio, storage, networking, and power subsystem maps are not yet
  curated. Add them one subsystem at a time with a named discriminator.
- This directory is not a live snapshot. A `LIVE_BOUND` claim must cite a report
  and target baseline; it does not automatically carry across a kernel boot.
