"""Experimental split of an emitted function's exhaustive dispatch fallback.
Input: one generated function and its declarations. No game contents included.
Usage: python split_hot_function.py source.c guest_address output.c
"""
from pathlib import Path
import sys
source, address, output = sys.argv[1:]
address = address.removeprefix("0x")
s = Path(source).read_text()
start = s.index(f"void f_{address}(Cpu *c) {{")
header, body = s[:start], s[start:]
assert body.count("L_dispatch:") == 1
cold = body.replace(f"void f_{address}(Cpu *c) {{",
    f"__attribute__((optnone,noinline)) static void cold_{address}(Cpu *c) {{\n    goto L_dispatch;", 1)
fast = body[:body.rindex("L_dispatch:")] + "}\n"
fast = fast.replace("goto L_dispatch;", f"return cold_{address}(c);")
Path(output).write_text(header + cold + "\n" + fast)
