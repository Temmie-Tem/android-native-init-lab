# Consume fixed-width hexadecimal od output. A frame must begin on a byte
# boundary. Keep one byte less than a frame across od lines.
BEGIN {
    width = 256
    if (length(first) != width || length(second) != width || first == second ||
        first ~ /[^0-9a-f]/ || second ~ /[^0-9a-f]/) bad = 1
}
function locate(window, wanted, which,    pos,step) {
    pos = 1
    while ((step = index(substr(window, pos), wanted)) != 0) {
        pos += step - 1
        if (pos % 2 == 1) {
            hits[which]++
            start[which] = previous - length(tail)/2 + (pos-1)/2
        }
        pos++
    }
}
{
    if (!NF || NF > 16) { bad=1; next }
    for (i=1; i<=NF; i++) if (length($i)!=2) bad=1
    line = $0
    gsub(/[[:space:]]/, "", line)
    if (line ~ /[^0-9a-f]/ || length(line) != 2*NF || length(line) > 32) bad = 1
    previous = total
    total += length(line)/2
    if (total > 2097136 || bad) { bad=1; next }
    window = tail line
    locate(window,first,1)
    locate(window,second,2)
    tail = length(window) >= width ? substr(window,length(window)-width+3) : window
}
END {
    if (bad || total != expected) exit 3
    paired = hits[1] == 1 && hits[2] == 1 && start[2]-start[1] == 128
    printf "y2q_log_v1=%d,%d,%d,%d\n",total,hits[1],hits[2],paired
}
