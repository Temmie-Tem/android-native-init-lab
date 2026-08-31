# S20+ G986N TWRP port T1 H0 build record

Date: 2026-08-31
Target: Samsung Galaxy S20+ 5G `SM-G986N` / `y2q` / `y2qksx`
Exact stock substrate: `G986NKSS8IYC2`
Tier: H0 host-only binary-donor port and static validation
Result: **PASS_TWRP_PORT_T1_HOST_BUILT_REVIEW_PENDING**

## Outcome

An exact AstroForge V2 `y2q` TWRP ramdisk was ported onto the exact IYC2 stock
recovery substrate. The output retains the stock recovery header, raw kernel,
DTB, recovery DTBO, partition size, and stock AVB footer; only the ramdisk comes
from TWRP and receives a closed five-entry safety delta.

This is a port candidate, not a direct promotion of the downloaded image. The
donor kernel, DTB, recovery DTBO, header, and AVB key are not used. Donor source
reproduction remains unproved and is recorded as such.

No ADB, USB, `su`, reboot, Download, Odin, device, or partition command was
issued. S22+, A90, and every other target received zero commands. No live
recovery-write authority exists.

## Exact inputs

### IYC2 stock substrate

| Component | Size | SHA-256 |
|---|---:|---|
| stock `recovery.img` | 82,694,144 | `dd797bc0a462d2486ff71c020e89d1137df46299374e48855012e36e86f97e0e` |
| header | 373 | `1f948cfa15174ab850d66c2600654aacece5f7c2a5cd871f1b30db153d3baff3` |
| kernel | 51,959,820 | `127d0f43de5e5e5ce5eee9e496b9593cf6ce7f0ce97581ad483e8f76feeb31ca` |
| DTB | 1,580,275 | `09ce85eab63208c985486bba8b450d17fd5907839361b53bf1971e0eeaceb883` |
| recovery DTBO | 1,034,509 | `11e0da1564c1e2bbbccfa13f41ceaa105135586a443646980baa421b00137455` |

### TWRP binary donor

