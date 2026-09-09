"""P375 Carrier decoder binding; Carrier never substitutes for console proof."""
from pathlib import Path
import hashlib

_TEMPLATE=Path(__file__).with_name('s22plus_fyg8_p345_stock_process_v2_adapter.py')
_raw=_TEMPLATE.read_bytes()
if len(_raw)!=7753 or hashlib.sha256(_raw).hexdigest()!='f9934c7d274a93ee079ee15e5f7daca089326d8da075086f03eaf77acf7bae40':
    raise ValueError('P375 sealed raw adapter template differs')
_raw=_raw.replace(b'P345',b'P375').replace(b'p345',b'p375')
_raw=_raw.replace(b'readonly-research-shell-v1',b'root-console-v1').replace(b'readonly_research_shell_v1',b'root_console_v1')
exec(compile(_raw,str(_TEMPLATE)+'#p375-raw','exec'),globals())

INITIAL_SESSION_COUNT=SAME_FD_SESSION_COUNT=1
INITIAL_RECONNECT_COUNT=IDLE_SECONDS=0
TOTAL_COMMANDS=5
POLICY_PREIMAGE=OVERLAY_CONTRACT_ID+'|'+P375_RUN_ID_HEX+'|root-sh-c|one-authenticated-tty|ram-work|bounded-separated-output|process-group-cancel|control-independent|finite-attended-session|exact-boot-rollback'
POLICY_ID=hashlib.sha256(POLICY_PREIMAGE.encode('ascii')).hexdigest()[:32]


def _contract():
    return dict(userspace_overlay_contract_id=OVERLAY_CONTRACT_ID,decoder=DECODER_ID,
        policy_id=POLICY_ID,profile=PROFILE,source_contract_id=PARENT_SOURCE_CONTRACT_ID,
        observer_contract_id=OBSERVER_CONTRACT_ID,payload_abi=P320_PAYLOAD_ABI,
        observer_receipt_size=OBSERVER_RECEIPT_SIZE,causal_result_allowed=False,candidate_success=False,
        runtime_behavior_unchanged=False,runtime_delta_identity_only=False,
        read_only_child_required=False,root_console=True,authenticated_cancel=True,
        initial_session_count=1,same_fd_session_count=1,initial_reconnect_count=0,idle_seconds=0,
        later_action_lease_active=False,mandatory_rollback=True,
        native_return_control=True,control_mode='download',control_ack_scope='acceptance-only',
        native_usb_departure_before_odin=True,software_window_renewed=False,
        odin_inventory_errors_tolerated=False,automatic_recovery_proved=False,
        native_session_ms=600000,root_workspace_bytes=67108864,
        arbitrary_operator_commands=True,permanent_boundaries_unchanged=True)


def acceptance_fixture():
    value=raw_parser_source.acceptance_fixture()
    value.update(decoder=DECODER_ID,policy_id=POLICY_ID,run_id=P375_RUN_ID_HEX,
        userspace_overlay_contract_id=OVERLAY_CONTRACT_ID,
        observer_contract=dict(id=OBSERVER_CONTRACT_ID,payload_abi=P320_PAYLOAD_ABI,receipt_size=OBSERVER_RECEIPT_SIZE),
        observer_contract_id=OBSERVER_CONTRACT_ID,initial_session_count=1,same_fd_session_count=1,
        initial_reconnect_count=0,idle_seconds=0,later_action_lease_active=False,mandatory_rollback=True,
        qualification_schema=observer.SCHEMA,qualification_commands=[dict(ordinal=step.ordinal,
            name=step.name,command_hex=step.command.hex(),expected_outcome='cancelled' if step.ordinal==4 else 'exit7' if step.ordinal==3 else 'ok')
            for step in observer.QUALIFICATION_COMMANDS])
    return value


def audit():
    return {**bind_exact_sources(), 'schema':SCHEMA,
        'verdict':'PASS_P375_STOCK_PROCESS_V2_ADAPTER_H0','contract':_contract(),
        'initial_session_count':1,'initial_reconnect_count':0,'total_commands':5,
        'runtime_behavior_unchanged':False,'catalog_unchanged':False,
        'later_action_lease_active':False,'mandatory_rollback':True}
