"""Fixed storage-before-client order; no target I/O or authority."""
from s22plus_native_records_v3 import require

PROFILE='debian-file-first-v1'
NAMESPACE='p426'
VERSION='v0.6.0-rc.2'
DOMAIN=b'S22PLUS-FYG8-DEBIAN-FILE-FIRST-v1'
CLIENTS=('msm_geni_se','gpi','i2c_msm_geni','spu_verify','mfd_max77705','pdic_max77705')
STORAGE_COUNT=76


def modules(inventory,logger):
    rows=inventory['modules'];count=inventory['platform_count']
    require(count==73 and len(rows)==81 and
        [r['runtime_name'] for r in rows[count-6:count]]==list(CLIENTS) and
        rows[count-7]['runtime_name']=='qcom_spmi_pmic','storage-first original plan differs')
    selected=[logger,*rows[:count-6],*rows[count:],*rows[count-6:count]]
    loaded=set();providers=set()
    for row in selected:
        require(set(row.get('declared_dependencies',()))<=loaded and
            set(row.get('earlier_symbol_providers',()))<=providers,
            'storage-first supplier follows its consumer')
        loaded.add(row['runtime_name']);providers.add(row['name'])
    require(len(selected)==82 and len(loaded)==82,'storage-first module set differs')
    return selected