The donor is the byte-pinned
[AstroForge V2 release image](https://github.com/AstroByteX-Code/android_device_samsung_y2q/releases/tag/AstroForge-V2):

- file: `Twrp_3.7.1_12-AstroForge-V2_y2q.img`;
- size: 82,694,144 bytes;
- SHA-256:
  `41d922d2c812256703981c3ce24ea467888d567a7e6c708670632af535787b0d`;
- embedded TWRP version string: `3.7.1_12-AstroForge_v2`;
- donor ramdisk CPIO: 71,193,344 bytes, SHA-256
  `0a84bf889e04ec97c896daa6de8074ff3cffad8e8cb836fef0ccfd5a0353e07b`.

The donor was copied into the exact-target private input tree mode `0400`.
The release digest proves downloaded-byte identity only. Authorship, complete
source provenance, and source reproduction remain unproved.

## Port construction

| Recovery component | T1 source | Treatment |
|---|---|---|
| header and command line | exact IYC2 stock | byte-identical |
| kernel | exact IYC2 stock `4.19.113-27166950` | byte-identical |
| DTB | exact IYC2 stock | byte-identical |
| recovery DTBO | exact IYC2 stock | byte-identical |
| ramdisk | AstroForge V2 donor | four replacements plus one marker |
| AVB footer | exact IYC2 stock | embedded signature retained; hash descriptor expected to fail changed image |

The stock-substrate choice avoids relying on the donor's different compressed
`4.19.325-AstroForge` kernel, different DTB, and different recovery DTBO. Static
compatibility is stronger, but runtime compatibility between the IYC2 stock
kernel and Android-12 TWRP userland remains unproved until a later live test.

## Closed ramdisk delta

The donor contains 3,685 entries. T1 contains 3,686. It removes none, changes
exactly four, adds exactly one, and retains every other entry byte-for-byte and
mode-for-mode.

### 1. Inert stock-recovery deletion hook

`system/bin/postrecoveryboot.sh` was replaced by a 94-byte mode-`0755` script
that only documents the policy and exits zero. It no longer remounts vendor,
removes `install-recovery.sh`, removes `vendor_flash_recovery.rc`, or removes
`recovery-from-boot.p`.

### 2. Read-only first-boot device mounts

`init.recovery.qcom.rc` keeps the exact persist and EFS paths but changes both
automatic mounts from read-write to `ro,noload,nosuid,nodev,noexec`. The final
`noload` is passed as the ext4 filesystem option under the
[AOSP init mount grammar](https://android.googlesource.com/platform/system/core/%2Bshow/0bfa1c8b3c19146405372d0cfb527b66ee75d433/init/README.md),
preventing the read-only-mount journal replay described by the
[Linux kernel ext4 documentation](https://www.kernel.org/doc/html/v5.1/admin-guide/ext4.html).
The APNHLOS firmware mount is
`ro,nosuid,nodev,noexec`. The health HAL still starts for recovery UI battery
state.

The automatic `/data/vendor/keymaster` directory creation and automatic starts
of keymaster, `spdaemon`, and `sec_nvm` are disabled. Consequently T1 makes no
claim that encrypted `/data` can be decrypted. `/data` support is a later,
separately observed unit; it is not required to establish TWRP UI and ADB.

### 3. Reduced TWRP partition UI

`system/etc/twrp.flags` was replaced by a 704-byte mode-`0644` definition.
It exposes exactly one `flashimg=1` surface: `boot`. It retains cache, MicroSD,
USB-OTG, and hidden misc definitions. It removes persist, recovery,
modem, dynamic-partition image, EFS/Sec EFS, OMR/optics/prism, DTBO, FRP, and
Samsung VBMeta flash/wipe/backup UI rows. Removable-storage wipe UI flags are
also absent.

The general TWRP terminal is still intrinsically privileged. Its existence is
not runner authority and it is outside the first T1 live observation sequence.

### 4. ADB-only first-boot USB

`init.recovery.usb.rc` was replaced by a mode-`0750` first-boot profile that
creates only `ffs.adb`. It creates no MTP or fastboot FunctionFS endpoint and
never starts fastbootd. Initial boot sets `sys.usb.config=adb`; MTP, sideload,
or fastboot property requests are redirected to the same ADB-only surface.
This is a bring-up constraint, not a permanent claim that later recovery builds
can never add independently reviewed transports.

### 5. Fixed marker

Mode-`0444` marker `/init.s20plus_g986n_twrp_port_t1` was added:

- size: 355 bytes;
- SHA-256:
  `9e772d73d58740e09abe7f75f30e99c66cda04547287189d859ed457b9c2c6c5`.

The donor recovery executable, TWRP CLI, properties, and `recovery.fstab` are
unchanged. USB init is the intentional ADB-only replacement above. The 89-byte
`rebootsystem.sh` is also unchanged
at SHA-256
`3c3058563bbe775505fb5c0be8b94ae4a5e44787b5971ca17fd49e599ae7dd07`,
identical to the A90-bound hook. It remains **inactive on S20+**: no S20+
exception or invocation is granted by retaining its bytes.

## Output artifacts

Private output:
`workspace/private/outputs/s20plus_g986n/twrp_port_t1_v1/`

| Artifact | Size | SHA-256 |
|---|---:|---|
| candidate `recovery.img` | 82,694,144 | `48406883b1f631c4dfa1b157708f2e320e70b744967024bad6cb50b08cd06cb2` |
| candidate `recovery.img.lz4` | 52,100,173 | `f4ccd3fbcd683b5597cf20b028b1230cfb0dd8f4f3c93d3db27c5314834ace7a` |
| candidate recovery-only `AP.tar.md5` | 52,111,401 | `3ed8498243ff09399ffd93fa3b0e90044a3cfe1709b7204dac53fe190647260f` |
| exact-stock rollback `recovery.img` | 82,694,144 | `dd797bc0a462d2486ff71c020e89d1137df46299374e48855012e36e86f97e0e` |
| rollback `recovery.img.lz4` | 36,600,544 | `6b962af2fc4fcc424d16ecdcee1793bdd6d4c8dba2e80d35cb21961fcb865923` |
| rollback recovery-only `AP.tar.md5` | 36,608,041 | `ac9745b642c7fbd950d988671f707e47d58f8e2092464b27a37bede2267d7157` |
| manifest | 9,703 | `c5901e75a81997c9ab7b7b964710c166c7a9650dfee8fcf92de637269ac19019` |

Both AP archives contain exactly one regular member named
`recovery.img.lz4` and have valid appended MD5 trailers. Neither contains
VBMeta or another partition payload.

## Validation

The fixed builder is 25,415 bytes at SHA-256
`300bd7f136dcb952db6ce7b1da2d4ce7ae382734b9f566f92e9ab6397f2aa3e7`.
The focused test source is 11,679 bytes at SHA-256
`d12d41f331329664f97a639841d58672302a1bbff5d3e0ee617979a26358812a`.

The focused corpus passes 14/14 and covers:

- frozen builder and output identities;
- exact donor image and critical-entry identities;
- exact stock substrate and donor-ramdisk-only component selection;
- closed four-replacement/one-addition ramdisk delta;
- neutralized vendor deletion, data mkdir, crypto-service autostart, and RW
  EFS/persist mounts;
- ext4 `noload` and ADB-only first-boot USB with no MTP/fastbootd endpoint;
- exactly one boot-only TWRP `flashimg` UI surface;
- preserved TWRP binary/version and recovery fstab, ADB-only replacement USB
  init, and A90-identical reboot helper;
- recovery-only candidate and rollback AP membership and MD5;
- exact stock AVB PASS and expected candidate recovery-hash mismatch;
- two complete independent builds with byte-identical outputs;
- hostile base/flags/output-reuse rejection; and
- absence of connected or flash command invocation in the builder.

The first reproducibility attempt used `/tmp` and stopped while extracting the
second 3,686-entry tree with that tmpfs near capacity. The retained output did
not include the final low-level error text, so the exact failure cause is not
promoted beyond that observation. Re-running under the repository's private
test workspace completed; all independently built hashes were already
identical before that repair.

## Claim boundary and next gate

This H0 result proves deterministic construction and the stated static delta.
It does not prove:

- boot-chain acceptance;
- display, touch, ADB, MicroSD, or USB-OTG operation; MTP and fastbootd are
  intentionally absent from this first-boot candidate;
- TWRP UI stability;
- encrypted or unencrypted `/data` mounting;
- safe use of the TWRP terminal or retained reboot helper;
- a demonstrated recovery-partition rollback; or
- live recovery-write authority.

T0 remains the first live rung because it tests custom-recovery acceptance with
the smallest possible ramdisk delta. T1 must not be transferred before T0
passes and the separate recovery-only contract/process, runner, journal,
rollback, observer, and independent review are activated. A T1 first boot must
use only fixed read-only identity/UI/ADB observations and return through the
prebound exact-stock recovery path; it must not invoke `Reboot -> System`,
mount or format `/data`, flash boot, or open a general terminal.
