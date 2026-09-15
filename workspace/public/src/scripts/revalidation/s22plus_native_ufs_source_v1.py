"""Fixed FYG8 UFS initialization over the existing reconnect/thermal runtime."""
from pathlib import Path

import s22plus_native_reconnect_source_v1 as previous

resident=previous.resident
ROOT,NATIVE,PROFILE=previous.ROOT,previous.NATIVE,previous.PROFILE
THERMAL_PROFILE,RECONNECT_PROFILE=previous.THERMAL_PROFILE,previous.RECONNECT_PROFILE
STORAGE_PROFILE='fyg8-stock-ufs-v1'
POLICY=ROOT/'docs/operations/S22PLUS_NATIVE_UFS_V1.md'
LOADER=NATIVE/'s22plus_native_ufs_load_v1.inc.c'
SAMPLE_MAGIC,VIEW_MAGIC=previous.SAMPLE_MAGIC,previous.VIEW_MAGIC
helper_template,materialize_helper=previous.helper_template,previous.materialize_helper
provider_sources,provider_files=previous.provider_sources,previous.provider_files
core_source,sensor_map,wire_source=previous.core_source,previous.sensor_map,previous.wire_source

# One fixed declaration supplies runtime names/sizes and H0 byte qualification.
MODULES=(
    ('phy-qcom-ufs.ko','phy_qcom_ufs',42208,'ebe4d3362e9b8d42510018d05c065b4364124b97c932a9798cbc87ddf1e5f501'),
    ('phy-qcom-ufs-qmp-v4-waipio.ko','phy_qcom_ufs_qmp_v4_waipio',30272,'cfc078b154b8741146556d64dae3459dd0f8b6b2056efcc6ce0b37ade3af18c0'),
    ('tmecom-intf.ko','tmecom_intf',39672,'d79bb41e4e323839f3af027f0fd7167c7fa729dea990e8863dc1864e99411b90'),
    ('hwkm.ko','hwkm',29200,'bfa351577a6166b775da8b9cd0fd7c9395197c883875d795b59ee0b82a145e32'),
    ('crypto-qti-hwkm.ko','crypto_qti_hwkm',18624,'bc696acc0884161c632fda2cdac9acdfa3b771f710a9c35a1a98011098eb6b5a'),
    ('crypto-qti-common.ko','crypto_qti_common',59600,'87f430e70cd5a88bf56b57bc3155ddedb93837ecfb8b8acb6003f071c54eff9c'),
    ('ufshcd-crypto-qti.ko','ufshcd_crypto_qti',18440,'b28515876002542c86aa58e8ee79bf6eeebd28c5771e23f210c8e2a6bc4f81e5'),
    ('ufs_qcom.ko','ufs_qcom',275352,'53ab8e05eaac014f87888420c8640184986cbc8b95ac0a13efb83fd005fab9ab'),
)


def loader_source():
    rows=b''.join(('    {"'+name+'", '+str(size)+'ULL},\n').encode()
        for name,_,size,_ in MODULES)
    return (b'struct ufs1_module { const char *name; uint64_t size; };\n'
        b'static const struct ufs1_module ufs1_modules[] = {\n'+rows+b'};\n'
        +resident.common._read(LOADER))


def render_display(identity,modules):
    selected={name for name,_,_,_ in MODULES}
    raw=previous.render_display(identity,tuple(row for row in modules if row.name not in selected))
    raw=resident.replace(raw,b'int main(int argc,char **argv) {',
        loader_source()+b'\nint main(int argc,char **argv) {')
    return resident.replace(raw,b'    p351_prepare_driver();',
        b'    p351_prepare_driver();\n    ufs1_prepare();')


def profile_contract():
    return dict(previous.profile_contract(),storage_profile=STORAGE_PROFILE,
        storage_modules=[name for name,_,_,_ in MODULES],
        storage_initialization='fixed stock driver insertion and ordinary UFS/SCSI discovery',
        storage_host_partition_writes=False,storage_key_requests=False,
        storage_module_retry=False,storage_access_requires_separate_census=True)


def source_files():
    return tuple(sorted(set(previous.source_files())|{Path(__file__),LOADER,POLICY}))
