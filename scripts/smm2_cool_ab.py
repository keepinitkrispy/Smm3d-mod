#!/usr/bin/env python3
"""Guarded 180s Pixel 6 O2 pace30 / default / no-quantum benchmark; reject slow-motion winners."""
import argparse
import json
import pathlib
import re
import statistics
import subprocess
import time

HOME = pathlib.Path.home()
REPO = HOME / "smm3d-source"
OUT = REPO / "benchmarks/2026-11-04-o2-speed"
ADB = ["adb", "-s", "127.0.0.1:5555"]
APP = "org.smcraft.smm2o2cap0"
DATA = f"/sdcard/Android/data/{APP}/files"
BRANCH = "experiment/main-x1-affinity-20261104"
FIXTURE_PATH = HOME / "smm2-hot/cap40/course-fixture.json"
CONF = {
    "LARECOMP_VK_NO_GMEM": "1",
    "LARECOMP_GMAP_RANGE_MB": "16",
    "LARECOMP_GMAP_TOTAL_MB": "32",
    "LARECOMP_IPC_RELEASE_CORE": "1",
    "LARECOMP_CORE_QUANTUM_US": "4000",
    "LARECOMP_BOUNDED_EVENTS": "1",
    "LARECOMP_FPS_INTERVAL": "5",
}

def adb(*args, timeout=30):
    return subprocess.run(ADB + list(args), text=True, capture_output=True, timeout=timeout)

def power():
    text = adb("shell", "dumpsys battery").stdout
    m = re.search(r"^\s*level:\s*(\d+)", text, re.M)
    plugged = [s for s in ("AC", "USB", "Wireless", "Dock")
               if re.search(r"^\s*" + s + r" powered:\s*true", text, re.M)]
    mt = re.search(r"Thermal Status:\s*(\d+)", adb("shell", "dumpsys thermalservice").stdout)
    return {"battery_pct": int(m.group(1)) if m else None,
            "plugged": plugged, "thermal_status": int(mt.group(1)) if mt else None}

def freqs():
    result = {}
    for c in (0, 1, 2, 3, 4, 5, 6, 7):
        path = pathlib.Path(f"/sys/devices/system/cpu/cpu{c}/cpufreq")
        result[str(c)] = {}
        for field in ("scaling_cur_freq", "scaling_max_freq"):
            try:
                result[str(c)][field] = int((path / field).read_text().strip())
            except (ValueError, OSError):
                result[str(c)][field] = None
    return result

def fixture():
    """A real, externally verified replay to one specific playable course."""
    try:
        x = json.loads(FIXTURE_PATH.read_text())
        if x.get("verified") is True and isinstance(x.get("seed"), int) and \
           isinstance(x.get("input_script"), str) and x["input_script"] and \
           isinstance(x.get("course_id"), str) and x["course_id"]:
            return x
    except (OSError, ValueError, TypeError):
        pass
    return None

def check():
    bat = power()
    freq = freqs()
    enough = bat["battery_pct"] is not None and bat["battery_pct"] >= 30
    cool = bat["thermal_status"] is not None and bat["thermal_status"] <= 1
    maxes = [freq[str(i)]["scaling_max_freq"] or 0 for i in (6, 7)]
    cold_clock = min(maxes) >= 2500000
    selected = fixture()
    apk = adb("shell", f"pm path {APP}").stdout.strip().startswith("package:")
    exefs = adb("shell", f"test -s {DATA}/extracted/exefs/main").returncode == 0
    romfs = adb("shell", f"test -d {DATA}/extracted/romfs").returncode == 0
    return {"battery": bat, "big_core_freq_khz": {i: freq[str(i)] for i in (6, 7)},
            "clone_installed": apk, "clone_exefs": exefs, "clone_romfs": romfs,
            "playable_course_fixture_verified": selected is not None,
            "ready": enough and not bat["plugged"] and cool and cold_clock and apk and exefs and romfs and selected is not None}

def winning_policy():
    """Post-validation decision; NEVER infer winner from FPS alone."""
    path = OUT / "winner.json"
    try:
        result = json.loads(path.read_text())
        if result.get("verified") is True and result.get("speed_ratio") is not None and \
           0.95 <= float(result["speed_ratio"]) <= 1.05 and \
           result.get("pace_mode") in ("pace30", "default"):
            return result["pace_mode"]
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return None

