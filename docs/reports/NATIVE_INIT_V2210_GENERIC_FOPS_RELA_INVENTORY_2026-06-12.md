# Native Init V2210 Generic Fops RELA Inventory

## Decision

- Decision: `v2210-generic-fops-rela-inventory-built`
- Reason: Built high-confidence semantic inventory for 570 RELA-backed fops objects.
- Runtime RELA slide: `0x80000`
- Parsed fops initializers: `2675`
- High-confidence objects: `570`
- High-confidence semantic rows: `2055`

## Interpretation

- V2210 generalizes V2209 from the `/dev/null`/`/dev/zero` proof pair to every parsable `static const struct file_operations` initializer with enough label evidence.
- Promotion is intentionally strict: a fops object is high-confidence only when the source initializer fields, stock clone-base RELA slots, and rebuilt-ELF field labels all agree.
- The full private inventory keeps partial and failed candidates for later parser work; the report only promotes high-confidence rows.
- This is still a RELA-backed callback-table naming layer. It does not decode ROPP-protected call stacks.

## Status Counts

| Status | Objects |
| --- | --- |
| `high_confidence` | 570 |
| `missing_symbol` | 1709 |
| `no_stock_clone_base` | 25 |
| `partial_stock_rela` | 312 |
| `too_few_labelled_fields` | 59 |

## Clone Delta Counts

| Clone delta | High-confidence objects |
| --- | --- |
| `0x35b4` | 7 |
| `0xb27c` | 4 |
| `0x3f2c` | 4 |
| `0xcc` | 4 |
| `0xb254` | 4 |
| `0xad74` | 4 |
| `0x7ff4` | 3 |
| `-0x3b9c` | 3 |
| `-0x44cc` | 3 |
| `0x18304` | 3 |
| `0xd684` | 3 |
| `0x4ef4` | 2 |

## High-Confidence Examples

| Fops | Clone delta | Fields | Source | Sample semantics |
| --- | --- | --- | --- | --- |
| `socket_file_ops` | `-0xf4` | 12 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/net/socket.c | llseek→no_llseek, read_iter→sock_read_iter, write_iter→sock_write_iter, poll→sock_poll |
| `tun_fops` | `-0x127c` | 10 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/net/tun.c | llseek→no_llseek, read_iter→tun_chr_read_iter, write_iter→tun_chr_write_iter, poll→tun_chr_poll |
| `ovr_ops` | `0xb144` | 9 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/hid/hid-ovr.c | llseek→noop_llseek, read→ovr_hidraw_read, write→ovr_hidraw_write, poll→ovr_hidraw_poll |
| `tvr_ops` | `0xb044` | 9 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/hid/hid-tvr.c | llseek→noop_llseek, read→tvr_hidraw_read, write→tvr_hidraw_write, poll→tvr_hidraw_poll |
| `hidraw_ops` | `0xeaec` | 9 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/hid/hidraw.c | llseek→noop_llseek, read→hidraw_read, write→hidraw_write, poll→hidraw_poll |
| `evdev_fops` | `0x11e4c` | 9 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/input/evdev.c | llseek→no_llseek, read→evdev_read, write→evdev_write, poll→evdev_poll |
| `dvb_dvr_fops` | `0x4ef4` | 9 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/media/dvb-core/dmxdev.c | llseek→default_llseek, read→dvb_dvr_read, write→dvb_dvr_write, poll→dvb_dvr_poll |
| `v4l2_fops` | `0x99f4` | 9 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/media/v4l2-core/v4l2-dev.c | llseek→no_llseek, read→v4l2_read, write→v4l2_write, poll→v4l2_poll |
| `wdm_fops` | `0x186f4` | 9 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/usb/class/cdc-wdm.c | llseek→noop_llseek, read→wdm_read, write→wdm_write, poll→wdm_poll |
| `uinput_fops` | `0x105dc` | 8 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/input/misc/uinput.c | llseek→no_llseek, read→uinput_read, write→uinput_write, poll→uinput_poll |
| `dvb_demux_fops` | `0x55fc` | 8 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/media/dvb-core/dmxdev.c | llseek→default_llseek, read→dvb_demux_read, poll→dvb_demux_poll, unlocked_ioctl→dvb_demux_ioctl |
| `media_devnode_fops` | `0x9a14` | 8 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/media/media-devnode.c | llseek→no_llseek, read→media_read, write→media_write, poll→media_poll |
| `conn_gadget_fops` | `0x13dcc` | 8 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/usb/gadget/function/f_conn_gadget.c | read→conn_gadget_read, write→conn_gadget_write, poll→conn_gadget_poll, unlocked_ioctl→conn_gadget_ioctl |
| `auxdev_fops` | `0xff4c` | 7 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/gpu/drm/msm/dp/secdp_aux_control.c | llseek→auxdev_llseek, read→auxdev_read, write→auxdev_write, unlocked_ioctl→auxdev_ioctl |
| `dvb_ca_fops` | `0x49cc` | 7 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/media/dvb-core/dvb_ca_en50221.c | llseek→noop_llseek, read→dvb_ca_en50221_io_read, write→dvb_ca_en50221_io_write, poll→dvb_ca_en50221_io_poll |
| `rtc_dev_fops` | `0x1030f` | 7 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/rtc/rtc-dev.c | llseek→no_llseek, read→rtc_dev_read, poll→rtc_dev_poll, unlocked_ioctl→rtc_dev_ioctl |
| `glink_pkt_fops` | `-0x684c` | 7 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/soc/qcom/glink_pkt.c | read→glink_pkt_read, write→glink_pkt_write, poll→glink_pkt_poll, unlocked_ioctl→glink_pkt_ioctl |
| `f_cdev_fops` | `0x14324` | 7 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/usb/gadget/function/f_cdev.c | read→f_cdev_read, write→f_cdev_write, poll→f_cdev_poll, unlocked_ioctl→f_cdev_ioctl |
| `ffs_ep0_operations` | `0x15fcc` | 7 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/usb/gadget/function/f_fs.c | llseek→no_llseek, read→ffs_ep0_read, write→ffs_ep0_write, poll→ffs_ep0_poll |
| `gsi_ctrl_dev_fops` | `0x13f5c` | 7 | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/usb/gadget/function/f_gsi.c | read→gsi_ctrl_dev_read, write→gsi_ctrl_dev_write, poll→gsi_ctrl_dev_poll, unlocked_ioctl→gsi_ctrl_dev_ioctl |

## Anchors

- V2209 anchor decision: `v2209-fops-clone-semantic-map-built`
- Stock RELA run: `0xffffff800a714724` → `0xffffff800aace214` (`162763` entries)

## Next

- Use the private `inventory_rows` as a semantic lookup source for RELA-backed callback tables.
- Improve source parsing for macro-generated or non-static fops only if a needed object is missing from high-confidence inventory.
- Keep ROPP stack decoding as a separate V2211 path; V2210 supplies semantic names for table callbacks, not stack return-address recovery.

## Safety

- host_only: `true`
- live_device_access: `false`
- probe_write_user_executed: `false`
- cgroup_attach: `false`
- wifi_action: `false`
- flash_reboot: `false`

## Evidence

- Private result: `workspace/private/runs/kernel/v2210-generic-fops-rela-inventory/result.json`
- V2209 result: `workspace/private/runs/kernel/v2209-fops-clone-semantic-mapper/result.json`
- V2208 result: `workspace/private/runs/kernel/v2208-rela-fops-discriminator/result.json`
- Stock raw: `workspace/private/runs/kernel/v2197-stock-kallsyms/kernel.raw`
- Source root: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source`
