"""Bounded V2 thermal rows joined to the exact retained resident frame.

Missing evicted companions are incomplete optional evidence. Conflicting
companions are malformed; neither can establish a temperature observation.
"""
from dataclasses import dataclass
import re

import s22plus_native_thermal_observer_v1 as previous
import s22plus_native_thermal_source_v2 as source

frames,wire=previous.frames,previous.wire
SENSORS=source.sensor_map()
_ARRAYS=('error','phase','seen','version','enable','ready','status_valid','temps')
_FIELDS=('seq','start_ms','end_ms','map_mask','mask','bound','mapped',*_ARRAYS,
         'battery_uv','battery_temp_deci','battery_error','battery_valid')
@dataclass(frozen=True)
class Dialect:
    sample_magic: str
    frame_prefix: bytes
    require_trdy: bool


DIALECT=Dialect('S22THERM2',b'RESIDENT_THERMAL2_FRAME ',True)


def frame_pattern(dialect):
    return re.compile(frames._FRAME.pattern.replace(b'RESIDENT_FRAME ',dialect.frame_prefix)
        .replace(b' expected=13',rb' expected=13 thermal_seq=(\d+)'))


def _integer(text,signed=False,bits=32):
    pattern=r'-?(?:0|[1-9][0-9]*)' if signed else r'(?:0|[1-9][0-9]*)'
    if not re.fullmatch(pattern,text):raise ValueError('thermal numeric grammar differs')
    value=int(text)
    if not (-(1<<(bits-1)) if signed else 0)<=value<(1<<(bits-1) if signed else 1<<bits):
        raise ValueError('thermal numeric range differs')
    return value


def parse_sample(raw, *, dialect=DIALECT):
    if type(raw) is not bytes or len(raw)>=768 or not raw.endswith(b'\n'):
        raise ValueError('thermal sample bound/framing differs')
    words=raw[:-1].decode('ascii').split(' ')
    if words[0]!=dialect.sample_magic or len(words)!=len(_FIELDS)+1:raise ValueError('thermal sample fields differ')
    value={}
    for key,word in zip(_FIELDS,words[1:],strict=True):
        if not word.startswith(key+'='):raise ValueError('thermal sample order differs')
        text=word[len(key)+1:]
        signed=key in ('error','temps','battery_uv','battery_temp_deci','battery_error')
        if key in _ARRAYS:
            parts=text.split(',')
            if len(parts)!=(16 if key=='temps' else 2):raise ValueError('thermal array size differs')
            value[key]=[_integer(p,signed) for p in parts]
        else:value[key]=_integer(text,signed,64 if key in ('seq','start_ms','end_ms') else 32)
    s=value
    if (not s['seq'] or s['end_ms']<s['start_ms'] or s['map_mask']>65535 or s['mask']>65535
            or s['mask']&~s['map_mask'] or s['bound']>3 or s['mapped']>3 or s['bound']&~s['mapped']
            or s['battery_valid']>1):raise ValueError('thermal sample shape differs')
    for bank in range(2):
        active=any(s['mask']&(1<<i) for i,(_,b,_) in enumerate(SENSORS) if b==bank)
        seen,phase=s['seen'][bank],s['phase'][bank]
        if (not -4095<=s['error'][bank]<=0 or phase>2 or seen>15 or s['status_valid'][bank]>65535
                or not phase and seen or phase==2 and not s['bound']&(1<<bank)
                or any(not seen&(1<<i) and s[key][bank] for i,key in enumerate(('version','enable','ready','status_valid')))):
            raise ValueError('thermal register provenance differs')
        if active and (s['error'][bank] or phase!=2 or seen!=15 or not s['bound']&(1<<bank)
                or s['version'][bank]>>28!=2 or not s['enable'][bank]&1
                or dialect.require_trdy and not s['ready'][bank]&1):
            raise ValueError('thermal active bank differs')
    for i,(_,bank,sensor) in enumerate(SENSORS):
        if s['mask']&(1<<i):
            if not -40000<=s['temps'][i]<=150000 or not s['status_valid'][bank]&(1<<sensor):
                raise ValueError('thermal sensor validity differs')
        elif s['temps'][i]:raise ValueError('invalid thermal sensor carries a value')
    if not -4095<=s['battery_error']<=0:raise ValueError('thermal battery error range differs')
    if s['battery_valid']:
        # The same frozen declaration is the authority for the conversion table.
        core=source.previous.CORE.read_text()
        uv=[int(x.strip(),16) for x in re.search(r's22_thermal_uv\[S22_THERMAL_TABLE_COUNT\] = \{([^}]+)',core).group(1).split(',')]
        deci=[int(x.strip()) for x in re.search(r's22_thermal_deci\[S22_THERMAL_TABLE_COUNT\] = \{([^}]+)',core).group(1).split(',')]
        if s['battery_error'] or not uv[0]<=s['battery_uv']<=uv[-1]:raise ValueError('thermal battery range differs')
        for i in range(1,len(uv)):
            if s['battery_uv']<=uv[i]:
                product=(s['battery_uv']-uv[i-1])*(deci[i]-deci[i-1])
                delta=abs(product)//(uv[i]-uv[i-1])*(-1 if product<0 else 1)
                if s['battery_temp_deci']!=deci[i-1]+delta:raise ValueError('thermal battery units differ')
                break
    elif not s['battery_error'] or s['battery_temp_deci']:
        raise ValueError('invalid battery sample differs')
    return value


