"""P376 boot HUD with the reviewed root console; fresh identity."""
from s22plus_fyg8_p376_namespace import load_template
load_template(globals())

TOTAL_COMMANDS=6
_base_contract=_contract

def _contract():
    return dict(_base_contract(),boot_hud=True,hud_required=True,
        hud_owner='separate-PID1-child',hud_restarts=0,root_console=True)

_base_audit=audit

def audit():
    return dict(_base_audit(),total_commands=TOTAL_COMMANDS)
