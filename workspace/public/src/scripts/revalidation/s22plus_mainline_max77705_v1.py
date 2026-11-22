"""One qualified g0q MAX77705 read-only USB observation artifact; no device I/O or recovery decisions.

Structure follows the dormant SCM draft (codex/s22-scm-attended-h0, 3b6ee4fb5b).
"""
from functools import lru_cache, partial
import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

import s22plus_boot_only_f1_transport as transport
from s22plus_native_records_v3 import digest, pin, private_path, read_bytes, require

from s22plus_mainline_profile_v1 import MX_SCHEMA, MX_WIRE_SCHEMA, MX_STATUS

QUALIFICATION_SHA256 = 'eeebf904f20cb402087e250c4a738ec60b777fe1ab56501546778d1b093c4569'
DECODER_SHA256 = 'c197479812662c2074e15202b9070d4511777d504c2eb2bc2af034c8ae4d48cd'
OBSERVED = ('INITIAL_COM_USB', 'OTHER_INITIAL_CONTROL1', 'OPEN_NO_ATTACH_SEEN', 'OPEN_NO_READ_AFTER_ATTACH',
            'OPEN_THEN_COM_USB_AFTER_ATTACH', 'OPEN_UNCHANGED_AFTER_ATTACH', 'OPEN_THEN_OTHER_AFTER_ATTACH')
NO_PROOF = ('NO_PROOF_ADAPTER_ABSENT', 'NO_PROOF_ADAPTER_OPEN_FAILED', 'NO_PROOF_IDENTITY_MISMATCH',
            'NO_PROOF_NO_CONTROL1_READ')
# The pinned board decoder derives OPEN_NO_ATTACH_SEEN from the event array only.
# The producer also saves the boot-time UIC latch before its first CONTROL1
# command (`initial_uic`), and the phone normally boots with the cable in. The
# binding refines that one verdict from the decoded latch, without changing
# the qualified decoder bytes or the board artifact:
#   latch unread             -> OPEN_INITIAL_LATCH_UNREAD (inconclusive)
#   latch has an attach bit  -> OPEN_BOOT_ATTACH_ONLY (attach before the first read only)
#   latch read, no attach    -> OPEN_NO_ATTACH_SEEN (as documented)
# The producer keeps the first 24 and the latest 24 events and overwrites the
# middle once more than 48 occur. The decoder's verdicts depend on the first
# successful CONTROL1 read, the first attach and the reads after it, any of
# which the dropped middle may hold. So once events were dropped, every switch
# verdict becomes EVENTS_DROPPED (inconclusive), except a first-read verdict
# (INITIAL_COM_USB, OTHER_INITIAL_CONTROL1) whose first successful read lies
# in the kept prefix, which is complete and in order.
ATTACH_BITS = frozenset({'VBUSDetI', 'CHGTypI'})
FIRST_READ_ONLY = ('INITIAL_COM_USB', 'OTHER_INITIAL_CONTROL1')
PREFIX = 24
REFINED_OBSERVED = ('OPEN_BOOT_ATTACH_ONLY',)
REFINED_INCONCLUSIVE = ('OPEN_INITIAL_LATCH_UNREAD', 'EVENTS_DROPPED')


def refine(verdict, record):
    if verdict in OBSERVED:
        total, events = record.get('events_total'), record.get('events')
        require(type(total) is int and type(events) is list and total >= len(events) and
                all(type(e) is dict for e in events), 'MAX77705 event count fields differ')
        if total > len(events):
            first = next((i for i, e in enumerate(events) if e.get('ctrl1') is not None), None)
            if not (verdict in FIRST_READ_ONLY and first is not None and first < PREFIX):
                return 'EVENTS_DROPPED'
    if verdict != 'OPEN_NO_ATTACH_SEEN':
        return verdict
    valid, bits = record.get('initial_uic_valid'), record.get('initial_uic_bits')
    require(type(valid) is bool and type(bits) is list and all(type(b) is str for b in bits),
            'MAX77705 initial latch fields differ')
    if not valid:
        return 'OPEN_INITIAL_LATCH_UNREAD'
    return 'OPEN_BOOT_ATTACH_ONLY' if ATTACH_BITS & set(bits) else verdict


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
    require(receipt['sha256'] == QUALIFICATION_SHA256, 'unqualified MAX77705 board artifact')
    return _checked(receipt)


