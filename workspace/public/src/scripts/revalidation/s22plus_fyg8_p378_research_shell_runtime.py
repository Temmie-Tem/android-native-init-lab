"""v0.1.2-rc.1 gauge telemetry HUD, prospective fresh candidate."""
from s22plus_fyg8_p378_namespace import load_predecessor
load_predecessor(globals())

_gauge_base_audit=audit_binding

def audit_binding(*,child=None):
    value=_gauge_base_audit(child=child)
    value.update(hud_metrics_wire_bytes=96,hud_fixed_gauge_read=True,
        gauge_soc='capped-register-estimate-not-Android-policy',
        gauge_status_and_temperature='unavailable-unless-separately-provided')
    return value
