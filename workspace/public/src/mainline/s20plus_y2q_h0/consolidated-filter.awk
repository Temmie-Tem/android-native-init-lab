# Fixed one-block BLAKE2s-128; only inspect records with the exact build tag.
BEGIN {
    hex="0123456789abcdef"; alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    word=4294967296
    split("6a09e667 bb67ae85 3c6ef372 a54ff53a 510e527f 9b05688c 1f83d9ab 5be0cd19", words)
    for (i=0;i<8;i++) iv[i]=hexval(words[i+1])
    split("0123456789abcdef ea489fd61c02b753 b8c052fdae367194 7931dcbe265a40f8 905724afe1bc683d 2c6a0b834d75fe19 c51fed4a0763928b db7ec13950f4862a 6fe9b308c2d714a5 a2847615fb9e3cd0",perm)
    for(i=0;i<10;i++) for(j=0;j<16;j++) sigma[i,j]=hexval(substr(perm[i+1],j+1,1))
    if(length(anchor)!=160 || length(tag)!=48 || tag ~ /[^0-9a-f]/ || anchor ~ /[^0-9a-f]/) bad=1
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
function valid(frame,    i,j,r,p,n,b) {
    for(i=0;i<16;i++) {
        n=0
        for(j=0;j<4;j++) n+=hexval(substr(frame,8*i+2*j+1,2))*256^j
        m[i]=n
    }
    for(i=0;i<8;i++) {h[i]=iv[i]; v[i+8]=iv[i]}
    h[0]=xor(h[0],16842768)
    for(i=0;i<8;i++) v[i]=h[i]
    v[12]=xor(v[12],64); v[14]=xor(v[14],4294967295)
    for(r=0;r<10;r++) {
        for(j=0;j<4;j++) mix(j,j+4,j+8,j+12,m[sigma[r,2*j]],m[sigma[r,2*j+1]])
        for(j=0;j<4;j++) mix(j,(j+1)%4+4,(j+2)%4+8,(j+3)%4+12,m[sigma[r,8+2*j]],m[sigma[r,9+2*j]])
    }
    for(i=0;i<4;i++) {
        n=xor(xor(h[i],v[i]),v[i+8])
        for(j=0;j<4;j++) {
            b=int(n/(256^j))%256
            if(b!=hexval(substr(frame,129+8*i+2*j,2))) return 0
        }
    }
    return 1
}
function encoded(s,    k,n,nb,out,x) {
    n=0;nb=0;out=""
    for(k=1;k<=length(s);k+=2) {
        n=n*256+hexval(substr(s,k,2));nb+=8
        while(nb>=6){nb-=6;x=int(n/2^nb);n=n%2^nb;out=out substr(alphabet,x+1,1)}
    }
    if(nb) out=out substr(alphabet,n*2^(6-nb)+1,1)
    return out
}
function collect(win,needle,kind,    at,step,frame,s,n,k,byte) {
    at=1
    while((step=index(substr(win,at),needle))) {
        at+=step-1
        if(at%2 && at+159<=length(win)) {
            frame=substr(win,at,160)
            if(kind==1) anchors++
            else if(valid(frame)) {
                s=substr(frame,49,80); n=0
                for(k=1;k<=80;k++){byte=hexval(substr(s,k,1));n+=and(byte,1)+and(int(byte/2),1)+and(int(byte/4),1)+int(byte/8)}
                if(!n || substr(s,79,1)!="0") bad=1
                else {
                    records++
                    if(n>best || (n==best && ("x" s)>("x" selected))){best=n;selected=s}
                }
            }
        }
        at+=1
    }
}
{
    if(!NF || NF>16){bad=1;next}
    for(i=1;i<=NF;i++) if(length($i)!=2) bad=1
    line=$0;gsub(/[[:space:]]/,"",line)
    if(line ~ /[^0-9a-f]/ || length(line)!=NF*2) bad=1
    total+=NF
    if(total>2097136 || bad){bad=1;next}
    win=tail line
    collect(win,anchor,1);collect(win,tag,2)
    tail=length(win)>158 ? substr(win,length(win)-157) : win
}
END {
    if(bad || total!=expected) exit 3
    printf "C1,%d,%d,%d,%s\n",total,anchors,records,(records?encoded(selected):"-")
}
