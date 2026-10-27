# S22+ mainline RAM canary — H0 tools

These host tools build and inspect a proposed g0q RAM-only carrier. They have
no device transport, flashing command, physical approval or host interface
configuration entry point. `vm.py` starts a local QEMU guest and loopback
forwarding. The loader now checks its actual source placement at entry; safe
copies and rejection cases are qualified in H0. Physical use still needs the
mainline execution/recovery owner and the target's review/attended requirements.

The [build report](../../../../../docs/reports/S22PLUS_MAINLINE_RAM_CANARY_H0_2026-10-27.md)
records the first artifacts, corrected bugs, tests and remaining uncertainty.
The [entry successor](../../../../../docs/reports/S22PLUS_MAINLINE_LOADER_ENTRY_H0_2026-10-28.md)
records the loader repair, actual instruction tests and boot-v4 packaging.

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
   fuzz, followed by `uniloader-g0q-entry.patch`. Input records, ELF/raw sections,
   file-backed copy length, complete runtime header, embedded members and fixed
   destination extents are checked. A private retained-RAM table bounds reads
   of the already-loaded image; reservations independently constrain destination
   writes. `--reuse` only completes qualification of an existing successful
   build whose result has not yet been published. `--kernel-label` selects a
   non-default kernel build record.
5. `vm.py --prepared <preparation> --init <VM-initramfs> --output <fresh-private-run>`
   exercises the actual kernel/PID1 observer; `--bad-key` checks rejection.
   The VM uses its separately sealed Ethernet endpoint. It does not exercise
   the physical USB PHY, Download entry or original-A return.
6. `qualify_loader.py --loader <loader> --output <fresh-private-qualification>`
   executes the actual linked blob in Unicorn 2.1.4 (with pyelftools). It checks
   placement/overflow/rejection, complete loader-to-kernel copies and FDT,
   stack bounds, natural alignment and memcpy/memmove edge cases. Install these
   dependencies in a private directory and use its `PYTHONPATH` if needed.
   Its EL/SCTLR injected guard tests are explicitly labelled; Unicorn's caches
   and CPU state are not physical entry evidence.
7. `loader_entry_vm.py --loader <loader> --gdb <gdb-multiarch>
   --output <fresh-private-entry-test>` uses the retained local QEMU distribution
   and loopback GDB connection. Actual reset EL1/EL2 enter the relocated body;
   actual EL3 rejects. It does not modify registers to obtain the expected EL.
8. `package_loader.py --loader <loader> --qualification <qualification>
   --entry-vm <entry-test> --output <fresh-private-package>` reuses the existing
   boot-only packager. Two independent repacks replace the outer kernel with
   uniLoader in the pinned original-A boot-v4 envelope. The outer ramdisk,
   signature and AVB bytes remain retained; uniLoader supplies its own DTB and
   initrd. Retained signatures do not authenticate the changed payload. The
   result is H0 only and is never registered, armed or transferred by this tool.

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

## Reusing a VM capture

A positive `vm.py` run now saves `capture.json`, the exact request/response,
input hashes and the acquisition source snapshot before interpreting the response.
The receipt is published only after full reception and QEMU settlement. A checker
failure can therefore be corrected against the same completed capture:

```sh
python3 workspace/public/src/mainline/s22plus_canary_h0/vm.py \
  --prepared <original-preparation> --init <original-VM-initramfs> \
  --recheck-run <completed-VM-run> --output <fresh-private-recheck>
```

This starts no VM and builds no image. It checks the retained input, request,
raw evidence and source hashes, then runs the current response verifier. The
new result preserves the original acquisition reference and records the new
checker sources separately. Existing files are not rewritten. Checker-only
changes do not require rebuilding the kernel, initramfs or loader.

The result is `PASS_H0_VM_EVIDENCE_RECHECK`: a revalidated historical VM
observation, with the original execution time separate from recheck time.
It does not qualify changed runtime bytes, new acquisition logic or a different
VM environment. A missing capture receipt, changed runtime input, incomplete
capture or changed evidence is rejected without starting a VM automatically.
Older runs and wrong-key rejection runs remain usable within their original
scope but are not accepted by this positive-capture recheck path. Physical
entry, USB/loader qualification and device authority are separate.

## Attended physical owner

The separate `s22plus_mainline_task_v1.py` and `s22plus_mainline_session_v1.py`
adapters connect this unchanged runtime to the existing V3 boot-only owner.
`prepare` is H0, `ready` is fixed preapproval D0, and `grant` requires the
returned finite approval and actual attendance statement. The shared task CLI
selects `execute mainline-ram`; its existing `continue`, `recover` and
`repair-close` entries preserve the original journal and no-replay rules.
Use the exact [mainline policy](../../../../../docs/operations/S22PLUS_MAINLINE_RAM_V1.md)
and current source-bound review before any connected action. The build tools
here still never open a live device session.
