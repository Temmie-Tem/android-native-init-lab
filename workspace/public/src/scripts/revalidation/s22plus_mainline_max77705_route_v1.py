"""One qualified g0q MAX77705 Stage 2 route artifact (one gated COM_USB write); no device I/O or recovery decisions.

Same structure as s22plus_mainline_max77705_v1 (Stage 1). The board observer
sends at most one CONTROL1_W(COM_USB) after its gates (max77705-usb-route.h);
this module only binds the qualified bytes and maps the decoder's verdict.
"""
from functools import lru_cache, partial
import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

import s22plus_boot_only_f1_transport as transport
from s22plus_native_records_v3 import digest, pin, private_path, read_bytes, require

from s22plus_mainline_profile_v1 import MXR_SCHEMA, MXR_WIRE_SCHEMA, MXR_STATUS

QUALIFICATION_SHA256 = 'c0a0e3ec6ad5fb591ffe308909daf14eb38f5cc2dfbcaf3270b73f930b648a0e'
DECODER_SHA256 = '2fb8cb9c9c8d2acb2c3fae07e69b44b8f6817366539320d5f27e36fdb7ef344f'
# The intervention was tested and the record answers the routing question.
TESTED = ('ROUTE_CONFIGURED_WITHOUT_REPLUG', 'ROUTE_CONFIGURED_AFTER_REPLUG', 'ROUTE_PARTIAL_ENUMERATION',
          'ROUTE_WRITE_NOT_HELD')
# No write, but the record answers a state question that supersedes it.
STATE = ('ENUMERATED_BEFORE_WRITE', 'SKIP_INITIAL_COM_USB', 'SKIP_PREWRITE_NOT_OPEN')
INCONCLUSIVE = ('ROUTE_WRITE_FAILED', 'ROUTE_NO_READBACK', 'ROUTE_COVERAGE_GAP', 'ROUTE_NO_ENUMERATION',
                'ROUTE_AMBIGUOUS_ORDER',
                'EVENTS_DROPPED', 'SKIP_PENDING', 'SKIP_PREREAD_FAILED', 'SKIP_VBUS', 'SKIP_CHGTYP', 'SKIP_CC',
                'SKIP_BUDGET', 'SKIP_UDC_UNREADABLE', 'SKIP_STATUS_CHANGED', 'SKIP_STALE')
NO_PROOF = ('NO_PROOF_ADAPTER_ABSENT', 'NO_PROOF_ADAPTER_OPEN_FAILED', 'NO_PROOF_IDENTITY_MISMATCH',
            'NO_PROOF_NO_CONTROL1_READ')


def _checked(receipt):
    """Hash and parse the same bytes: no second read between check and use."""
    require(type(receipt) is dict and set(receipt) == {'path', 'size', 'sha256'}, 'record receipt fields differ')
    data = read_bytes(Path(receipt['path']))
    require(len(data) == receipt['size'] and hashlib.sha256(data).hexdigest() == receipt['sha256'],
            'record receipt changed')

    def unique(pairs):
        out = {}
        for key, value in pairs:
            require(key not in out, 'duplicate record key')
            out[key] = value
        return out
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda value: require(False, 'nonfinite record number'))


def qualification(receipt):
    require(receipt['sha256'] == QUALIFICATION_SHA256, 'unqualified MAX77705 route board artifact')
    return _checked(receipt)


def image_fields(root, receipt):
    import s22plus_mainline_profile_v1 as profile

    qualified = qualification(receipt)
    build = qualified['candidate_build_manifest']
    manifest = _checked(build)
    require(manifest['vm'] is False and manifest['debian_ram']['schema'] == MXR_WIRE_SCHEMA,
            'MAX77705 route board manifest required')
    require(manifest['network']['udc'] == 'a600000.usb', 'MAX77705 board UDC differs')
    key = pin(private_path(root, manifest['key_path']), maximum=32)
    require(key['size'] == 32, 'invalid MAX77705 key size')
    identity = dict(schema=MXR_WIRE_SCHEMA, inputs=manifest['inputs'], key_commitment=key['sha256'])
    encoded = json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()
    require(digest(encoded) == manifest['candidate_id'], 'MAX77705 key does not match embedded identity')
    package = _checked(qualified['package'])
    copy = package['copies'][0]
    require(copy['ap'] == qualified['packaged_ap'], 'MAX77705 boot package differs')
    member = dict(copy['package']['boot_img_lz4'], name='boot.img.lz4')
    runtime = dict(loader=qualified['loader'], init=manifest['init'], initramfs=manifest['initramfs'],
                   dtb=manifest['dtb'], observer=manifest['debian_ram']['observer'],
                   kernel_sha256=qualified['nested']['kernel'], decoder=qualified['selected_decoder'],
                   expected_fdt=qualified['expected_loader_fdt'])
    image = dict(schema=MXR_SCHEMA, profile=profile.PROFILE, version=profile.VERSION, namespace=profile.NAMESPACE,
                 run_id_hex=manifest['candidate_id'][:32], ap=copy['ap'], member=member, key=key,
                 qualification=receipt, runtime_sources=runtime)
    return image, manifest


