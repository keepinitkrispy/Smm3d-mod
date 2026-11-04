# 2026-11-03 Vulkan guest-memory A/B evidence

These files were captured from actual Android runs; they are **not** equal-scene controlled trials.

- `baseline.log`: 3,220 MB GPU guest-heap import; severe late multi-second stalls.
- `no_gmem.log`: direct full-heap import disabled; late heavy scene ~3.6–4.0 FPS; no-import does NOT itself fix FPS.
- `unit_scale_1.log`: unit heap scale 1; guest heap import still 3,220 MB, so it does not solve import.
- `bounded-run.log`: per-draw staging with `LARECOMP_GMAP_RANGE_MB=16`, `LARECOMP_GMAP_TOTAL_MB=32`, and `LARECOMP_VK_NO_GMEM=1`. Later heavy scene ~11–13 FPS despite zero shader compiling and nearly zero Vulkan wait.
- `memory.csv` and `bounded-run.csv`: time-sampled approximate memory/PID data. They do NOT establish exact physical residency of every Vulkan import.

The installed APK matches `bounded-run` but **does not yet include the subsequent CPU-profiler opt-in edit**. For exact status and checks see ../../CURRENT_STATE.md.
