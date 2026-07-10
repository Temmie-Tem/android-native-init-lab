# V3434 S22+ Boot Boundary Static Map Host Pass

## Verdict

`HOST_STATIC_MAP_PASS_NO_LIVE`.

V3434 converted the S22+ boot/PID1/watchdog/observer boundary into a
machine-checked static map and selected the stock-first-stage namespace handoff
as the primary runtime architecture. No device contact, reboot, image build,
flash, or partition write occurred. No live action is authorized.

Artifacts:

```text
workspace/public/src/scripts/revalidation/s22plus_v3434_boot_boundary_map.py
docs/plans/s22plus-v3434-boot-boundary-map.json
docs/plans/NATIVE_INIT_V3434_S22PLUS_BOOT_BOUNDARY_AND_STOCK_HANDOFF_DESIGN_2026-07-11.md
tests/test_s22plus_v3434_boot_boundary_map.py
```

## Evidence Closed

The checker pins and validates:

- the 566 MB Samsung base OSRC kernel archive;
- the known-booting Magisk kernel and its embedded IKCONFIG;
- stock `boot.img` and `vendor_boot.img`;
- vendor bootconfig and live `/proc/cmdline`/`/proc/bootconfig` captures;
- FYG8 first-stage `modules.load` and retention module map;
- O1.1, M31B, PMIC/PON, and V3433 result reports;
- the V3433 first-rollback retained ring;
- the FYG8 BL tar and exact decompressed `abl.elf` identity.

The source map proves:

```text
start_kernel
  -> arch_call_rest_init
  -> rest_init
  -> kernel_thread(kernel_init) as PID 1
  -> kernel_init_freeable / initcalls / initramfs
  -> init_eaccess("/init")
  -> kernel_init
  -> run_init_process
  -> kernel_execve("/init")
```

It also pins `/init`/`rdinit=` selection, fallback init ordering, exec-failure
panics, and the post-exec `Attempted to kill init!` panic.

## Structural Finding

V3432 did not have a module-free PID1 witness. Its first retained marker was
after `/dev` construction, proc/sysfs mounts, `finit_module(sec_log_buf.ko)`,
platform bind, and proc-node creation. V3433 absence therefore cannot identify
which earlier boundary failed.

The useful observation stages are now explicit:

| Channel | FYG8 status | Earliest stage |
|---|---|---|
| earlycon/UART | unavailable by default | kernel entry |
| ramoops/pstore | backend disabled | platform probe |
| `sec_log_buf.ko` | live proven | stock PID1 module #2 + bind |
| `sec_debug.ko` | live proven | stock PID1 module #105 + bind |
| PMIC/PON reason | available as reset class | XBL/ABL before Linux |
| stock tty control | O1.1 live proven | stock gadget configured |

Running-kernel IKCONFIG confirms earlycon and pstore support are compiled in,
but the live cmdline disables the UART path and the live DT disables ramoops.
The watchdog core is built in with boot handling enabled and infinite userspace
takeover timeout. Stock first-stage modules #5/#6 instantiate the watchdog path;
M31B's 120-second survival is the live positive discriminator.

## ABL Scope

The stock headers parse as boot/vendor_boot v4. `vendor_boot` supplies the
kernel/ramdisk/tags/DTB load addresses, vendor ramdisk, cmdline, and bootconfig.
The exact FYG8 ABL is a 4 MiB ELF32 ARM UEFI firmware volume with entry
`0x9fa00000`.

Retained ABL evidence includes `AUTHENTICATE fail but allow Kernel binary`, the
custom boot warning, `Device is unlocked, Skipping boot verification`, and
continued hypervisor/DT selection. This closes bootloader rejection as the
explanation for the warning but does not prove the final kernel branch or
`start_kernel`. Broad ABL reverse engineering remains deferred.

## Selected Architecture

The primary architecture is:

```text
stock Android init (global PID 1, hardware/watchdog/recovery owner)
  -> native supervisor service
  -> new PID + mount namespaces
  -> Debian root identity preflight
  -> private mount propagation and allowlisted device binds
  -> pivot_root
  -> Debian /sbin/init as namespace PID 1
```

The O1.1-proven `ttyGS0` framed control plane stays in the global namespace.
This is a real namespace root handoff, not `chroot`, while preserving a recovery
owner if Debian or a device transfer fails. Direct `/init` replacement is now a
research-only line until a pre-userspace witness exists.

## Validation

```text
py_compile                                      PASS
V3434 focused tests                            11/11 PASS
V3426-V3434 regression tests                 124/124 PASS (59.565 s)
committed JSON exact regeneration              PASS
boot/vendor_boot v4 parsing                    PASS
running-kernel IKCONFIG checks                 PASS
source/report/artifact SHA pins                PASS
host-only/no-live source contract              PASS
```

Next host units are the supervisor protocol/prerequisite contract, a disposable
namespace+`pivot_root` implementation test, and only then a stock-first-stage
overlay build. Each future device action still requires a new narrow review and
authorization.
