"""Fixed mainline bundle and entry for the approved ordinary-terminal connector."""
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[5]
ENTRY='workspace/public/src/scripts/host_tools/s22plus_mainline_terminal_v1.py'
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_mainline_task_v1 as mainline
from s22plus_native_records_v3 import canonical,pin,private_path,publish,read,require,verify


def bundle(root,base,*,current=False,approval=False,recovery=False):
    root=Path(root);base=Path(base)
    declaration_pin=pin(base/'connector-preparation.json');declaration=read(verify(declaration_pin))
    require(set(declaration)=={'schema','status','task','proposal','review','preceding_closed'} and
        declaration['schema']=='s22plus-mainline-connector-preparation-v1' and
        declaration['status']=='PREPARED_H0_NOT_RUN_APPROVAL','mainline connector preparation differs')
    directory=base/'task-1';task_pin=pin(directory/'task.json');task=read(verify(task_pin))
    require(declaration['task']==task_pin and declaration['review']==task['review'] and
        task['schema']=='s22plus-mainline-task-v1' and task['N']['profile']==mainline.profile.PROFILE and
        task['N']['namespace']==mainline.profile.NAMESPACE and task['N']['version']==mainline.profile.VERSION and
        task['operations']==[mainline.profile.OPERATION] and task['seconds']==mainline.profile.SECONDS and
        task['operation_budget']==1 and task['recovery_mode']=='attended' and task['E'] is None,
        'mainline connector scope differs')
    proposal_pin=pin(directory/'proposal.json');proposal=read(verify(proposal_pin))
    require(declaration['proposal']==proposal_pin and proposal['task']==task_pin and
        proposal['approval']==mainline.tasks.approval_text(task,task_pin) and
        proposal['grants_device_authority'] is False,'mainline proposal differs')
    previous_pin=declaration['preceding_closed'];private_path(root,Path(previous_pin['path']))
    previous=read(verify(previous_pin))
    private_path(root,Path(previous['task']['path']))
    private_path(root,Path(previous['current_android_terminal']['path']))
    previous_task=read(verify(previous['task']));terminal=read(verify(previous['current_android_terminal']))
    require(previous['terminal_state']==terminal['terminal_state']=='ANDROID_CLOSED_HEALTHY' and
        terminal['research_closed'] is True and previous_task['target']==task['target'] and
        previous_task['A']==task['A'],'mainline predecessor target/Android closure differs')
    entry_pin=pin(root/ENTRY)
    if current:
        completed=False
        if recovery and (directory/'operation-0001/operation.json').exists():
            from s22plus_native_adapter_v3 import Adapter
            adapter=Adapter(root,directory/'operation-0001')
            completed=adapter.android_transfer_completed(read(directory/'operation-0001/operation.json'))
        mainline.validate_task(root,task,live=True,recovery=recovery or completed,require_android=not completed)
    approved=None
    if approval:
        approved=pin(base/'operator-approval.json');value=read(verify(approved))
        require(set(value)=={'task','entry','preceding_closed','selected_returned_approval','actual_user_text','attended'} and
            value['task']==task_pin and value['entry']==entry_pin and value['preceding_closed']==previous_pin and
            value['selected_returned_approval']==proposal['approval'] and value['attended'] is True and
            type(value['actual_user_text']) is str and 0<len(value['actual_user_text'].strip())<=4096,
            'actual finite attended mainline approval is absent or differs')
    return dict(base=base,directory=directory,task=task_pin,task_value=task,entry=entry_pin,
        entry_args=['start',str(directory/'task.json')],review=declaration_pin,approval=approved,
        preceding_closed=previous_pin,namespace=mainline.profile.NAMESPACE,operation=mainline.profile.OPERATION)


def start(root,task_path):
    from s22plus_approved_terminal_tasks_v1 import verify_bridge,DISPATCH
    from s22plus_native_session_v3 import Session,prepare_operation
    from s22plus_native_adapter_v3 import Adapter
    root=Path(root);task_path=private_path(root,task_path);base=task_path.parent.parent
    require(base.parent==root/'workspace/private/outputs' and task_path==base/'task-1/task.json',
            'mainline entry task path differs')
    bound=bundle(root,base,current=True,approval=True)
    intent=read(base/DISPATCH/'intent.json')
    require(intent['task']==bound['task'] and intent['entry']==bound['entry'] and
        intent['approval']==bound['approval'] and intent['entry_review']==bound['review'] and
        intent['command']==['/usr/bin/python3',str(root/ENTRY),'start',str(task_path)],
        'mainline entry lacks its exact connector dispatch')
    verify_bridge(root,expected=intent['bridge_review'])
    require(not (task_path.parent/'grant.json').exists() and not list(task_path.parent.glob('operation-*')),
            'mainline entry was already attempted')
    approved=read(verify(bound['approval']))
    publish(base/'mainline-entry-intent.json',dict(dispatch=pin(base/DISPATCH/'intent.json'),
        task=bound['task'],entry=bound['entry'],approval=bound['approval']))
    grant=mainline.open_grant(root,task_path,returned_approval=approved['selected_returned_approval'],
        operator_statement=approved['actual_user_text'])
    publish(base/'opened-grant.json',dict(grant=grant,approval=bound['approval'],terminal_entry_point=bound['entry']))
    directory=prepare_operation(root,Path(grant['path']),operation=mainline.profile.OPERATION,
        adapter=Adapter(root,task_path.parent))
    return Session(root,directory,Adapter(root,directory)).execute(attended=True)


def main():
    rows=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    require(os.getuid()==os.geteuid()==1000 and rows['NoNewPrivs'].strip()=='0' and
        len(sys.argv)==3 and sys.argv[1]=='start','use the exact reviewed ordinary-terminal entry')
    print(canonical(start(ROOT,Path(sys.argv[2]))).decode(),end='')


if __name__=='__main__':main()
