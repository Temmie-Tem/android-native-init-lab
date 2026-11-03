#!/usr/bin/env python3
"""H0 actual-driver lookup/init traces; mocks do not prove physical PHY behavior."""
import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

import yaml
from prepare import ROOT, digest, nodes, require

DRIVER='drivers/phy/qualcomm/phy-qcom-snps-femto-v2.c'
BINDING='Documentation/devicetree/bindings/phy/qcom,usb-snps-femto-v2.yaml'
RANGES=(('#define USB2_PHY_USB_PHY_UTMI_CTRL0', '\nstatic int qcom_snps_hsphy_clk_init'),
        ('static inline void qcom_snps_hsphy_write_mask', '\nstatic int qcom_snps_hsphy_suspend'),
        ('static const struct override_param hs_disconnect_sc7280', '\nstatic int qcom_snps_hsphy_init'),
        ('static int qcom_snps_hsphy_init', '\nstatic int qcom_snps_hsphy_exit'),
        ('static const struct of_device_id qcom_snps_hsphy_of_match_table', '\nMODULE_DEVICE_TABLE'),
        ('static void qcom_snps_hsphy_override_param_update_val', '\nstatic int qcom_snps_hsphy_probe'))
MASKS={0x6c:0xe7,0x70:0xef,0x74:0x3f,0x78:0x0f}


def pin(path):
    path=Path(path).resolve()
    return dict(path=str(path),size=path.stat().st_size,sha256=digest(path))


