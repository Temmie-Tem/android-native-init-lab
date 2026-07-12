# S22+ FYG8 R1 v3 / R2 v2 FX-8300 Clean Reproduction Runbook

Date: 2026-07-12 KST  
Remote: `<BUILD_HOST>`  
Workspace: `/home/temmie/a90-fyg8-build`  
Scope: host-only build; no image packaging, USB, device, or flash action

## Purpose

Re-close reproducible R1 and strict R2 after the exact-banner timestamp defect.
This run must preserve the existing `source/out` tree and historical
`outputs/r1-full-lto` evidence. It uses a separate `source-clean-final` tree.

## Tool Pins

| Tool | SHA256 |
|---|---|
| R1 v3 wrapper | `fa7570ea874f0d8c7147a975860a69b98e6fb96bdb92936803e2c13d856c8a6b` |
| R2 v2 auditor | `fe7afd6bfc7dbbff15d0c4217bf6d65f54aa4a772c3d970508714cf8da55883a` |
| canonical banner helper | `ab801d7ba988fd22f1c281aec930eaec1c25afcc9527b81b2bf57e5ad6cdd8aa` |
| source-overlay auditor | `61a07c07aea3df5000cf8bb45f874d73dde20ea7509184a419ce5f77760d2556` |

The wrapper must report `s22plus_fyg8_kernel_build_v3`; the auditor must report
`s22plus_fyg8_kernel_r2_audit_v2`.

## R2 Data Pins

| Input | SHA256 |
|---|---|
| stock kernel baseline | `3041f6a50c5ac77631c747dc3d21e5fd0ad68a520ffc9a2052b1c0b5976db092` |
| stock IKCONFIG | `99352a4f8db49814330c9d2c28038fafbbd1dadbe1fef3082c6d7e2614c2dbf1` |
| vendor ramdisk module manifest | `f18e692511f4f37387f916be9266bd6c744eac650fad3455d8fef139257dfc33` |
| vendor ramdisk symbol requirements | `9be63bf9d2086d0823cc2b87cc2412b34f3d44394444c0cb693a5b1edf5a6e86` |
| complete module layout | `89d97fd7215ca1e830a983de61779baa13d4ecba3573bc2778ba98c5c26bca3e` |
| vendor_dlkm-only symbol requirements | `870d7cf4d077c7bb98bfe42d5ef24b5765136a7166c4850b6031168ce78dd00e` |

## Authentication Blocker

At 2026-07-12 18:04 KST, the host answered SSH but rejected non-interactive
authentication. No password or key is stored in the repository. Establish one
attended password-authenticated shell or install an operator-approved SSH key;
do not store a password in a command, script, shell history, or evidence file.

## 1. Sync Current Host Tools

From the primary workstation, after authentication is available:

```bash
cd /home/temmie/dev/A90_5G_rooting
rsync -avR \
  AGENTS.md GOAL.md \
  workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_build.py \
  workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_r2_audit.py \
  workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_banner.py \
  workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_overlay_audit.py \
  workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/stock-baseline/stock-kernel-baseline.json \
  workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/stock-baseline/stock-ikconfig \
  docs/module-map/s22plus-fyg8/manifest.json \
  docs/module-map/s22plus-fyg8/symbol-crc-requirements.tsv \
  docs/module-map/s22plus-fyg8-super/layout-manifest.json \
  docs/module-map/s22plus-fyg8-super/vendor-dlkm-only-symbol-crc-requirements.tsv \
  <BUILD_HOST>:/home/temmie/a90-fyg8-build/
```

On the remote, verify every tool and R2 input before continuing:

```bash
cd /home/temmie/a90-fyg8-build
sha256sum --check --strict <<'EOF'
fa7570ea874f0d8c7147a975860a69b98e6fb96bdb92936803e2c13d856c8a6b  workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_build.py
fe7afd6bfc7dbbff15d0c4217bf6d65f54aa4a772c3d970508714cf8da55883a  workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_r2_audit.py
ab801d7ba988fd22f1c281aec930eaec1c25afcc9527b81b2bf57e5ad6cdd8aa  workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_banner.py
61a07c07aea3df5000cf8bb45f874d73dde20ea7509184a419ce5f77760d2556  workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_overlay_audit.py
3041f6a50c5ac77631c747dc3d21e5fd0ad68a520ffc9a2052b1c0b5976db092  workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/stock-baseline/stock-kernel-baseline.json
99352a4f8db49814330c9d2c28038fafbbd1dadbe1fef3082c6d7e2614c2dbf1  workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/stock-baseline/stock-ikconfig
f18e692511f4f37387f916be9266bd6c744eac650fad3455d8fef139257dfc33  docs/module-map/s22plus-fyg8/manifest.json
9be63bf9d2086d0823cc2b87cc2412b34f3d44394444c0cb693a5b1edf5a6e86  docs/module-map/s22plus-fyg8/symbol-crc-requirements.tsv
89d97fd7215ca1e830a983de61779baa13d4ecba3573bc2778ba98c5c26bca3e  docs/module-map/s22plus-fyg8-super/layout-manifest.json
870d7cf4d077c7bb98bfe42d5ef24b5765136a7166c4850b6031168ce78dd00e  docs/module-map/s22plus-fyg8-super/vendor-dlkm-only-symbol-crc-requirements.tsv
EOF
```

