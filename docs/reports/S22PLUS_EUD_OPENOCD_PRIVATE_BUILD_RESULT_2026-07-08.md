# S22+ EUD OpenOCD Private Build Result (2026-07-08)

## Verdict

Host-only B1 EUD-SWD/JTAG staging advanced from "not staged" to "private OpenOCD-EUD binary built and runnable".

Live OpenOCD attach is still **not ready**: the host currently has no EUD USB endpoint, and the staged fork provides a QCS6490/QCM6490-oriented Qualcomm target sample rather than an SM8450/S22+ target cfg.

## Scope

- Device action: no
- Flash/reboot/partition write: no
- Sysfs write/EUD enable: no
- System package install: no
- Public committed payloads: report + GOAL only
- Private build/staging paths: `workspace/private/tools/...`

## Inputs

- `linux-msm/openocd`, branch `eud-rebased`
  - commit: `880c11c56b5bc5e8acd2adef5c97ab37b3ca9349`
  - contains `--enable-eud`, `tcl/interface/eud.cfg`, `tcl/target/qualcomm/qcom.cfg`
- `quic/eud`
  - standalone staged commit: `693741a3b0448690402539ed0e6af067510e386f`
  - OpenOCD submodule commit: `2e89590f5a77e1909c1ba6fa115061db4e09c4e1`
- OpenOCD submodules:
  - `jimtcl`: `f160866171457474f7c4d6ccda70f9b77524407e`
  - `libjaylink`: `0d23921a05d5d427332a142d154c213d0c306eb1`

## Build

The host lacks installed `autoreconf`, `automake`, `libtool`, and `libusb-1.0` dev headers, so build dependencies were unpacked into a private sysroot under `workspace/private/tools/openocd_build_deps/`. No apt install or system path mutation was performed.

The successful build configuration was:

```text
./configure --enable-eud --enable-internal-jimtcl --disable-werror --prefix="$OCD/install"
```

Key build notes:

- `quic/eud` `autoreconf`: pass
- `linux-msm/openocd` `bootstrap`: pass
- `configure`: pass, summary includes `Embedded USB Debugger yes`
- initial final link failed because private `libusb-1.0.so` was a dangling symlink and the linker selected static `libusb-1.0.a`, which required unresolved `libudev` symbols
- copying the runtime `libusb-1.0.so.0.5.0` into the private sysroot made the existing private `.so` symlink valid; final link and `make install` then passed

Installed private binary:

```text
workspace/private/tools/linux-msm-openocd-eud/install/bin/openocd
Open On-Chip Debugger 0.12.0+dev-g880c11c (2026-07-08-07:39)
```

Dynamic dependency check confirms it is not bound to the static libusb failure mode:

```text
libusb-1.0.so.0 => /usr/lib/x86_64-linux-gnu/libusb-1.0.so.0
libudev.so.1 => /usr/lib/x86_64-linux-gnu/libudev.so.1
```

## Host Audit Result

Command:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_eud_openocd_host_audit.py \
  --openocd workspace/private/tools/linux-msm-openocd-eud/install/bin/openocd \
  --script-dir workspace/private/tools/linux-msm-openocd-eud/install/share/openocd/scripts
```

Result:

```text
S22+ EUD OpenOCD host audit: blocked_missing_sm8450_target; openocd=1 eud_cfg=1 qcom_cfg=1 sm8450_cfg=0 host_eud_usb=0
```

The audit now sees:

- OpenOCD binary: present
- EUD interface cfg: present
- Qualcomm target cfg: present
- SM8450/S22+ target cfg: absent
- current host EUD USB hint: absent

## Config Smoke

Adapter/transport inventory from the private binary includes the expected EUD adapter and SWD transport:

```text
adapter list: eud present
transport list: swd present
```

Loading `interface/eud.cfg` and selecting SWD fails at SWD driver init:

```text
Error: Error selecting 'swd' as transport
```

Debug log narrows that to `adi_v5_swd.c: swd_select(): can't init SWD driver`. The EUD driver source initializes SWD by calling `get_device_id_array()` and then `eud_initialize_device_swd(...)`, so this failure is consistent with the current host audit result: no enumerated EUD USB endpoint is available.

## Interpretation

B1 is now a real local toolchain path, but not a live probe path yet. The next gate is not another native-init flash. The next gate is either:

1. make a defensible SM8450/S22+ OpenOCD target cfg from source/reference data, then keep it host-only until an EUD endpoint appears; or
2. attach/enable a real EUD/SWD endpoint and rerun the host audit before any OpenOCD `init` attempt.

Operator live approval was received during this unit, but no live attach was attempted because the prerequisite endpoint and target cfg are missing.

## References

- Qualcomm OpenOCD debug documentation: https://docs.qualcomm.com/doc/80-70029-12/topic/debug_using_openocd.html
- Qualcomm EUD host library: https://github.com/quic/eud
- linux-msm OpenOCD EUD fork: https://github.com/linux-msm/openocd/tree/eud-rebased
- Linaro EUD overview: https://www.linaro.org/blog/hidden-jtag-qualcomm-snapdragon-usb/
