    if(!strcmp(argv[1],"bounds")) {
        struct s22_thermal_data s=m.thermal;
        s.sequence=s.start_ms=s.end_ms=UINT64_MAX;
        s.status_valid[0]=s.status_valid[1]=65535;
        for(unsigned i=0;i<2;i++) {s.version[i]=0x2fffffff;s.enable[i]=s.ready[i]=UINT32_MAX;}
        for(unsigned i=0;i<16;i++)s.temp_mc[i]=150000;
        s.battery_uv=INT32_MIN;s.battery_deci=s.battery_valid=0;s.battery_error=-4095;
        assert(s22_thermal_data_valid(&s));char row[768];
        int n=thermal_record(row,sizeof(row),UINT64_MAX,&s);assert(n>0&&n<768);
        printf("record_bytes=%d sample_bytes=%zu view_bytes=%zu\n",n,sizeof(struct status_metrics),sizeof(struct hud_snapshot));
        fputs(row,stderr);return 0;
    }
    if(!strcmp(argv[1],"ipc")) {
        struct status_metrics old={0};
        assert(resident_sample_valid(&m,&old,1,test_now,m.run));
        old=m;
        assert(!resident_sample_valid(&m,&old,1,test_now,m.run));
        m.sequence++;m.collected_ms++;
        m.valid=0;m.cpu_mask=0;m.cpu_temp_mc=m.battery_temp_deci=0;
        memset(&m.thermal,0,sizeof(m.thermal));
        assert(resident_sample_valid(&m,&old,1,test_now,m.run));
        struct status_metrics replay=old;replay.sequence=m.sequence+1;
        assert(!resident_sample_valid(&replay,&old,1,test_now,replay.run));
        replay=old;old=(struct status_metrics){0};replay.magic=0x31525353;
        assert(!resident_sample_valid(&replay,&old,1,test_now,replay.run));
        puts("PASS V2 acquisition order, unavailable gap and old magic rejection");return 0;
    }