Any missing file or hash mismatch stops before source reconstruction or build.

## 2. Preserve Historical Output

Do not remove or rename `source/out` in this run. Before reconstruction:

```bash
cd /home/temmie/a90-fyg8-build
test -d source/out
test -f outputs/r1-full-lto/result.json
test -f workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/stock-baseline/stock-kernel-baseline.json
test -f workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/stock-baseline/stock-ikconfig
test ! -e source-clean-final
test ! -e outputs/r1-clean-final
test ! -e outputs/r2-clean-final
```

Any failed `test` stops. Existing clean-final paths require an explicit audit,
not automatic deletion.

## 3. Reconstruct A Separate Source Tree

```bash
cd /home/temmie/a90-fyg8-build
mkdir source-clean-final
tar -xzf workspace/private/inputs/s22plus_kernel_source/SM-S906N_15_base_osrc/Kernel.tar.gz \
  -C source-clean-final
tar -xzf workspace/private/inputs/s22plus_kernel_source/S906NKSS7FYG8_osrc/S906NKSS7FYG8_kernel.tar.gz \
  --strip-components=1 -C source-clean-final
```

Copy only the already pinned, Git-clean tool repositories from the historical
source tree into the new tree. Removal below is confined to the new
reconstruction:

```bash
cd /home/temmie/a90-fyg8-build
for rel in \
  kernel_platform/prebuilts/build-tools \
  kernel_platform/prebuilts/gcc/linux-x86/host/x86_64-linux-glibc2.17-4.8 \
  kernel_platform/prebuilts/kernel-build-tools
do
  rm -rf "source-clean-final/$rel"
  mkdir -p "source-clean-final/$(dirname "$rel")"
  cp -a --reflink=auto "source/$rel" "source-clean-final/$rel"
done

mkdir -p source-clean-final/kernel_platform/prebuilts-master/clang/host/linux-x86
rm -f source-clean-final/kernel_platform/prebuilts-master/clang/host/linux-x86/clang-r416183b
ln -s /home/temmie/a90-fyg8-build/toolchains/aosp-clang-android12-release/clang-r416183b \
  source-clean-final/kernel_platform/prebuilts-master/clang/host/linux-x86/clang-r416183b
```

The wrapper's source-overlay audit must still report all 166,037 members exact.
Tool-repository extras and the clang symlink are separately commit/hash gated.

## 4. Preflight

```bash
cd /home/temmie/a90-fyg8-build
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_build.py \
  --mode preflight \
  --lto full \
  --jobs 8 \
  --work-tree source-clean-final \
  --clang-repo toolchains/aosp-clang-android12-release \
  --stock-baseline workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/stock-baseline/stock-kernel-baseline.json \
  --result-dir outputs/r1-clean-final
```

Require schema v3, `build_allowed=true`, source-overlay and timestamp-control
PASS, exact clean tool repositories, at least 30 GiB physical RAM, and the disk
gate.

## 5. Full-LTO R1 v3

Run under a detached session so an SSH disconnect does not terminate the build:

```bash
cd /home/temmie/a90-fyg8-build
tmux new-session -d -s fyg8-r1v3-clean \
  "cd /home/temmie/a90-fyg8-build && \
   PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
   python3 workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_build.py \
     --mode build --lto full --jobs 8 \
     --work-tree source-clean-final \
     --clang-repo toolchains/aosp-clang-android12-release \
     --stock-baseline workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/stock-baseline/stock-kernel-baseline.json \
     --result-dir outputs/r1-clean-final \
   > outputs/r1-clean-final/runner.stdout 2> outputs/r1-clean-final/runner.stderr; \
   printf '%s\n' \$? > outputs/r1-clean-final/runner.rc"
```

The wrapper writes `/usr/bin/time -v` evidence. Do not launch another build in
the same output tree.

R1 v3 PASS requires zero return, eight required outputs, nonzero generated
modules, both provider closures, restored timestamp-control source, and the
exact stock kernel-banner gate.

## 6. R2 v2

Only after R1 v3 PASS:

```bash
cd /home/temmie/a90-fyg8-build
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_r2_audit.py \
  --mode r2 \
  --work-tree source-clean-final \
  --stock-baseline workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/stock-baseline/stock-kernel-baseline.json \
  --stock-config workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/stock-baseline/stock-ikconfig \
  --r1-result outputs/r1-clean-final/result.json \
  --out outputs/r2-clean-final/result.json
```

Require exact banner equality, Full-LTO config, 25,864 requirement rows, zero
missing/mismatched/conflicting CRCs, complete 491-module corpus declaration,
and boot-capacity PASS.

## 7. Return Evidence

First return the small records and logs, then the approximately 69.5 MB
operational artifact set. Preserve all 15 symvers path identities even when
their byte hashes duplicate.

Do not compare whole R1/R2 JSON SHA across work-tree names. Compare schemas,
gates, relative output paths, sizes, hashes, generated-module identities,
symvers identities, provider closure, exact banner, config delta, and CRC
closure. Live disk values and absolute paths are expected to differ.

## Stop Rules

- No device, USB, ADB, Odin, image repack, AP generation, or flash.
- No deletion of historical `source/out` or `outputs/r1-full-lto`.
- No R2 execution after any R1 v3 failure.
- No R3 artifact implementation until returned R1 v3/R2 v2 evidence is
  independently audited and the roadmap is explicitly re-closed.
