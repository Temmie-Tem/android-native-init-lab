#!/usr/bin/env python3
"""P347 exact static closure using the read-only successor builder."""
from pathlib import Path
import hashlib

TEMPLATE_SOURCE = Path(__file__).with_name('s22plus_fyg8_p345_process_v2_candidate_static.py')
TEMPLATE_IDENTITY = {'size': 8107, 'sha256': '4537f63080f1397c2775da0557f3c2622d103fc2b284144d2a3df1623efbb3e0'}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P347 source template identity differs")
_template = _template.replace(b"P345", b"P347").replace(b"p345", b"p347")
_template = _template.replace(b"s22plus_fyg8_p347_readonly_child",
                              b"s22plus_fyg8_readonly_child_v2")
_template = _template.replace(b"process-v2-candidate-static-20260906-02",
                              b"process-v2-candidate-static-20260906-01")
# Keep CLI dispatch after registering the full executed-template closure.
_template = _template[:_template.rindex(b'if __name__ == "__main__":')]
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p347", "exec"), globals())
for _directory, _names in (
    (REVALIDATION, ("research_shell_runtime", "research_shell_observer",
                    "artifact_identity", "stock_process_v2_adapter")),
    (Path(__file__).parent, ("stock_candidate_build", "process_v2_candidate_static")),
):
    for _name in _names:
        SOURCE_FILES["p347_template_" + _name] = _directory / ("s22plus_fyg8_p345_" + _name + ".py")
# The thin preparer itself and its executed base affect emitted addresses.
SOURCE_FILES["p347_prepare"] = Path(__file__).with_name("prepare_s22plus_fyg8_p347_process_v2.py")
SOURCE_FILES["p347_template_prepare"] = Path(__file__).with_name("prepare_s22plus_fyg8_p345_process_v2.py")

SOURCE_FILES["p347_child_loader_template"] = REVALIDATION / "s22plus_fyg8_p345_readonly_child.py"

if __name__ == "__main__":
    raise SystemExit(main())