def qualify(baseline,prepared,output):
    baseline,prepared,output=(Path(p).resolve() for p in (baseline,prepared,output))
    require(output.is_relative_to(ROOT/'workspace/private') and not output.exists(),'fresh private PHY tests')
    output.mkdir(mode=0o700,parents=True)
    old=json.loads((baseline/'prepared.json').read_text());new=json.loads((prepared/'prepared.json').read_text())
    old_source=Path(old['kernel'])/DRIVER;new_source=Path(new['kernel'])/DRIVER
    a=old_source.read_text();z=new_source.read_text()
    before='\t\t\t\t\tREFCLK_SEL_DEFAULT, REFCLK_SEL_MASK);'
    after='\t\t\t\t\tREFCLK_SEL_MASK, REFCLK_SEL_DEFAULT);'
    require(a.count(before)==1 and z==a.replace(before,after),'PHY source delta is not the single REFCLK correction')
    trees=[nodes(p/'sm8450-samsung-g0q-ram.dtb') for p in (baseline,prepared)]
    phys=[p for p,n in trees[1].items() if b'qcom,sm8450-usb-hs-phy' in n.get('compatible',b'').split(b'\0')]
    require(len(phys)==1,'active PHY cardinality');phy=phys[0]
    require(trees[1][phy]['status']==b'okay\0' and trees[0][phy]['reg']==trees[1][phy]['reg'],'PHY identity/status changed')
    changes=[(p,k) for p in sorted(set(trees[0])|set(trees[1]))
             for k in sorted(set(trees[0].get(p,{}))|set(trees[1].get(p,{})))
             if trees[0].get(p,{}).get(k)!=trees[1].get(p,{}).get(k)]
    schema=yaml.safe_load((Path(new['kernel'])/BINDING).read_text())['properties']
    expected_names={'qcom,hs-disconnect-bp','qcom,squelch-detector-bp','qcom,hs-amplitude-bp',
        'qcom,pre-emphasis-duration-bp','qcom,pre-emphasis-amplitude-bp','qcom,hs-rise-fall-time-bp',
        'qcom,hs-crossover-voltage-microvolt','qcom,hs-output-impedance-micro-ohms','qcom,ls-fs-output-impedance-bp'}
    require(len(changes)==9 and {k for p,k in changes if p==phy}==expected_names,'DT delta is not exactly the nine PHY properties')
    values={}
    for name in expected_names:
        require(name not in trees[0][phy] and len(trees[1][phy][name])==4,'tuning property shape differs')
        val=struct.unpack('>i',trees[1][phy][name])[0]
        require(schema[name]['minimum']<=val<=schema[name]['maximum'],
                'PHY value outside the selected binding range')
        values[name]=val
    live=nodes(new['live_fdt']['path']);vendor=live['/soc/hsphy@88e3000']
    require(vendor['compatible']==b'qcom,usb-hsphy-snps-femto\0','retained vendor PHY differs')
    pairs=list(struct.iter_unpack('>II',vendor['qcom,param-override-seq']))
    require([offset for value,offset in pairs]==list(MASKS),'vendor device-mode offset order differs')
    desired={offset:value for value,offset in pairs}
    require(all(value&~MASKS[offset]==0 for offset,value in desired.items()),'vendor one-bits exceed mapped tuning fields')
    fixture=ROOT/'tests/s22plus_mainline_phy_fixture.c'
    fdt=Path(new['kernel'])/'scripts/dtc/libfdt'
    libs=sorted(fdt.glob('*.c'))
    require(libs,'retained libfdt sources absent')
    results={};producers=[]
    for label,source,dtb in [('baseline',old_source,baseline/'sm8450-samsung-g0q-ram.dtb'),
                             ('candidate',new_source,prepared/'sm8450-samsung-g0q-ram.dtb')]:
        work=output/label;work.mkdir();text=source.read_text();pieces=[];ranges=[]
        for start,end in RANGES:
            require(text.count(start)==1,'ambiguous selected driver fragment')
            lo=text.index(start);hi=text.index(end,lo);piece=text[lo:hi]
            pieces.append(piece);ranges.append(dict(start=lo,end=hi,sha256=__import__('hashlib').sha256(piece.encode()).hexdigest()))
        selected=work/'selected-phy.c';selected.write_text('\n\n'.join(pieces)+'\n')
        producers.append(dict(driver=pin(source),selected=pin(selected),verbatim_ranges=ranges))
        for arch,cc,prefix in [('host','gcc',[]),('arm64','aarch64-linux-gnu-gcc',['/usr/bin/qemu-aarch64'])]:
            exe=work/('fixture-'+arch)
            command=[cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-sign-compare','-static','-I'+str(work),'-I'+str(fdt),
                     str(fixture),*[str(p) for p in libs],'-o',str(exe)]
            with (work/('compile-'+arch+'.log')).open('xb') as log:
                subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
            (work/('compile-'+arch+'.json')).write_text(json.dumps(dict(command=command,compiler=pin(Path(shutil.which(cc)).resolve())),indent=2)+'\n')
            with (work/('file-'+arch+'.log')).open('xb') as log:subprocess.run(['file',exe],stdout=log,check=True)
            cases={}
            inputs=[(seed,0) for seed in (0,0xffffffff,0xaaaaaaaa,0x55555555)]+[(0xffffffff,f) for f in range(1,5)]
            for seed,failure in inputs:
                name=f'{arch}-{seed:08x}-{failure}'
                command=prefix+[str(exe),str(dtb),hex(seed),str(failure)]
                result=subprocess.run(command,capture_output=True,timeout=15)
                (work/(name+'.stdout')).write_bytes(result.stdout);(work/(name+'.stderr')).write_bytes(result.stderr)
                require(result.returncode==0 and not result.stderr,'actual PHY fixture failed: '+name)
                row=json.loads(result.stdout);require(row['properties']==(9 if label=='candidate' else 0),'property lookup count differs')
                cases[(seed,failure)]=row
            results[(label,arch)]=cases
    for label in ('baseline','candidate'):
        require(results[(label,'host')]==results[(label,'arm64')],'host/ARM64 actual-C behavior differs')
    for key,oldrow in results[('baseline','arm64')].items():
        newrow=results[('candidate','arm64')][key];seed,failure=key
        require(oldrow['events']==newrow['events'],'supply/clock/reset operations changed')
        if failure:
            require(not oldrow['writes'] and not newrow['writes'] and oldrow['returncode']==newrow['returncode']==-5,'failure path wrote MMIO')
            continue
        require(newrow['final'][0]==(seed&~3)|2 and oldrow['final'][0]==seed|2,'REFCLK field/outside bits differ')
        require(newrow['final'][1:]==[(seed&~MASKS[o])|desired[o] for o in MASKS],'mapped tuning field parity/outside-bit preservation failed')
        filtered=[(o,(v&~3)|2 if o==0xa0 else v) for o,v in oldrow['writes']]
        require(filtered==[(o,v) for o,v in newrow['writes'] if o not in MASKS],'unexpected existing init write difference')
        require(len([x for x in newrow['writes'] if x[0] in MASKS])==9,'nine explicit tuning RMWs missing')
    result=dict(status='PASS_H0_ACTUAL_PHY_LOOKUP_AND_COMPLETE_INIT',source_fragments=producers,
        fixture=pin(fixture),checker=pin(__file__),binding=pin(Path(new['kernel'])/BINDING),
        baseline_dtb=pin(baseline/'sm8450-samsung-g0q-ram.dtb'),candidate_dtb=pin(prepared/'sm8450-samsung-g0q-ram.dtb'),
        retained_fdt=pin(Path(new['live_fdt']['path'])),dt_changes=changes,dt_values=values,
        mapped_vendor_values=desired,masks=MASKS,host_and_arm64_cases=32,
        physical_phy_reach_proved=False,physical_register_values_proved=False,full_register_parity_proved=False,
        results={label:[dict(row) for row in results[(label,'arm64')].values()] for label in ('baseline','candidate')},device_actions=0)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],cases=32,dt_properties=9,device_actions=0)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','prepared','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();qualify(a.baseline,a.prepared,a.output)
