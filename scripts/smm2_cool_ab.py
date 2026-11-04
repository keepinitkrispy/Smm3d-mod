#!/usr/bin/env python3
"""Guarded 180s Pixel 6 O2 capped-vs-uncapped benchmark. Never spoof charging."""
import argparse
import json
import pathlib
import re
import statistics
import subprocess
import time

HOME = pathlib.Path.home()
REPO = HOME / "smm3d-source"
OUT = REPO / "benchmarks/2026-11-04-o2-cap40"
ADB = ["adb", "-s", "127.0.0.1:5555"]
APP = "org.smcraft.smm2o2cap0"
DATA = f"/sdcard/Android/data/{APP}/files"
BRANCH = "experiment/main-x1-affinity-20261104"
CONF = {
    "LARECOMP_VK_NO_GMEM": "1",
    "LARECOMP_GMAP_RANGE_MB": "16",
    "LARECOMP_GMAP_TOTAL_MB": "32",
    "LARECOMP_IPC_RELEASE_CORE": "1",
    "LARECOMP_CORE_QUANTUM_US": "4000",
    "LARECOMP_BOUNDED_EVENTS": "1",
    "LARECOMP_PACE": "0",
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

def check():
    bat = power()
    freq = freqs()
    enough = bat["battery_pct"] is not None and bat["battery_pct"] >= 30
    cool = bat["thermal_status"] is not None and bat["thermal_status"] <= 1
    maxes = [freq[str(i)]["scaling_max_freq"] or 0 for i in (6, 7)]
    cold_clock = min(maxes) >= 2500000
    apk = adb("shell", f"pm path {APP}").stdout.strip().startswith("package:")
    exefs = adb("shell", f"test -s {DATA}/extracted/exefs/main").returncode == 0
    romfs = adb("shell", f"test -d {DATA}/extracted/romfs").returncode == 0
    return {"battery": bat, "big_core_freq_khz": {i: freq[str(i)] for i in (6, 7)},
            "clone_installed": apk, "clone_exefs": exefs, "clone_romfs": romfs,
            "ready": enough and not bat["plugged"] and cool and cold_clock and apk and exefs and romfs}

def collect(mode):
    info = check()
    if not info["ready"]:
        raise SystemExit("NO RUN: cool/unplugged/battery/data gate not met: " + json.dumps(info))
    OUT.mkdir(parents=True, exist_ok=True)
    config = OUT / f"{mode}.env"
    config.write_text("".join(f"{k}={v}\n" for k, v in (CONF | {"LARECOMP_FPS_CAP": "40" if mode == "cap40" else "0"}).items()))
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
              "scene_verified": False, "note": "Course equality requires screenshot/save-state verification."}
    report = OUT / f"{mode}.json"
    report.write_text(json.dumps(result, indent=2) + "\n")
    clean = OUT / f"{mode}.sanitized.log"
    clean.write_text("\n".join(line[-600:] for line in lines if
                               "[vk] t=" in line or "[framecap]" in line or
                               "[eventpump]" in line or "[gmap]" in line) + "\n")
    subprocess.run(["git", "add", str(report.relative_to(REPO)), str(clean.relative_to(REPO))],
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
    parser.add_argument("--run", choices=["cap40", "uncapped"])
    a = parser.parse_args()
    if a.check or not a.run:
        print(json.dumps(check(), indent=2))
    if a.run:
        collect(a.run)
