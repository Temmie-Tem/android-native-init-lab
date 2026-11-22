# SPDX-License-Identifier: GPL-2.0-only
# Input: toybox od -An -v -tx1, one bounded FDT. Output: aggregate geometry.
# Four decimal interval endpoints are bound by the host to the reviewed model.
function invalid() { failed = 1; exit 2 }
function byte(p,    pair) {
    if (p < 0 || p >= bytes) invalid()
    pair = substr(block[int(p / 256)], (p % 256) * 2 + 1, 2)
    return hex["x" pair]
}
function word(p) {
    return ((byte(p) * 256 + byte(p+1)) * 256 + byte(p+2)) * 256 + byte(p+3)
}
function addr(p,    high) {
    high = word(p)
    if (high >= 65536) invalid()
    return high * 4294967296 + word(p+4)
}
function text_at(p, limit,    i,v,result) {
    for (i = p; i < limit && i <= p + 255; i++) {
        v = byte(i)
        if (!v) { text_end = i + 1; return result }
        if (v < 32 || v > 126) invalid()
        result = result sprintf("%c",v)
    }
    invalid()
}
function overlap(a,b,c,d) { return a < d && c < b }
function extent(a,n,kind,    b) {
    if (!n) return
    b = a + n
    if (b > 281474976710656) invalid()
    if (kind == "ram") {
        if (++banks > 1024) invalid()
        bank_lo[banks] = a; bank_hi[banks] = b
        if (a <= dst && de <= b) dst_ram = 1
        if (a <= src && se <= b) src_ram = 1
    } else {
        fixed++
        if (overlap(a,b,dst,de)) dst_res = 1
        if (overlap(a,b,src,se)) src_res = 1
    }
}
function scalar(p,n) {
    if (n == 4) return word(p)
    if (n == 8) return addr(p)
    invalid()
}
function finish_node(    p,value) {
    if (depth == 1 || (depth == 2 && group == "reserved-memory")) {
        if (prop["#address-cells"] != 2 || prop["#size-cells"] != 2) invalid()
        if (depth == 2 && !("ranges" in prop)) invalid()
        if ("status" in prop && prop["status"] !~ /^(ok|okay)$/) invalid()
    }
    if (depth == 2 && group == "chosen") {
        rs = prop["linux,initrd-start"] + 0
        re = prop["linux,initrd-end"] + 0
        if ((rs || re) && (!rs || re <= rs)) invalid()
    }
    if (depth == 2 && group == "other" && prop["device_type"] == "memory") invalid()
    if (depth == 2 && group == "ram") {
        if (prop["device_type"] != "memory" || !("reg" in prop)) invalid()
        if (!("status" in prop) || prop["status"] ~ /^(ok|okay)$/)
            for (p = reg_start; p < reg_end; p += 16) extent(addr(p),addr(p+8),"ram")
    }
    if (depth == 3 && group == "reserved-memory") {
        if ("reg" in prop) {
            for (p = reg_start; p < reg_end; p += 16) extent(addr(p),addr(p+8),"fixed")
        } else if ("size" in prop) dynamic++
        else invalid()
    }
}
function begin_node(name) {
    depth++
    if (depth > 64 || (depth == 1 && (name != "" || root_seen++))) invalid()
    if (depth == 2) {
        if (name == "chosen" || name == "reserved-memory") {
            if (groups[name]++) invalid()
            group = name
        } else if (name == "memory" || name ~ /^memory@/) group = "ram"
        else group = "other"
    }
    if (group == "reserved-memory" && depth > 3) invalid()
}
function take_property(k,p,n,    v) {
    if (depth == 2 && ((group == "ram" && k == "linux,usable-memory") ||
                       (group == "chosen" && k == "linux,usable-memory-range"))) invalid()

    if ((depth == 1 || (depth == 2 && group == "reserved-memory")) &&
        (k == "#address-cells" || k == "#size-cells")) {
        if (n != 4) invalid()
        v = word(p)
    } else if (depth == 2 && group == "reserved-memory" && k == "ranges") {
        if (n) invalid()
        v = 1
    } else if ((depth == 1 || (depth == 2 && group ~ /^(ram|reserved-memory)$/)) && k == "status" ||
               depth == 2 && k == "device_type") {
        v = text_at(p,p+n)
        if (text_end != p+n) invalid()
    } else if (depth == 2 && group == "chosen" && k ~ /^linux,initrd-(start|end)$/) {
        v = scalar(p,n)
        if (!v) invalid()
    } else if ((depth == 2 && group == "ram" || depth == 3 && group == "reserved-memory") && k == "reg") {
        if (!n || n % 16) invalid()
        reg_start=p; reg_end=p+n; v=1
    } else if (depth == 3 && group == "reserved-memory" && k == "size") {
        if (n != 8) invalid()
        v = addr(p)
        if (!v) invalid()
    } else return
    if (k in prop) invalid()
    prop[k] = v
}
# Properties precede children in a flattened node. Finalize once at that boundary.
function flush_properties() {
    finish_node()
    for (key in prop) delete prop[key]
    reg_start = reg_end = 0
}
function parse(    pos,stop,strings,slimit,res,token,n,off,k,name,i,a,b) {
    if (bytes < 40 || word(0) != 3490578157 || word(4) != bytes || word(20) != 17 ||
        word(24) > 17 || word(24) < 16) invalid()
    pos = word(8); stop = pos+word(36)
    strings = word(12); slimit = strings+word(32)
    res = word(16)
    if (res < 40 || res%8 || pos < res+16 || pos%4 || stop > strings ||
        strings >= slimit || slimit > bytes || pos >= stop) invalid()
    while (1) {
        if (res+16 > pos) invalid()
        a=addr(res); b=addr(res+8); res+=16
        if (!a && !b) break
        if (!b) invalid()
        extent(a,b,"fixed")
    }
    while (pos+4 <= stop) {
        token=word(pos); pos+=4
        if (token == 1) {
            if (open_props) flush_properties()
            name=text_at(pos,stop); pos=4*int((text_end+3)/4)
            begin_node(name); open_props=1
        } else if (token == 2) {
            if (depth < 1) invalid()
            if (open_props) flush_properties()
            if (depth == 2) group=""
            depth--; open_props=0
        } else if (token == 3) {
            if (!open_props || depth < 1 || pos+8 > stop) invalid()
            n=word(pos); off=word(pos+4); pos+=8
            if (pos+n > stop || strings+off >= slimit) invalid()
            if (!(off in names)) names[off]=text_at(strings+off,slimit)
            take_property(names[off],pos,n); pos+=4*int((n+3)/4)
        } else if (token == 9) {
            if (depth || pos!=stop || root_seen!=1 || !groups["chosen"] || !groups["reserved-memory"]) invalid()
            return
        } else if (token != 4) invalid()
    }
    invalid()
}
BEGIN {
    for (i=0; i<256; i++) hex["x" sprintf("%02x",i)]=i
    if (dst<=0 || de<=dst || src<=0 || se<=src || de>281474976710656 || se>281474976710656) invalid()
}
{
    # od emits sixteen bytes per full row. Decode ASCII whitespace in bulk
    # so BusyBox awk does not allocate fields or append array values per byte.
    row=$0
    gsub(/[ \t]/,"",row)
    width=length(row)
    if (short_row || width<2 || width>32 || width%2 || row ~ /[^0-9a-f]/) invalid()
    short_row=(width<32)
    bytes+=width/2
    if (bytes>2097152) invalid()
    chunk=chunk row
    if (length(chunk)==512) { block[blocks++]=chunk; chunk="" }
}
END {
    if (failed) exit 2
    if (length(chunk)) block[blocks]=chunk
    parse()
    for (i=1; i<=banks; i++)
        if (rs && bank_lo[i] <= rs && re <= bank_hi[i]) initrd_ram=1
    printf "layout_v1=%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n", bytes,banks,fixed,dynamic,(re>rs),dst_ram,src_ram,dst_res,src_res,(rs && overlap(rs,re,dst,de)),(rs && overlap(rs,re,src,se)),(bytes<=1310464),initrd_ram
}