def collect(mode):
    info = check()
    if not info["ready"]:
        raise SystemExit("NO RUN: cool/unplugged/battery/data gate not met: " + json.dumps(info))
    OUT.mkdir(parents=True, exist_ok=True)
    if mode == "noquantum" and winning_policy() is None:
        raise SystemExit("NO RUN: validate game-speed/correct winner first, record winner.json")
    config = OUT / f"{mode}.env"
    selected = fixture()
    assert selected is not None
    settings = CONF | {"SMM2_SEED": str(selected["seed"]),
                       "LARECOMP_INPUT": selected["input_script"],
                       "LARECOMP_NO_USER_INPUT": "1"}
    pace = winning_policy() if mode == "noquantum" else mode
    if pace == "pace30":
        settings["LARECOMP_PACE"] = "30"
    if mode == "noquantum":
        del settings["LARECOMP_CORE_QUANTUM_US"]
    config.write_text("".join(f"{k}={v}\n" for k, v in settings.items()))
    config_record = OUT / f"{mode}.recomp.env"
    config_record.write_text(config.read_text())
    assert adb("push", str(config), DATA + "/recomp.env", timeout=90).returncode == 0
    config.unlink()
    adb("shell", f"am force-stop {APP}")
    samples = []
    raw = OUT / f"{mode}.raw-local.log"
    with raw.open("w") as sink:
        log = subprocess.Popen(ADB + ["logcat", "-v", "time", "-s", "smm2recomp:I"],
                               stdout=sink, stderr=subprocess.DEVNULL)
        try:
            launch = adb("shell", f"am start -n {APP}/org.libsdl.app.SDLActivity")
            if launch.returncode:
                raise RuntimeError(launch.stderr)
            start = time.monotonic()
            for n in range(37):
                remaining = 5 * n - (time.monotonic() - start)
                if remaining > 0:
                    time.sleep(remaining)
                t = round(time.monotonic() - start, 2)
                # Evidence is local only: a screenshot just before the scoring window,
                # and another at the end, after confirming the clone is foreground.
                if n in (12, 24, 30, 36):
                    top = adb("shell", "dumpsys activity activities | grep -m1 topResumedActivity").stdout
                    if APP in top:
                        screenshot = OUT / f"{mode}-scene-{n*5}s.local.png"
                        with screenshot.open("wb") as png:
                            capture = subprocess.run(ADB + ["exec-out", "screencap", "-p"], stdout=png, timeout=20)
                        if capture.returncode:
                            screenshot.unlink(missing_ok=True)
                samples.append({"seconds": t, "cpu_khz": freqs(),
                                "battery": power() if n % 6 == 0 else None,
                                "game_pid": adb("shell", f"pidof {APP}").stdout.strip()})
        finally:
            adb("shell", f"am force-stop {APP}")
            log.terminate()
            try:
                log.wait(timeout=5)
            except subprocess.TimeoutExpired:
                log.kill()
    lines = raw.read_text(errors="replace").splitlines()
    fps = []
    for line in lines:
        m = re.search(r"\[vk\] t=([0-9.]+) frame \d+ ([0-9.]+) fps", line)
        if m:
            fps.append({"time": float(m.group(1)), "fps": float(m.group(2))})
    last = [x["fps"] for x in fps if 150 <= x["time"] <= 180]
    result = {"mode": mode, "duration_seconds": 180, "fps": fps,
              "cpu_and_battery_5s": samples,
              "steady_150_180": {"n": len(last), "mean": statistics.mean(last) if last else None,
                                  "minimum": min(last) if last else None},
              "fixture_id": selected["course_id"],
              "scene_verified": False, "speed_ratio": None, "correct_speed_verified": False,
              "nvn_present_intervals": [line.strip()[-350:] for line in lines if "[gamemode]" in line],
              "pace_policy": pace, "core_quantum_us": None if mode == "noquantum" else 4000,
              "note": "Review local scene snapshots at 60s and 120s; compare game in-course timer delta to 60 real seconds. Only compare verified runs with speed ratio 0.95..1.05."}
    report = OUT / f"{mode}.json"
    report.write_text(json.dumps(result, indent=2) + "\n")
    clean = OUT / f"{mode}.sanitized.log"
    clean.write_text("\n".join(line[-600:] for line in lines if
                               "[vk] t=" in line or "[pace]" in line or
                               "[gamemode]" in line or "[eventpump]" in line or
                               "[gmap]" in line) + "\n")
    subprocess.run(["git", "add", str(report.relative_to(REPO)), str(clean.relative_to(REPO)),
                    str(config_record.relative_to(REPO))],
                   cwd=REPO, check=True)
    subprocess.run(["git", "commit", "-m", f"Pixel O2 {mode} 180s FPS and clock run"], cwd=REPO, check=True)
    pushed = subprocess.run(["git", "push", "origin", f"HEAD:refs/heads/{BRANCH}"],
                            cwd=REPO, capture_output=True, text=True)
    print(json.dumps({"steady": result["steady_150_180"],
                      "published": pushed.returncode == 0,
                      "git_output": (pushed.stdout + pushed.stderr)[-700:]}, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--run", choices=["pace30", "default", "noquantum"])
    a = parser.parse_args()
    if a.check or not a.run:
        print(json.dumps(check(), indent=2))
    if a.run:
        collect(a.run)
