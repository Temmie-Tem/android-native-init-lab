# Input is od -An -v -tx1. Emit one classification of a bounded, terminated
# command line. Other argument values are neither interpreted nor returned.
BEGIN { digits = "0123456789abcdef" }
# The firmware passes unsigned 32-bit arguments. Reject representations
# outside that domain before using AWK number arithmetic.
function number(s, radix,    acc, i, v) {
    if (s == "") return -1
    acc = 0
    for (i = 1; i <= length(s); i++) {
        v = index(digits, substr(s, i, 1)) - 1
        if (v < 0 || v >= radix) return -1
        acc = acc * radix + v
        if (acc > 4294967295) return -1
    }
    return acc
}
function compare_geometry(value,    a,size,addr,scale,radix,k,power) {
    if (split(tolower(value), a, "@") != 2) return -1
    size = a[1]; addr = a[2]; scale = 1; radix = 10
    k = substr(size, length(size), 1)
    if (k == "k" || k == "m" || k == "g") {
        scale = k == "k" ? 1024 : (k == "m" ? 1048576 : 1073741824)
        size = substr(size, 1, length(size)-1)
    }
    if (substr(size, 1, 2) == "0x") { size = substr(size, 3); radix = 16 }
    else if (substr(size, 1, 1) == "0") radix = 8
    if (substr(addr, 1, 2) == "0x") addr = substr(addr, 3)
    size = number(size, radix) * scale
    addr = number(addr, 16)
    if (size <= 0 || size > 4294967295 || addr < 0) return -1
    power = 1
    while (power < size) power *= 2
    if (power != size) return -1
    return size == 2097152 && addr == 2669674496
}
function finish_word() {
    if (!stopped && (word == "sec_log" || word ~ /^sec-log(=|$)/ ||
        word ~ /^"sec[_-]log(=|")/ || word ~ /^sec_log=.*"/)) bad = 1
    if (word == "--" || word == "\"--\"") stopped = 1
    if (!stopped && substr(word, 1, 8) == "sec_log=") {
        found++
        compared = compare_geometry(substr(word, 9))
        if (compared < 0) bad = 1
        else if (compared) matched++
    }
    word = ""
}
{
    for (i = 1; i <= NF; i++) {
        if ($i !~ /^[0-9a-f][0-9a-f]$/) { bad = 1; next }
        byte = (index(digits, substr($i, 1, 1))-1)*16 + index(digits, substr($i, 2, 1))-1
        count++
        if (count > 8192 || ended) { bad = 1; continue }
        if (byte == terminator) { ended = 1; finish_word(); continue }
        if (byte == 34) { quoted = !quoted; word = word sprintf("%c", byte); continue }
        if ((byte == 32 || byte == 9) && !quoted) { finish_word(); continue }
        if (byte < 32 || byte > 126) { bad = 1; continue }
        word = word sprintf("%c", byte)
    }
}
END {
    if (bad || quoted || !ended) print "unsupported"
    else if (found > 1) print "ambiguous"
    else if (!found) print "absent"
    else if (matched) print "match"
    else print "different"
}
