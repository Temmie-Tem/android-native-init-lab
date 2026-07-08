# S22+ M34 S6 Stock-Speed Softdep Host Build

Date: 2026-07-09 KST

Status: HOST-ONLY BUILD COMPLETE. No live flash is authorized by this report.

## Question

The operator asked whether USB version differences introduce additional
variables, and whether there are easy implementation candidates. The current
evidence says yes: stock Android is not a USB2-only gadget, and the M34 S2-S5
native-init candidates intentionally forced USB2 high-speed.

## USB Version Differences

Stock Android target:

- product: `04e8:6860`
- negotiated speed: USB3 SuperSpeed 5000M
- descriptor version: `bcdUSB 3.20`
- class: composite class 0
- config: 5-interface `mtp_conn_adb` with MTP, CDC ACM, `conn_gadget`, and ADB

M34 S2-S5 native-init path:

- `g1/max_speed = high-speed`
- S4/S5 also wrote `/sys/devices/platform/soc/a600000.ssusb/speed = high-speed`
- S4/S5 wrote `/sys/devices/platform/soc/a600000.ssusb/mode = peripheral`
- S5 additionally wrote `/sys/class/udc/a600000.dwc3/soft_connect = connect`

M34 S5 did not enumerate the intended `04e8:6860` Android/ACM composite. It
later fell to Samsung `04e8:685d` upload/download style endpoints:

- around 62.987 s: `MSM_UPLOAD`, USB2/480M, CDC-class interfaces, no host ACM
- around 73.950 s: `SAMSUNG USB`, USB3/5000M, no host ACM, Odin usable for rollback

Therefore the highest-signal easy change is not descriptor string polish first.
It is to stop artificially pinning USB2 high-speed and restore the stock
controller softdep path that can support the SuperSpeed side.

## Easy Candidate Ranking

1. Observation helper improvement: already done in the S5 gap recon unit. Future
   snapshots summarize every Samsung `04e8:*` device, including `685d`.
2. Remove USB2 high-speed forcing: easy source guard change; S6 implements this.
3. Restore stock `dwc3_msm` softdep parity: moderate but bounded module-list
   closure change; S6 implements this without writing EUD sysfs knobs.
4. Descriptor/string parity: easy text values, but weaker explanation for the
   `685d` fallback. Keep as follow-up after controller speed parity is tested.
5. Companion functions: `conn_gadget.0` and `ss_mon.mtp` are plausible later;
   `ffs.mtp`/`ffs.adb` are not cheap because FunctionFS usually needs userspace
   descriptors/daemons.
6. `super.img` logical partition extraction: host-only but heavier. Needed to
   recover Android USB rc/service details before cloning more of the Android
   sequence.

## Implemented S6

S6 extends the M34 runtime-gadget split to v0.5:

- keeps configfs gadget creation and initial `UDC=none`
- does not write `g1/max_speed`
- does not write `ssusb/speed`
- keeps `ssusb/mode=peripheral`
- binds `UDC=a600000.dwc3`
- does not write `soft_connect`
- restores QMP/EUD/ucsi softdep parity through the module list only
- does not write `/sys/module/eud/parameters/enable` or any other EUD sysfs knob

S1-S5 keep the previous M32/P30 45-module closure. S6 uses a 55-module closure:

```text
new modules:
eud.ko
phy-msm-ssusb-qmp.ko
qmi_helpers.ko
qcom_glink.ko
qcom_glink_smem.ko
qcom_smd.ko
rproc_qcom_common.ko
pdr_interface.ko
pmic_glink.ko
ucsi_glink.ko
```

S6 module list size is 839 bytes, below the native-init 1024-byte parser buffer.

## Artifacts

Output directory:

```text
workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_5/
```

S6 pins:

```text
AP.tar.md5   f1ff77b7df434536029db417291689bff8b3a7dcdf4fda38fef5322475daad39
boot.img     b1bfc4ece7ece60af752bc570e0ae4ce76230d13b129b1c58d4e840cd92225f6
/init        ca3eb2b5a0fedff73cfb0aaa249d42f4b92fcb99b360e9ec5a041649dcd7dd8c
module list  51ba77aeed1966a2de8c78d307ca3d6fe5440daa2b96488679446f6056142515
```

The S6 AP contains exactly one tar member:

```text
boot.img.lz4
```

The S6 compiled `/init` required strings include:

```text
max_speed_high_speed=0
ssusb_speed_high_speed=0
ssusb_mode_peripheral=1
stock_softdep_parity=1
qmp_module=1
eud_module=1
ucsi_glink=1
```

The S6 compiled `/init` does not contain the `high-speed` string.

## Validation

Passed:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_s22plus_m34_runtime_gadget_split_build
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py --force
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_s22plus_m34_runtime_gadget_split_build
tar -tf workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_5/S6/odin4/AP.tar.md5
grep -a "high-speed" workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_5/S6/build/s22plus_init_m34_s6_runtime_gadget_split
```

The final `grep` intentionally returned no matches.

## Next

No live action is authorized. The next live unit, if selected, needs a fresh
SHA-pinned `AGENTS.md` exception for the exact S6 AP and rollback AP, plus a
helper that reuses the enhanced all-Samsung `04e8:*` observation path.
