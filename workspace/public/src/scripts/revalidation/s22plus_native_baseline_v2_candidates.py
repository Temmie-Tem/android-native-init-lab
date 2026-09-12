"""Closed resident baseline/experiment catalog; registration is H0 only.

Each declaration owns one content identity. Admission and the original global
candidate claim are independent records made only by the attended owner.
"""
import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace

import s22plus_native_source_v1 as common
import s22plus_native_resident_source_v1 as source
import s22plus_native_baseline_resident_v2 as resident
import s22plus_native_baseline_health_v1 as health
import s22plus_native_candidate_definition_v1 as definition
import s22plus_native_candidate_artifacts_v1 as artifacts
import s22plus_native_carrier_adapter_v1 as carrier
import s22plus_native_console_owner_v1 as owner
import s22plus_native_thermal_source_v1 as thermal_source
import s22plus_native_thermal_observer_v1 as thermal_observer

ROOT = common.ROOT
POLICY = 'native-baseline-v2'
AUTH_KEY_IDENTITY = dict(size=32,sha256='7eb6a32ca96daa9cd125b2798834f45515265a76d653ae719091d98f0a1f515b')
CONTROL = SimpleNamespace(BOOT_ID_SEMANTIC='kernel-uuid-lowercase-ascii36-sha256-v2',
                         BOOT_RECEIPT_SEMANTIC='sha256-of-boot-v2-wire-digest')


def declaration(namespace, run_id, version, image_sha256, *, runtime_source=source,
                observer_class=resident.Observer, added_modules=()):
    selected = common.Identity(namespace,run_id,version)
    runtime = definition.runtime(selected,common.BASELINE_PROFILE,(health.COMMAND,))
    runtime.SOURCE = Path(runtime_source.__file__)
    runtime.CONTRACT_ID = runtime.SCHEMA = f's22plus-fyg8-{namespace}-resident-baseline-runtime-v2'
    runtime.build_helper = lambda:runtime_source.helper_template(selected)
    runtime.materialize_helper = lambda key:runtime_source.materialize_helper(selected,key)
    runtime.audit_binding = lambda:dict(runtime_source.profile_contract(),run_id_hex=run_id,
                                        target=runtime.TARGET,live_authorized=False)
    observer = observer_class(selected,CONTROL)
    artifact = artifacts.Artifacts(selected,dict(size=41490944,sha256=image_sha256),AUTH_KEY_IDENTITY)
    artifact.PACKAGED_MODULE_NAMES = (*artifact.PACKAGED_MODULE_NAMES,*added_modules)
    adapter = carrier.CarrierAdapter(selected,observer)
    adapter.OVERLAY_CONTRACT_ID = f's22plus-fyg8-{namespace}-native-baseline-console-v2'
    adapter.DECODER_ID = f's22plus_fyg8_{namespace}_native_baseline_console_v2'
    adapter.POLICY_ID = hashlib.sha256((adapter.OVERLAY_CONTRACT_ID+'|'+run_id+
        '|fixed-health-pair|resident-clean-detach|exact-N-E-N|one-exact-A').encode()).hexdigest()[:32]
    adapter.INITIAL_SESSION_COUNT = 2
    adapter.SAME_FD_SESSION_COUNT = adapter.INITIAL_RECONNECT_COUNT = 1
    adapter.TOTAL_COMMANDS = 3
    adapter.NATIVE_SOURCE_PROFILE = runtime_source.PROFILE
    return SimpleNamespace(__file__=__file__,IDENTITY=selected,PROFILE=runtime_source.PROFILE,OWNER_PROFILE=POLICY,
        THERMAL_PROFILE=getattr(runtime_source,'THERMAL_PROFILE',None),
        runtime=runtime,observer=observer,artifact=artifact,adapter=adapter,
        return_host=owner.ReturnHost(selected,CONTROL),console_owner=owner.EmptyPlan(selected))


DECLARATIONS = {
    'p387':declaration('p387','d138d789faee28fd9fbd7ee576913c61','v0.2.0-rc.5',
                       '64896d9d304bcb094cd28067d372f7e52758ef0ace39b99421dd630521987ea7'),
    'p388':declaration('p388','c751faa0c8580d07bc3c355985fc0c25','v0.2.0-rc.6',
                       '4c20aa2bbfa6f8254daed2ca63d9efb8564e8b27d968bcb77278fee9f9a380b9'),
    'p389':declaration('p389','60d377fedd013a3cd41b7afc3b79563b','v0.2.0-rc.7',
                       'fe8dfd63799efba54387e9071a5394a80e6758293c673d59f5f1c7bc55370f05',
                       runtime_source=thermal_source,observer_class=thermal_observer.Observer,
                       added_modules=('qcom-vadc-common.ko','qcom-spmi-adc5.ko','s22plus_thermal_telemetry.ko')),
}


def static(prefix):
    if prefix not in DECLARATIONS: raise ValueError('unknown resident baseline declaration')
    analysis = ROOT/'workspace/public/src/scripts/analysis'
    if str(analysis) not in sys.path: sys.path.insert(0,str(analysis))
    from s22plus_native_baseline_v2_build import Builder, EXTRA_SOURCES
    from s22plus_native_candidate_static_v1 import CandidateStatic
    declared = DECLARATIONS[prefix]
    if declared.THERMAL_PROFILE is not None:
        from s22plus_native_thermal_build_v1 import Builder, EXTRA_SOURCES
    return CandidateStatic(declared,Builder(declared),__file__,extra_sources=EXTRA_SOURCES)


def static_for(bundle):
    run_id = bundle.manifest['observation']['acceptance']['run_id']
    matches = [prefix for prefix,d in DECLARATIONS.items() if d.IDENTITY.run_id_hex == run_id]
    if len(matches) != 1: raise ValueError('bundle is outside the resident baseline catalog')
    return static(matches[0])


def review_sources():
    import device_action_f1_live_v2 as live
    sources = {}
    groups = []
    for prefix, declared in DECLARATIONS.items():
        # Source selection needs the exact declared observer route, including
        # its conditional transport and final-health readers, but no AP or
        # target binding. This object is never a prepared/live bundle.
        route = SimpleNamespace(manifest=dict(observation=dict(
            acceptance=declared.adapter.acceptance_fixture(),
            candidate_observer=live.typed_evidence._shell_observer_spec(prefix),
            **{live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY:
               live.typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE})))
        groups.append(live._closure(ROOT, route)['sources'].values())
    for group in groups:
        for original in group:
            path = Path(original['path'])
            if path.is_absolute(): path = path.relative_to(ROOT)
            receipt = dict(original, path=str(path))
            key = 'source_'+hashlib.sha256(receipt['path'].encode()).hexdigest()[:16]
            if key in sources and sources[key] != receipt: raise ValueError('review source collision')
            sources[key] = receipt
    return dict(sorted(sources.items()))
