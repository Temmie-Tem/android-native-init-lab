# SPDX-License-Identifier: GPL-2.0-only
# Hooks for the pinned byte parser in fdt_layout_observer.awk.
function input_property(k,p,n,    i) {
    if (depth==1 && k=="compatible") {
        if (got_root++) invalid()
        root_match = (n==10 && text_at(p,p+n)=="qcom,kona" && text_end==p+n)
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
    printf "input_v1=%d,%s,%s,%s,%s,%d,%d,%d,%d,%d,%d,%d\n", bytes,start_state,end_state,size_state,(got_root ? (root_match ? "match" : "different") : "missing"),(!got_chosen_status || chosen_status),(!bad_fixed),(de<=src),dst_ram,src_ram,dst_res,src_res
}
