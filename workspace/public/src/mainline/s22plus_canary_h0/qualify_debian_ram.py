#!/usr/bin/env python3
"""Qualify fixed Debian RAM artifacts and complete VM captures; H0 only."""
import argparse
import json
from pathlib import Path
import shutil

from prepare import ROOT,digest,require,config_values
from debian_ram import validate,pin
import verify
import vm_evidence


def qualification(prepared,physical,vm,positive,negative,output,*,kernel_label='build-1',ssh_cases=None):
    prepared,physical,vm,positive,negative,output=[p.resolve() for p in (prepared,physical,vm,positive,negative,output)]
    require(output.is_relative_to(ROOT/'workspace/private'),'private qualification output')
    output.mkdir(parents=True,mode=0o700,exist_ok=False)
    paths=[physical/'result.json',vm/'result.json',prepared/(kernel_label+'-result.json')]
    actual,test,kernel=[json.loads(p.read_text()) for p in paths]
    production=validate(actual);emulated=validate(test)
    ssh=verify.has_ssh(actual)
    require(ssh==(ssh_cases is not None),'SSH qualification requires its exact VM failure cases')
    require(actual['vm'] is False and test['vm'] is True and actual['inputs']==test['inputs'] and
            actual['kernel_release']==test['kernel_release'] and production['members']==emulated['members'] and
            production['inittab_sha256']==emulated['inittab_sha256'], 'VM/physical runtime source closure differs')
    for item in actual['inputs']:
        require(digest(item['path'])==item['sha256'], 'runtime input changed')
    config=prepared/'kernel-build/.config'
    values=config_values(config.read_text())
    require(values.get('CONFIG_SECURITY_SELINUX','n')=='n' and values.get('CONFIG_SCSI_UFSHCD','n')=='n' and
            digest(config)==kernel['config_sha256'], 'Debian kernel capability exclusion differs')
    kernel_pin=pin(kernel['image'])
    require(kernel_pin['sha256']==kernel['sha256'],'actual VM kernel changed')
    binding=vm_evidence.inputs(prepared,vm,kernel_label)
    rederived=None
    for directory,bad_key in ((positive,False),(negative,True)):
        capture=json.loads((directory/'capture.json').read_text())
        require(capture['schema']=='g0q-h0-vm-capture-v1' and capture['bad_key'] is bad_key and
                capture['device_actions']==0 and capture['inputs']==binding and
                capture['qemu_returncode'] in (0,-15,-9), 'complete settled VM capture required')
        extra=set()
        if ssh and not bad_key:
            import ssh_ram
            checked=ssh_ram.check_case(directory,test,pin(vm/'result.json'),kernel_pin,'positive')
            extra=set(capture['evidence'])-{'command.json','nonce.bin','request.raw','response.raw','serial.log','qemu.stderr'}
        require(set(capture['evidence'])=={'command.json','nonce.bin','request.raw','response.raw','serial.log','qemu.stderr'}|extra,
                'complete VM raw evidence required')
        for name,sha in capture['evidence'].items():
            require(digest(directory/name)==sha, 'VM raw evidence changed')
        for name,sha in capture['source'].items():
            require(Path(name).name==name and digest(directory/'source'/name)==sha, 'VM producer source changed')
        require('debian_ram.py' in capture['source'], 'VM producer lacks Debian validator provenance')
        nonce=(directory/'nonce.bin').read_bytes();key=Path(test['key_path']).read_bytes()
        if bad_key:key=bytes([key[0]^1])+key[1:]
        require((directory/'request.raw').read_bytes()==verify.request(key,bytes.fromhex(test['candidate_id']),nonce,manifest=test),
                'VM actual request differs')
        result=json.loads((directory/'result.json').read_text())
        if bad_key:
            require(not (directory/'response.raw').read_bytes() and
                    b'G0Q_RAM_PARK error=13' in (directory/'serial.log').read_bytes() and
                    result['status']=='PASS_H0_VM_UNAUTHENTICATED_REQUEST_REJECTED', 'wrong-key runtime rejection differs')
        else:
            scratch=output/'positive-response.raw';shutil.copyfile(directory/'response.raw',scratch)
            rederived=verify.verify(scratch,test,nonce,vm=True)
            require(all(result[k]==v for k,v in rederived.items()) and
                    result['status']=='PASS_H0_VM_DEBIAN_SYSVINIT_RAM', 'VM positive proof differs from complete raw')
        require(result['kernel_sha256']==kernel_pin['sha256'] and result['device_actions']==0, 'VM result/kernel differs')
    result=dict(schema='s22plus-mainline-debian-ram-qualification-v1',status='PASS_H0_DEBIAN_SYSVINIT_RAM',
                physical_manifest=pin(paths[0]),kernel=kernel_pin,vm_manifest=pin(paths[1]),
                positive_capture=pin(positive/'capture.json'),negative_capture=pin(negative/'capture.json'),
                positive_result=pin(positive/'result.json'),negative_result=pin(negative/'result.json'),
                physical_pid1_proved=False,device_actions=0)
    if ssh:
        import ssh_ram
        require(production['keys']==emulated['keys'],'VM and physical SSH keys differ')
        cases={case:ssh_ram.check_case(Path(ssh_cases)/case,test,pin(vm/'result.json'),kernel_pin,case)
               for case in ssh_ram.VM_CASES if case!='positive'}
        positive_ssh=ssh_ram.check_case(positive,test,pin(vm/'result.json'),kernel_pin,'positive')
        require(all(row['executable']==positive_ssh['executable'] for row in cases.values()),'SSH clients differ across VM cases')
        result['ssh']=dict(executable=positive_ssh['executable'],positive=positive_ssh,cases=cases,physical_ssh_proved=False)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],pid=rederived['pid'],responder_ppid=rederived['responder_ppid'],
                         physical_pid1_proved=False,device_actions=0)))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('prepared','physical','vm','positive','negative','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--kernel-label',default='build-1')
    parser.add_argument('--ssh-cases',type=Path)
    args=parser.parse_args()
    qualification(args.prepared,args.physical,args.vm,args.positive,args.negative,args.output,kernel_label=args.kernel_label,
                  ssh_cases=args.ssh_cases)
