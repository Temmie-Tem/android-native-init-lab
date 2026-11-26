# Keep the last 79 bytes and bounded offset tables for immediately preceding frames.
BEGIN {
    width = 160
    if (length(first)!=width || length(second)!=width || length(third)!=width ||
        first==second || second==third || first==third ||
        first ~ /[^0-9a-f]/ || second ~ /[^0-9a-f]/ || third ~ /[^0-9a-f]/) bad=1
}
function locate(window, wanted, stage,    pos,step,at,prior,linked) {
    pos = 1
    while ((step = index(substr(window, pos), wanted)) != 0) {
        pos += step - 1
        if (pos % 2 == 1) {
            at = previous - length(tail)/2 + (pos-1)/2
            hits[stage]++
            if (stage == 1) a_slot[at % 256] = at+1
            if (stage == 2) {
                prior = at-80
                linked = prior >= 0 && a_slot[prior % 256] == prior+1
                ab += linked
                b_slot[at % 256] = at+1
                has_a[at % 256] = linked
            }
            if (stage == 3) {
                prior = at-80
                if (prior >= 0 && b_slot[prior % 256] == prior+1) {
                    bc++
                    abc += has_a[prior % 256]
                }
            }
        }
        pos++
    }
}
{
    if (!NF || NF>16) { bad=1; next }
    for (i=1; i<=NF; i++) if (length($i)!=2) bad=1
    line=$0
    gsub(/[[:space:]]/, "", line)
    if (line ~ /[^0-9a-f]/ || length(line)!=2*NF) bad=1
    previous=total
    total+=NF
    if (total>2097136 || bad) { bad=1; next }
    window=tail line
    locate(window, first, 1)
    locate(window, second, 2)
    locate(window, third, 3)
    tail=length(window)>=width ? substr(window,length(window)-width+3) : window
}
END {
    if (bad || total!=expected) exit 3
    printf "y2q_basic_v1=%d,%d,%d,%d,%d,%d,%d\n",total,hits[1],hits[2],hits[3],ab,bc,abc
}
