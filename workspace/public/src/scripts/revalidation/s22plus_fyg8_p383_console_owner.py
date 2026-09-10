"""v0.2.0-rc.1 native baseline first roundtrip qualification."""
from s22plus_fyg8_p383_namespace import load_predecessor
load_predecessor(globals())

_base_validate = validate

def validate(value):
    result = _base_validate(value)
    if result['commands']:
        raise ConsolePlanError('P383 permits only fixed native health commands')
    return result

MAX_COMMANDS = 0