def image_binding(image, *, artifact_bytes=False):
    import s22plus_mainline_profile_v1 as profile

    expected, manifest = image_fields(profile.ROOT, image['qualification'])
    require(image == expected, 'MAX77705 image differs from qualified board artifact')
    runtime = expected['runtime_sources']
    # The actual transfer reopens and verifies the AP on its pinned descriptor.
    if artifact_bytes:
        ap = expected['ap']
        with transport.pin_boot_only_ap(Path(ap['path']), label='MAX77705 route board', expected_size=ap['size'],
                                        expected_sha256=ap['sha256']) as fd:
            require(transport.boot_only_member_receipt(fd, label='MAX77705 route board') == expected['member'],
                    'MAX77705 boot member differs')
    return dict(manifest, max77705_decoder=runtime['decoder'],
                expected_loader_fdt_sha256=runtime['expected_fdt']['sha256'])


@lru_cache(maxsize=1)
def _decoder(source):
    # Load only the exact bytes checked here; the record decoder is embedded
    # in them, so no second file is read at verify time.
    require(digest(source) == DECODER_SHA256, 'unreviewed route board decoder')
    namespace = {'__name__': 'mainline.s22plus_canary_h0.max77705_route_board_decoder',
                 '__package__': 'mainline.s22plus_canary_h0'}
    exec(compile(source, '<qualified MAX77705 route board decoder>', 'exec'), namespace)
    return namespace


def wire(manifest):
    receipt = manifest['max77705_decoder']
    require(receipt['sha256'] == DECODER_SHA256, 'MAX77705 route decoder selection differs')
    source = read_bytes(Path(receipt['path']), maximum=65536)
    require(len(source) == receipt['size'], 'MAX77705 decoder size differs')
    decoder = _decoder(source)
    return SimpleNamespace(request=decoder['request'], response_size=decoder['response_size'],
                           FDT_LIMIT=decoder['FDT_LIMIT'], verify_capture=partial(
                               decoder['verify_capture'], expected_loader_fdt_sha256=manifest['expected_loader_fdt_sha256']))


def outcome(proof, *, cue_issued):
    """Map one verified record. A pass also needs the host side: no replug cue
    was issued before the authenticated response (cue_issued is False)."""
    require(proof['status'] == MXR_STATUS and proof['subject'] == 'max77705-route' and
            proof['runtime_schema'] == MXR_WIRE_SCHEMA, 'MAX77705 route result identity differs')
    verdict = proof['max77705_verdict']
    require(verdict in TESTED + STATE + INCONCLUSIVE + NO_PROOF, 'unknown MAX77705 route result')
    require(type(cue_issued) is bool, 'cue issuance must be known')
    record = proof['max77705']
    if verdict == 'ROUTE_CONFIGURED_WITHOUT_REPLUG' and cue_issued:
        # The phone saw no cable change, but the host had already asked for a
        # replug: keep the observation, do not call it a cable-untouched pass.
        verdict = 'ROUTE_CONFIGURED_AFTER_CUE'
    tested = verdict in TESTED + STATE + ('ROUTE_CONFIGURED_AFTER_CUE',)
    return dict(status='OBSERVED_MAX77705_USB_ROUTE' if tested else 'MAX77705_ROUTE_INCONCLUSIVE',
                max77705_route_verdict=verdict, max77705_route_decoder_verdict=proof['max77705_verdict'],
                max77705_route_gate=record.get('gate'), max77705_route_cue_issued=cue_issued,
                max77705_route_write_status=record.get('write_status'),
                max77705_commands=record.get('commands'), max77705_adapter=record.get('adapter'),
                max77705_io_errors=record.get('io_errors'))
