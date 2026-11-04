"""Split generated giant ARM64 jump-table functions at guest instruction boundaries.

Each chunk has its own bounded PC switch; intra-chunk gotos stay local. An
out-of-chunk goto uses an ABI-compatible musttail call via a compact dispatcher.
This preserves the full original indirect-branch fallback without optnone.

Usage: split_hot_function.py INPUT.c OUTPUT.c [MAX_INSTRUCTIONS=512]
"""
import re
import sys
from pathlib import Path

LABEL = re.compile(r"(?m)^L_([0-9a-f]+):;\s*$")
FN = re.compile(r"(?m)^__attribute__\(\(optnone, noinline\)\) void (f_([0-9a-f]+))\(Cpu \*c\) \{\n")
GOTO = re.compile(r"\bgoto (L_[0-9a-f]+);|\bgoto L_dispatch;")

def split_function(source, match, max_instr):
    name, address = match.group(1, 2)
    start = match.end()
    endmatch = re.search(r"(?m)^}\s*$", source[start:])
    if endmatch is None:
        raise ValueError('No closing function brace')
    end = start + endmatch.start()
    original = source[start:end]
    marker = re.search(r"(?m)^L_dispatch:\s*$", original)
    if marker is None:
        raise ValueError(f'{name}: no fallback')
    body = original[:marker.start()]
    labels = list(LABEL.finditer(body))
    if not labels or labels[0].group(1) != address:
        raise ValueError(f'{name}: entry label mismatch')
    if any(int(b.group(1),16)-int(a.group(1),16)!=4 for a,b in zip(labels,labels[1:])):
        raise ValueError(f'{name}: non-contiguous 4-byte instructions')
    prefix = body[:labels[0].start()]
    if not re.fullmatch(r'\s*FN_ENTER\(0x[0-9a-f]+ull\);\s*',prefix):
        raise ValueError(f'{name}: unexpected prologue: {prefix[:160]!r}')
    route = f'split_route_{address}'
    count = (len(labels)+max_instr-1)//max_instr
    parts = [f'split_part_{address}_{i}' for i in range(count)]
    decl = ''.join(f'static void {p}(Cpu *c);\n' for p in parts) + f'static void {route}(Cpu *c);\n'
    out = [decl, f'void {name}(Cpu *c) {{\n{prefix}    c->pc = 0x{address}ull;\n    __attribute__((musttail)) return {parts[0]}(c);\n}}\n']
    all_names={f'L_{x.group(1)}' for x in labels}
    for i,part in enumerate(parts):
        lo=i*max_instr; hi=min(len(labels),(i+1)*max_instr)
        chunk=body[labels[lo].start(): labels[hi].start() if hi<len(labels) else len(body)]
        local={f'L_{x.group(1)}' for x in labels[lo:hi]}
        def route_branch(mt):
            target=mt.group(1)
            if target and target in local:return mt.group(0)
            if target and target not in all_names:raise ValueError(f'{name}: unknown goto target {target}')
            setter=f'c->pc = 0x{target[2:]}ull; ' if target else ''
            return f'do {{ {setter}__attribute__((musttail)) return {route}(c); }} while (0);'
        chunk=GOTO.sub(route_branch,chunk)
        cases=' '.join(f'case 0x{x.group(1)}ull: goto L_{x.group(1)};' for x in labels[lo:hi])
        out.append(f'static void {part}(Cpu *c) {{\n    switch (c->pc) {{ {cases} default: __attribute__((musttail)) return rt_dispatch(c); }}\n')
        out.append(chunk)
        if hi<len(labels):
            next_addr=labels[hi].group(1)
            out.append(f'    c->pc = 0x{next_addr}ull;\n    __attribute__((musttail)) return {route}(c);\n')
        else:
            out.append(f'    __attribute__((musttail)) return {route}(c);\n')
        out.append('}\n')
    start_addr=int(address,16); end_addr=start_addr+len(labels)*4
    out.append(f'static void {route}(Cpu *c) {{\n')
    out.append(f'    uint64_t off = c->pc - 0x{address}ull;\n    if (off >= {len(labels)*4}ull || (off & 3)) __attribute__((musttail)) return rt_dispatch(c);\n')
    out.append(f'    switch (off / {max_instr*4}ull) {{\n')
    out.extend(f'    case {i}: __attribute__((musttail)) return {p}(c);\n' for i,p in enumerate(parts))
    out.append('    default: __attribute__((musttail)) return rt_dispatch(c);\n    }\n}\n')
    return source[:match.start()]+''.join(out)+source[end+2:], len(labels),count

def run():
    src=Path(sys.argv[1]); dest=Path(sys.argv[2]); size=int(sys.argv[3]) if len(sys.argv)>3 else 512
    if not 64 <= size <= 2048:raise ValueError('Invalid chunk size')
    data=src.read_text()
    replaced=0
    while m:=FN.search(data):
        data,n,k=split_function(data,m,size)
        print(f'{src.name} {m.group(1)}: {n} instructions / {k} chunks / optimization enabled',flush=True)
        replaced+=1
    if not replaced:raise ValueError('No optnone jump-table function found')
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(data)
    print('PASS',replaced,'functions',len(data),'output bytes',flush=True)
if __name__=='__main__':run()
