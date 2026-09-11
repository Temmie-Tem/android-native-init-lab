"""P386 / v0.2.0-rc.4 resident adoption; H0 only, ordinary one-N/one-A."""
import hashlib
from pathlib import Path
from types import SimpleNamespace

import s22plus_native_source_v1 as common
import s22plus_native_resident_source_v1 as source
import s22plus_native_resident_observer_v1 as resident
import s22plus_native_candidate_definition_v1 as definition
import s22plus_native_console_owner_v1 as owner
import s22plus_native_candidate_artifacts_v1 as artifacts
import s22plus_native_carrier_adapter_v1 as carrier

IDENTITY=common.Identity('p386','7f1353bace30354ce06cf401add38fec','v0.2.0-rc.4')
PROFILE=source.PROFILE
IMAGE_IDENTITY=dict(size=41490944,sha256='2b856336482137d0c9c3fbc1593cd79a859e039f5e226f65fdb8fb0c59cd2ee9')
AUTH_KEY_IDENTITY=dict(size=32,sha256='7eb6a32ca96daa9cd125b2798834f45515265a76d653ae719091d98f0a1f515b')
CONTROL=SimpleNamespace(BOOT_ID_SEMANTIC='kernel-uuid-lowercase-ascii36-sha256-v2',BOOT_RECEIPT_SEMANTIC='sha256-of-boot-v2-wire-digest')
runtime=definition.runtime(IDENTITY,common.BASELINE_PROFILE,(resident.health.COMMAND,))
runtime.SOURCE=Path(source.__file__)
runtime.MAX_SESSIONS=4
runtime.CONTRACT_ID=runtime.SCHEMA='s22plus-fyg8-p386-resident-runtime-v1'
runtime.build_helper=lambda:source.helper_template(IDENTITY)
runtime.materialize_helper=lambda key:source.materialize_helper(IDENTITY,key)
runtime.audit_binding=lambda:dict(source.profile_contract(),run_id_hex=IDENTITY.run_id_hex,target=runtime.TARGET,live_authorized=False)
observer=resident.Observer(IDENTITY,CONTROL)
return_host=owner.ReturnHost(IDENTITY,CONTROL)
console_owner=owner.EmptyPlan(IDENTITY)
artifact=artifacts.Artifacts(IDENTITY,IMAGE_IDENTITY,AUTH_KEY_IDENTITY)
adapter=carrier.CarrierAdapter(IDENTITY,observer)
adapter.OVERLAY_CONTRACT_ID='s22plus-fyg8-p386-native-resident-console-v1'
adapter.DECODER_ID='s22plus_fyg8_p386_native_resident_console_v1'
adapter.POLICY_ID=hashlib.sha256((adapter.OVERLAY_CONTRACT_ID+'|'+IDENTITY.run_id_hex+
    '|four-fixed-checkpoints|1800s-native-span|clean-detach-reopen|exact-android-return').encode()).hexdigest()[:32]
adapter.INITIAL_SESSION_COUNT=4
adapter.SAME_FD_SESSION_COUNT=1
adapter.INITIAL_RECONNECT_COUNT=3
adapter.TOTAL_COMMANDS=8
adapter.NATIVE_SOURCE_PROFILE=PROFILE
