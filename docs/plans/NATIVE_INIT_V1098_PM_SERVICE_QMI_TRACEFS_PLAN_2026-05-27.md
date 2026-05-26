# Native Init V1098 PM Service QMI Tracefs Plan

## Goal

Replay the V1095 PM provider + `pm-proxy` + bounded `cnss-daemon` observer
window while arming tracefs-only dynamic uprobes on `/mnt/vendor/bin/pm-service`
PLT entries. V1097 proved Binder delivery into `pm-service`; V1098 classifies
whether `pm-service` then enters QMI register/send/handle paths that could move
the lower modem/eSoC state.

## Scope

- Reuse deployed `a90_android_execns_probe v206`.
- Keep V1095 as the predecessor gate.
- Mount tracefs and vendor read-only only for the bounded observation window.
- Register dynamic uprobes on `pm-service` PLT entries for:
  - `__android_log_print`
  - `property_set`
  - `get_system_info`
  - `qmi_csi_register_with_options`
  - `select`
  - `qmi_csi_handle_event`
  - `qmi_csi_send_resp`
  - `qmi_csi_send_ind`
  - `qmi_csi_unregister`

## Guardrails

- No BPF attach; this gate uses tracefs dynamic uprobes only.
- No `mdm_helper`.
- No Wi-Fi HAL, supplicant, hostapd, scan, connect, DHCP, route, credential use,
  or external ping.
- No `/dev/subsys_esoc0` open, eSoC ioctl, GPIO write, partition write, flash,
  or reboot.
- Tracefs events must be disabled and removed during cleanup.

## Success Criteria

- V1095 predecessor manifest is present and accepted.
- Remote helper sha/usage match `a90_android_execns_probe v206`.
- `/mnt/vendor/bin/pm-service` is visible from the read-only vendor mount.
- Tracefs registers/enables/removes all events cleanly.
- The child reaches the V1095 CNSS phase.
- QMI send/handle/register hits are counted separately from log/property hits.
- Wi-Fi HAL/start/connect/link-up/credential/DHCP/external ping remain false.

## Decision Rules

- `qmi_csi_send_ind` or `qmi_csi_send_resp` hits mean PM service sends a QMI
  response/indication but mdm3 still does not move; the next gate should
  classify QMI message semantics or lower eSoC trigger.
- QMI register/select/unregister hits without send/handle hits mean the QMI loop
  starts but receives no actionable request/response during the PM Binder
  window.
- Log/property hits without QMI hits mean PM service handles the Binder path but
  does not enter QMI at all.
