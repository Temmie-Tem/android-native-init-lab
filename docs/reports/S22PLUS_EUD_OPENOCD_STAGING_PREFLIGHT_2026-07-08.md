# S22+ EUD OpenOCD Staging Preflight (2026-07-08)

## Verdict

HOST-ONLY PREFLIGHT DONE / CORRECT FORK IDENTIFIED / BUILD BLOCKED ON HOST
DEPENDENCIES.

No device action was performed. This unit only inspected package/source
availability and attempted build preflight commands in `workspace/private/tools`.

## Why This Unit

The EUD Phase-B live run proved that no-jig EUD enable does not create a
host-visible EUD USB device or new serial/TTY path. The prior host audit then
proved the local host has no OpenOCD/EUD toolchain. This unit resolves which
OpenOCD source is actually useful for EUD-SWD and what blocks a local build.

## Source Findings

| Item | Result |
| --- | --- |
| Ubuntu `openocd` package | Candidate `0.12.0-3build3`; not installed |
| Ubuntu package contents | no `interface/eud.cfg`; no SM8450 target; only unrelated `target/qualcomm_qca4531.cfg` |
| Upstream OpenOCD master | staged privately at `2ed9f231a47300c39c2573f3a98266aceebc7dd0`; no EUD adapter/config found |
| Qualcomm EUD library | staged privately at `quic/eud` `693741a3b0448690402539ed0e6af067510e386f` |
| EUD-capable OpenOCD fork | `linux-msm/openocd` branch `eud-rebased` staged privately at `880c11c56b5bc5e8acd2adef5c97ab37b3ca9349` |
| EUD interface config | present: `tcl/interface/eud.cfg` |
| Qualcomm target config | present: `tcl/target/qualcomm/qcom.cfg` |
| SM8450-specific cfg | not present; generic Qualcomm/QCS6490-style aarch64 SWD config is the starting point |
| EUD build flag | present: `--enable-eud` |
| EUD submodule | `src/jtag/drivers/eud -> https://github.com/quic/eud.git` |

The EUD-capable fork's `qcom.cfg` is written around Qualcomm SWD/JTAG target
setup and uses SWD DPIDR `0x5ba02477`, aarch64 targets, and GDB port `3333`.
That matches the intended B1 path at the tooling level, but it does not prove
SM8450/S22+ connectivity without a host-visible EUD interface.

## Build Preflight

Current host tools:

```text
git: present
make: present
gcc/cc: present
pkg-config: present
autoconf/autoreconf: absent
automake: absent
libtool: absent
libusb-1.0 dev pkg-config entry: absent
libusb runtime library: present
```

Attempted preflight:

```text
cd workspace/private/tools/quic-eud
autoreconf --verbose --force --install
```

Result:

```text
autoreconf_rc=127
autoreconf: command not found
```

Attempted preflight:

```text
cd workspace/private/tools/linux-msm-openocd-eud
./bootstrap
```

Result:

```text
bootstrap_rc=1
./bootstrap: Error: libtool is required
```

So the build is blocked before compilation. This is a host dependency issue,
not a device result.

## Required Next Host Dependencies

The minimum next install set is:

```text
autoconf automake libtool libusb-1.0-0-dev
```

The Ubuntu `openocd` binary package alone is not enough for this path because
its packaged scripts do not include the EUD adapter config.

## Proposed Build Shape

After host dependencies are present:

```text
git clone --branch eud-rebased --recurse-submodules \
  https://github.com/linux-msm/openocd.git \
  workspace/private/tools/linux-msm-openocd-eud

cd workspace/private/tools/linux-msm-openocd-eud
./bootstrap
./configure --enable-eud --prefix="$PWD/install"
make -j"$(nproc)"
make install
```

Then rerun:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_eud_openocd_host_audit.py \
  --openocd workspace/private/tools/linux-msm-openocd-eud/install/bin/openocd \
  --script-dir workspace/private/tools/linux-msm-openocd-eud/install/share/openocd/scripts
```

Only after that audit sees `openocd=1`, `eud_cfg=1`, and `qcom_cfg=1` should an
attended OpenOCD probe be considered. The current no-EUD-USB state still means
the probe may require physical EUD/SWD hardware or a different secure enable
state.

## Safety

No ADB, flash, reboot, partition write, sysfs write, EUD enable, Magisk action,
or A90 action was performed. Private source/download payloads remain under
`workspace/private/tools` and are not committed.

## References

- Qualcomm `quic/eud`: https://github.com/quic/eud
- Linux-msm EUD OpenOCD fork: https://github.com/linux-msm/openocd/tree/eud-rebased
- Linaro EUD/OpenOCD demonstration: https://www.linaro.org/blog/hidden-jtag-qualcomm-snapdragon-usb/
- Qualcomm OpenOCD debug docs: https://docs.qualcomm.com/doc/80-70029-12/topic/debug_using_openocd.html
- LWN Qualcomm EUD driver/platform series: https://lwn.net/Articles/1056174/
