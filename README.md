# Smm3d-mod — SMM2 recomp Android optimization review

Current task: reduce native Super Mario Maker 2 Android memory/CPU pressure and achieve sustained >=30–35 FPS on Pixel 6 without correctness regressions.

**Start with [CURRENT_STATE.md](CURRENT_STATE.md).** It distinguishes the latest source edits, installed APK version, completed tests, unverified hypotheses, and proposed next work.

- Source under `recomp/runtime/`: Android runtime, scheduler safe points, Vulkan backend including bounded per-draw guest-memory staging and opt-in CPU profiling.
- Test evidence under `benchmarks/`, especially `benchmarks/2026-11-03-vulkan-ab/`.
- Game files, ROMs, generated game-code objects, APKs, credentials and saves are intentionally excluded.

**Not yet implemented/validated:** full `-O1` generated game-code build, profiler-opt-in APK install, >=30 FPS acceptance, and final scheduler performance fix.
