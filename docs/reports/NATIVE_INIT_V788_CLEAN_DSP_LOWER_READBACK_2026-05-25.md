# Native Init V788 Clean-DSP Lower Readback Report

## Result

- decision: `v788-clean-dsp-lower-readback-blocked`
- pass: `false`
- runner: `scripts/revalidation/native_wifi_clean_dsp_lower_readback_v788.py`
- evidence: `tmp/wifi/v788-clean-dsp-lower-readback/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_clean_dsp_lower_readback_v788.py
python3 scripts/revalidation/native_wifi_clean_dsp_lower_readback_v788.py plan
python3 scripts/revalidation/native_wifi_clean_dsp_lower_readback_v788.py run \
  --assume-yes \
  --allow-arm-clean-dsp \
  --allow-reboot \
  --allow-cleanup-umount \
  --allow-system-mount \
  --allow-selinuxfs-mount \
  --allow-policy-load \
  --allow-firmware-mounts \
  --allow-subsys-modem-holder \
  --allow-cnss-start-only \
  --allow-cleanup-reboot
```

## Evidence Summary

| Signal | Result |
| --- | --- |
| stock build | `A90 Linux init 0.9.68 (v724)` |
| inline clean-DSP proof | pass |
| V401 SELinuxfs mount | pass |
| V490 policy load | pass |
| firmware mounts | executed |
| `subsys_modem` holder | opened |
| companion order | `qrtr-ns,rmt_storage,tftp_server,pd-mapper,cnss_diag,cnss-daemon` |
| `mss` | `OFFLINING -> ONLINE -> ONLINE` |
| `mdm3` | `OFFLINING -> OFFLINING -> OFFLINING` |
| QRTR RX/TX | `1 / 1` |
| `sysmon-qmi` | `4` |
| service-notifier markers | `2` |
| QRTR services `69/74/180` | `0 / 0 / 0` |
| MHI/QCA6390/WLFW/BDF/`wlan0` | `0 / 0 / 0 / 0 / 0` |
| warning boundary | `pm_qos_add_request` duplicate request |
| post-cleanup health | healthy v724 |

## Interpretation

V788 proves the clean-DSP precondition and current SELinux policy-load
precondition can be composed with the CNSS-only lower companion path. The run
reaches modem QRTR RX/TX, `sysmon-qmi`, and service-notifier markers, but still
does not publish WLFW service `69`, BDF, wiphy, or `wlan0`.

The run is blocked because the dmesg delta contains:

- `pm_qos_add_request() called for already added request`
- call trace through `msm_asoc_machine_probe`
- deferred probe work after ADSP/APR/audio service activity

Historical V733 and V735 evidence had `kernel_warning=0`, so this is a new
current-cycle safety boundary, not a harmless baseline line. The next gate must
not widen toward HAL/scan/connect. It should classify whether the warning is
caused by the clean-DSP + lower companion composition, CNSS-only addition,
service-notifier/audio deferred probe ordering, or the current V401/V490
runtime environment.

## Safety

- service-manager start: not executed
- Wi-Fi HAL start: not executed
- scan/connect: not executed
- credential use: not executed
- DHCP/routes/external ping: not executed
- boot image or partition write: not executed
- custom kernel flash: not executed
- cleanup reboot: executed and post-cleanup status is healthy

## Next

V789 should be host-only first: classify the V788 `pm_qos_add_request` warning
against V733/V735/V787 and current dmesg evidence, then choose the narrowest
safe live follow-up. A lower-only clean-DSP replay may be safer than repeating
CNSS-only, but it should be justified by the host-only warning classifier first.
