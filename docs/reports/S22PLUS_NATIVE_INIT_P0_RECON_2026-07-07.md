# S22+ Native-Init P0 Recon

Date: 2026-07-07 KST

Device:
- Samsung Galaxy S22+ `SM-S906N` / `g0q`
- Build: `S906NKSS7FYG8`
- State at collection: Android booted, Magisk root working, TWRP/vbmeta
  checkpoint still installed

Scope:
- P0 read-only recon for the S22+ native-init PID1 epic.
- No reboot, no Odin transfer, no partition write, no module load/unload, no
  filesystem mutation on the device.
- Raw run artifacts are private because `adb devices` and `/proc/cmdline` carry
  device identifiers.

Private run:

```text
workspace/private/runs/s22plus_p0_recon_20260706T152153Z
```

Collector:

```text
workspace/public/src/scripts/revalidation/s22plus_p0_recon_collect.py
```

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_p0_recon_collect.py

python3 workspace/public/src/scripts/revalidation/s22plus_p0_recon_collect.py
```

Result:

```text
target identity: SM-S906N / g0q / S906NKSS7FYG8
sys.boot_completed=1
verifiedbootstate=orange
flash_locked=0
warranty_bit=1
Magisk root: uid=0(root) gid=0(root) context=u:r:magisk:s0
```

## Current Boot-Surface Hashes

Read-only Android-side partition hashes:

```text
boot:
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e

vendor_boot:
096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7

recovery:
153373cd6c1efda2a9b57f91fac761ff92d515ae604cd3d22f97877759e51f18

vbmeta:
79edc1de4bf12853fc0cf9438efdd64f04e48241cab77137826fe1e1cc6f0b0e

vbmeta_system:
e7d35658dfbd9d82fdea803ceaba81801d328c0fc68158a032139b6d92756512
```

Interpretation:

- `boot` is the Magisk-patched boot image from the root checkpoint, not stock.
- `vendor_boot` still matches the pinned stock FYG8 image.
- The recovery/vbmeta full-partition hashes include trailing partition bytes;
  the prior checkpoint verified their payload prefixes as pinned TWRP and
  FYG8-disabled vbmeta.

## Shipped Kernel Config Facts

The collector pulled and decompressed the live `/proc/config.gz`.

Container/network primitives:

```text
CONFIG_CGROUPS=y
CONFIG_NAMESPACES=y
CONFIG_UTS_NS=y
CONFIG_USER_NS is not set
CONFIG_PID_NS is not set
CONFIG_NET_NS=y
CONFIG_SECCOMP=y
CONFIG_SECCOMP_FILTER=y
CONFIG_BRIDGE=y
CONFIG_WIREGUARD=y
CONFIG_TUN=y
CONFIG_VETH=y
CONFIG_OVERLAY_FS=y
CONFIG_SECURITY_SELINUX=y
CONFIG_SECURITY_APPARMOR is not set
```

Other selected config:

```text
CONFIG_MODULES=y
CONFIG_MODULE_UNLOAD=y
CONFIG_DEVTMPFS is not set
CONFIG_TMPFS=y
```

Samsung hardening/security features present:

```text
CONFIG_UH=y
CONFIG_RKP=y
CONFIG_KDP=y
CONFIG_SECURITY_DEFEX=y
CONFIG_FIVE=y
CONFIG_PROCA=y
```

Implication:

- The earlier generic-GKI assumption was only partly right. Stock S906N has the
  useful server primitives `overlay`, `veth`, `bridge`, `tun`, `WireGuard`,
  `netns`, `cgroups`, and `seccomp`.
- It does **not** have `USER_NS` or `PID_NS`. `IPC_NS` was not present in the
  live config text. Treat full Docker/LXC-style container isolation as not
  stock-proven.
- Path L is still useful for a rootful server/distro path, but stock-kernel
  containers are limited unless they can run without private PID/user namespace.
  Path R/custom kernel remains the route for full namespace support.

## Runtime Readiness Observations

Read-only runtime probes:

```text
/dev/net/tun: present
/proc/filesystems: overlay, cgroup, cgroup2, fuse, f2fs, erofs, pstore present
/proc/self/ns: mnt, net, uts, cgroup, time present
/proc/cgroups: cpuset, cpu, cpuacct, blkio, memory, freezer enabled
```

This supports a practical Stage-1 server path using stock Android-owned hardware
and root, but not a complete namespace container claim.

## Module / Hardware Bring-Up Map

Observed module inventory:

```text
module files under /vendor_dlkm/lib/modules: 356 .ko files
currently loaded modules from /proc/modules: 482 entries
modules.load/modules.dep captured with root read access
```

Important loaded/module-order anchors for native-init planning:

```text
USB/adb/gadget: dwc3-msm, usb_f_diag, usb_f_qdss, usb_f_ccid, usb_f_cdev,
usb_f_gsi, usb_f_conn_gadget, usb_f_ss_mon_gadget, usb_f_ss_acm

Wi-Fi: dhd, bcm4389, cfg80211, mac80211, icnss2, cnss2, cnss_utils,
wlan_firmware_service, cnss_plat_ipc_qmi_svc, cnss_nl, cnss_prealloc

GPU/display: msm_drm, msm_kgsl, gpucc-waipio, dispcc-waipio

Subsystems/remoteproc/QRTR: qcom_q6v5, qcom_q6v5_pas, adsp_loader_dlkm,
cdsp-loader, qrtr, qrtr-smd, qrtr-mhi, qrtr-gunyah, q6_dlkm,
q6_notifier_dlkm, q6_pdr_dlkm

Data path: ipa_fmwk, ipam, ipa_clientsm, ipanetm, rmnet_core, rmnet_ctl,
rmnet_offload, rmnet_perf, rmnet_wlan, mhi, mhi_cntrl_qcom
```

Implication for PID1 first-light:

- Do not expect A90-style built-in hardware availability. S22+ native-init must
  either preserve Android/Magisk init for first proof or reproduce enough module
  load and configfs/uevent behavior to get an observation channel.
- The current `modules.load` gives a useful order seed, but Android's actual
  loaded set is larger than the file list. The next module-map unit should
  derive a staged bring-up order from `modules.load`, `modules.dep`, and the
  live `/proc/modules` dependency column.

## P1 Direction

The previous chainload candidates were built before the final root/TWRP
checkpoint and did not provide a readable proof marker. Now the current boot
image is Magisk-patched and root survives Android boot, so the next host-only P1
unit should:

1. Dump or reuse the current Magisk-patched `boot` image into private storage.
2. Unpack its ramdisk and identify the Magisk `/init` chain.
3. Build a new first-light candidate that wraps the current Magisk `/init`
   rather than the stock `/init`, preserving rooted Android as the fallback
   observation environment.
4. Add a stronger readback channel for first-light proof, preferably one that
   rooted Android can observe after boot: root-readable file under `/data`,
   kmsg/dmesg marker, or pstore marker if available.
5. Stop before live boot flashing until a new SHA-pinned S22+ boot-only
   `AGENTS.md` exception is added for the exact candidate AP.

## Result

PASS: P0 read-only recon completed and produced concrete design inputs for the
S22+ native-init PID1 path.

The first-light milestone is not achieved yet. The next bounded unit is P1
host-only Magisk-boot-wrapper candidate construction and static validation; the
P2 flash boundary remains gated by a new SHA-pinned boot-only S22+ exception.
