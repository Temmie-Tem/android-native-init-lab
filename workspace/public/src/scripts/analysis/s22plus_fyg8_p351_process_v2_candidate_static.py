"""P351 H0-only fresh promotion binding over the unchanged P350 template."""
from pathlib import Path
import ast
import hashlib
PARENT_TEMPLATE = Path(__file__).with_name('s22plus_fyg8_p350_process_v2_candidate_static.py')
PARENT_TEMPLATE_SHA = 'a1ef060a67a23c965604fbd6f7358ba84219a0efd839c04e0118b149a199b74b'
_parent_source = PARENT_TEMPLATE.read_bytes()
if hashlib.sha256(_parent_source).hexdigest() != PARENT_TEMPLATE_SHA:
    raise ValueError('P351 promotion template identity differs')
_parent_source = _parent_source.replace(b'P350', b'P351').replace(b'p350', b'p351')
_tree = ast.parse(_parent_source)
_tree.body = [n for n in _tree.body if not (isinstance(n, ast.If) and '__name__' in ast.unparse(n.test))]
exec(compile(ast.fix_missing_locations(_tree), str(PARENT_TEMPLATE) + '#p351', 'exec'), globals())

SOURCE_FILES.update({
    'p351_static_parent_template':PARENT_TEMPLATE,
    'p351_renderer_generator':Path(candidate_build.renderer_source.__file__),
    'p351_readiness':candidate_build.NATIVE/'s22plus_native_display_ready_v2.inc.c',
    'p351_visible_layout':candidate_build.NATIVE/'s22plus_native_display_visible_layout_h0.c',
    'p351_prerequisite_extractor':Path(candidate_build.prerequisites.__file__),
})

if __name__ == '__main__':
    raise SystemExit(main())
