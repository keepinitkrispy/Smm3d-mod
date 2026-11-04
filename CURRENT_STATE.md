# SMM2 native Android: current review state (2026-11-03, 20:28 ET)

**Review goal:** 30–35 FPS steady for >=2 minutes in the same menu and a busy course on Pixel 6, with 60 FPS as aspirational target. Correctness (rendering/audio/save/load/touch) must be preserved. This gate is **not met**.

## Repo contents and provenance
- `recomp/runtime/` is the source snapshot copied from the active local recomp workspace, not a dump of installed ELF binaries. Prior scheduler instrumentation in `runtime/kernel.c` and `runtime/fnprof.c` is still current.
- The **only source-file difference** between the previous tracked runtime snapshot and the current local workspace was `runtime/nvn/vulkan/exec.c`. The new diff has two sections: (1) bounded per-draw shader global-memory staging with `LARECOMP_GMAP_RANGE_MB` and `LARECOMP_GMAP_TOTAL_MB`; (2) opt-in native CPU profiler with `LARECOMP_CPU_PROF=1`. See git diff/history for exact code.
- `runtime/nvn/vulkan/device.c` already has a no-import switch: `LARECOMP_VK_NO_GMEM=1`, which selects per-draw copies instead of a full guest-heap host import.
- No copyrighted game contents, generated game-code units, saves, APKs, local keys or binary assets are included.

## Verified phone and build state
- Installed Pixel app: `org.smcraft.smm2recomp`, 3.0.3, versionCode 29895623. Its base APK SHA-256 `a46473e90825f9d50bf06442c02b62946d76dc49a7f4f905c5eaa1d9bd36c42e` matched the local `SMM2Recomp.bounded-signed.apk` exactly. **The app has been force-stopped and remains stopped.**
- Pixel data config retained `LARECOMP_VK_NO_GMEM=1`, `LARECOMP_GMAP_RANGE_MB=16`, and `LARECOMP_GMAP_TOTAL_MB=32`. `LARECOMP_LOG_PACE=1` was removed from the currently active config, with a backup on the device; the corresponding per-frame log in this repository was gathered while logging was enabled.
- The profiler opt-in change in `exec.c` was **compiled into the Android ARM64 object and relinked into a local `libmain.so` (both exit 0)**. **No APK containing this last change has been packaged, signed, installed, or performance-tested.** The prior `libmain.so` was backed up.
- The recompiled game library has **982 generated objects compiled at `-O0`** in the current locally built APK (not the intended `-O1` experiment). A **full `-O1` game-code build has not yet been completed**. Changing runtime profiling is not itself game-code optimization.
- Working wireless ADB + uid 2000 shell were verified. Stopping SMM2 immediately increased Android available memory by roughly 1.8 GiB. Excess stale Shizuku service processes were also cleaned up independently, reducing swap pressure. Separate PPHarness source changes are NOT part of this Mario repository.

## Performance and memory evidence (all from Pixel)
- `benchmarks/2026-11-03-vulkan-ab/baseline.log`: original path logged **3,220 MB guest heap imported for shader global memory**. Later 2-sec FPS summaries include 0.2–0.8 FPS with multi-second stalls around t=158–163s.
- `no_gmem.log`: `LARECOMP_VK_NO_GMEM=1` **removed the full-heap import**, confirmed via the `[vk] shader global memory:` log. In a demanding later scene at t=324–328s, only **~3.6–4.0 FPS**; this pathway alone is not a frame-rate fix. PSS in the associated `memory.csv` was still increasing with time. CSV values are the experiment script's sampled columns, not a fully trustworthy breakdown of shared GPU mapping.
- `unit_scale_1.log`: changing `LARECOMP_UNIT_HEAP_SCALE=1` did **not** remove the 3,220 MB import; ~10–14 FPS near t=117–122s. It exited/stopped around 120s; do not overinterpret.
- `bounded-run.log`: **same bounded-signed APK currently installed**, now using no-import + 16 MB max bound range / 32 MB total staging. At t=150–174s FPS was **~11–13**, despite nearly zero reported Vulkan waits, zero shader compilation in those samples, and about 32–40ms measured frame busy time with large blocked intervals. NOT >=30 FPS acceptance.
- These runs have different scene progression; they are diagnostic comparisons, not controlled proof of speedup. The no-import setting cannot legitimately be reported as a final memory/FPS solution.

## Core scheduling issue
- `benchmarks/2026-11-03-safepoint-display5.log` shows guest core waits of 2001–2272ms even after instrumentation. Some core owners changed last-SVC values during these waits; they were not simply spending the entire interval in one uninterrupted guest leaf function.
- Safepoints currently hand off only to strictly better numeric guest priorities; ties are not covered. Repeated `[corepreempt]` handoffs can also occur quickly. Do not remove guest-core exclusivity without correctness validation.

## Immediate review/build requests for Claude
1. Read this file, `recomp/runtime/kernel.c`, `recomp/runtime/fnprof.c`, `recomp/runtime/nvn/vulkan/exec.c`, and benchmark logs. **Separate measured effects from hypotheses.**
2. Review full-`-O1` generated-game compile feasibility and risks. A prior one-function `-O2` experiment yielded 9.0 median FPS vs 9.7 baseline with differing conditions; it did not pass the gate.
3. Instrument/identify critical-path frame time and core-holder state under a controlled, repeatable test. Confirm per-draw memory staging correctness (including rejected bound ranges and draw fallback).
4. Preserve the signed known-running APK, original code, saves, and ADB shell access. The game is intentionally **stopped** until a controlled performance trial.
