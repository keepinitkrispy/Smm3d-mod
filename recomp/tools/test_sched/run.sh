#!/bin/sh
# Builds tools/test_sched against runtime/kernel.c (Android configuration: the FN_ENTER safe point) and runs it with
# the IPC core release off and on. Usage: tools/test_sched/run.sh [kernel.c] [seconds] [ipc ms]
set -e
cd "$(dirname "$0")/../.."
K=${1:-runtime/kernel.c}
OUT=${TMPDIR:-/tmp}/test_sched.$$
clang -std=gnu11 -O2 -D__ANDROID__ -Wno-format -Iruntime -Iruntime/nvn -pthread tools/test_sched/test_sched.c "$K" -o "$OUT"
for v in 0 1; do printf 'LARECOMP_IPC_RELEASE_CORE=%s  ' $v; LARECOMP_IPC_RELEASE_CORE=$v "$OUT" ${2:-2} ${3:-2}; done
rm -f "$OUT"