def image_fields(root, receipt):
    import s22plus_mainline_profile_v1 as profile

    qualified = qualification(receipt)
    build = qualified['candidate_build_manifest']
    manifest = _checked(build)
    require(manifest['vm'] is False and manifest['debian_ram']['schema'] == MX_WIRE_SCHEMA,
            'MAX77705 board manifest required')
    require(manifest['network']['udc'] == 'a600000.usb', 'MAX77705 board UDC differs')
    key = pin(private_path(root, manifest['key_path']), maximum=32)
    require(key['size'] == 32, 'invalid MAX77705 key size')
    identity = dict(schema=MX_WIRE_SCHEMA, inputs=manifest['inputs'], key_commitment=key['sha256'])
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
    image = dict(schema=MX_SCHEMA, profile=profile.PROFILE, version=profile.VERSION, namespace=profile.NAMESPACE,
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
        with transport.pin_boot_only_ap(Path(ap['path']), label='MAX77705 board', expected_size=ap['size'],
                                        expected_sha256=ap['sha256']) as fd:
            require(transport.boot_only_member_receipt(fd, label='MAX77705 board') == expected['member'],
                    'MAX77705 boot member differs')
    return dict(manifest, max77705_decoder=runtime['decoder'],
                expected_loader_fdt_sha256=runtime['expected_fdt']['sha256'])


@lru_cache(maxsize=1)
def _decoder(source):
    # Load only the exact bytes checked here; the record decoder is embedded
    # in them, so no second file is read at verify time.
    require(digest(source) == DECODER_SHA256, 'unreviewed board decoder')
    namespace = {'__name__': 'mainline.s22plus_canary_h0.max77705_board_decoder',
                 '__package__': 'mainline.s22plus_canary_h0'}
    exec(compile(source, '<qualified MAX77705 board decoder>', 'exec'), namespace)
    return namespace


def wire(manifest):
    receipt = manifest['max77705_decoder']
    require(receipt['sha256'] == DECODER_SHA256, 'MAX77705 decoder selection differs')
    source = read_bytes(Path(receipt['path']), maximum=32768)
    require(len(source) == receipt['size'], 'MAX77705 decoder size differs')
    decoder = _decoder(source)
    return SimpleNamespace(request=decoder['request'], response_size=decoder['response_size'],
                           FDT_LIMIT=decoder['FDT_LIMIT'], verify_capture=partial(
                               decoder['verify_capture'], expected_loader_fdt_sha256=manifest['expected_loader_fdt_sha256']))


def outcome(proof):
    require(proof['status'] == MX_STATUS and proof['subject'] == 'max77705' and proof['runtime_schema'] == MX_WIRE_SCHEMA,
            'MAX77705 result identity differs')
    decoder_verdict = proof['max77705_verdict']
    require(decoder_verdict in OBSERVED + NO_PROOF, 'unknown MAX77705 result')
    record = proof['max77705']
    verdict = refine(decoder_verdict, record)
    observed = verdict in OBSERVED + REFINED_OBSERVED
    return dict(status='OBSERVED_MAX77705_USB_SWITCH' if observed else 'MAX77705_OBSERVATION_INCONCLUSIVE',
                max77705_verdict=verdict, max77705_decoder_verdict=decoder_verdict,
                max77705_initial_uic_bits=record.get('initial_uic_bits'), max77705_commands=record.get('commands'),
                max77705_adapter=record.get('adapter'), max77705_io_errors=record.get('io_errors'))
