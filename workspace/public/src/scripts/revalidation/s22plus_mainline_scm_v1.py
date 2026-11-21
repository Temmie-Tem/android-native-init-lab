"""One qualified g0q SCM USB artifact; no device I/O or recovery decisions."""
from functools import lru_cache, partial
import json
from pathlib import Path
from types import SimpleNamespace

import s22plus_boot_only_f1_transport as transport
from s22plus_native_records_v3 import digest, pin, private_path, read, read_bytes, require, verify

from s22plus_mainline_profile_v1 import SCM_SCHEMA, SCM_WIRE_SCHEMA, SCM_STATUS

QUALIFICATION_SHA256 = 'f7b87ae16ed194cd20306a090a1dbfe953d4d772e993e02adc593d6a7aef3a75'
DECODER_SHA256 = '59eb50d2b93edcff15a0aafe23558d10dba1eb500bf6a5c85c552afc22380e2e'


def qualification(receipt):
    require(receipt['sha256'] == QUALIFICATION_SHA256, 'unqualified SCM board artifact')
    return read(verify(receipt))


def image_fields(root, receipt):
    import s22plus_mainline_profile_v1 as profile

    qualified = qualification(receipt)
    build = qualified['candidate_build_manifest']
    manifest = read(verify(build))
    require(manifest['vm'] is False and manifest['debian_ram']['schema'] == SCM_WIRE_SCHEMA,
            'SCM board manifest required')
    key = pin(private_path(root, manifest['key_path']), maximum=32)
    require(key['size'] == 32, 'invalid SCM key size')
    identity = dict(schema=SCM_WIRE_SCHEMA, inputs=manifest['inputs'], key_commitment=key['sha256'])
    encoded = json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()
    require(digest(encoded) == manifest['candidate_id'], 'SCM key does not match embedded identity')
    package = read(verify(qualified['package']))
    copy = package['copies'][0]
    require(copy['ap'] == qualified['packaged_ap'], 'SCM boot package differs')
    member = dict(copy['package']['boot_img_lz4'], name='boot.img.lz4')
    runtime = dict(loader=qualified['loader'], init=manifest['init'], initramfs=manifest['initramfs'],
                   dtb=manifest['dtb'], observer=manifest['debian_ram']['observer'],
                   kernel_sha256=qualified['nested']['kernel'], decoder=qualified['selected_decoder'],
                   expected_fdt=qualified['expected_loader_fdt'])
    image = dict(schema=SCM_SCHEMA, profile=profile.PROFILE, version=profile.VERSION, namespace=profile.NAMESPACE,
                 run_id_hex=manifest['candidate_id'][:32], ap=copy['ap'], member=member, key=key,
                 qualification=receipt, runtime_sources=runtime)
    return image, manifest


def image_binding(image, *, artifact_bytes=False):
    import s22plus_mainline_profile_v1 as profile

    expected, manifest = image_fields(profile.ROOT, image['qualification'])
    require(image == expected, 'SCM image differs from qualified board artifact')
    runtime = expected['runtime_sources']
    # The actual transfer reopens and verifies the AP on its pinned descriptor.
    if artifact_bytes:
        ap = expected['ap']
        with transport.pin_boot_only_ap(Path(ap['path']), label='SCM board', expected_size=ap['size'],
                                        expected_sha256=ap['sha256']) as fd:
            require(transport.boot_only_member_receipt(fd, label='SCM board') == expected['member'],
                    'SCM boot member differs')
    return dict(manifest, scm_decoder=runtime['decoder'], expected_loader_fdt_sha256=runtime['expected_fdt']['sha256'])


@lru_cache(maxsize=1)
def _decoder(source):
    # Load only the exact bytes checked here. The retained file is private;
    # ordinary source import could reopen it or select an unrelated .pyc.
    require(digest(source) == DECODER_SHA256, 'unreviewed board decoder')
    namespace = {'__name__': 'mainline.s22plus_canary_h0.scm_board_decoder',
                 '__package__': 'mainline.s22plus_canary_h0'}
    exec(compile(source, '<qualified SCM board decoder>', 'exec'), namespace)
    return namespace


def wire(manifest):
    receipt = manifest['scm_decoder']
    require(receipt['sha256'] == DECODER_SHA256, 'SCM decoder selection differs')
    source = read_bytes(Path(receipt['path']), maximum=32768)
    require(len(source) == receipt['size'], 'SCM decoder size differs')
    decoder = _decoder(source)
    return SimpleNamespace(request=decoder['request'], response_size=decoder['response_size'],
                           FDT_LIMIT=decoder['FDT_LIMIT'], verify_capture=partial(
                               decoder['verify_capture'], expected_loader_fdt_sha256=manifest['expected_loader_fdt_sha256']))


def outcome(proof):
    require(proof['status'] == SCM_STATUS and proof['subject'] == 'scm' and proof['runtime_schema'] == SCM_WIRE_SCHEMA,
            'SCM result identity differs')
    state = proof['scm_binding']
    require(state in ('bound', 'unbound', 'indeterminate'), 'unknown SCM result')
    return dict(status='SCM_OBSERVATION_INDETERMINATE' if state == 'indeterminate' else 'OBSERVED_SCM_BINDING',
                scm_binding=state)
