"""Build and reopen exact resident N/E boot-only packages without device IO."""
import json
from pathlib import Path
import shutil

import s22plus_native_resident_build_h0_v1 as resident_build
import s22plus_fyg8_p386_stock_candidate_build as packaging
import s22plus_native_resident_source_v1 as source

ROOT = source.ROOT
SHARED = packaging.shared
PROVIDER_INPUT = packaging.RETAINED/'provider'
_MODULES = (
    'device_action_f1_v2','device_action_f1_live_v2','device_action_f1_evidence_v2',
    'device_action_d0_v2','device_action_raw_capture_v1','consumed_candidate_registry_v1',
    's22plus_boot_only_f1_transport','s22plus_native_baseline_owner_v1','s22plus_native_baseline_backend_v1',
    's22plus_native_baseline_guard_v1','device_action_cdc_acm_observer_v1','s22plus_fyg8_p324_cdc_acm_observer',
    's22plus_native_baseline_protocol_v1','s22plus_native_baseline_observer_v1','s22plus_native_baseline_resident_v2',
    's22plus_native_baseline_v2_candidates','s22plus_native_resident_protocol_v1','s22plus_native_resident_observer_v1',
    's22plus_native_console_observer_v1','s22plus_native_console_owner_v1','s22plus_native_candidate_definition_v1',
    's22plus_native_candidate_artifacts_v1','s22plus_native_carrier_adapter_v1',
    's22plus_native_baseline_health_v1','s22plus_local_display_observer_v1','s22plus_root_console_v1',
    's22plus_fyg8_p363_return_host','s22plus_fyg8_p336_long_idle_acm_observer',
    's22plus_fyg8_p335_retained_listener_acm_observer','s22plus_fyg8_p334_first_read_rc_acm_observer',
    's22plus_fyg8_p333_open_entry_diag_acm_observer','s22plus_fyg8_p332_logical_resident_acm_observer',
    's22plus_fyg8_p330_auth_acm_observer','s22plus_fyg8_p329_auth_acm_observer','s22plus_fyg8_p328_auth_acm_observer',
    's22plus_fyg8_p363_return_spec','s22plus_native_usb_departure_v1','s22plus_native_roundtrip_owner_v1',
    's22plus_odin_transition_core','s22plus_odin_usbfs_identity','s22plus_fyg8_p324_typec_lane_binding',
    's22plus_fyg8_p325_cdc_acm_guard_adapter','s22plus_attended_f1_session_v1')
EXTRA_SOURCES = ['workspace/public/src/scripts/revalidation/'+name+'.py' for name in _MODULES] + [
    'AGENTS.md','docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md',
    'docs/operations/DEVICE_ACTION_PROCESS_V2.md','docs/operations/DEVICE_ACTION_RISK_TIERS.md',
    'docs/operations/S22PLUS_NATIVE_BASELINE_V2.md','docs/operations/S22PLUS_NATIVE_RESIDENT_H0_V1.md',
    'docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md',
    'workspace/public/src/device-action/profiles/s22plus_fyg8.json']


