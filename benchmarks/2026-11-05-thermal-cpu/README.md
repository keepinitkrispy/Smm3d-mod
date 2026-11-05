# Pixel 6 CPU heat / sustained FPS investigation — 2026-11-05

## Direct observations (not an accepted A/B)

A separately installed O2 ThinLTO test app was used on Pixel 6 virtual display 2, while the original app and saves were left untouched. The successful bounded event pump was enabled. The launcher/title screen was shown; no verified playable course fixture was available, so these observations cannot establish sustained gameplay FPS.

- Graphics-destination Vulkan-pass barrier experiment: approximately 46.7 FPS near 21 seconds, followed by 12.0 at 71s and 9.0 at 106s. Restored the original barrier after that run. No accepted benefit.
- Original ALL_COMMANDS destination barrier in the same experimental APK: 15–18 FPS at 35–70 seconds; phone had already accumulated heat. Not a matched cool-start comparison.
- Original barrier with LARECOMP_SCALE=0.5: 47.6 at 20s, 30.0 at 55s, 21.3 at 80s. Rendering fewer pixels did not stop the eventual slowdown.
- CPU BIG temperature was reported up to 79°C, G3D around 49–53°C, and the big core maximum clock dropped as low as 984 MHz while running. Thermal service status reached 2 (moderate). Swap was nearly full. These are substantial thermal/memory constraints; not proof of which function burns the most energy.
- Logs repeatedly recorded approximately 170–225 core-preemption handoffs per second, confirming active guest scheduling. No per-function CPU profile was captured.
- Low battery (about 21–24%), nonmatching starts, and title-screen-only scene prevent declaring a winning configuration.

## Next *isolated* CPU-side candidate

Branch: experiment/sched-hook-batch-20261105

On Android, with any guest-core waiters, the generated game's FN_ENTER hook calls fnprof_hit on each guest function entry, and that normally calls rt_guest_safepoint on each entry. The existing kernel only performs a full safepoint check on every 32nd entry. Enabling `LARECOMP_SCHED_BATCH_HOOK=1` moves that count into fnprof_hit and calls the same core-owned/scheduling safepoint body only once per 32 guest entries. The default behavior is unchanged.

The patch does **not** remove any guest-core ownership check, modify the equal-priority quantum, slow the game clock, disable the successful bounded SDL event pump, or change graphics correctness. It is not yet benchmarked.

Android 33 ARM64 fnprof.c and kernel.c compiled successfully, and the new objects linked into a local 18 MB libmain.so against the previously paired O2 build with --no-undefined; no APK for this variant has been installed. Unmodified link-only runtime objects remain in the existing local workspace.

## Validation gate

Use the existing separate test package, preserve the original install/save data, and get a repeatable *playable* course fixture. Compare *unset* versus `LARECOMP_SCHED_BATCH_HOOK=1` with the same code, scene, pacing, display, and temperature/battery starting conditions. Record per-thread CPU time, scheduler handoffs, `/proc/vmstat` swap-in/out deltas, thermal status, BIG/G3D temperatures, CPU frequency ceilings, and FPS per 5 seconds. Verify visual, audio, input and normal game-clock speed. Do not claim success unless gameplay remains >=30 FPS in the final 30 seconds of a 180s run without a downward trend. Target 60 FPS with correct game speed.

Further CPU candidates if this does not deliver: redundant stage-set descriptor updates, repeated command-list pipeline-key scans, guest-core scheduling scans, and graphics allocation/free churn. These were previously audited; none has a measured thermal benefit yet.

The original Vulkan-pass branch experiment/vk-pass-dependency-20261105 remains separately available and disabled in the test app's restored baseline recomp.env. The actual tested APK packaging received a 16 KB alignment fix before installing; local signing and CRC checks passed.
