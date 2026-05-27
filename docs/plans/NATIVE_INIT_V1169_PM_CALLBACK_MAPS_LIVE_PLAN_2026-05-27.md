# Native Init V1169 PM-Service Callback Maps Live Plan

Date: `2026-05-27`

## Goal

Map the V1168 callback pointer `0x7f9a0eca5c` while `pm-service` is still
alive.  V1168 captured the callback branch but its maps capture ran after the
child gate exited, so the maps section was empty.

## Change

Reuse the V1168 callback probes and move `/proc/<pm-service-pid>/maps` capture
into the same live sampling loop that already captures thread state.

## Added Evidence

- `pm_service_maps_sample_begin index=N`
- `pm_service_maps_sample_pid index=N pid=<pid>`
- `/proc/<pid>/maps` lines for samples where `pm-service` exists
- `pm_callback_dispatch.unique_mapped_callbacks`

## Success Criteria

- Manifest decision is `v1169-callback-target-mapped-no-esoc0` or
  `v1169-callback-target-unmapped`.
- `pm_callback_dispatch.callback_branch_seen == true`.
- `pm_callback_dispatch.maps_samples_with_entries > 0`.
- Cleanup returns to native v724 health.
- No Wi-Fi HAL, scan/connect, credential use, DHCP, route, external ping,
  partition write, boot image write, or flash is performed.

## Next Branches

- If mapped to `libperipheral_client.so`: trace the client-side PM callback
  implementation around that file offset.
- If mapped to `/vendor/bin/pm-service`: trace the local callback body.
- If still unmapped: preserve sample maps and classify whether the callback
  is in a transient anonymous/JIT/trampoline region.
