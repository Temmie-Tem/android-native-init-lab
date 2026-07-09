# V3410 S22+ O2 Loader-Parity Host Pass

## Verdict

`HOST PASS`. O2 now has a FYG8-pinned module metadata planner, deterministic
load plan, generated C contract, EOF-complete `/proc/modules` scanner,
fail-stop module executor, and ordered functional bind-gate checker.

No boot image was built or flashed. No reboot, module insertion, sysfs/configfs
write, persistent mount, block write, or partition write occurred. A read-only
stock Android query was used only to confirm the gate paths and generic ACM
kernel configuration.

## Authoritative Metadata

The planner pins the extracted FYG8 vendor module database:

| File | Records | SHA256 |
|---|---:|---|
| `modules.dep` | 441 | `21eae389f1d8b0a9fc93cec0b12d36e736cfac656d91ae55055c793f2ed67b27` |
| `modules.softdep` | 31 | `21d6a678d186356c2fb0349a8a9a5190e6e225dab0feb5012e495a100c33afb0` |
| `modules.load` | 140 | `8491b842e6e05cfba42694ad003301a6598e8d152ec10cc8f0cc6fb17f10e232` |
| `modules.load.recovery` | 446 | `616bdb71f2b68d76eca23f72883aea25d5202d4e14f5c99dd934720df863ac10` |
| `modules.alias` | 901 | `5679e647fcdcb6a13bd4f20d24a901f158e641fbd0a813274c99006ec8fa2c20` |
| `modules.blocklist` | 64 | `1fd4e3e5e5a13920c2fa75f0cdb7149869ceef6c194f2516ce977c0e492cb706` |

The 901 alias records collapse to 898 unique patterns and every alias target
resolves to a module in `modules.dep`. The blocklist has 63 unique names;
`dummy_hcd` is duplicated. The selected closure does not intersect it.
`modules.options` is absent. The parser supports it when present and carries
its parameter strings into generated `finit_module` calls.

Five stock softdep edges refer to names absent from this vendor module DB:

```text
pinctrl-cape.ko   pre:qcom_tlmm_vm_irqchip
pinctrl-diwali.ko pre:qcom_tlmm_vm_irqchip
pinctrl-waipio.ko pre:qcom_tlmm_vm_irqchip
slsi_ts.ko        pre:acpm-mfd-bus
stm_ts_spi.ko     pre:acpm-mfd-bus
```

They are retained as unresolved inventory. They do not affect the default O2
closure. Selecting any affected target fails closed instead of silently
dropping the edge.

## Planning Semantics

Source:
`workspace/public/src/scripts/revalidation/s22plus_o2_module_plan.py`.

The planner:

1. Resolves module filenames and kernel runtime names with checked
   hyphen/underscore normalization.
2. Recursively adds every `modules.dep` hard dependency.
3. Recursively adds every selected module's softdep `pre:` and `post:` edges.
4. Performs one DAG topological sort. Among simultaneously ready modules it
   uses `modules.load`, then `modules.load.recovery`, then `modules.dep` order.
5. Fails on dependency cycles, missing selected softdeps, normalized-name
   ambiguity, selected blocklist intersection, malformed metadata, or pin
   drift.
6. Parses aliases for exact-root resolution; wildcard modalias autoload is
   explicitly not claimed.
7. Generates a TSV plan and C header. The default plan count and full TSV SHA
   are pinned, so module, order, runtime-name, or parameter drift is fatal.

Default roots are the functional substrate providers plus the O3-selected USB
leaf:

```text
qcom_rpmh.ko
gcc-waipio.ko
dwc3-msm.ko
```

The resulting plan has 42 modules. Important ordering proofs include:

```text
qcom_hwspinlock.ko < smem.ko
qrtr.ko < qmi_helpers.ko
phy-generic.ko < dwc3-msm.ko
phy-msm-snps-hs.ko < dwc3-msm.ko
phy-msm-snps-eusb2.ko < dwc3-msm.ko
phy-msm-ssusb-qmp.ko < dwc3-msm.ko
eud.ko < dwc3-msm.ko < ucsi_glink.ko
```

Generated private artifacts:

