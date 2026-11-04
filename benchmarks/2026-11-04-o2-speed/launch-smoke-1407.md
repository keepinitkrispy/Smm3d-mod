# Pixel 6 O2 correctness smoke test — 2026-11-04 14:03–14:07 EST

**Result: APK launches after repairing cloned-file permissions; NOT a verified playable-course or 180s performance test.**

## Tested variant
- Installed experimental package `org.smcraft.smm2o2cap0`, with O2 ThinLTO runtime and event pump. Original package `org.smcraft.smm2recomp` and original saves were left unchanged.
- Bench battery 10–13% **AC-powered** (not eligible for requested cold/unplugged run). User foreground interactions precluded uninterrupted 3-minute course testing.
- Initial smoke env forced `LARECOMP_PACE=30` for checking codepath; after smoke, clone env restored to **default automatic pacing** (no `LARECOMP_PACE` line; no 40 FPS cap).

## Failure and repair evidence
1. **14:03:** app exited with `FATAL: cannot load extracted/exefs/main: Permission denied`. The copied `extracted` directories were shell-owned with mode 2770, preventing the clone package UID from traversing them. Applied `chmod o+rx` on shell-owned directories within clone only.
2. **14:04:** app initialized Vulkan but guest trapped `FATAL: svcBreak... `; immediately preceding guest log: `SaveDataMgr | SDK has been aborted or failed assertion with no message.` Cloned save files were shell-owned `-rw-r-----` so the app UID could not read or update them. Added clone-file read permissions, clone-save read/write permissions and clone-save directory traverse/write. Original save directory was not modified.
3. **14:05:** app stayed alive for an ~9-second startup smoke and logged `[pace] policy=force30`; no further `FATAL` during that smoke. At this point one early FPS entry reported ~13.6 FPS during initialization, not gameplay.
4. **14:06:** app reached `[vk] t=4.9 frame 54 24.7 fps` and read ROMFS, initialized audio and input. Android then logged a swipe-up `Gesture Monitor ... stealing input`, `onPause`, `surfaceDestroyed`, and `[vk] surface lost; no new one yet` due to backgrounding. Later `ActivityManager: Killing ... (adj 900): remove task`. A screenshot at ~16 seconds was black because the app task had been removed. This is **not an app-crash or valid gameplay measurement**.

## Remaining constraints
- The clone's ROMFS currently contains all non-stream game assets plus only selected common/M1 music. Other style audio (e.g. `3W_BGM_Plain_Play.bwav`) is not copied and may cause future missing-resource errors.
- FPS at true gameplay and correct game speed are **unverified**. No 60s in-course timer ratio, no 180s gameplay run, and no 150–180s steady FPS number.
- Recharge to >=30%, cool and unplug for comparable tests; ensure uninterrupted foreground scene, same playable course and audio, before deciding between forced 30, auto and no-quantum experiments.
- Guest-core exclusivity and original installed package preserved.
