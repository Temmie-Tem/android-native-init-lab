# S22+ mainline RAM canary — H0 tools

These host tools build and inspect a proposed g0q RAM-only carrier. They have
no device transport, flashing command, physical approval or host interface
configuration entry point. `vm.py` starts a local QEMU guest and loopback
forwarding. Physical use remains blocked on the initial ABL load/copy binding
and the selected target contract's review and attended entry requirements.

The [build report](../../../../../docs/reports/S22PLUS_MAINLINE_RAM_CANARY_H0_2026-10-27.md)
records the first artifacts, corrected bugs, tests and remaining uncertainty.

## Inputs and outputs

`sources.json` pins Linux 7.2.11, the r0q port configuration and the published
uniLoader revision/DTB-relocation patch. The latest full-phone r0q DTS and
`r0q_defconfig.append` are pinned as provenance references; the build uses the
kernel's minimal r0q USB DTS and explicit g0q placement configuration. It does
not execute the sister port's installation scripts or copy its battery policy.

`prepare.py` takes a private base directory containing `linux-7.2.11.tar.xz`,
its extracted tree, `r0q-port/` and `uniloader-upstream/`. It verifies the locked
inputs and a retained g0q live FDT, generates private memory data, compiles the
DTB, validates enabled USB2/PHY/supply joins and active non-reusable no-map
coverage, and resolves the kernel configuration. Fixed disabled live reserves
are preserved conservatively; addressless CMA requests are recorded separately.

The public fragment retains BLOCK and SMP, limits the initial boot to one CPU,
disables UFS/MMC and selected unused drivers, clears the sister port's built-in
initramfs path and forces the canary command line. All generated blobs, private
network data, keys and logs belong under `workspace/private/`.

1. Run `prepare.py --base <private-source-base> --live-fdt <retained-fdt>
   --output <fresh-private-preparation>`.
2. Run `build_kernel.py --prepared <preparation> --deps <private-build-dependency-root>`.
   The dependency root contains extracted host OpenSSL/libelf/zlib development
   packages. Its package identities are recorded with the run; no global
   package installation is required. A changed prepared config is rejected.
3. Run `build_initramfs.py --prepared <preparation> --network <private-network-json>
   --output <fresh-private-initramfs>`. Network JSON contains `device_ip`,
   `host_ip` and `netmask`; it is normalized and sealed, without changing the
   host. `--vm` creates a distinct test artifact that physical packaging rejects.
4. Run `build_loader.py --base <base> --prepared <preparation> --init <production-initramfs>
   --output <fresh-private-loader>`. The published patch is applied without
   fuzz, input records are joined, ELF member bytes and placement can be
   inspected, and the result explicitly retains the unresolved initial source
   binding. `--reuse` only completes qualification of an existing successful
   build whose result has not yet been published. `--kernel-label` selects a
   non-default kernel build record.
5. `vm.py --prepared <preparation> --init <VM-initramfs> --output <fresh-private-run>`
   exercises the actual kernel/PID1 observer; `--bad-key` checks rejection.
   The VM uses its separately sealed Ethernet endpoint. It does not exercise
   the physical USB PHY, Download entry or original-A return.

## Evidence protocol and tests

The runtime accepts one fixed 72-byte authenticated request. Its fixed response
binds a host nonce, candidate identity, boot identity, measured PID1 executable
and live FDT hashes, kernel release, CPU/block counts and a bounded memory/timer
check. The live FDT follows the 288-byte response and is capped at 2 MiB.
Both producer and consumer use an absolute 120-second boot-time bound. There
is no command execution, module loading, root mount or reset request.

`verify.py` is an offline verifier. It checks HMAC and exact fields, then joins
all DT properties, header reservations, version and boot CPU to the packaged
tree, allowing only the loader's exact initrd bounds. Embedded identities and
software measurements are not measured-boot attestation or recovery proof.

Run the focused suite from the repository root:

```sh
python3 -m unittest discover -s tests -p test_s22plus_mainline_canary_h0.py -v
```

It cross-compiles the real protocol code for ARM64 and checks the C/Python
wire boundary plus authenticated invalid fields, DT header reservations and
memory-coverage predicates. The separate USB fixture includes the production
`usb()` function unchanged and supplies a dummy UDC only in its test seal.
Only that H0 harness loads `dummy_hcd`; production archives contain no module.
The FDT fixture links the actual compiled uniLoader handler/library objects,
using its effective buffer size and linked ramdisk size. Exact commands, raw
outputs and source snapshots are retained with the private build.
