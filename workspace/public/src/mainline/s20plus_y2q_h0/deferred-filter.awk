# Fixed one-block BLAKE2s-128; only inspect records with the exact build tag.
BEGIN {
    hex="0123456789abcdef"; alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    word=4294967296
    split("6a09e667 bb67ae85 3c6ef372 a54ff53a 510e527f 9b05688c 1f83d9ab 5be0cd19", words)
    for (i=0;i<8;i++) iv[i]=hexval(words[i+1])
    split("0123456789abcdef ea489fd61c02b753 b8c052fdae367194 7931dcbe265a40f8 905724afe1bc683d 2c6a0b834d75fe19 c51fed4a0763928b db7ec13950f4862a 6fe9b308c2d714a5 a2847615fb9e3cd0",perm)
    for(i=0;i<10;i++) for(j=0;j<16;j++) sigma[i,j]=hexval(substr(perm[i+1],j+1,1))
    if(length(key)!=32 || key ~ /[^0-9a-f]/ || length(legacy)!=160) bad=1
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
function legacy_digest(data,   i,j,b,out){
    for(i=0;i<8;i++)h[i]=iv[i]
    h[0]=xor(h[0],16842768);compress(data,64,1)
    for(i=0;i<4;i++)for(j=0;j<4;j++){
        b=int(h[i]/256^j)%256;out=out substr(hex,int(b/16)+1,1) substr(hex,b%16+1,1)
    }
    return out
}
function little(s, off,  i,n) {
    n=0
    for(i=0;i<4;i++) n+=hexval(substr(s,off+2*i,2))*256^i
    return n
}
function b64(s,    i,x,bits,n,r,out) {
    for(i=1;i<=length(s);i+=2) {
        n=n*256+hexval(substr(s,i,2));bits+=8
        while(bits>=6) {bits-=6;x=int(n/2^bits);n=n%2^bits;out=out substr(alphabet,x+1,1)}
    }
    if(bits)out=out substr(alphabet,n*2^(6-bits)+1,1)
    return out
}
function observe(g,mode,   a,instance,i,f,type,n,k,seq) {
    a=substr(g,1,160)
    if(length(a)<160){flags=or(flags,1);return}
    if(digest(substr(a,1,128),key)!=substr(a,129,32) || (!mode && substr(a,49,32)!="52554e2d4c4556454c2d4f4e4c592121")){
        flags=or(flags,2);return
    }
    groups[mode]++
    if(length(g)<480)flags=or(flags,1)
    instance=digest(substr(a,49,32),key)
    delete seqs;delete seen
    for(i=0;i<4;i++){
        f=substr(g,161+80*i,80);type=i<2?1:2
        if(substr(f,1,8)!=(type==1?"484c5032":"484c5732"))continue
        if(length(f)!=80){flags=or(flags,1);continue}
        if(digest(substr(f,1,48),instance)!=substr(f,49,32)){flags=or(flags,4);continue}
        seq=little(f,9)
        if(!seq || ((seq-1)%2)!=(i%2) || (type==1 && (little(f,17)>159 || little(f,25)>159)) ||
            (type==2 && int(little(f,33)/2097152)!=1 && int(little(f,33)/2097152)!=2)){
            flags=or(flags,16);continue
        }
        if(seq>4294967280 || (type==1 && little(f,33)>=2147483648) || (type==2 && int(little(f,33)/2097152)==2 && little(f,17)!=little(f,25))){flags=or(flags,16);continue}
        if(seqs[type]<seq){seqs[type]=seq;seen[type]=substr(f,9,40)}
    }
    if(groups[0]+groups[1]==1){s1=seen[1];s2=seen[2]}
}
function flush(end,   stop,i,n,mode,tag,b) {
    # Handle a start position once; allow a short final window.
    stop=end?length(buf)-1:length(buf)-479
    if(stop<1)return
    for(mode=0;mode<3;mode++){
        tag=mode==2?legacy:((mode?"483045504f434833":"4830554e41545233") key)
        i=1
        while((n=index(substr(buf,i),tag))){
            i+=n-1
            if(saturated || i>stop)break
            if(i%2){
                if(++signature_hits>256){saturated=1;break}
               if(mode==2)flags=or(flags,8)
               else observe(substr(buf,i,480),mode)
            }
            i++
        }
    }
    # Without an authenticated anchor these signatures only veto an absence claim.
    for(mode=0;mode<6;mode++){
        t=(mode==0?"483045504f434833":mode==1?"4830554e41545233":mode==2?"593251414e434831":mode==3?"484c5032":mode==4?"484c5732":"5932515355525631")
        i=1
        while((n=index(substr(buf,i),t))){
            i+=n-1
            if(saturated || i>stop)break
            if(i%2){
                if(++signature_hits>256){saturated=1;break}
                if(mode==3 || mode==4)orphan=1
                else if(mode==5 && substr(buf,i+16,32)==key){
                    f=substr(buf,i,160)
                    if(length(f)<160)flags=or(flags,1)
                    else if(legacy_digest(substr(f,1,128))==substr(f,129,32))flags=or(flags,8)
                    else flags=or(flags,2)
                }else if(mode<2 && length(substr(buf,i))>=160 && substr(buf,i+16,32)!=key){
                    f=substr(buf,i,160)
                    if(digest(substr(f,1,128),substr(f,17,32))==substr(f,129,32))flags=or(flags,64)
                }else if(end && length(substr(buf,i))<48 && index(t key,substr(buf,i))==1)flags=or(flags,1)
            }
            i++
        }
    }
    buf=substr(buf,stop+2)
}
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
    if(saturated)next
    buf=buf line
    if(length(buf)>=8192) flush(0)
}
END{
    if(bad || total!=expected)exit 3
    if(!saturated)flush(1)
    if(saturated){printf "R4,%d,0,0,128,-,-\n",total;exit}
    if(!groups[0] && !groups[1] && orphan)flags=or(flags,32)
    if(groups[0]+groups[1]!=1 || and(flags,88)){s1="";s2=""}
    printf "R4,%d,%d,%d,%d,%s,%s\n",total,groups[1],groups[0],flags,(s1?b64(s1):"-"),(s2?b64(s2):"-")
}
