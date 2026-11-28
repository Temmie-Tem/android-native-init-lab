# Fixed one-block BLAKE2s-128; only inspect records with the exact build tag.
BEGIN {
    hex="0123456789abcdef"; alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    word=4294967296
    split("6a09e667 bb67ae85 3c6ef372 a54ff53a 510e527f 9b05688c 1f83d9ab 5be0cd19", words)
    for (i=0;i<8;i++) iv[i]=hexval(words[i+1])
    split("0123456789abcdef ea489fd61c02b753 b8c052fdae367194 7931dcbe265a40f8 905724afe1bc683d 2c6a0b834d75fe19 c51fed4a0763928b db7ec13950f4862a 6fe9b308c2d714a5 a2847615fb9e3cd0",perm)
    for(i=0;i<10;i++) for(j=0;j<16;j++) sigma[i,j]=hexval(substr(perm[i+1],j+1,1))
    if(length(key)!=32 || key ~ /[^0-9a-f]/) bad=1
}
function hexval(s,    k,n) {
    n=0
    for(k=1;k<=length(s);k++) n=n*16+index(hex,substr(s,k,1))-1
    return n
}
function rot(x,n) {return int(x/(2^n)) + (x % (2^n))*(2^(32-n))}
function mix(a,b,c,d,x,y) {
    v[a]=(v[a]+v[b]+x)%word; v[d]=rot(xor(v[d],v[a]),16)
    v[c]=(v[c]+v[d])%word; v[b]=rot(xor(v[b],v[c]),12)
    v[a]=(v[a]+v[b]+y)%word; v[d]=rot(xor(v[d],v[a]),8)
    v[c]=(v[c]+v[d])%word; v[b]=rot(xor(v[b],v[c]),7)
}

function compress(block,count,last,  i,j,k,n,r) {
    for(i=0;i<16;i++) {
        n=0
        for(j=0;j<4;j++) n+=hexval(substr(block,8*i+2*j+1,2))*256^j
        m[i]=n
    }
    for(i=0;i<8;i++){v[i]=h[i];v[i+8]=iv[i]}
    v[12]=xor(v[12],count)
    if(last) v[14]=xor(v[14],4294967295)
    for(r=0;r<10;r++) {
        for(j=0;j<4;j++) mix(j,j+4,j+8,j+12,m[sigma[r,2*j]],m[sigma[r,2*j+1]])
        for(j=0;j<4;j++) mix(j,(j+1)%4+4,(j+2)%4+8,(j+3)%4+12,m[sigma[r,8+2*j]],m[sigma[r,9+2*j]])
    }

    for(i=0;i<8;i++) h[i]=xor(xor(h[i],v[i]),v[i+8])
}
function zeros(n,   s){s="";while(n--) s=s "0";return s}

function digest(data,secret,   bytes,i,j,b,hx){
    for(i=0;i<8;i++)h[i]=iv[i]
    h[0]=xor(h[0],16846864)
    compress(secret zeros(96),64,0)
    bytes=length(data)/2
    compress(data zeros(128-length(data)),64+bytes,1)
    hx=""
    for(i=0;i<4;i++) for(j=0;j<4;j++) {
       b=int(h[i]/(256^j))%256
       hx=hx substr(hex,int(b/16)+1,1) substr(hex,b%16+1,1)
    }
    return hx
}
function little(s, off,  i,n) {
    n=0
    for(i=0;i<4;i++) n+=hexval(substr(s,off+2*i,2))*256^i
    return n
}
# Presence across authenticated slots only. rc classes: zero, -517, other.
function rc_class(value){return value==0 ? 1 : (value==65019 ? 2 : 4)}
function observe(g,    a,instance,i,f,seq,x,y,z,rc,lo,hi) {
    a=substr(g,1,160)
    if(length(g)!=480 || substr(a,17,32)!=key || substr(a,81,48)!=reserved_zeros ||
       digest(substr(a,1,128),key)!=substr(a,129,32) ||
       (substr(a,1,16)=="544c464958454431" && substr(a,49,32)!="52554e2d4c4556454c2d4f4e4c592121")){
        invalid=1;return
    }
    instance=digest(substr(a,49,32),key)
    for(i=0;i<4;i++){
        f=substr(g,161+80*i,80)
        if(substr(f,1,8)!=(i>=2?"544c5731":"544c5031"))continue
        if(digest(substr(f,1,48),instance)!=substr(f,49,32)){ignored++;continue}
        seq=little(f,9);x=little(f,17);y=little(f,25);z=little(f,33);rc=little(f,41)
        lo=rc%65536;hi=int(rc/65536)
        if(seq<1 || seq>32 || (seq-1)%2!=i%2 || x>65535 || y>65535 || z>1023 ||
           and(z,12)==12 || and(z,192)==192 ||
           (lo && !and(x,8192)) || (hi && !and(y,8192))){invalid=1;return}
        slots++;initial=or(initial,x);worker=or(worker,y);progress=or(progress,z)
        if(and(x,8192))irc=or(irc,rc_class(lo))
        if(and(y,8192))wrc=or(wrc,rc_class(hi))
        # All these bits must coexist in one slot to attest a completed barrier wait.
        if(and(z,187)==187)completed=1
    }
}
function flush(end,    stop,i,n,start,tag) {
    stop=end?length(buf)-1:length(buf)-479
    if(stop<1)return
    i=1
    while(!invalid && match(substr(buf,i),/544c464958454431|544c45504f434831|544c5031|544c5731/)){
        n=i+RSTART-1
        if(n>stop)break
        if(n%2){
            start=consumed+(n-1)/2;tag=substr(buf,n,16)
            if(substr(tag,1,8)=="544c5031" || substr(tag,1,8)=="544c5731"){signature=1;i=n+1;continue}
            if(start<next_start || ++windows>256){invalid=1;break}
            next_start=start+240
            observe(substr(buf,n,480))
        }
        i=n+1
    }
    consumed+=(stop+1)/2
    buf=substr(buf,stop+2)
}
BEGIN {reserved_zeros=zeros(48)}
{
    # A bounded cache of validated od rows; never skip appending a repeated row.
    if ($0 in rowhex) { line=rowhex[$0]; nbytes=length(line)/2 }
    else {
        if (length($0)>128 || $0 !~ /^[[:blank:]]*[0-9a-f][0-9a-f]([[:blank:]]+[0-9a-f][0-9a-f])*[[:blank:]]*$/){bad=1;next}
        line=$0;gsub(/[[:blank:]]+/,"",line); nbytes=length(line)/2
        if(nbytes>16 || nbytes<1){bad=1;next}
        pos=serial++%256
        delete rowhex[oldrow[pos]]
        oldrow[pos]=$0;rowhex[$0]=line
    }
    total+=nbytes
    if(total>2097136 || bad){bad=1;next}
    if(invalid)next
    buf=buf line
    if(length(buf)>=8192) flush(0)
}
END {
    if(bad || total!=expected)exit 3
    if(!invalid)flush(1)
    if(invalid || (signature && !windows)){print "TL1,invalid";exit}
    printf "TL1,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n",total,windows,slots,ignored,initial,worker,progress,irc,wrc,completed
}
