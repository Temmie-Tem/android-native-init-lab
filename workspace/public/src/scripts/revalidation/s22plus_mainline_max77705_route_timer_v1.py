"""Qualified g0q MAX77705 route-timer artifacts; no device I/O or recovery decisions.

The observer is the reviewed Stage 2 route producer (max77705-usb-route.h:
at most one gated CONTROL1_W(COM_USB)) composed with the ML050 timer child
by max77705_route_timer_h0.py. PID1 arms the child before USB setup and
closes its IPC, so the only return is the child's single ordinary
RESTART2("download") at guest BOOTTIME 555 s. An authenticated response
implies the child was armed: a failed arm parks PID1 before USB.

There is no attach cue for this board. This module binds the qualified
bytes and maps the decoder's verdict; the original owner's timed return
and its proof are separate (s22plus_mainline_auto_recovery_v1).
"""
from functools import lru_cache, partial
import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

import s22plus_boot_only_f1_transport as transport
from s22plus_native_records_v3 import digest, pin, private_path, read_bytes, require

from s22plus_mainline_profile_v1 import MXT_COMPILE_FLAGS, MXT_GUEST, MXT_SCHEMA, MXT_WIRE_SCHEMA, MXT_STATUS

# Each qualification is one board build of the same reviewed guest sources,
# Image and DT, with its own run ID and key. The candidate registry consumes
# each AP once, so a repeated normal run needs its own qualified build.
# The first entry is the 2026-11-26 run's (consumed).
QUALIFICATIONS = (
    '55bbeedf0737914c58dc5b7da73c35280ad7f730625d3a76ee4ad37c3027806f',
    'c42725e1bf0d9346a9f98ba07f47e1b4cd2b86e7dce1726fb706185aba06ec5b',
    '9a19b32b56ae44ef2d24198301fe48409ade604f5e043614ddf3c2f53a20580f',
    '821c15fafc0da34fd9e10c8550bd851e79283167babdfe1626e364e38d597f9f',
    '34763bedf661b2e1e8145febaf8a6340fb64b0bcb7b3a3ff29e43502c85aa044',
)
DECODER_SHA256 = 'e3974368f4dea823e470be2eedf90a7eee2796efdd5e9fda3258bf062b8dae36'
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
    require(receipt['sha256'] in QUALIFICATIONS, 'unqualified MAX77705 route-timer board artifact')
    return _checked(receipt)


def image_fields(root, receipt):
    import s22plus_mainline_profile_v1 as profile

    qualified = qualification(receipt)
    build = qualified['candidate_build_manifest']
    manifest = _checked(build)
    require(manifest['vm'] is False and manifest['debian_ram']['schema'] == MXT_WIRE_SCHEMA,
            'MAX77705 route-timer board manifest required')
    require(manifest['network']['udc'] == 'a600000.usb', 'MAX77705 board UDC differs')
    # The qualified observer was rebuilt from these exact reviewed guest bytes
    # (check_package compares the rebuilt ELF with the shipped member).
    for relative in MXT_GUEST:
        current = digest(read_bytes(Path(root) / relative, maximum=1024 * 1024))
        rows = [row for row in manifest['inputs'] if Path(row['path']).as_posix().endswith('/' + relative)]
        require(len(rows) == 1 and rows[0]['sha256'] == current, 'route-timer guest source differs: ' + relative)
    require(qualified['selected_generator']['sha256'] == digest(read_bytes(Path(root) / MXT_GUEST[0])) and
            qualified['route_generator']['sha256'] == digest(read_bytes(Path(root) / MXT_GUEST[1])),
            'route-timer generator differs from the reviewed staging')
    require(tuple(qualified['observer_compile_flags']) == MXT_COMPILE_FLAGS,
            'route-timer observer compile flags differ')
    key = pin(private_path(root, manifest['key_path']), maximum=32)
    require(key['size'] == 32, 'invalid MAX77705 key size')
    identity = dict(schema=MXT_WIRE_SCHEMA, inputs=manifest['inputs'], key_commitment=key['sha256'])
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
    image = dict(schema=MXT_SCHEMA, profile=profile.PROFILE, version=profile.VERSION, namespace=profile.NAMESPACE,
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
        with transport.pin_boot_only_ap(Path(ap['path']), label='MAX77705 route-timer board', expected_size=ap['size'],
                                        expected_sha256=ap['sha256']) as fd:
            require(transport.boot_only_member_receipt(fd, label='MAX77705 route-timer board') == expected['member'],
                    'MAX77705 boot member differs')
    return dict(manifest, max77705_decoder=runtime['decoder'],
                expected_loader_fdt_sha256=runtime['expected_fdt']['sha256'])


@lru_cache(maxsize=1)
def _decoder(source):
    # Load only the exact bytes checked here; the record decoder is embedded
    # in them, so no second file is read at verify time.
    require(digest(source) == DECODER_SHA256, 'unreviewed route-timer board decoder')
    namespace = {'__name__': 'mainline.s22plus_canary_h0.max77705_route_timer_board_decoder',
                 '__package__': 'mainline.s22plus_canary_h0'}
    exec(compile(source, '<qualified MAX77705 route-timer board decoder>', 'exec'), namespace)
    return namespace


def wire(manifest):
    receipt = manifest['max77705_decoder']
    require(receipt['sha256'] == DECODER_SHA256, 'MAX77705 route-timer decoder selection differs')
    source = read_bytes(Path(receipt['path']), maximum=65536)
    require(len(source) == receipt['size'], 'MAX77705 decoder size differs')
    decoder = _decoder(source)
    return SimpleNamespace(request=decoder['request'], response_size=decoder['response_size'],
                           FDT_LIMIT=decoder['FDT_LIMIT'], verify_capture=partial(
                               decoder['verify_capture'], expected_loader_fdt_sha256=manifest['expected_loader_fdt_sha256']))


def outcome(proof):
    """Map one verified record. No cue exists for this board, so a
    ROUTE_CONFIGURED_WITHOUT_REPLUG record is a cable-untouched pass."""
    require(proof['status'] == MXT_STATUS and proof['subject'] == 'max77705-route-timer' and
            proof['runtime_schema'] == MXT_WIRE_SCHEMA, 'MAX77705 route-timer result identity differs')
    verdict = proof['max77705_verdict']
    require(verdict in TESTED + STATE + INCONCLUSIVE + NO_PROOF, 'unknown MAX77705 route result')
    record = proof['max77705']
    tested = verdict in TESTED + STATE
    return dict(status='OBSERVED_MAX77705_USB_ROUTE' if tested else 'MAX77705_ROUTE_INCONCLUSIVE',
                max77705_route_verdict=verdict, max77705_route_gate=record.get('gate'),
                max77705_route_write_status=record.get('write_status'),
                max77705_commands=record.get('commands'), max77705_adapter=record.get('adapter'),
                max77705_io_errors=record.get('io_errors'), timer_armed_implied_by_response=True)