```text
workspace/private/outputs/s22plus_native_init/o2_loader_parity_v0_1/module-plan.tsv
  SHA256 47b9a44331310951eb8bcb27d9dfe58bf44441ef7d981eee42ab658f60643987

workspace/private/outputs/s22plus_native_init/o2_loader_parity_v0_1/module-plan.generated.h
  SHA256 02ccc6d34148e652071bb5247e8856f4b36974bc203e0f29d5c73eeb2a3c8ebc

workspace/private/outputs/s22plus_native_init/o2_loader_parity_v0_1/functional-bind-gates.json
  SHA256 952496134adb496c49a7a7b4a5dd0c46ed418ffe8161641ebe066ff5790f5e9c
```

The longest selected runtime name is 20 bytes and longest filename is 23
bytes, below the C core's checked 128-byte runtime-name limit.

## Runtime Core

Source:
`workspace/public/src/native-init/s22plus_o2_loader_core.h`.

The freestanding core provides three bounded operations:

- `s22plus_o2_execute_module_plan`: invokes the generated plan in order,
  passes per-module params, accepts only rc 0 or `-EEXIST`, and stops at the
  first open, `finit_module`, or close failure.
- `s22plus_o2_scan_proc_modules`: repeatedly reads until an actual EOF and
  retains only each line's first token. It has no 16KiB whole-file ceiling and
  does not need to buffer long dependency columns.
- `s22plus_o2_check_bind_gates`: evaluates gates in order and stops at the
  first missing path or read error.

The host behavior test placed a wanted module after byte 16,384 and supplied
257-byte chunks. The scanner found both early and late names, consumed the
entire stream, and observed EOF. A loader fixture returned success, `-EEXIST`,
then failure; the fourth module was never opened. A gate fixture stopped at the
second missing gate.

The core and generated plan header compiled together as an ELF64 AArch64
relocatable object using `-ffreestanding -fno-builtin -Wall -Wextra -Werror`.

## Functional Gates

Current stock Android read-only evidence confirms generic ACM is built in:

```text
CONFIG_USB_LIBCOMPOSITE=y
CONFIG_USB_F_ACM=y
CONFIG_USB_CONFIGFS=y
CONFIG_USB_CONFIGFS_ACM=y
```

Therefore O3 does not need Samsung `usb_f_ss_acm.ko` merely to create
`acm.usb0`. O2 pins these eight functional proof paths in order:

```text
1 /sys/bus/platform/drivers/qcom_hwspinlock/soc:hwlock
2 /sys/bus/platform/drivers/qcom-smem/soc:qcom,smem
3 /sys/bus/platform/drivers/cmd-db/80860000.aop_cmd_db_region
4 /sys/bus/platform/drivers/rpmh/af20000.rsc
5 /sys/bus/platform/drivers/gcc-waipio/100000.clock-controller
6 /sys/bus/platform/drivers/msm-dwc3/a600000.ssusb
7 /sys/bus/platform/drivers/dwc3/a600000.dwc3
8 /sys/class/udc/a600000.dwc3
```

`finit_module` rc and `/proc/modules` presence remain registration evidence,
not bind proof. O3 must prove these paths in order before gadget creation and
UDC binding.

## Validation

```text
Ran 14 tests
OK
```

The final combined O0/O1/O1.1/O2 regression run passed 53 tests.

Coverage includes hard-dep recursion, recursive softdep pre/post, stock-order
tie-breaking, exact alias roots, blocklist rejection, options propagation,
cross-edge cycle rejection, selected unresolved-softdep rejection, normalized
name collision, FYG8 pins, deterministic plan identity, EOF scanning beyond
16KiB, fail-stop module execution, ordered gate failure, host compilation, and
AArch64 freestanding compilation.

Python compilation and `git diff --check` also passed.

## Risk Boundary And Next Rung

The exact stock closure contains these modules that require explicit O3 review:

```text
abc.ko
sec_debug.ko
minidump.ko
eud.ko
qc_usb_audio.ko
```

They arrived through stock hard/soft metadata and were not manually added. O3
must either accept the complete semantics under a fresh narrow gate or change
its roots with a documented discriminator. It must not silently delete a hard
or soft dependency to make the candidate look smaller.

The operator expressed live approval intent during O2, but no SHA-pinned O3
boot artifact and no active one-shot O3 exception exist. No live authorization
was consumed. Next is an O3 host build around generic configfs `acm.usb0`, the
generated loader plan, EOF scanner, and per-gate bounded observation. A future
live run still requires an exact artifact, rollback pins, active exception, and
candidate-specific acknowledgement.
