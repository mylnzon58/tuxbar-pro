"""
tuxbar_pro/audio_db.py — Real-time PipeWire / PulseAudio PCM dBFS Decibel Telemetry
Measures live output audio RMS & Peak in dBFS (-60.0 dB to 0.0 dB) with peak hold.
"""
import math
import shutil
import struct
import subprocess
import threading
import time


class PipeWireDecibelMeter:
    def __init__(self):
        self.rms_db = -60.0
        self.peak_db = -60.0
        self.hold_db = -60.0
        self.hold_time = 0.0
        self.bands_db = [-60.0] * 16
        self.running = False
        self._thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def _capture_loop(self):
        cmd = None
        if shutil.which("parec"):
            cmd = [
                "parec",
                "--format=s16le",
                "--rate=48000",
                "--channels=2",
                "--latency-msec=30",
                "--device=@DEFAULT_MONITOR@",
            ]
        elif shutil.which("pw-cat"):
            cmd = [
                "pw-cat",
                "--record",
                "--format=s16",
                "--rate=48000",
                "--channels=2",
                "-",
            ]

        if not cmd:
            return

        frame_bytes = 2048 * 4  # 2048 stereo frames @ 16-bit (~42ms)
        while self.running:
            try:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
                )
                while self.running and proc.poll() is None:
                    raw = proc.stdout.read(frame_bytes)
                    if not raw or len(raw) < 64:
                        break
                    self._process_pcm(raw)
                proc.terminate()
            except Exception:
                time.sleep(1.0)

    def _process_pcm(self, raw: bytes):
        count = len(raw) // 2
        samples = struct.unpack(f"<{count}h", raw[: count * 2])
        if not samples:
            return

        sum_sq = 0.0
        peak_abs = 0
        for s in samples:
            a = abs(s)
            if a > peak_abs:
                peak_abs = a
            norm = s / 32768.0
            sum_sq += norm * norm

        rms = math.sqrt(sum_sq / count)
        peak = peak_abs / 32768.0

        rms_db = 20.0 * math.log10(max(rms, 1e-4))
        peak_db = 20.0 * math.log10(max(peak, 1e-4))

        self.rms_db = max(-60.0, min(0.0, rms_db))
        self.peak_db = max(-60.0, min(0.0, peak_db))

        now = time.monotonic()
        if self.peak_db >= self.hold_db or (now - self.hold_time) > 1.2:
            self.hold_db = self.peak_db
            self.hold_time = now

        # Sub-band envelope approximation across 16 slices for OLED bar visualization
        chunk = max(1, count // 16)
        for b in range(16):
            seg = samples[b * chunk : (b + 1) * chunk]
            if seg:
                seg_rms = math.sqrt(sum((x / 32768.0) ** 2 for x in seg) / len(seg))
                db = max(-60.0, min(0.0, 20.0 * math.log10(max(seg_rms, 1e-4))))
                # Smooth attack/decay
                self.bands_db[b] = self.bands_db[b] * 0.45 + db * 0.55
