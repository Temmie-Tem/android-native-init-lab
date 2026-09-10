"""Reusable direct-candidate static and private H0 bundle producer.

The declaration supplies image semantics; this helper preserves the existing
Process-v2 archive, evidence and source-closure readers. No device IO lives here.
"""
import hashlib
import json
from pathlib import Path


class CandidateStatic:
    def __init__(self, declaration, builder, authority, *, extra_sources):
        self.declaration, self.builder = declaration, builder
        self.root = builder.ROOT
        self.authority = Path(authority)
        self.artifact, self.adapter, self.observer = declaration.artifact, declaration.adapter, declaration.observer
        self.prefix = declaration.IDENTITY.namespace
        self.RUN_ID = declaration.IDENTITY.run_id_hex
        self.TARGET = dict(builder.TARGET)
        self.SCHEMA = f's22plus_fyg8_{self.prefix}_process_v2_candidate_static_v1'
        self.VERDICT = f'PASS_{self.prefix.upper()}_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY'
        self.RUN_SCHEMA = f's22plus_fyg8_{self.prefix}_process_v2_run_manifest_v1'
        self.CHECK_SCHEMA = f's22plus_fyg8_{self.prefix}_process_v2_static_result_v1'
        self.CHECK_VERDICT = f'PASS_{self.prefix.upper()}_PROCESS_V2_STATIC_RESULT_HOST_ONLY'
        self.DEFAULT_OUTPUT = self.root/f'workspace/private/outputs/s22plus_fyg8_{self.prefix}/candidate-static-v1.json'
        self.ROLLBACK_AP = self.root/'workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5'
        self.ROLLBACK_IDENTITY = dict(size=23367721, sha256='d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56')
        paths = {Path(__file__), self.authority, Path(builder.__file__), Path(declaration.__file__)}
        paths.update(self.root/name for name in builder.source_receipts())
        paths.update(self.root/name for name in self.adapter.SOURCE_PATHS.values())
        paths.update(self.root/name for name in extra_sources)
        self.SOURCE_FILES = {self.prefix+'_source_'+hashlib.sha256(str(path.relative_to(self.root)).encode()).hexdigest()[:16]: path
                             for path in sorted(paths)}

    @staticmethod
    def canonical(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

    def receipt(self, path):
        raw = self.artifact.stable_bytes(Path(path))
        return dict(path=str(Path(path).relative_to(self.root)), size=len(raw), sha256=hashlib.sha256(raw).hexdigest())

    def source_receipts(self):
        return {name: self.receipt(path) for name, path in self.SOURCE_FILES.items()}

    def build_result(self):
        built = self.builder.audit_existing()
        inventory = built['candidate']['a']['inventory']
        assets = {name: pin for name, pin in inventory.items() if name in ('s22-display', 's22-display-modules')
                  or name.startswith('s22-display-modules/')}
        self.artifact.validate_rollback_ap(self.ROLLBACK_AP, self.ROLLBACK_IDENTITY)
        candidate = dict(a=built['candidate']['a'], b=built['candidate']['b'], image=built['image'], init=built['init'],
            child=built['child'], busybox={k: inventory['bin/busybox'][k] for k in ('size','sha256')},
            display_assets=assets, boot_only=True, byte_identical=True)
        return dict(schema=self.SCHEMA, verdict=self.VERDICT, target=self.TARGET, run_id=self.RUN_ID,
            predecessor_run_id=self.builder.REFERENCE_IDENTITY.run_id_hex,
            source_contract_id=self.adapter.PARENT_SOURCE_CONTRACT_ID,
            userspace_overlay_contract_id=self.adapter.OVERLAY_CONTRACT_ID, profile=self.adapter.PROFILE,
            authority_source=self.receipt(self.authority), builder_result=self.receipt(self.builder.DEFAULT_OUTPUT_ROOT/'result.json'),
            candidate=candidate, source_closure=self.source_receipts(),
            rollback_ap=dict(path=str(self.ROLLBACK_AP.relative_to(self.root)), **self.ROLLBACK_IDENTITY),
            auth_key=self.artifact.auth_key_identity(), adapter=self.adapter.audit(),
            qualification=self.adapter.acceptance_fixture()['qualification_commands'],
            observer_binding=self.observer.audit_binding(), safety=dict(host_only=True, device_contact=False,
                live_authorized=False, later_action_lease_active=False, mandatory_rollback=True))

    def validate_result(self, value):
        if self.canonical(value) != self.canonical(self.build_result()):
            raise ValueError('direct native static binding does not regenerate')
        return value

    def promotion_payloads(self, static, static_receipt, *, run_id):
        common = dict(run_id=self.RUN_ID, target=self.TARGET,
            source_contract_id=self.adapter.PARENT_SOURCE_CONTRACT_ID,
            userspace_overlay_contract_id=self.adapter.OVERLAY_CONTRACT_ID,
            decoder=self.adapter.DECODER_ID, policy_id=self.adapter.POLICY_ID,
            profile=self.adapter.PROFILE, candidate_static=dict(static_receipt),
            candidate_ap=static['candidate']['a']['ap_tar_md5'], qualification=static['qualification'],
            host_only=True, device_contact=False, live_authorized=False, later_action_lease_active=False,
            mandatory_rollback=True)
        return (dict(common, schema=self.RUN_SCHEMA, promotion_run_id=run_id),
                dict(common, schema=self.CHECK_SCHEMA, verdict=self.CHECK_VERDICT, promotion_run_id=run_id))

    def prepare_h0(self, output):
        import device_action_f1_v2 as core
        import device_action_f1_live_v2 as live
        import device_action_f1_evidence_v2 as evidence
        output = Path(output).absolute()
        if (output.exists() or output.is_symlink() or output.resolve() != output
                or not output.is_relative_to(self.root/'workspace/private')):
            raise ValueError('fresh direct private H0 bundle output required')
        value = self.build_result(); output.mkdir(mode=0o700, parents=True)
        self.builder.write(output/'candidate-static.json', self.canonical(value))
        static_pin = self.receipt(output/'candidate-static.json')
        run, check = self.promotion_payloads(value, static_pin, run_id=f's22plus-fyg8-{self.prefix}-h0-review')
        for name, body in (('run-manifest.json', run), ('static-check-result.json', check)):
            self.builder.write(output/name, self.canonical(body))
        acceptance = self.adapter.acceptance_fixture()
        acceptance['contract'] = {name: self.receipt(output/file) for name, file in (
            ('candidate_static','candidate-static.json'), ('run_manifest','run-manifest.json'),
            ('static_check','static-check-result.json'))}
        manifest = dict(schema=core.MANIFEST_SCHEMA, manifest_id=f's22plus-fyg8-{self.prefix}-native-baseline-v1-ready-1',
            run_id=f's22plus-fyg8-{self.prefix}-native-baseline-v1', status='ready-for-f1-approval',
            target_profile='workspace/public/src/device-action/profiles/s22plus_fyg8.json',
            candidate_ap=self.receipt(self.builder.DEFAULT_OUTPUT_ROOT/'candidate-a/odin4/AP.tar.md5'),
            rollback_ap=self.receipt(self.ROLLBACK_AP), allowed_member='boot.img.lz4',
            observation=dict(timeout_sec=60, acceptance=acceptance,
                candidate_observer=evidence._shell_observer_spec(self.prefix),
                **{evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY:evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE}),
            final_health_profile='s22plus-fyg8-magisk', runner_version=core.RUNNER_VERSION)
        path = output/'review-manifest.json'; self.builder.write(path, self.canonical(manifest))
        bundle = core.verify_bundle(self.root, path)
        closure = live._closure(self.root, bundle)
        if self.source_receipts() != value['source_closure']:
            raise ValueError('direct native execution sources changed during H0 verification')
        self.builder.write(output/'execution-closure.json', self.canonical(closure))
        import s22plus_native_baseline_owner_v1 as owner
        probe = output/'serialization-probe'; probe.mkdir(mode=0o700)
        request = owner.request_value(live, self.root, bundle,
            target={'serial':'H0_UNBOUND', 'topology':live.p324_typec_lane.SOURCE_TOPOLOGY},
            manifest_receipt=self.receipt(path), review_receipt={'H0_ONLY':'NO_AUTHORITY'},
            operations=['bootstrap'], reservations=1, seconds=600, closure=closure)
        # Outside the grant/request root, with no independent authority or
        # physical target binding: this is never an approval proposal.
        serialized = owner.publish(probe/'request.json', request)
        if not owner.same(owner.read(probe/'request.json')[0], request):
            raise ValueError('actual full native request did not reopen')
        result = dict(schema=f's22plus-fyg8-{self.prefix}-review-bundle-v1',
            verdict=f'PASS_{self.prefix.upper()}_REVIEW_BUNDLE_H0', manifest=self.receipt(path),
            candidate_ap=value['candidate']['a']['ap_tar_md5'],
            execution_closure=self.receipt(output/'execution-closure.json'),
            full_request_serialization=serialized,
            source_inputs=value['source_closure'], device_contact=False, live_authorized=False)
        self.builder.write(output/'result.json', self.canonical(result))
        return result
