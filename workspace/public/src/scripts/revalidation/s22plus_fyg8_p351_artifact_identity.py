"""P351 fresh binding over the unchanged P350 template; no live authority."""
from pathlib import Path
import hashlib

PARENT_TEMPLATE = Path(__file__).with_name('s22plus_fyg8_p350_artifact_identity.py')
PARENT_TEMPLATE_SHA = '31a96966709c41a3288e2a215a316d931b38790af0739fdbb58c8498501a11f2'
_parent_source = PARENT_TEMPLATE.read_bytes()
if hashlib.sha256(_parent_source).hexdigest() != PARENT_TEMPLATE_SHA:
    raise ValueError('P351 template identity differs')
_parent_source = _parent_source.replace(b'P350', b'P351').replace(b'p350', b'p351')
_parent_source = _parent_source.replace(b'c350f1e0a90b5e6d7c8a9b0c1d2e3f0a', b'c351f1e0a90b5e6d7c8a9b0c1d2e3f0b')
_parent_source = _parent_source.replace(b'b0cce78535eb553d493b8c7ca0117f390f4c4c5648899f8d2afcc182cb58276b', b'4873dc3ac17d9d5fc5da21a969ba48e6b71f122742db08ae3fbfc54442813082')
exec(compile(_parent_source, str(PARENT_TEMPLATE) + '#p351', 'exec'), globals())

DISPLAY_MODULE_NAMES = ('pmic_class.ko', 's2dos05-regulator.ko', 'i2c-gpio.ko') + DISPLAY_MODULE_NAMES
