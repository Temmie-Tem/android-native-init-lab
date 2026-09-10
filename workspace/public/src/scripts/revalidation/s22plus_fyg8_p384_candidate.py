"""P384 / v0.2.0-rc.2: direct local display adoption, H0 only.

Ordinary one-candidate/one-Android-rollback ownership. This declaration does
not select or renew the consumed P383 same-native restoration exception.
"""
from pathlib import Path
from types import SimpleNamespace

import s22plus_native_source_v1 as source
import s22plus_native_console_observer_v1 as console
import s22plus_native_console_owner_v1 as owner
import s22plus_native_candidate_artifacts_v1 as artifacts
import s22plus_native_carrier_adapter_v1 as carrier

ROOT = Path(__file__).resolve().parents[5]
IDENTITY = source.Identity('p384', 'c384f1e0a90b5e6d7c8a9b0c1d2e3f0b', 'v0.2.0-rc.2')
IMAGE_IDENTITY = dict(size=41490944, sha256='0ea4a1c5d0a0f063acda2eaf9c05ff6426adb99c9a75f2ac4af8268fcb3bb53a')
AUTH_KEY_IDENTITY = dict(size=32, sha256='7eb6a32ca96daa9cd125b2798834f45515265a76d653ae719091d98f0a1f515b')
PROFILE = source.LOCAL_PROFILE
CONTROL = SimpleNamespace(BOOT_ID_SEMANTIC='kernel-uuid-lowercase-ascii36-sha256-v2',
                         BOOT_RECEIPT_SEMANTIC='sha256-of-boot-v2-wire-digest')

# The established initial-frame codec consumes these explicit protocol fields.
# No candidate source text or function globals are projected into this object.
runtime = SimpleNamespace(__file__=__file__, TARGET='SM-S906N/g0q/S906NKSS7FYG8',
    FRAME_MAGIC=b'S328', FRAME_VERSION=1, FRAME_OPEN=1, FRAME_EXEC=2, FRAME_CLOSE=3,
    FRAME_READY=129, FRAME_DATA=130, FRAME_EXIT=131, FRAME_DONE=132, FRAME_CHALLENGE=133,
    FRAME_AUTH=4, FRAME_BOOT_ID=135, FRAME_CANCEL=5, FRAME_CANCEL_ACK=136,
    AUTH_DOMAIN_OPEN=b'S22PLUS-FYG8-P328-AUTH-OPEN-v1',
    AUTH_DOMAIN_READY=b'S22PLUS-FYG8-P328-AUTH-READY-v1',
    AUTH_DOMAIN_EXEC=b'S22PLUS-FYG8-P328-AUTH-EXEC-v1',
    AUTH_DOMAIN_CLOSE=b'S22PLUS-FYG8-P328-AUTH-CLOSE-v1',
    AUTH_DOMAIN_BOOT_ID=b'S22PLUS-FYG8-P384-AUTH-KERNEL-BOOT-ID-v2',
    AUTH_KEY_SIZE=32, AUTH_TAG_SIZE=32, NONCE_SIZE=32,
    DIAGNOSTIC_FRAME_TYPE=134, DIAGNOSTIC_STAGE_CONSOLE_ENTER=0,
    DIAGNOSTIC_STAGE_OPEN_PARSED=1, DIAGNOSTIC_STAGE_RNG=2, RNG_EAGAIN_RETRY_LIMIT=64,
    P335_FRAME_BOOT_ID=135, P335_BOOT_ID_SEQUENCE=2, P335_BOOT_ID_SIZE=32, P335_COMMANDS_PER_SESSION=1,
    DEFAULT_COMMANDS=(console.health.COMMAND,), DEVICE_BANNER=b'S22PLUS-FYG8-E3:'+IDENTITY.run_id_hex.encode()+b'\n',
    COMMAND_TIMEOUT_SEC=15, MAX_COMMANDS=2, MAX_COMMAND_SIZE=1023, MAX_FRAME_PAYLOAD=1055,
    MAX_OUTPUT_BYTES=131072, MAX_SESSIONS=1,
    CONTRACT_ID='s22plus-fyg8-p384-local-display-runtime-v1', SCHEMA='s22plus-fyg8-p384-local-display-runtime-v1')
runtime.SOURCE = Path(source.__file__)
runtime.OPEN_HEADER_SIZE = 16
runtime.OPEN_HEADER_WORD_STAGES = (4, 5, 6, 7)
runtime.OPEN_READ_BRANCHES = {0: 'header-read-errno', 1: 'header-grammar', 2: 'body-read-errno', 3: 'crc', 4: 'open-semantic'}
for _prefix in ('P328', 'P329', 'P330', 'P331', 'P332', 'P333', 'P334', 'P335', 'P345', 'P384'):
    setattr(runtime, _prefix+'_RUN_ID', bytes.fromhex(IDENTITY.run_id_hex))
    setattr(runtime, _prefix+'_RUN_ID_HEX', IDENTITY.run_id_hex)
runtime.build_helper = lambda: source.helper_template(IDENTITY, profile=PROFILE)
runtime.materialize_helper = lambda key: source.materialize_helper(IDENTITY, key, profile=PROFILE)
runtime.audit_binding = lambda: dict(source.profile_contract(PROFILE), run_id_hex=IDENTITY.run_id_hex,
                                     target=runtime.TARGET, live_authorized=False)
observer = console.Observer(IDENTITY, CONTROL)
return_host = owner.ReturnHost(IDENTITY, CONTROL)
console_owner = owner.EmptyPlan(IDENTITY)
artifact = artifacts.Artifacts(IDENTITY, IMAGE_IDENTITY, AUTH_KEY_IDENTITY)
adapter = carrier.CarrierAdapter(IDENTITY, observer)
