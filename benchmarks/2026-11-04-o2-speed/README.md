# SMM2 Pixel 6 O2 correct-speed test plan

40 FPS cap retired; nonintegral frame rates could change game speed. Current source removes cap.

Compare LARECOMP_PACE=30 forced 30-mode GPU hint against unset LARECOMP_PACE auto, then compare the verified speed-correct winner without LARECOMP_CORE_QUANTUM_US. Force30 is a hint to the game's own 30-mode selection, not a cap. On-screen timer must advance ~60 seconds over 60 seconds of real time (accepted ratio 0.95..1.05). Actual NVN present interval transitions logged with [gamemode]; 1 requests 60Hz and 2 requests 30Hz on Switch's 60Hz present clock. Audio/controls must work normally. Do not accept higher FPS that runs at wrong game speed.

The user named pace30-and-hz.patch, but NO copy was found in Pixel, Mac or Project files. The currently implemented source is a locally reconstructed narrower variant, not that named patch. It changes pace policy interpretation and logs present interval, WITHOUT applying a separate overlapping display-poll patch. Correctness remains unmeasured.

The original app org.smcraft.smm2recomp and original saves remain preserved. Experiment org.smcraft.smm2o2cap0 was separately updated with matching O2 ThinLTO game ID ff0e33f110679bd7. Signing and 16k library alignment verified. No 180-second gameplay runs have been done; device was at 6% battery unplugged at last check. The script refuses below 30%, warm or plugged, and requires a truly verified playable course fixture.

Historic sanitized logs and original env text are under historic/. The O2 env is extracted from logged CONF in bench-originfixed.txt; split env from the preserved production-paceoff.env. Historic runs are NOT controlled 180-second gameplay runs.

Next: choose and verify one playable course, run 180s at cool unplugged starts, compare 150-180s FPS ONLY if 60s in-course timer tracks real time, verify audio and input, and push every run. Then profile kernel dmabuf worker and alloc threads with game running versus stopped, count Vulkan buffer/image allocation/free rates, and use simpleperf where permitted. Preserve guest-core exclusivity.
