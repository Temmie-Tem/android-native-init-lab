"""Model independent TRDY/VALID combinations; count actual provider MMIO reads."""
import s22plus_thermal_v2_fixtures as previous


def kernel_harness():
    raw=previous.kernel_harness()
    replace=previous.source.resident.replace
    raw=replace(raw,b'static unsigned mmio_reads,adc_reads',
        b'static unsigned status_reads[2][16],trdy_reads[2];\nstatic unsigned mmio_reads,adc_reads')
    raw=replace(raw,b'assert(allowed);mmio_reads++;return *(const u32*)p;',
        b'assert(allowed);if(p==t+0xe4)trdy_reads[b]++;\n'
        b'            else {unsigned sensor=(unsigned)((p-t-0xa0)/4);assert(sensor<16);status_reads[b][sensor]++;}\n'
        b'            mmio_reads++;return *(const u32*)p;')
    raw=replace(raw,b'    int n=sample_get(text,NULL);',b'''
    if(!strncmp(scenario,"cross-",6)) {
        unsigned trdy,valid;assert(sscanf(scenario,"cross-%u-%u",&trdy,&valid)==2);
        assert((trdy==0||trdy==1||trdy==8)&&valid<=1);
        for(unsigned b=0;b<2;b++) {
            tm_words[b][0xe4/4]=trdy;
            for(unsigned i=0;i<16;i++) {
                tm_words[b][0xa0/4+i]&=~(1U<<21);
                if(valid)tm_words[b][0xa0/4+i]|=1U<<21;
            }
        }
    }
    int n=sample_get(text,NULL);''')
    raw=replace(raw,b'    fputs(text,stdout);',b'''
    for(unsigned b=0;b<2;b++) {
        unsigned total=0;
        for(unsigned i=0;i<16;i++){assert(status_reads[b][i]<=1);total+=status_reads[b][i];}
        assert(trdy_reads[b]<=1);
        fprintf(stderr,"bank=%u status_reads=%u trdy_reads=%u\\n",b,total,trdy_reads[b]);
    }
    fputs(text,stdout);''')
    return raw
