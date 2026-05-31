# V1266 Execns Helper v264 Deploy

## Result

- decision: `execns-helper-v264-deploy-pass`
- evidence: `tmp/wifi/v1266-execns-helper-v264-deploy/manifest.json`
- helper: `a90_android_execns_probe v264`
- helper SHA256: `a06ff29245023c265c69e58e2ae3f32a4facbc291bcb63a4450f39efd9515dc5`
- transfer: serial fallback, `1010` chunks, safe line check passed
- post-deploy direct SHA verification: passed
- post-deploy selftest: `fail=0`

## Scope

V1266 deployed only `/cache/bin/a90_android_execns_probe`.  It did not start
service-manager, CNSS, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
external ping.  It did not write boot images or partitions.

## Notes

- The first deploy attempt used `--serial-chunk-size 3000` and failed before
  writing any chunks because the generated cmdv1x line exceeded the native
  console line limit.
- The retry used `--serial-chunk-size 1800`; the line check passed and the
  helper was installed successfully.
- NCM was not active during this gate, so serial fallback was used.

## Next

V1267 should run the bounded read-only ext-mdm/AP2MDM observer with helper v264.
The live observer should use the existing late `per_proxy` / PM-service
`/dev/subsys_esoc0` response window and now parse the PMIC GPIO9
`gpiochip_lineinfo_*` fields from the same samples.
