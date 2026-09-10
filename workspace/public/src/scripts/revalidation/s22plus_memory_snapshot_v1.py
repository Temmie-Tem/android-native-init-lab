"""Interpret optional S22MEM1 output; never qualify console or gauge behavior."""
import hashlib
import re

EARLY_COMMAND=b'/s22-display --memory-snapshot early'
LATE_COMMAND=b'/bin/busybox sleep 2; /s22-display --memory-snapshot late'
COMMAND_PHASES={EARLY_COMMAND:'early',LATE_COMMAND:'late'}
MEMORY_KEYS=('MemTotal MemAvailable MemFree RbinTotal RbinAlloced RbinFree RbinCached RbinPool '
             'CmaTotal CmaFree Shmem Cached Slab SReclaimable SUnreclaim KernelStack PageTables Percpu '
             'SwapTotal SwapFree HugepagePool AnonPages').split()
NUMBERS=set(MEMORY_KEYS)|set(('error read_bytes expected present metadata_match missing mismatch errors '
    'logical_bytes allocated_metadata_bytes content_verified total_bytes free_bytes avail_bytes '
    'records parsed bad page_size pages slabs nominal_bytes object_bytes seq age_ms allocations '
    'retired live_handles peak_handles requested_bytes physical_bytes root_present').split())
CMD_KEYS=('kasan','kasan.stacktrace','kfence.sample_interval','page_owner','page_pinner','slub_debug','stack_depot_disable')


