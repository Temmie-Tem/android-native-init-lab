"""Shared fixed-variant metadata; complements actual runtime/observer validation."""
_step_name=Path(__file__).name
_step_suffix=_STEP_MODULE_NAME
if _step_suffix.endswith('_artifact_identity.py'):
    _step_previous_identity=globals()['validate_'+_STEP_PREFIX+'_identity']
    def _step_identity():
        value=_step_previous_identity()
        value.update(total_command_count=6+_STEP_MAX,control_sequence=14,status_count=2,
            display_steps=_STEP_MAX,display_exit_before_completion=_STEP_EXIT)
        return value
    globals()['validate_'+_STEP_PREFIX+'_identity']=_step_identity

if _step_suffix.endswith('_stock_process_v2_adapter.py'):
    TOTAL_COMMANDS=6+_STEP_MAX
    POLICY_PREIMAGE=OVERLAY_CONTRACT_ID+'|'+globals()[_STEP_PREFIX.upper()+'_RUN_ID_HEX']+'|eventfd-fixed-steps='+str(_STEP_MAX)+'|exit='+str(_STEP_EXIT)+'|control-14|original-deadline|exact-rollback'
    POLICY_ID=hashlib.sha256(POLICY_PREIMAGE.encode('ascii')).hexdigest()[:32]
    _step_contract=_contract;_step_acceptance=acceptance_fixture;_step_adapter_audit=audit
    def _contract():
        value=_step_contract();value.update(control_sequence=14,status_response_bytes=12,
            step_maximum=_STEP_MAX,step_exit_before_completion=_STEP_EXIT,step_ack_scope='queued-only')
        return value
    def acceptance_fixture():
        value=_step_acceptance();value.update(total_commands=TOTAL_COMMANDS,display_steps=_STEP_MAX,display_exit_before_completion=_STEP_EXIT)
        return value
    def audit():
        value=_step_adapter_audit();value.update(total_commands=TOTAL_COMMANDS,contract=_contract())
        return value
