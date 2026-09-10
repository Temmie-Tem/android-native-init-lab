"""P385 / v0.2.0-rc.3: bounded clean native detach and reauthentication.

Host qualification only until exact reviewed preparation and attended grant.
P384's image and consumed roundtrip claims are not reused by this declaration.
"""
import hashlib
from pathlib import Path
from types import SimpleNamespace

import s22plus_native_source_v1 as source
import s22plus_native_candidate_definition_v1 as definition
import s22plus_native_baseline_observer_v1 as baseline
import s22plus_native_baseline_health_v1 as health
import s22plus_native_console_owner_v1 as owner
import s22plus_native_candidate_artifacts_v1 as artifacts
import s22plus_native_carrier_adapter_v1 as carrier

IDENTITY = source.Identity('p385','c385f1e0a90b5e6d7c8a9b0c1d2e3f0b','v0.2.0-rc.3')
PROFILE = source.BASELINE_PROFILE
NATIVE_BYTE_SOURCES = (Path(definition.__file__),
    source.ROOT/'workspace/public/src/scripts/analysis/s22plus_fyg8_p385_stock_candidate_build.py')
IMAGE_IDENTITY = dict(size=41490944, sha256='387a30add17926c97013c71ae38d623c578d9571be11dc40e0233e4d67fa9813')
AUTH_KEY_IDENTITY = dict(size=32, sha256='7eb6a32ca96daa9cd125b2798834f45515265a76d653ae719091d98f0a1f515b')
CONTROL = SimpleNamespace(BOOT_ID_SEMANTIC='kernel-uuid-lowercase-ascii36-sha256-v2',
                         BOOT_RECEIPT_SEMANTIC='sha256-of-boot-v2-wire-digest')
runtime = definition.runtime(IDENTITY, PROFILE, (health.COMMAND,))
observer = baseline.Observer(IDENTITY, CONTROL)
return_host = owner.ReturnHost(IDENTITY, CONTROL)
console_owner = owner.EmptyPlan(IDENTITY)
artifact = artifacts.Artifacts(IDENTITY, IMAGE_IDENTITY, AUTH_KEY_IDENTITY)
adapter = carrier.CarrierAdapter(IDENTITY, observer)
adapter.OVERLAY_CONTRACT_ID = 's22plus-fyg8-p385-native-baseline-console-v1'
adapter.DECODER_ID = 's22plus_fyg8_p385_native_baseline_console_v1'
adapter.POLICY_ID = hashlib.sha256((adapter.OVERLAY_CONTRACT_ID+'|'+IDENTITY.run_id_hex+
    '|bounded-clean-detach|same-boot-fresh-auth|fixed-health|exact-android-fallback').encode()).hexdigest()[:32]
adapter.INITIAL_SESSION_COUNT = 2
adapter.SAME_FD_SESSION_COUNT = 1
adapter.INITIAL_RECONNECT_COUNT = 1
adapter.TOTAL_COMMANDS = 3
adapter.NATIVE_SOURCE_PROFILE = source.BASELINE_PROFILE