class Builder:
    ROOT = ROOT
    __file__ = __file__
    REFERENCE_IDENTITY = packaging.REFERENCE_IDENTITY
    TARGET = packaging.TARGET
    write = staticmethod(packaging.write)

    def __init__(self, declaration):
        self.declaration = declaration
        self.DEFAULT_OUTPUT_ROOT = ROOT/('workspace/private/outputs/s22plus-native-baseline-v2/'+declaration.IDENTITY.namespace+'/build-2')

    def source_receipts(self):
        paths = {ROOT/name for name in resident_build.closure()} | {
            Path(__file__),Path(self.declaration.artifact.__file__),Path(packaging.__file__)}
        return {str(path.relative_to(ROOT)):packaging.identity(packaging.stable(path)) for path in sorted(paths)}

    def native_selection(self):
        selected=self.declaration.IDENTITY
        return dict(namespace=selected.namespace,run_id=selected.run_id_hex,display_version=selected.display_version,
            image=self.declaration.artifact.image_identity,auth_key=self.declaration.artifact.auth_key_identity(),
            runtime_profile=source.profile_contract())

    def runtime_inputs(self, out=None):
        out = self.DEFAULT_OUTPUT_ROOT/'runtime' if out is None else Path(out).absolute()
        if out.resolve() != out or not out.is_relative_to(ROOT/'workspace/private'):
            raise ValueError('resident runtime path must be a direct private input')
        value = json.loads(packaging.stable(out/'result.json'))
        if (value['verdict'] != 'PASS_RESIDENT_BUILD_H0' or value['source_inputs'] != resident_build.closure()
                or value['profile'] != source.profile_contract() or value['ab_identical'] is not True
                or value['run_id_hex'] != self.declaration.IDENTITY.run_id_hex):
            raise ValueError('resident N/E runtime inputs changed')
        for label in ('a','b'):
            for path,pin in ((out/('userspace-'+label)/'init',value['init']),
                             (out/('renderer-'+label),value['renderer']),
                             (out/'provider'/('module-'+label+'.ko'),value['provider']['module'])):
                packaging.stable(path,expected=pin)
        for path,pin in value['toolchain_inputs'].items(): packaging.stable(Path(path),expected=pin)
        for path,pin in value['provider']['inputs'].items(): packaging.stable(ROOT/path,expected=pin)
        for name,raw in source.provider_sources().items():
            if packaging.stable(out/'provider/module-stage'/name) != raw: raise ValueError('provider source differs')
        telemetry = resident_build.telemetry
        packaging.stable(telemetry.IMAGE,expected=value['provider']['image'])
        imports = telemetry.linkage._imports(out/'provider/module-a.ko')
        exports = telemetry.linkage._image_provider_map(telemetry.IMAGE.read_bytes(),telemetry.linkage.IMAGE_SECTION_LAYOUT)
        if imports != value['provider']['imports'] or any(exports.get(k) != v for k,v in imports.items()):
            raise ValueError('resident provider linkage differs')
        return value

    def replacements(self, runtime):
        out = self.DEFAULT_OUTPUT_ROOT/'runtime'
        return {'init':packaging.stable(out/'userspace-a/init',expected=runtime['init']),
            's22-display':packaging.stable(out/'renderer-a',expected=runtime['renderer']),
            packaging.PROVIDER_MEMBER:packaging.stable(out/'provider/module-a.ko',expected=runtime['provider']['module'])}

    def build(self, *, runtime_input=None):
        out = self.DEFAULT_OUTPUT_ROOT
        if out.exists() or out.is_symlink(): raise ValueError('fresh N/E build output required')
        out.mkdir(mode=0o700,parents=True)
        pins = self.source_receipts()
        if runtime_input is None:
            runtime = resident_build.build(out/'runtime',PROVIDER_INPUT,selected=self.declaration.IDENTITY)
        else:
            runtime_input=Path(runtime_input).absolute()
            runtime=self.runtime_inputs(runtime_input)
            if any(path.is_symlink() for path in runtime_input.rglob('*')): raise ValueError('indirect runtime input')
            shutil.copytree(runtime_input,out/'runtime')
            if self.runtime_inputs() != runtime: raise ValueError('reused native runtime differs')
        reference,_ = SHARED.reference_inputs()
        image,transform = self.declaration.artifact.transform_image(
            packaging.stable(SHARED.REFERENCE/'inputs/fixed-Image',expected=reference['image']))
        self.write(out/'inputs/fixed-Image',image)
        replacements = self.replacements(runtime)
        self.declaration.artifact._validate_init(replacements['init'])
        baseline = packaging.stable(SHARED.REFERENCE/'candidate-a/boot.img',expected=reference['candidate']['a']['boot_img'])
        tools = SHARED.packager._bind_tools()
        packages = {label:packaging.build_package(out,label,baseline,image,replacements,tools) for label in ('a','b')}
        if packages['a'] != packages['b']: raise ValueError('resident N/E package A/B differs')
        inventory = packages['a']['inventory']
        result = dict(schema='s22plus-native-baseline-v2-build-v1',verdict='PASS_NATIVE_BASELINE_V2_BUILD_H0',
            run_id_hex=self.declaration.IDENTITY.run_id_hex,source_inputs=pins,native_selection=self.native_selection(),
            image=packaging.identity(image),
            image_transform=transform,init=runtime['init'],renderer=runtime['renderer'],provider=runtime['provider']['module'],
            child={k:inventory['s22-e1-child'][k] for k in ('size','sha256')},candidate=packages,byte_identical=True,
            scope=dict(tier='H0',device_contact=False,live_authorized=False,candidate_transfers=0,rollback_transfers=0))
        if pins != self.source_receipts(): raise ValueError('N/E package sources changed')
        self.write(out/'result.json',packaging.canonical(result))
        return self.audit_existing()

    def audit_existing(self):
        out = self.DEFAULT_OUTPUT_ROOT
        value = json.loads(packaging.stable(out/'result.json'))
        runtime = self.runtime_inputs()
        if (value['schema'] != 's22plus-native-baseline-v2-build-v1'
                or value['verdict'] != 'PASS_NATIVE_BASELINE_V2_BUILD_H0'
                or value['run_id_hex'] != self.declaration.IDENTITY.run_id_hex
                or value['native_selection'] != self.native_selection()
                or value['source_inputs'] != self.source_receipts()
                or value['candidate']['a'] != value['candidate']['b']): raise ValueError('N/E package binding differs')
        reference,_ = SHARED.reference_inputs()
        baseline = packaging.stable(SHARED.REFERENCE/'candidate-a/boot.img',expected=reference['candidate']['a']['boot_img'])
        image,transform = self.declaration.artifact.transform_image(
            packaging.stable(SHARED.REFERENCE/'inputs/fixed-Image',expected=reference['image']))
        if value['image_transform'] != transform or packaging.stable(out/'inputs/fixed-Image',expected=value['image']) != image:
            raise ValueError('N/E exact Image transform differs')
        replacements = self.replacements(runtime)
        for label in ('a','b'):
            folder = out/('candidate-'+label);package = value['candidate'][label]
            raw = packaging.stable(folder/'boot.img',expected=package['boot_img'])
            if packaging.check_boot(raw,baseline,image,replacements) != package['inventory']:
                raise ValueError('N/E boot inventory differs')
            packaging.stable(folder/'boot.img.lz4',expected=package['boot_img_lz4'])
            self.declaration.artifact.inspect_ap(folder/'odin4/AP.tar.md5',expected_ap=package['ap_tar_md5'],
                                                expected_image=image,expected_init=replacements['init'])
            frame,_ = SHARED.artifacts.reference._INNER._parse_ap(packaging.stable(folder/'odin4/AP.tar.md5'),'N/E AP')
            decoded = SHARED.boot.decompress_lz4_frame_python(frame,maximum=128*1024*1024)
            if decoded != raw or packaging.check_boot(decoded,baseline,image,replacements) != package['inventory']:
                raise ValueError('N/E actual AP join differs')
        return value


if __name__ == '__main__':
    import argparse
    import s22plus_native_baseline_v2_candidates as candidates
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate',choices=tuple(candidates.DECLARATIONS))
    parser.add_argument('--audit-only',action='store_true')
    parser.add_argument('--runtime-input',type=Path)
    args=parser.parse_args();builder=Builder(candidates.DECLARATIONS[args.candidate])
    result=builder.audit_existing() if args.audit_only else builder.build(runtime_input=args.runtime_input)
    print(json.dumps(dict(verdict=result['verdict'],candidate=result['candidate']['a']['ap_tar_md5']),sort_keys=True))
