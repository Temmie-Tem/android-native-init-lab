#!/usr/bin/env python3
"""P348 exact static closure using the retained P347 construction engine."""

from pathlib import Path
import hashlib


TEMPLATE_SOURCE = Path(__file__).with_name(
    "s22plus_fyg8_p347_process_v2_candidate_static.py"
)
TEMPLATE_IDENTITY = {
    "size": 1947,
    "sha256": "ac95cd243f2edb347d136be927bb6a7caa99c36bd2cca153fde2efef7c23fc85",
}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P348 source template identity differs")
_template = _template.replace(b"P347", b"P348").replace(b"p347", b"p348")
_template = _template.replace(
    b"process-v2-candidate-static-20260906-01",
    b"process-v2-candidate-static-20260906-01",
)
# Keep CLI dispatch after registering the complete executed-template closure.
_template = _template[: _template.rindex(b'if __name__ == "__main__":')]
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p348", "exec"), globals())

# The executed P348 wrappers load P347 wrappers before projecting the P345
# construction base.  Keep those intermediate source identities explicit;
# inherited ``SOURCE``/``TEMPLATE_SOURCE`` globals are intentionally not used
# as a substitute for this closure.
for _role, _directory, _name in (
    ("p348_p347_runtime_wrapper", REVALIDATION, "s22plus_fyg8_p347_research_shell_runtime.py"),
    ("p348_p347_observer_wrapper", REVALIDATION, "s22plus_fyg8_p347_research_shell_observer.py"),
    ("p348_p347_artifact_wrapper", REVALIDATION, "s22plus_fyg8_p347_artifact_identity.py"),
    ("p348_p347_adapter_wrapper", REVALIDATION, "s22plus_fyg8_p347_stock_process_v2_adapter.py"),
    ("p348_p347_builder_wrapper", Path(__file__).parent, "s22plus_fyg8_p347_stock_candidate_build.py"),
    ("p348_p347_static_wrapper", Path(__file__).parent, "s22plus_fyg8_p347_process_v2_candidate_static.py"),
    ("p348_p347_prepare_wrapper", Path(__file__).parent, "prepare_s22plus_fyg8_p347_process_v2.py"),
):
    SOURCE_FILES[_role] = _directory / _name

# The retained lease/action owner is supplied by the separate live worker.  A
# source receipt is included when that worker is present, without making this
# H0 packaging module import or execute the live caller.
SOURCE_FILES["p348_shell_session"] = REVALIDATION / "s22plus_fyg8_p348_shell_session.py"
SOURCE_FILES["p348_shell_action"] = REVALIDATION / "s22plus_fyg8_p348_shell_action.py"
SOURCE_FILES["p348_raw_capture"] = REVALIDATION / "device_action_raw_capture_v1.py"
