# Combined with the pinned TLMM reader's BLAKE2s and bounded od input loop.
function observe(g,    a,instance,i,f,seq,x,y,z,rc,lo,hi) {
    a=substr(g,1,160)
    if(length(g)!=480 || substr(a,17,32)!=key || substr(a,81,48)!=reserved_zeros ||
       digest(substr(a,1,128),key)!=substr(a,129,32) ||
       (substr(a,1,16)=="544c464958454432" && substr(a,49,32)!="52554e2d4c4556454c2d4f4e4c592121")){
        invalid=1;return
    }
    instance=digest(substr(a,49,32),key)
    for(i=0;i<4;i++){
        f=substr(g,161+80*i,80)
        if(substr(f,1,8)!=(i>=2?"544c5732":"544c5032"))continue
        if(digest(substr(f,1,48),instance)!=substr(f,49,32)){ignored++;continue}
        seq=little(f,9);x=little(f,17);y=little(f,25);z=little(f,33);rc=little(f,41)
        lo=rc%65536;hi=int(rc/65536)
        if(seq<1 || seq>32 || (seq-1)%2!=i%2 || x>=33554432 || y>=33554432 || z>=1024 ||
           (and(z,184) && and(z,68)) ||
           (lo && !and(x,8192)) || (hi && !and(y,8192))){invalid=1;return}
        slots++;initial=or(initial,x);worker=or(worker,y);progress=or(progress,z)
        if(and(x,8192)) initial_rc[lo]=1
        if(and(y,8192)) worker_rc[hi]=1
        if(and(z,59)==59) wait_done=1
        if(and(z,187)==187) outer_true=1
        if(and(z,71)==71) outer_false=1
    }
}
function flush(end,    stop,i,n,start,tag) {
    stop=end?length(buf)-1:length(buf)-479
    if(stop<1)return
    i=1
    while(!invalid && match(substr(buf,i),/544c464958454432|544c45504f434832|544c5032|544c5732/)){
        n=i+RSTART-1
        if(n>stop)break
        if(n%2){
            start=consumed+(n-1)/2;tag=substr(buf,n,8)
            if(tag=="544c5032" || tag=="544c5732"){
                if(start>=next_start)invalid=1
            }else{
                if(start<next_start || ++windows>256){invalid=1;break}
                next_start=start+240
                observe(substr(buf,n,480))
            }
        }
        i=n+1
    }
    consumed+=(stop+1)/2
    buf=substr(buf,stop+2)
}
function report(    k) {
    if(invalid){print "GP2,invalid";return}
    printf "GP2,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,",total,windows,slots,ignored,initial,worker,progress,wait_done,outer_true,outer_false
    for(k in initial_rc) printf "%04x",k+0
    printf ","
    for(k in worker_rc) printf "%04x",k+0
    printf "\n"
}
