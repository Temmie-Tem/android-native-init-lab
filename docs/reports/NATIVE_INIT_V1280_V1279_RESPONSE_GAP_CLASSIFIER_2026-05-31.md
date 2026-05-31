# Native Init V1280 V1279 Response Gap Classifier

- generated: 2026-05-31
- cycle: V1280
- command: host-only
- decision: `v1280-pcie-gdsc-response-sampler-selected`
- pass: true

## Result

V1280 compared V1279 native evidence with existing Android positive references
and selected the next gate as a bounded PCIe/GDSC/RC1 response sampler.

| check | result |
| --- | --- |
| V1279 input | pass |
| native PM-service `/dev/subsys_esoc0` reached | pass |
| native TLMM range visible | pass (`0-174`) |
| native lower response | absent: no GPIO142 IRQ, PCI, MHI, MHI pipe, or `wlan0` |
| Android positive reference | pass |
| line-level GPIO values as next gate | rejected as hard precondition |
| next response gate | PCIe/GDSC/RC1 sampler |

Evidence:

- `tmp/wifi/v1280-v1279-response-gap-classifier/manifest.json`
- `tmp/wifi/v1280-v1279-response-gap-classifier/summary.md`

## Interpretation

V1279 closed the TLMM controller visibility question: the native path can see
the TLMM gpiochip range and GPIO135/GPIO142 pinmux ownership. The remaining
failure is still below the PM-service eSoC entry and before the Android-positive
PCIe/SDX50M response sequence.

Existing Android evidence proves readable GPIO135/GPIO142 snapshots and a
working Wi-Fi-positive chain, but it does not prove exact AP2MDM/MDM2AP
transition timing. Therefore line-level GPIO values should not be the next hard
precondition. The next live unit should instead capture whether PCIe RC1/GDSC
and relevant dmesg markers ever advance during the same bounded PM-service
window.

## Safety

Host-only classifier. No device command, deploy, PMIC write, GPIO request, eSoC
ioctl, Wi-Fi HAL, scan/connect, credential use, DHCP/route mutation, external
ping, flash, boot image write, or partition write occurred.

## Next

V1281 should add source/build support for a read-only PCIe/GDSC/dmesg response
sampler. The sampler should preserve the current bounded PM-service path and add
filtered evidence for PCIe RC1, GDSC/regulator, MHI, and SDX50M/ext-mdm dmesg
markers before any Wi-Fi HAL/connect attempt.