def identity(raw):return {'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def _uint(value):
    if not re.fullmatch(r'0|[1-9][0-9]{0,19}',value) or int(value)>2**64-1:
        raise ValueError('noncanonical or out-of-range integer')
    return int(value)


def parse(raw,phase):
    result={'schema':'s22plus_memory_snapshot_v1','valid':False,'phase':phase,'raw':identity(raw)}
    try:
        if phase not in ('early','late') or not raw or len(raw)>4096 or not raw.endswith(b'\n') or b'\0' in raw:
            raise ValueError('output bound or framing')
        lines=raw.decode('ascii').splitlines()
        begin=re.fullmatch(r'S22MEM1 BEGIN phase=(early|late) start_ms=([0-9]+) clock_error=([0-9]+)',lines[0])
        end=re.fullmatch(r'S22MEM1 END phase=(early|late) end_ms=([0-9]+) clock_error=([0-9]+)',lines[-1])
        if not begin or not end or begin[1]!=phase or end[1]!=phase:raise ValueError('phase/framing differs')
        start,finish=_uint(begin[2]),_uint(end[2]);clock=[_uint(begin[3]),_uint(end[3])]
        if not any(clock) and finish<start:raise ValueError('monotonic interval regressed')
        groups={};order=[]
        for line in lines[1:-1]:
            parts=line.split(' ');label=parts[0]
            if label not in ('MEM','CMD','FS','FILES','SLAB','CACHE','GEM'):raise ValueError('unknown record')
            fields={}
            for token in parts[1:]:
                key,sep,value=token.partition('=')
                if not sep or key in fields or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.]*',key) or not re.fullmatch(r'[A-Za-z0-9_.,:+*=()/\-]{1,80}',value):
                    raise ValueError('malformed or duplicate field')
                if key in NUMBERS or key.endswith('_count'):
                    fields[key]=None if value=='NA' else _uint(value)
                else:fields[key]=value
            if label!='CACHE' and fields.get('status') not in ('ok','partial','unavailable','stale'):
                raise ValueError('missing source status')
            groups.setdefault(label,[]).append(fields);order.append(label)
        if (any(len(groups.get(k,[]))!=1 for k in ('MEM','CMD','FILES','SLAB','GEM')) or
                len(groups.get('FS',[])) not in (1,3) or len(groups.get('CACHE',[]))>5):
            raise ValueError('source record counts differ')
        expected=['MEM','CMD']+['FS']*len(groups['FS'])+['FILES','SLAB']+['CACHE']*len(groups.get('CACHE',[]))+['GEM']
        if order!=expected:raise ValueError('source order differs')
        if len(groups['FS'])==3 and [row.get('name') for row in groups['FS']]!=['root','modules','work']:
            raise ValueError('filesystem identity labels differ')
        if len(groups['FS'])==1 and groups['FS'][0].get('status')!='unavailable':raise ValueError('missing filesystem records')
        mem=groups['MEM'][0]
        if mem['status'] in ('ok','partial') and (mem.get('unit')!='KiB' or any(k not in mem for k in MEMORY_KEYS)):
            raise ValueError('memory fields/units differ')
        if mem['status']=='ok' and any(type(mem[k]) is not int for k in MEMORY_KEYS):raise ValueError('missing memory value claimed complete')
        for fs in groups['FS']:
            if fs['status']!='ok':continue
            if fs.get('type')=='ramfs':
                if fs.get('accounting')!='unavailable':raise ValueError('ramfs accounting claimed available')
            elif fs.get('type')=='tmpfs':
                if any(type(fs.get(k)) is not int for k in ('total_bytes','free_bytes','avail_bytes')) or not fs['total_bytes']>=fs['free_bytes']>=fs['avail_bytes']:
                    raise ValueError('filesystem block totals differ')
            else:raise ValueError('unbound filesystem type')
        files=groups['FILES'][0]
        if files['status'] in ('ok','partial'):
            names=('expected','present','metadata_match','missing','mismatch','errors','logical_bytes','allocated_metadata_bytes')
            if any(type(files.get(k)) is not int for k in names) or files.get('content_verified')!=0:
                raise ValueError('file metadata fields differ')
            if files['present']!=files['metadata_match']+files['mismatch'] or files['expected']!=files['present']+files['missing']+files['errors']:
                raise ValueError('file census coverage differs')
            if files['status']=='ok' and files['metadata_match']!=files['expected']:raise ValueError('incomplete file census claimed complete')
        command=groups['CMD'][0]
        if command['status']=='ok':
            args={k:v for k,v in command.items() if re.fullmatch(r'arg[0-9]+',k)}
            if set(args)!={'arg'+str(i) for i in range(len(args))}:raise ValueError('command token order differs')
            counts={k:0 for k in CMD_KEYS}
            for i in range(len(args)):
                name=args['arg'+str(i)].partition('=')[0]
                if name not in counts:raise ValueError('unapproved command-line token')
                counts[name]+=1
            if any(command.get(k+'_count')!=n for k,n in counts.items()):raise ValueError('command-line occurrence count differs')
            if command.get('root_present') not in (0,1) or command.get('rootfstype') not in ('absent','ramfs','tmpfs','other'):
                raise ValueError('root argument summary differs')
        slab=groups['SLAB'][0];caches=groups.get('CACHE',[])
        if slab['status'] in ('ok','partial'):
            if any(type(slab.get(k)) is not int for k in ('error','records','parsed','bad','page_size')) or slab.get('estimate')!='nominal':
                raise ValueError('slab coverage/geometry differs')
            if slab['status']=='ok' and (slab['error'] or slab['bad'] or slab['records']!=slab['parsed']):raise ValueError('partial slab claimed complete')
            if len(caches)!=min(5,slab['parsed']):raise ValueError('slab top count differs')
            ranking=[]
            for cache in caches:
                if not isinstance(cache.get('name'),str) or any(type(cache.get(k)) is not int for k in ('pages','slabs','nominal_bytes','object_bytes')):
                    raise ValueError('slab cache fields differ')
                if cache['nominal_bytes']!=cache['pages']*cache['slabs']*slab['page_size'] or cache['object_bytes']>cache['nominal_bytes']:
                    raise ValueError('slab estimate differs')
                ranking.append((-cache['nominal_bytes'],cache['name']))
            if ranking!=sorted(ranking) or len({name for _,name in ranking})!=len(ranking):raise ValueError('slab ranking differs')
        elif caches:raise ValueError('unavailable slab has cache claims')
        gem=groups['GEM'][0]
        if gem['status'] in ('ok','stale'):
            if any(type(gem.get(k)) is not int for k in ('seq','age_ms','allocations','retired','live_handles','peak_handles','requested_bytes')):
                raise ValueError('GEM bookkeeping fields differ')
            if gem.get('source')!='renderer_last_retirement' or gem.get('physical_bytes','absent') is not None or gem['live_handles']!=1 or gem['allocations']!=gem['retired']+1 or gem['peak_handles'] not in (1,2):
                raise ValueError('GEM ownership claim differs')
        result.update(valid=True,start_ms=start,end_ms=finish,clock_errors=clock,sections=groups,
            all_source_status_ok=all(row.get('status')=='ok' for k,rows in groups.items() if k!='CACHE' for row in rows),
            file_content_verified=False,reclaimability_proved=False,kernel_gem_ownership_proved=False)
    except (ValueError,UnicodeError,IndexError) as exc:
        result['reason']=str(exc)
    return result


def from_command(raw,phase,terminal,stderr):
    value=parse(raw,phase)
    complete=(terminal is not None and len(terminal)==7 and terminal[1:4]==[0,0,0] and
              terminal[5]==0 and not stderr)
    value['command_complete']=complete
    if not complete:value.update(valid=False,reason='command output is not a clean complete result')
    return value
