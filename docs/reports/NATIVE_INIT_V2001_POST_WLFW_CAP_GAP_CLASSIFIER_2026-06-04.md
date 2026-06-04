# Native Init V2001 Post-WLFW-Cap Gap Classifier

## Summary

- Cycle: `V2001`
- Type: host-only classifier over V2000 rollback-verified evidence plus `cnss-daemon` disassembly
- Decision: `v2001-post-wlfw-cap-no-bdf-no-firmware-request-pass`
- Label: `post-wlfw-cap-no-bdf-no-firmware-request`
- Result: `PASS`
- Reason: V2000 reached WLFW ind-register, firmware-memory wait, and capability QMI send, but no BDF/FW-ready/wlan0 or wlanmdsp request/load followed
- Evidence: `tmp/wifi/v2001-post-wlfw-cap-gap-classifier`
- Source: `docs/reports/NATIVE_INIT_V2000_DOWNSTREAM_CASCADE_HANDOFF_2026-06-04.md`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | post-wlfw-cap-no-bdf-no-firmware-request | V2000 reached WLFW ind-register, firmware-memory wait, and capability QMI send, but no BDF/FW-ready/wlan0 or wlanmdsp request/load followed |
| source | True | v2000-native-downstream-cascade-wlan-pd-up-no-wlanmdsp-token-no-wlfw69-rollback-pass |
| cascade |  | wlan_pd=1 icnss_qmi=1 bdf=0 fw_ready=0 wlan0=0 |
| firmware | False | requested_any=0 wlanmdsp_tftp=0 pd_load=0 |
| ipc | 1 | service69_text=0 first=[     7.937174242/        0x1dfef0ee] icnss: PM stay awake, state: 0x180, count: 1 |
| labels |  | nonlog=wlfw-worker-thread-started-qmi-cap-sent libqmi=qmi-client-init-instance-returned service_window=modem-holder-regression |
| timing |  | thread=637 up=7.934782 wait_ret=7.937322 instance_ret=7.937538 client_ret=7.939331 init_ret=7.939362 ind=7.940815 fw_mem_wait=7.941636 cap=7.944563 |

## WLFW Events

| event | hits | first |
| --- | --- | --- |
| wlfw_start | 1 | cnss-daemon-626   [002] ....     6.775904: wlfw_start: (0x557119fc00) |
| wlfw_service_request | 1 | cnss-daemon-637   [002] ....     6.782734: wlfw_service_request: (0x557119e9fc) |
| wlfw_worker_pthread_create_success | 1 | cnss-daemon-626   [002] ....     6.781442: wlfw_worker_pthread_create_success: (0x557119fda0) |
| wlfw_client_init_instance_call | 1 | cnss-daemon-637   [002] ....     6.782799: wlfw_client_init_instance_call: (0x557119eaa8) arg0=0x55711a7f90 arg1=0xffff arg2=0x557119f100 arg3=0x0 |
| wlfw_client_init_instance_retcheck | 1 | cnss-daemon-637   [002] ....     7.939362: wlfw_client_init_instance_retcheck: (0x557119eaac) rc=0x0 |
| wlfw_send_ind_register_entry | 1 | cnss-daemon-637   [002] ....     7.940780: wlfw_send_ind_register_entry: (0x55711a0268) |
| wlfw_ind_register_qmi | 1 | cnss-daemon-637   [002] ....     7.940815: wlfw_ind_register_qmi: (0x55711a032c) |
| wlfw_fw_mem_cond_wait | 1 | cnss-daemon-637   [001] ....     7.941636: wlfw_fw_mem_cond_wait: (0x557119ec18) |
| wlfw_cap_qmi | 1 | cnss-daemon-637   [001] ....     7.944563: wlfw_cap_qmi: (0x55711a0460) |

## Libqmi Events

| event | hits | first |
| --- | --- | --- |
| libqmi_get_service_list_lookup_call | 11 | cnss-daemon-637   [002] ....     6.782825: libqmi_get_service_list_lookup_call: (0x7faba31eec) xport=0x0 xport_id=0x0 svc_id=0x45 idl_version=0x1 capacity_ptr=0x7f22d5799c list_ptr=0x7f22d57ae0 lookup_fn=0x7faba35a30 |
| libqmi_get_service_list_lookup_ret | 11 | cnss-daemon-637   [002] ....     6.783906: libqmi_get_service_list_lookup_ret: (0x7faba31ef0) found=0x0 list=0x7f22d57ae0 capacity_ptr=0x7f22d57a14 count_ptr=0x7f22d57a10 offset=0x0 xport_index=0x0 |
| libqmi_wait_return | 2 | cnss-daemon-636   [003] ....     7.753097: libqmi_wait_return: (0x7faba33908) |
| libqmi_loop_get_service_instance_ret | 4 | cnss-daemon-637   [002] ....     6.785619: libqmi_loop_get_service_instance_ret: (0x7faba33924) rc=0xfffffffe |
| libqmi_loop_client_init_ret | 2 | cnss-daemon-636   [003] ....     7.756290: libqmi_loop_client_init_ret: (0x7faba33944) rc=0x0 |
| libqmi_init_return | 2 | cnss-daemon-636   [003] ....     7.756310: libqmi_init_return: (0x7faba33970) rc=0x0 |
| libqmi_xport_new_server_service |  |  |
| libqmi_xport_new_server_signal |  |  |

