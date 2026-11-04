SUPERSEDED: 40 FPS cap DROPPED. See ../2026-11-04-o2-speed/README.md. Do not run this old protocol.

# Pixel 6: ThinLTO O2 + event pump + optional 40 FPS cap

Verified build and side-by-side install, but **no 180-second gameplay A/B completed** (Nov 4, 2026, approximately 10 AM EST).

## Provenance and safety

- Original installed org.smcraft.smm2recomp unchanged (APK SHA256 71c07e0393726e572850ae0d13c77d0c386089304d1c379db83fdfc7e61afe27), original saves preserved.
- Experimental org.smcraft.smm2o2cap0 installed as separate package; signed artifact ~/smm2-hot/cap40/clone-signed.apk, SHA256 c064a45c7f34f17901a62eaa4dbad87c214650bfb542d4710f77e3c817e0414b.
- Game lib compiled with -O2 -flto=thin, matching native runtime ID ff0e33f110679bd7. Bounded SDL event pump present. Runtime cap via LARECOMP_FPS_CAP=40/0; cap source committed 588e2d4. Guest-core exclusivity unchanged.
- Signed original and rollback APKs, game archive, saves and unique source preserved. Only verified unsigned intermediates and byte-for-byte redundant extracted source removed. Mac available storage increased ~221MiB to 1.0GiB. Pixel storage increased from <1GiB to ~2.5GiB before game data staging.
- Clone has separately copied exefs, saves, non-stream romfs plus common/M1 music (~1.39GiB). Not a full game-data clone; additional music styles not included. Hardlinks and FICLONE between package-specific storage denied by Android.

## Benchmark contract / blockers

- Harness scripts/smm2_cool_ab.py committed d7cbc54. --check requires physically unplugged, battery >=30%, thermal status <=1, big core maximum >=2.5GHz, installed clone and game files. --run cap40 and --run uncapped: each 180 seconds, 5s FPS renderer interval and CPU frequency sampling, 150-180s summary, sanitized logs/JSON pushed to GitHub after each run.
- Latest phone power was 13% AC charging; no valid unplugged cool-start test can run in this state.
- Historical screenshot of earlier test was title screen (Press L+R) over a rendered course. game_level_name() in source is a weak placeholder: blank level field does NOT confirm gameplay. Current harness marks scene_verified=false; 180-second runs and a steady-gameplay >=30 claim must wait for identical confirmed playable course/scene evidence. The scripted menu navigation in recomp/tools/shader_ab.sh only reaches Course World; do not assume it entered playable course. Verify before interpreting data.
- After physical power and course conditions are satisfied, run same course capped/uncapped, publish logs after each, choose the higher steady 150-180s FPS, then profile selected build and remove biggest measured CPU waste, preserving guest core exclusivity.
