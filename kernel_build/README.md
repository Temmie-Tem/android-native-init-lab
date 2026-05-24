# Kernel Source Staging

This directory is for local-only Samsung kernel source archives and extracted
source trees. Large archives and build outputs must stay untracked.

## Expected Package

- official source package: `SM-A908N_KOR_12_Opensource.zip`
- model: `SM-A908N`
- build version: `A908NKSU5EWA3`
- OSRC source upload id: `13272`

## Recommended Layout

```text
kernel_build/
  SM-A908N_KOR_12_Opensource.zip
  source/
    SM-A908N_KOR_12_Opensource/
```

After staging the archive or extracted tree, run:

```sh
python3 scripts/revalidation/native_wifi_source_staging_v760.py run
```

The verifier records evidence under `tmp/wifi/v760-source-staging/` and does
not patch source, build a kernel, write a boot image, or touch the device.
