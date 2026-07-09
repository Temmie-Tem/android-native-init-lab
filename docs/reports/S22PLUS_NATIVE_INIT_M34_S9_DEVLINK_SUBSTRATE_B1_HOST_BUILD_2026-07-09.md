# S22+ M34 S9 Devlink-Substrate B1 Host Build (2026-07-09)

## Verdict

Host build complete. No live flash was performed or authorized.

S9 is the next host-only candidate after the S8B1/S8B1A B1 probe work and the
devlink-supplier root-cause analysis. It keeps the S8B1A wide B1
download-beacon predicate, but pins the resolved Waipio substrate load-set and
adds the missing provider modules before GENI I2C/max77705 probing.

## Scope

S9 still does not create configfs, bind UDC, write TypeC role nodes, write
soft_connect, mount persistent partitions, write block devices, or start
Android. The only intended runtime side effect beyond module loading is the
existing B1 one-bit beacon: predicate true requests `reboot(download)`,
predicate false parks.

The resolved S9 substrate load-set is:

```text
clk-qcom.ko
pinctrl-msm.ko
qcom_rpmh.ko
icc-rpmh.ko
icc-bcm-voter.ko
gcc-waipio.ko
pinctrl-waipio.ko
clk-rpmh.ko
rpmh-regulator.ko
gdsc-regulator.ko
qnoc-waipio.ko
arm_smmu.ko
qcom-pdc.ko
```

Most of that set was already present in the existing S8B1A dependency closure
through the USB/ACM base. The S9 dep-complete delta is exactly:

```text
qcom-pdc.ko
pinctrl-msm.ko
pinctrl-waipio.ko
```

This reconciles the latest root-cause report with the current builder: S9
asserts the full substrate load-set, while the actual new module delta remains
the three missing module-visible providers.

## Artifact

Output directory:

```text
workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_10/
```

S9 AP path:

```text
workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_10/S9/odin4/AP.tar.md5
```

Pinned hashes:

```text
S9 AP.tar.md5 SHA256: 41a76ac1404c99273e9ec3aeae591dbfc94e1aa83daf97de9a7068e3c155022f
S9 padded boot.img SHA256: 509a05e4ff97dad39ca52eae6c57169e20d3ddbf1524d292e8c91b9286a80414
S9 boot.img.lz4 SHA256: dc357d7d8edbf521fd86a3f845fd4699a54290778fa5b65a98ab1f666a767db7
S9 /init SHA256: 9f231faff6154dc08b6b4d1b6cd169e82c81bfdc1e8d02cc92d1ea5a02dbd390
S9 module-list SHA256: c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26
Template source SHA256: 8364aca94582fc325f89855b5cfd4e47ff8e41d2f18c341c99bd750ea3ebe3ae
Known booting Magisk base boot SHA256: 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

The v0.10 manifest confirms S8B1 and S8B1A stayed byte-stable:

```text
S8B1 AP.tar.md5 SHA256: 0bf313cdf24a5f5babc3d0073a1e90686f1b734b6dafdfa548154ef3eac6c2c8
S8B1 padded boot.img SHA256: 4e599087f242fdf2ae6bee1465e0725b60057bad893b665a178bcf87b88b9a20
S8B1A AP.tar.md5 SHA256: 5c5df5f3fd83adf15c521f4509f90696ba3372e1aee5a79128a29f74a701ceb1
S8B1A padded boot.img SHA256: df3ee853bb84541f9d494a97f9ba3db5d08bda67662782de0868e90c49d22145
```

## Runtime Contract

S9:

- loads the 89-module dep-complete closure;
- emits `stage=S9`, `devlink_supplier_closure=1`, and
  `substrate_load_set=waipio_devlink`;
- polls `/sys/class/typec/port0` OR `/sys/bus/i2c/devices/*-0066`;
- requests `reboot(download)` only if the predicate is true;
- parks if the predicate is false.

The S9 marker also explicitly records `driver_load_only=1` and
`manual_power_write=0`. Loading stock provider drivers such as
`rpmh-regulator.ko`, `gdsc-regulator.ko`, and `qnoc-waipio.ko` is not a manual
PMIC/GDSC/rail write.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py \
  --stages S9 \
  --out workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_s9_smoke \
  --force

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py \
  --force

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_m34_runtime_gadget_split_build.py

git diff --check
```

Result:

```text
py_compile: OK
S9 smoke build: OK
full v0.10 build: OK
tests/test_s22plus_m34_runtime_gadget_split_build.py: Ran 5 tests, OK
git diff --check: OK
```

## Next Gate

No active live authorization exists. A future S9 live run requires a fresh
boot-only AGENTS exception, a fail-closed live helper that pins the S9 hashes
above, default dry-run pass, rollback proof, and explicit operator approval.