## Next Live Probe Contract

| probe | offset | fetch | meaning |
| --- | --- | --- | --- |
| wlfw_fw_mem_wait_return | 0xdc1c | none | pthread_cond_wait returned before the capability-send call path |
| wlfw_cap_send_ret | 0xf464 | send_rc=%x0 | qmi_client_send_msg_sync returned from the WLFW capability request |
| wlfw_cap_send_or_result_error_branch | 0xf470 | send_rc=%x0 | send rc or QMI result was nonzero after the capability request |
| wlfw_cap_invalid_0x77_branch | 0xf49c | reason_reg=%x8 | capability response hit the 0x77 special failure branch |
| wlfw_cap_success_branch | 0xf4b4 | none | send rc and QMI result were both zero |
| wlfw_cap_rsp_result_error_branch | 0xf564 | qmi_result=%x8 | capability response QMI result error branch |
| wlfw_cap_return | 0xf580 | rc=%x19 | final return from the capability-request helper |

## Static Evidence

- `cnss-daemon`: `tmp/wifi/v222-vendor-root-evidence-export/vendor-root/bin/cnss-daemon`
- SHA256: `bced9853a77cfb02252571196584efa535be14f8f3fd9ce32712ddee224ba4bc`
- The next unit should add only the branch probes above to the existing light V1999/V2000 route; no tftp ptrace, QRTR matrix, strace, HAL, scan/connect, or eSoC/PCIe/GDSC path is needed.

### Firmware-Memory Wait Window

```
    /home/temmie/dev/A90_5G_rooting/tmp/wifi/v222-vendor-root-evidence-export/vendor-root/bin/cnss-daemon:     file format elf64-littleaarch64
    Disassembly of section .text:
    000000000000dbf0 <.text+0x4bf0>:
        dbf0:	aa1303e0 	mov	x0, x19
        dbf4:	940019cf 	bl	14330 <pthread_mutex_lock@plt>
        dbf8:	3940e2e8 	ldrb	w8, [x23, #56]
        dbfc:	37080108 	tbnz	w8, #1, dc1c <__libc_init@plt-0x6214>
        dc00:	f0ffffa1 	adrp	x1, 4000 <__libc_init@plt-0xfe30>
        dc04:	91350c21 	add	x1, x1, #0xd43
        dc08:	52800080 	mov	w0, #0x4                   	// #4
        dc0c:	97fff184 	bl	a21c <__libc_init@plt-0x9c14>
        dc10:	910412e0 	add	x0, x23, #0x104
        dc14:	aa1303e1 	mov	x1, x19
        dc18:	940019de 	bl	14390 <pthread_cond_wait@plt>
        dc1c:	aa1303e0 	mov	x0, x19
        dc20:	940019cc 	bl	14350 <pthread_mutex_unlock@plt>
        dc24:	940005ec 	bl	f3d4 <__libc_init@plt-0x4a5c>
        dc28:	2a0003f3 	mov	w19, w0
        dc2c:	34000080 	cbz	w0, dc3c <__libc_init@plt-0x61f4>
```

### Capability Send Window

