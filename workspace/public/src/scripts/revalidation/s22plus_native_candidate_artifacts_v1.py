"""Explicit candidate Image/init/AP identity over a frozen FYG8 platform.

The existing boot-only archive parser, IKCONFIG tools and boot reader are
reused. No historical candidate validator is relabelled as a new result.
"""
import hashlib
from pathlib import Path
import stat
import zlib

import s22plus_boot_verify as boot
import s22plus_fyg8_p383_artifact_identity as reference


def reference_source_files():
    """Reachable sealed image/parser loaders, including their dynamic reads.

    This is the reviewed P383 artifact loader closure; unrelated PREDECESSORS
    entries and unused runtime/build/observer generators are not execution.
    """
    folder = Path(__file__).parent
    names = {f's22plus_fyg8_p{n}_artifact_identity.py' for n in (*range(321, 346), 350, 351, 353)}
    names.update(f's22plus_fyg8_p{n}_{role}.py'
                 for n in (*range(363, 372), *range(375, 384))
                 for role in ('artifact_identity', 'namespace', 'return_spec'))
    names.add('s22plus_display_step_v1_namespace.py')
    return tuple(folder/name for name in sorted(names))


def identity(raw): return dict(size=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def stable_bytes(path, label='candidate input', maximum=128*1024*1024, expected=None, *, nlink=1, **kwargs):
    path = Path(path); before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != nlink or not 0 <= before.st_size <= maximum:
        raise ValueError(label+' metadata differs')
    if 'required_mode' in kwargs and stat.S_IMODE(before.st_mode) != kwargs['required_mode']:
        raise ValueError(label+' mode differs')
    raw = path.read_bytes(); after = path.lstat()
    fields = lambda st: (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
    if fields(before) != fields(after) or len(raw) != before.st_size or expected is not None and identity(raw) != expected:
        raise ValueError(label+' changed or identity differs')
    return raw


class Artifacts:
    ArtifactIdentityError = ValueError
    stable_bytes = staticmethod(stable_bytes)
    identity = staticmethod(identity)
    AUTH_KEY_SIZE = 32
    AUTH_KEY_MODE = reference.AUTH_KEY_MODE
    AUTH_KEY_SCHEMA = reference.AUTH_KEY_SCHEMA
    DISPLAY_MODULE_NAMES = reference.DISPLAY_MODULE_NAMES
    PACKAGED_MODULE_NAMES = reference.PACKAGED_MODULE_NAMES
    validate_rollback_ap = staticmethod(reference.validate_rollback_ap)

    def __init__(self, selected, image_identity, auth_key_identity):
        self.selected = selected; self.image_identity = image_identity; self.key_identity = auth_key_identity
        self.__file__ = __file__
        self.SOURCE = Path(__file__)
        setattr(self, selected.namespace.upper()+'_IMAGE_IDENTITY', image_identity)
        setattr(self, selected.namespace.upper()+'_RUN_ID_HEX', selected.run_id_hex)
        setattr(self, selected.namespace.upper()+'_RUN_ID', bytes.fromhex(selected.run_id_hex))
        setattr(self, 'validate_'+selected.namespace+'_identity', self.audit_binding)

    def auth_key_identity(self): return dict(self.key_identity)

    def transform_image(self, original):
        if identity(original) != reference.P383_IMAGE_IDENTITY:
            raise ValueError('frozen platform Image differs')
        reference.validate_image(original)
        start, end, compressed, config = reference._gzip_config(original, 'frozen platform Image')
        old = reference.P383_RUN_ID_HEX.encode(); new = self.selected.run_id_hex.encode()
        line = reference.RUN_CONFIG_KEY.encode()+b'="'+old+b'"'
        if config.count(line) != 1 or original.count(old) != 1:
            raise ValueError('frozen platform Image identity slots differ')
        offset = original.index(old)
        if start <= offset < end: raise ValueError('raw Image identity overlaps IKCONFIG')
        updated = config.replace(line, reference.RUN_CONFIG_KEY.encode()+b'="'+new+b'"', 1)
        encoded = reference._recompress_config(updated)
        if len(encoded) != len(compressed) or zlib.decompress(encoded, 31) != updated:
            raise ValueError('Image identity-only transform changes layout')
        image = original[:start]+encoded+original[end:]
        image = image[:offset]+new+image[offset+len(old):]
        self.validate_image(image)
        # Reverse only the two declared spans and require every original byte.
        inverse = image[:start]+compressed+image[end:]
        inverse = inverse[:offset]+old+inverse[offset+len(new):]
        if inverse != original: raise ValueError('Image changed outside declared identity spans')
        return image, dict(method='identity_only_post_link_v1', source=identity(original), target=identity(image),
            source_run_id_hex=old.decode(), run_id_hex=new.decode(), raw_offset=offset,
            ikconfig_start=start, ikconfig_end=end, outside_declared_spans_unchanged=True,
            image_size_unchanged=True, section_layout_unchanged=True)

    def validate_image(self, image, *, expected_run_id=None):
        run = bytes.fromhex(self.selected.run_id_hex)
        if expected_run_id is not None and expected_run_id != run:
            raise ValueError('candidate Image requested run differs')
        if identity(image) != self.image_identity: raise ValueError('candidate Image identity differs')
        start, end, _, config = reference._gzip_config(image, 'candidate Image')
        values = reference._config_values(config, 'candidate Image')
        if values[reference.RUN_CONFIG_KEY] != '"'+self.selected.run_id_hex+'"':
            raise ValueError('candidate Image IKCONFIG run differs')
        outside = image[:start]+image[end:]
        if outside.count(self.selected.run_id_hex.encode()) != 1 or reference.P383_RUN_ID_HEX.encode() in outside:
            raise ValueError('candidate Image raw identity differs')
        return dict(identity=identity(image), run_id_hex=self.selected.run_id_hex, identity_only=True)

    def _validate_init(self, init, expected_run_id=None):
        run = bytes.fromhex(self.selected.run_id_hex)
        if expected_run_id is not None and expected_run_id != run: raise ValueError('candidate init requested run differs')
        if (init.count(run) != 1 or bytes.fromhex(reference.P383_RUN_ID_HEX) in init
                or self.selected.run_id_hex.encode() not in init
                or ('S22PLUS-FYG8-'+self.selected.namespace.upper()+'-PROGRESS-v1').encode() not in init):
            raise ValueError('candidate init identity/domain differs')
        return dict(identity=identity(init), run_id_hex=self.selected.run_id_hex)

    def inspect_ap(self, ap_path, *, expected_run_id=None, expected_image=None, expected_init=None,
                   expected_child=None, expected_ap=None, label='native candidate AP'):
        if expected_run_id is not None and expected_run_id != bytes.fromhex(self.selected.run_id_hex):
            raise ValueError('candidate AP requested run differs')
        raw = stable_bytes(ap_path, label, expected=expected_ap)
        frame, structure = reference._INNER._parse_ap(raw, label)
        image = boot.decompress_lz4_frame_python(frame, maximum=128*1024*1024)
        parsed = boot.parse_boot_v4(image)
        entries = boot.parse_newc(boot.decompress_lz4_stream_python(parsed.ramdisk, maximum=128*1024*1024))
        rows = {row.name: row for row in entries}
        if len(rows) != len(entries): raise ValueError('candidate AP duplicate ramdisk entry')
        init, child = rows['init'].data, rows['s22-e1-child'].data
        if (expected_image is not None and parsed.kernel != expected_image
                or expected_init is not None and init != expected_init
                or expected_child is not None and child != expected_child):
            raise ValueError('candidate AP payload join differs')
        return dict(ap=identity(raw), ap_structure=structure, boot_img_lz4=identity(frame), boot_img=identity(image),
            image=self.validate_image(parsed.kernel), init=self._validate_init(init), child=identity(child),
            run_id_hex=self.selected.run_id_hex, joined=True, boot_only=True)

    def audit_binding(self):
        return dict(schema='s22plus_'+self.selected.namespace+'_native_artifact_identity_v1',
            run_id_hex=self.selected.run_id_hex, image_identity=dict(self.image_identity),
            ap_identity=None, ap_identity_owner='new A/B build and actual boot-only AP join',
            image_delta_identity_only=True, runtime_behavior_unchanged=False,
            boot_only=True, ab_must_match=True, later_action_lease_active=False, mandatory_rollback=True,
            device_contact=False, live_authorized=False)
