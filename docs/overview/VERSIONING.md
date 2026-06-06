# Native Init Versioning

Updated: `2026-06-07`

This is the short reader-facing summary. The normative policy is
`docs/operations/VERSIONING_POLICY.md`.

## Axes

| Axis | Format | Meaning | Example |
| --- | --- | --- | --- |
| Run ID | `VNNNN` | project run/report/validation/promotion number | `V2169` |
| Native init version | `MAJOR.MINOR.PATCH` | device-visible native init build | `0.9.247` |
| Build tag | `vNNNN-purpose` | flashed boot/init baseline role | `v2169-wifi-lifecycle-baseline` |
| Helper version | `helper-vNNN` | helper binary marker stream | `a90_android_execns_probe helper-v427` |
| Artifact hash | `sha256:<hex>` | exact binary/evidence identity | boot image SHA256 |

## Rules

- Run IDs (`V2167`, `V2168`, `V2169`) are global project execution numbers.
- Native init versions (`0.9.246`, `0.9.247`) change only when the boot artifact
  that can be flashed changes.
- Build tags name the boot/init baseline and should not be confused with helper
  markers.
- Helper versions must be written with the `helper-` prefix in summaries:
  `helper-v427`, not bare `v427`.
- SHA256 is the final artifact identity. If the boot SHA changes and the image is
  promoted as a rollback/test baseline, give it a new run/build identity.

## Current Verified Example

```text
Native init: A90 Linux init 0.9.246 (v726-wifi-lifecycle)
Build tag: v726-wifi-lifecycle
Helper: a90_android_execns_probe helper-v427
Boot image: stage3/boot_linux_v726_wifi_lifecycle.img
Boot SHA256: 6b34aac93d4fa6d5b40355b9e13b2c1ae847c24a3685d84b0d1cd78751351d40
Evidence: V2167, V2168, and v726 baseline source/build/promotion reports
```

## Next Baseline Naming

The next promoted baseline after the `V2168` run stream should use a new global
run/build identity, not an unrelated helper number and not a recycled validation
run:

```text
Run ID: V2169
Native init: A90 Linux init 0.9.247
Build tag: v2169-wifi-lifecycle-baseline
Boot image: stage3/boot_linux_v2169_wifi_lifecycle_baseline.img
Helper: a90_android_execns_probe helper-v427
```

## Historical Note

Earlier project phases often used `vNNN` for both project cycles and boot image
build tags because most cycles produced a boot image. During Wi-Fi bring-up,
host-only classifiers and rollbackable test boots made these streams diverge.
Use the table above for current work.

## Local Artifact Retention

- Keep current verified baseline artifacts, previous rollback artifacts, and
  known-good fallback artifacts.
- Current cleanup defaults preserve `v48`, `v724`, `v725`, and `v726`.
- Cleanup tools are dry-run first:

```bash
python3 scripts/revalidation/cleanup_tmp_wifi_artifacts.py
python3 scripts/revalidation/cleanup_stage3_artifacts.py
```