```
    /home/temmie/dev/A90_5G_rooting/tmp/wifi/v222-vendor-root-evidence-export/vendor-root/bin/cnss-daemon:     file format elf64-littleaarch64
    Disassembly of section .text:
    000000000000f450 <.text+0x6450>:
        f450:	ad0383e0 	stp	q0, q0, [sp, #112]
        f454:	ad0283e0 	stp	q0, q0, [sp, #80]
        f458:	ad0183e0 	stp	q0, q0, [sp, #48]
        f45c:	ad0083e0 	stp	q0, q0, [sp, #16]
        f460:	9400132c 	bl	14110 <qmi_client_send_msg_sync@plt>
        f464:	294217e4 	ldp	w4, w5, [sp, #16]
        f468:	2a040008 	orr	w8, w0, w4
        f46c:	34000248 	cbz	w8, f4b4 <__libc_init@plt-0x497c>
        f470:	2a0003f3 	mov	w19, w0
        f474:	f0ffffa1 	adrp	x1, 6000 <__libc_init@plt-0xde30>
        f478:	90ffffc2 	adrp	x2, 7000 <__libc_init@plt-0xce30>
        f47c:	913b2c21 	add	x1, x1, #0xecb
        f480:	9107bc42 	add	x2, x2, #0x1ef
        f484:	52800020 	mov	w0, #0x1                   	// #1
        f488:	2a1303e3 	mov	w3, w19
        f48c:	97ffeb64 	bl	a21c <__libc_init@plt-0x9c14>
        f490:	b94017e8 	ldr	w8, [sp, #20]
        f494:	7101dd1f 	cmp	w8, #0x77
        f498:	54000641 	b.ne	f560 <__libc_init@plt-0x48d0>  // b.any
        f49c:	90ffffa1 	adrp	x1, 3000 <__libc_init@plt-0x10e30>
        f4a0:	913bd021 	add	x1, x1, #0xef4
        f4a4:	52800020 	mov	w0, #0x1                   	// #1
        f4a8:	97ffeb5d 	bl	a21c <__libc_init@plt-0x9c14>
        f4ac:	12800153 	mov	w19, #0xfffffff5            	// #-11
        f4b0:	14000030 	b	f570 <__libc_init@plt-0x48c0>
        f4b4:	f0ffffa1 	adrp	x1, 6000 <__libc_init@plt-0xde30>
        f4b8:	90ffffc2 	adrp	x2, 7000 <__libc_init@plt-0xce30>
        f4bc:	913f2421 	add	x1, x1, #0xfc9
        f4c0:	9107bc42 	add	x2, x2, #0x1ef
        f4c4:	52800080 	mov	w0, #0x4                   	// #4
        f4c8:	2a1f03e3 	mov	w3, wzr
        f4cc:	2a0503e4 	mov	w4, w5
        f4d0:	97ffeb53 	bl	a21c <__libc_init@plt-0x9c14>
        f4d4:	394063e8 	ldrb	w8, [sp, #24]
        f4d8:	34000068 	cbz	w8, f4e4 <__libc_init@plt-0x494c>
        f4dc:	f841c3e8 	ldur	x8, [sp, #28]
        f4e0:	f900e2a8 	str	x8, [x21, #448]
        f4e4:	394093e8 	ldrb	w8, [sp, #36]
        f4e8:	b9402be9 	ldr	w9, [sp, #40]
        f4ec:	3940b3ea 	ldrb	w10, [sp, #44]
        f4f0:	7100011f 	cmp	w8, #0x0
        f4f4:	52801fe8 	mov	w8, #0xff                  	// #255
        f4f8:	1a890105 	csel	w5, w8, w9, eq	// eq = none
        f4fc:	b901caa5 	str	w5, [x21, #456]
        f500:	3400006a 	cbz	w10, f50c <__libc_init@plt-0x4924>
        f504:	b94033e8 	ldr	w8, [sp, #48]
        f508:	b901cea8 	str	w8, [x21, #460]
        f50c:	3940d3e8 	ldrb	w8, [sp, #52]
        f510:	340000c8 	cbz	w8, f528 <__libc_init@plt-0x4908>
        f514:	3cc383e0 	ldur	q0, [sp, #56]
        f518:	3cc483e1 	ldur	q1, [sp, #72]
        f51c:	f9402fe8 	ldr	x8, [sp, #88]
        f520:	ad0e86a0 	stp	q0, q1, [x21, #464]
        f524:	f900faa8 	str	x8, [x21, #496]
        f528:	b941c2a3 	ldr	w3, [x21, #448]
        f52c:	b941c6a4 	ldr	w4, [x21, #452]
        f530:	b941cea6 	ldr	w6, [x21, #460]
        f534:	b941d2a7 	ldr	w7, [x21, #464]
        f538:	b0ffffa1 	adrp	x1, 4000 <__libc_init@plt-0xfe30>
        f53c:	90ffffc2 	adrp	x2, 7000 <__libc_init@plt-0xce30>
        f540:	910752a8 	add	x8, x21, #0x1d4
        f544:	91188421 	add	x1, x1, #0x621
        f548:	9107bc42 	add	x2, x2, #0x1ef
        f54c:	52800060 	mov	w0, #0x3                   	// #3
        f550:	f90003e8 	str	x8, [sp]
        f554:	97ffeb32 	bl	a21c <__libc_init@plt-0x9c14>
        f558:	2a1f03f3 	mov	w19, wzr
        f55c:	14000005 	b	f570 <__libc_init@plt-0x48c0>
        f560:	b94013e8 	ldr	w8, [sp, #16]
        f564:	34000068 	cbz	w8, f570 <__libc_init@plt-0x48c0>
        f568:	6b0803f3 	negs	w19, w8
        f56c:	54000186 	b.vs	f59c <__libc_init@plt-0x4894>
        f570:	f9401688 	ldr	x8, [x20, #40]
        f574:	f85f83a9 	ldur	x9, [x29, #-8]
        f578:	eb09011f 	cmp	x8, x9
        f57c:	540000e1 	b.ne	f598 <__libc_init@plt-0x4898>  // b.any
        f580:	2a1303e0 	mov	w0, w19
```

## Safety Scope

- Host-only: no live device command, flash, reboot, service start, or filesystem mutation was performed.
- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.
- No `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator write, forced RC1/case, or fake ONLINE action was used.
