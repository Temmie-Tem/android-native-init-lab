"""P376 boot HUD with the reviewed root console; fresh identity."""
from s22plus_fyg8_p376_namespace import load_template
load_template(globals())

_base_hud_identity=validate_p376_identity

def validate_p376_identity():
    return dict(_base_hud_identity(),boot_hud=True,hud_required=True,
        immutable_hud_frames=True,hud_restarts=0)
