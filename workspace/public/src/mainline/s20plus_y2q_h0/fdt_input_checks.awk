# SPDX-License-Identifier: GPL-2.0-only
# Hooks for the pinned byte parser in fdt_layout_observer.awk.
# Only classifications and membership in three fixed public identifiers leave this parser.
function root_form(p,n,    i,c,token,num,other,padding,kona_seen,sm8250_seen,y2q_seen) {
    if (!n) return "empty"
    if (n>512) return "over_limit"
    for (i=0; i<n; i++) {
        c=byte(p+i)
        if (!c) {
            if (!length(token)) { padding=1; continue }
            if (++num>16) return "over_limit"
            if (token=="qcom,kona") kona_seen=1
            else if (token=="qcom,sm8250") sm8250_seen=1
            else if (token=="samsung,y2q") y2q_seen=1
            else other=1
            token=""
        } else {
            if (padding || c<33 || c>126) return "noncanonical"
            if (length(token)>=127) return "over_limit"
            token=token sprintf("%c",c)
        }
    }
    if (length(token)) return "noncanonical"
    if (!num) return "empty"
    root_members=kona_seen+2*sm8250_seen+4*y2q_seen+8*other
    return (padding ? "padded_" : "") (num==1 ? "single" : "list")
}
function input_property(k,p,n,    i) {
    if (depth==1 && k=="compatible") {
        if (got_root++) invalid()
        form=root_form(p,n)
        root_match = (form=="single" && root_members==1)
    }
    if (depth==2 && group=="chosen" && k=="status") {
        if (got_chosen_status++) invalid()
        chosen_status = ((n==3 && text_at(p,p+n)=="ok") ||
                         (n==5 && text_at(p,p+n)=="okay")) && text_end==p+n
    }
    if (depth==3 && group=="reserved-memory" && k=="reg") {
        if (!n || n%16) invalid()
        for (i=0; i<n; i+=16) if (!addr(p+i+8)) bad_fixed=1
    }
}
function endpoint(present,value,expected) {
    if (!present) return "missing"
    return value==expected ? "match" : (value<expected ? "lower" : "higher")
}
END {
    if (failed) exit 2
    if (length(chunk)) block[blocks]=chunk
    de=dst+bytes
    parse()
    start_state=endpoint(rs!=0,rs,src)
    end_state=endpoint(re!=0,re,se)
    size_state=(rs && re) ? endpoint(1,re-rs,se-src) : "missing"
    printf "input_v2=%d,%s,%s,%s,%s,%d,%d,%d,%d,%d,%d,%d,%s,%d\n", bytes,start_state,end_state,size_state,(got_root ? (root_match ? "match" : "different") : "missing"),(!got_chosen_status || chosen_status),(!bad_fixed),(de<=src),dst_ram,src_ram,dst_res,src_res,(got_root ? form : "missing"),root_members+0
}
