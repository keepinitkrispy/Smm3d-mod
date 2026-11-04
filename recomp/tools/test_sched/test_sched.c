// Scheduler regression test: links the real runtime/kernel.c against stubs and replays the 2026-11-03 Pixel stall:
// a better-priority thread pinned to core 0 alternating guest work and SendSyncRequest (host I/O), and a
// worse-priority thread on the same core. Reports how much each got done, how often the FN_ENTER safe point was
// armed, and how many times it ran. Build and run: tools/test_sched/run.sh
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include "kernel.h"
#include "cpu.h"

// ---- stubs for what kernel.c links against
void rt_log(const char *fmt, ...) { (void)fmt; }
void rt_fatal_trace(void) { abort(); }
void crash_handler_install(void) {}
void plat_commit(uint64_t a, uint64_t s) { (void)a; (void)s; }
void plat_print_backtrace(void) {}
const char *plat_symbol(uint64_t pc, uint64_t *off) { (void)pc; (void)off; return NULL; }
uint64_t plat_now_ns(void) { struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts); return ts.tv_sec * 1000000000ull + ts.tv_nsec; }
uint32_t ipc_connect_named_port(const char *n) { (void)n; return 0; }
uint32_t vi_vsync_handle(void) { return 0; }
Module g_modules[4]; int g_nmodules;

static _Atomic int armed;                 // fnprof's g_sched_hook_active
static _Atomic unsigned long long armed_ns, armed_since, safepoint_calls;
void fnprof_sched_enable(int on) {
    unsigned long long now = plat_now_ns();
    if (on && !atomic_exchange(&armed, 1)) atomic_store(&armed_since, now);
    else if (!on && atomic_exchange(&armed, 0)) atomic_fetch_add(&armed_ns, now - atomic_load(&armed_since));
}
extern void rt_guest_safepoint(void);
static inline void fn_enter(void) {      // what every generated function's FN_ENTER does on Android
    if (atomic_load_explicit(&armed, memory_order_relaxed)) { safepoint_calls++; rt_guest_safepoint(); }
}

static int ipc_ms = 2;
int ipc_handle_request(Cpu *c, uint32_t h) {  // a service doing host I/O (romfs read) for ipc_ms
    (void)c; (void)h;
    struct timespec ts = {0, ipc_ms * 1000000L};
    nanosleep(&ts, NULL);
    return 0;
}

static volatile int stop;
extern __thread uint64_t g_blocked_ns, g_corewait_ns, g_corewait_max_ns, g_corewait_holder;
static uint64_t hi_blocked, hi_corewait, hi_corewait_max, hi_holder;
static _Atomic unsigned long long hi_work, hi_ipc, lo_work;
static void busy_us(int us) {             // guest code: function entries all along
    uint64_t end = plat_now_ns() + us * 1000ull;
    while (plat_now_ns() < end) fn_enter();
}
static int sleep_mode;                   // TEST_MODE=sleep: the better thread sleeps instead of IPC, the worse one
                                         // makes no kernel call (only the safe point can give the core back)
static void hi_thread(Cpu *c) {           // thread 82: work, IPC, work, IPC...
    while (!stop) {
        busy_us(1000); hi_work++;
        if (sleep_mode) { c->x[0] = ipc_ms * 1000000ull; rt_svc(c, 0x0B, 0); }
        else rt_svc(c, 0x21, 0);
        hi_ipc++;
    }
    hi_blocked = g_blocked_ns, hi_corewait = g_corewait_ns, hi_corewait_max = g_corewait_max_ns, hi_holder = g_corewait_holder;
    rt_svc(c, 0x0A, 0);
}
static void lo_thread(Cpu *c) {           // threads 80 / 88: worse priority, same core
    while (!stop) {
        busy_us(100); lo_work++;
        if (!sleep_mode) rt_svc(c, 0x0C, 0);  // (any kernel call)
    }
    rt_svc(c, 0x0A, 0);
}
void guest_call(Cpu *c, uint64_t addr) { (addr == 1 ? hi_thread : lo_thread)(c); }

static uint32_t create(Cpu *c, uint64_t entry, int prio) {
    c->x[1] = entry; c->x[2] = 0; c->x[3] = 0x1000; c->x[4] = prio; c->x[5] = 0;
    rt_svc(c, 0x08, 0);
    return (uint32_t)c->x[1];
}

int main(int argc, char **argv) {
    int secs = argc > 1 ? atoi(argv[1]) : 2;
    if (argc > 2) ipc_ms = atoi(argv[2]);
    sleep_mode = getenv("TEST_MODE") && !strcmp(getenv("TEST_MODE"), "sleep");
    Cpu boot = {0};
    uint32_t h = create(&boot, 1, 30), l = create(&boot, 2, 44);
    boot.x[0] = l; rt_svc(&boot, 0x09, 0);  // the worse thread first: it holds core 0 when the better one starts
    usleep(20000);
    boot.x[0] = h; rt_svc(&boot, 0x09, 0);
    uint64_t t0 = plat_now_ns();
    sleep(secs);
    stop = 1;
    usleep(50000);  // (the better thread notes its kernel.c wait totals)
    double el = (plat_now_ns() - t0) / 1e9;
    fnprof_sched_enable(0);
    printf("hi_work=%llu hi_ipc=%llu lo_work=%llu armed=%.1f%% safepoint_calls=%llu | hi blocked %.0f ms, core wait %.1f ms"
           " (longest %.2f ms, holder %llu)\n", hi_work, hi_ipc, lo_work, 100.0 * armed_ns / 1e9 / el, safepoint_calls,
           hi_blocked / 1e6, hi_corewait / 1e6, hi_corewait_max / 1e6, (unsigned long long)hi_holder);
    fflush(stdout);
    _exit(0);
}