def _maximum(sample,first,count):
    values=[sample['temps'][i] for i in range(first,first+count) if sample['mask']&(1<<i)]
    return max(values) if values else 0


def decode_hud(raw, *, dialect=DIALECT):
    if type(raw) is not bytes or len(raw)>50000:raise ValueError('thermal HUD bound differs')
    parts=raw.split(b'\n',2);tail=b'S22RPROBE1 COMPLETE\n'
    if len(parts)!=3 or not parts[2].endswith(tail):raise ValueError('thermal HUD framing differs')
    retained=wire.decode_log(parts[2][:-len(tail)])
    samples={};claims={};converted=[];pattern=frame_pattern(dialect)
    for row in retained['records']:
        if row.startswith((b'RESIDENT_FRAME ',b'RESIDENT_THERMAL_FRAME ')):
            raise ValueError('old HUD dialect in thermal V2')
        if row.startswith((b'RESIDENT_THERMAL2_FRAME ',b'RESIDENT_THERMAL3_FRAME ')) and not row.startswith(dialect.frame_prefix):
            raise ValueError('other thermal frame dialect')
        if row.startswith(b'RESIDENT_THERMAL_SAMPLE '):
            match=re.fullmatch(rb'RESIDENT_THERMAL_SAMPLE frame=(\d+) ('+
                re.escape(dialect.sample_magic.encode())+rb' .*\n)',row)
            if not match:raise ValueError('thermal companion grammar differs')
            frame=_integer(match[1].decode(),bits=64)
            if not frame or frame in samples or frame in claims:raise ValueError('duplicate/zero/late thermal frame companion')
            samples[frame]=parse_sample(match[2],dialect=dialect)
        if row.startswith(dialect.frame_prefix):
            match=pattern.fullmatch(row)
            if not match:raise ValueError('thermal frame grammar differs')
            groups=match.groups();frame=int(groups[0]);thermal_sequence=int(groups[-2]);valid=int(groups[9])
            if frame in claims or thermal_sequence>(1<<64)-1 or valid&~2044:
                raise ValueError('thermal frame fields differ')
            claims[frame]=(thermal_sequence,valid,int(groups[1]),int(groups[13]),int(groups[14]),int(groups[7]))
            row=re.sub(rb' thermal_seq=\d+',b'',row,count=1).replace(dialect.frame_prefix,b'RESIDENT_FRAME ',1)
            row=re.sub(rb' hardware_valid=\d+',b' hardware_valid='+str(valid&508).encode(),row,count=1)
        converted.append(row)
    header=parts[2].split(b'\n',1)[0]+b'\n'
    normalized=parts[0]+b'\n'+parts[1]+b'\n'+header+b''.join(converted)+b'S22RLOG1 COMPLETE\n'+tail
    value=frames.decode_probe(normalized);latest=value['latest'];complete=False;fresh=False
    # Check every retained companion that still has its frame, without joining
    # an evicted frame to a different acquisition or silently rewriting it.
    last_sample=None;last_hardware=None
    for frame,claim in claims.items():
        sample=samples.get(frame)
        if sample is None:continue
        sequence,valid,stamp,cpu_mc,cpu_mask,hardware_sequence=claim
        if (not sequence or sample['seq']!=sequence or sample['end_ms']>stamp
                or cpu_mask!=(sample['mask']&8191) or cpu_mc!=_maximum(sample,0,13)):
            raise ValueError('thermal acquisition/frame join differs')
        if last_sample:
            if sample['seq']<last_sample['seq'] or sample['start_ms']<last_sample['start_ms']:
                raise ValueError('thermal acquisition order regressed')
            if sample['seq']==last_sample['seq']:
                if sample!=last_sample or hardware_sequence!=last_hardware:
                    raise ValueError('retained thermal acquisition was rewritten or replayed')
            elif hardware_sequence<=last_hardware:
                raise ValueError('new thermal acquisition did not advance its hardware sample')
            elif sample['start_ms']<last_sample['end_ms']:
                raise ValueError('thermal acquisitions overlap or clock regressed')
        last_sample,last_hardware=sample,hardware_sequence
    if latest:
        sequence,valid,*_=claims[latest['sequence']];sample=samples.get(latest['sequence'])
        if sample is not None:
            if not sequence or sample['seq']!=sequence or sample['end_ms']>latest['boottime_ms']:
                raise ValueError('thermal frame time/sequence join differs')
            if latest['cpu_mask']!=(sample['mask']&8191) or latest['cpu_temp_mc']!=_maximum(sample,0,13):
                raise ValueError('thermal CPU frame join differs')
            if valid and any(bool(valid&flag)!=bool(sample['mask']&mask) for flag,mask in ((256,8191),(512,24576),(1024,32768))):
                raise ValueError('thermal domain validity join differs')
            if valid and bool(valid&16)!=bool(sample['battery_valid']):raise ValueError('thermal battery frame join differs')
            complete=True
            fresh=(latest['hardware_state']=='FRESH' and value['current_age_upper_ms']['hardware_age_ms']<=5000
                   and 0<=value['proc_boottime_ms']+9-sample['start_ms']<=5000)
            latest.update(thermal=sample,battery_temp_deci=sample['battery_temp_deci'],
                gpu_temp_mc=_maximum(sample,13,2),gpu_mask=(sample['mask']>>13)&3,
                ddr_temp_mc=_maximum(sample,15,1),ddr_mask=(sample['mask']>>15)&1)
        elif not sequence and valid&(16|256|512|1024):raise ValueError('temperature validity lacks acquisition')
        latest['hardware_valid']=valid
    valid=latest['hardware_valid'] if latest else 0
    return dict(value,thermal_diagnostics_complete=complete,
        cpu_temperature_observed=bool(complete and fresh and valid&256),
        gpu_temperature_observed=bool(complete and fresh and valid&512),
        ddr_temperature_observed=bool(complete and fresh and valid&1024),
        battery_temperature_observed=bool(complete and fresh and valid&16),
        cpu_hardware_conversion_age='UNPROVED',ddr_source='SoC-DDR-region-TSENS-not-RAM-die',
        battery_source='board-adc-temp-0x14b-shared-wpc')


class IO(previous.IO):
    @staticmethod
    def decode_hud(raw,run_id):return decode_hud(raw)


class Observer(previous.resident.Observer):
    io_class=IO
    def __init__(self,identity,control):
        super().__init__(identity,control);self.__file__=__file__
