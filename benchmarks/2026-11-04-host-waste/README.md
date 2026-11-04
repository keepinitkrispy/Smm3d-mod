# Host CPU investigation — 2026-11-04

Status: diagnostic capture complete; optimization acceptance NOT measured.

Physical Pixel 6 selected explicitly as 127.0.0.1:5555; emulator excluded. Shell UID 2000 and Shizuku+ shell server verified. Installed package versionCode 29896278; startup confirms bounded event pump enabled. Full installed binary/source equivalence and best-build status are not established by versionCode alone.

## Captures
Two ~40-second launches; whole-device top sampled every 5 seconds over 30 seconds. First top capture sorted incorrectly with custom columns: do not use for ranking. Second capture explicitly sorts CPU; ranking excludes first snapshot and averages six intervals. No controlled 3-minute trial completed. Title courses differed between launches; no warm-cache speedup claim. Another foreground app was active during capture. Phone was unplugged, battery 5% initially, 3% after captures; game stopped. Temperature increased from 35.8 to 37.5 C. No thermal override, fixed-performance or game-mode change.

## Findings
- Top external thread: dmabuf-deferred-free-worker 18.7% of one core, graphics-buffer cleanup.
- Two graphics allocator service threads: 10.7% + 9.2%, buffer allocation service work.
- kswapd0: 6.4%, memory reclaim; initial second-launch swap occupancy 3060648/3145724 KiB.
- Mali job thread: 8.5%, GPU job servicing.
- SurfaceFlinger main/render-service threads: 6.0% + 6.6%, composition.
- top itself: 5.8%; measurement overhead matters.
- Game threads have generic names; cannot assign functions from top.
- Pace logging already off in baseline. No new pace-off comparison.
- Shader prefetch remains active at ~34 seconds in second launch (1 program + 5 pipelines). This is not proof that ahead.c's separate background worker is active. ahead_vk.done absent; completion remains unknown.
- SDL HIDAPI flag consumption supported by unrestricted recomp.env parser, but benefit/input compatibility untested.

## Profiler blocker
simpleperf exists. Kernel-inclusive cpu-clock rejected; cpu-clock:u retry rejected with Permission denied opening the perf event for the game. No function profile was recorded. Top 20 functions, libc/SDL3/unmapped attribution UNKNOWN. Next dependency: verify APK profileable-by-shell manifest and package a matching signed profileable APK, retaining current game/runtime pairing and known-good APK. Do not treat the shell self-stat probe as game profiling permission.

## Prepared experiments
- display-poll-experimental.patch: opt-in LARECOMP_DISPLAY_POLL_MS=1000; default unchanged. Limits refresh-rate query to once per second on UI thread.
- sleep-counter-experimental.patch: opt-in LARECOMP_HOST_POLL_PROF=1; records exact SleepThread(0) and sched_yield counts with elapsed nanoseconds. Keeps guest-core exclusivity and scheduling intact. Diagnostic overhead must be excluded from acceptance trials; discard first reporting interval.
Both patches pass git apply --check separately against active workspace source. Not compiled, installed or measured. Source hashes saved. Active source, APK and recomp.env unchanged.

## Remaining
Recharge then unplug and cool to the same starting temperature. Verify current best runtime/game hashes. Set identical course/seed for every run. Mark APK profileable if required and rerun function sampling. Run baseline plus one-factor 180-second trials; compare FPS at 150–180 seconds, verify input/audio/rendering, retain only demonstrated improvements. All prospective savings and SleepThread rates remain UNKNOWN.
