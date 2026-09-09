"""P376 boot HUD with the reviewed root console; fresh identity."""
from s22plus_fyg8_p376_namespace import load_template
load_template(globals())

HUD_SOURCE=ROOT/'workspace/public/src/native-init/s22plus_boot_hud_v1.inc.c'
_hud_base_build=build_helper

def build_helper(child=None):
    value=_hud_base_build(child)
    anchor=b'static long rc1_console('
    value=_once(value,anchor,HUD_SOURCE.read_bytes()+b'\n'+anchor)
    value=_once(value,b'    for(;;) {\n        uint64_t now=0;rc=rc1_now(&now);if(rc)break;',
        b'    struct hud1_state hud={0};hud1_start(&hud);\n    for(;;) {\n        uint64_t now=0;rc=rc1_now(&now);if(rc)break;')
    value=_once(value,b'        if(s.control){\n',b'        if(s.control)hud1_stop(&hud);else hud1_tick(&hud,now,s.blocked?2U:s.active?1U:0U);\n        if(s.control){\n')
    value=_once(value,b'if(s.control==2 && !s.qcount){rc1_signal(&s,9);',
        b'if(s.control==2 && !s.qcount){hud1_stop(&hud);rc1_signal(&s,9);')
    value=_once(value,b'    rc1_signal(&s,9);rc1_close_pipes(&s);return rc;\n}',
        b'    hud1_stop(&hud);rc1_signal(&s,9);rc1_close_pipes(&s);return rc;\n}')
    return value

P345_HELPER_TEMPLATE=P345_HELPER=build_helper()
P376_HELPER_TEMPLATE=P376_HELPER=P345_HELPER
_hud_base_audit=audit_binding

def audit_binding(*,child=None):
    value=_hud_base_audit(child=child)
    value.update(hud_source=identity(HUD_SOURCE.read_bytes()),
        hud_child='separate-PID1-owned-process-group',hud_restart=False,
        hud_snapshot='AF_UNIX-SOCK_SEQPACKET-nonblocking-MSG_NOSIGNAL',
        hud_snapshot_bytes=40,hud_snapshot_interval_ms=1000,hud_log_limit=131072,
        hud_failure_blocks_console=False,hud_cleanup_wait=False,
        hud_control_signal_maximum=1,hud_pixel_output='operator-observation-only')
    return value
