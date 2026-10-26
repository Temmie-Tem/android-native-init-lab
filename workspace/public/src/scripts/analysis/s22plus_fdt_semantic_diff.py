"""Semantic diff of two flattened device trees (node path -> properties).

Usage: python s22plus_fdt_semantic_diff.py <base.dtb> <live.dtb> <out.json>
Prints a summary; writes added/removed nodes and added/removed/changed
properties. Property values are reported as lengths plus a short hex prefix,
so the output carries no full blob contents.
"""
import json
import struct
import sys

FDT_BEGIN_NODE, FDT_END_NODE, FDT_PROP, FDT_NOP, FDT_END = 1, 2, 3, 4, 9


def parse(blob):
    magic, total, off_struct, off_strings = struct.unpack_from('>4I', blob, 0)
    if magic != 0xd00dfeed:
        raise ValueError('not an FDT')
    strings = blob[off_strings:]
    nodes = {}
    stack = []
    pos = off_struct
    while True:
        token, = struct.unpack_from('>I', blob, pos)
        pos += 4
        if token == FDT_BEGIN_NODE:
            end = blob.index(b'\0', pos)
            name = blob[pos:end].decode()
            pos = (end + 4) & ~3
            stack.append(name)
            path = '/' + '/'.join(s for s in stack[1:])
            nodes[path] = {}
        elif token == FDT_END_NODE:
            stack.pop()
        elif token == FDT_PROP:
            length, nameoff = struct.unpack_from('>II', blob, pos)
            pos += 8
            value = blob[pos:pos + length]
            pos = (pos + length + 3) & ~3
            pname = strings[nameoff:strings.index(b'\0', nameoff)].decode()
            path = '/' + '/'.join(s for s in stack[1:])
            nodes[path][pname] = value
        elif token == FDT_NOP:
            continue
        elif token == FDT_END:
            return nodes
        else:
            raise ValueError('bad token %d at %d' % (token, pos))


def show(value):
    text = value.rstrip(b'\0')
    if text and all(32 <= c < 127 or c == 0 for c in text):
        return 'str:' + text.replace(b'\0', b'|').decode()[:80]
    return 'len=%d hex=%s' % (len(value), value[:16].hex())


base = parse(open(sys.argv[1], 'rb').read())
live = parse(open(sys.argv[2], 'rb').read())
out = {
    'nodes_added': sorted(set(live) - set(base)),
    'nodes_removed': sorted(set(base) - set(live)),
    'props_added': {}, 'props_removed': {}, 'props_changed': {},
}
for path in sorted(set(base) & set(live)):
    b, l = base[path], live[path]
    for p in sorted(set(l) - set(b)):
        out['props_added'].setdefault(path, {})[p] = show(l[p])
    for p in sorted(set(b) - set(l)):
        out['props_removed'].setdefault(path, {})[p] = show(b[p])
    for p in sorted(set(b) & set(l)):
        if b[p] != l[p]:
            out['props_changed'].setdefault(path, {})[p] = {'base': show(b[p]), 'live': show(l[p])}
json.dump(out, open(sys.argv[3], 'w'), indent=1)
print('nodes base %d live %d | added %d removed %d | props added in %d nodes, '
      'removed in %d, changed in %d' % (
          len(base), len(live), len(out['nodes_added']), len(out['nodes_removed']),
          len(out['props_added']), len(out['props_removed']), len(out['props_changed'])))
