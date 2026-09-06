#!/usr/bin/env python3
"""P349 fresh H0 packaging over an immutable retained construction template."""
from pathlib import Path
import hashlib
import ast
TEMPLATE_SOURCE = Path(__file__).with_name('s22plus_fyg8_p348_process_v2_candidate_static.py')
TEMPLATE_IDENTITY = {"size": 2518, "sha256": 'da770b2ba66c00db9261ef1f46b356a4e3ea7471e7df0ae35871cb9ad0365feb'}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P349 packaging template identity differs")
_template = _template.replace(b"P348", b"P349").replace(b"p348", b"p349")
_template = _template.replace(b"P3.48", b"P3.49")
_template = _template.replace(b"s22plus_fyg8_readonly_child_v2", b"s22plus_fyg8_ram_workspace_child_v1")
_template = _template.replace(b'_template = _template[:', b'_template = _template.replace(b"s22plus_fyg8_readonly_child_v2", b"s22plus_fyg8_ram_workspace_child_v1")\n_template = _template[:')
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p349", "exec"), globals())
# Every actually executed intermediate wrapper remains in the source closure.
for _directory, _names in (
    (REVALIDATION, ("research_shell_observer", "artifact_identity", "stock_process_v2_adapter", "shell_session", "shell_action")),
    (Path(__file__).parent, ("stock_candidate_build", "process_v2_candidate_static")),
):
    for _name in _names:
        SOURCE_FILES["p349_p348_" + _name] = _directory / ("s22plus_fyg8_p348_" + _name + ".py")
SOURCE_FILES["p349_p348_prepare"] = Path(__file__).with_name("prepare_s22plus_fyg8_p348_process_v2.py")

if __name__ == "__main__":
    raise SystemExit(main())
