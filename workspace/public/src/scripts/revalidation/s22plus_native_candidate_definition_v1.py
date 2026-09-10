"""Shared declaration of the direct native framing ABI for new candidates.

Historical declarations remain frozen. Identity/profile are explicit data;
no candidate source text or function globals are projected into this object.
"""
from pathlib import Path
from types import SimpleNamespace

import s22plus_native_source_v1 as source


def runtime(identity, profile, commands):
    contract = source.profile_contract(profile)
    result = SimpleNamespace(__file__=__file__, TARGET='SM-S906N/g0q/S906NKSS7FYG8',
        FRAME_MAGIC=b'S328', FRAME_VERSION=1, FRAME_OPEN=1, FRAME_EXEC=2, FRAME_CLOSE=3,
        FRAME_READY=129, FRAME_DATA=130, FRAME_EXIT=131, FRAME_DONE=132, FRAME_CHALLENGE=133,
        FRAME_AUTH=4, FRAME_BOOT_ID=135, FRAME_CANCEL=5, FRAME_CANCEL_ACK=136,
        AUTH_DOMAIN_OPEN=b'S22PLUS-FYG8-P328-AUTH-OPEN-v1',
        AUTH_DOMAIN_READY=b'S22PLUS-FYG8-P328-AUTH-READY-v1',
        AUTH_DOMAIN_EXEC=b'S22PLUS-FYG8-P328-AUTH-EXEC-v1',
        AUTH_DOMAIN_CLOSE=b'S22PLUS-FYG8-P328-AUTH-CLOSE-v1',
        AUTH_DOMAIN_BOOT_ID=('S22PLUS-FYG8-'+identity.namespace.upper()+'-AUTH-KERNEL-BOOT-ID-v2').encode(),
        AUTH_KEY_SIZE=32, AUTH_TAG_SIZE=32, NONCE_SIZE=32,
        DIAGNOSTIC_FRAME_TYPE=134, DIAGNOSTIC_STAGE_CONSOLE_ENTER=0,
        DIAGNOSTIC_STAGE_OPEN_PARSED=1, DIAGNOSTIC_STAGE_RNG=2, RNG_EAGAIN_RETRY_LIMIT=64,
        P335_FRAME_BOOT_ID=135, P335_BOOT_ID_SEQUENCE=2, P335_BOOT_ID_SIZE=32, P335_COMMANDS_PER_SESSION=1,
        DEFAULT_COMMANDS=tuple(commands), DEVICE_BANNER=b'S22PLUS-FYG8-E3:'+identity.run_id_hex.encode()+b'\n',
        COMMAND_TIMEOUT_SEC=15, MAX_COMMANDS=2, MAX_COMMAND_SIZE=1023, MAX_FRAME_PAYLOAD=1055,
        MAX_OUTPUT_BYTES=131072, MAX_SESSIONS=contract.get('authentication_limit', 1),
        CONTRACT_ID='s22plus-fyg8-'+identity.namespace+'-'+profile+'-runtime',
        SCHEMA='s22plus-fyg8-'+identity.namespace+'-'+profile+'-runtime',
        OPEN_HEADER_SIZE=16, OPEN_HEADER_WORD_STAGES=(4, 5, 6, 7),
        OPEN_READ_BRANCHES={0:'header-read-errno',1:'header-grammar',2:'body-read-errno',3:'crc',4:'open-semantic'})
    result.SOURCE = Path(source.__file__)
    for prefix in ('P328','P329','P330','P331','P332','P333','P334','P335','P345',identity.namespace.upper()):
        setattr(result, prefix+'_RUN_ID', bytes.fromhex(identity.run_id_hex))
        setattr(result, prefix+'_RUN_ID_HEX', identity.run_id_hex)
    result.build_helper = lambda: source.helper_template(identity, profile=profile)
    result.materialize_helper = lambda key: source.materialize_helper(identity, key, profile=profile)
    result.audit_binding = lambda: dict(contract, run_id_hex=identity.run_id_hex,
                                       target=result.TARGET, live_authorized=False)
    return result
