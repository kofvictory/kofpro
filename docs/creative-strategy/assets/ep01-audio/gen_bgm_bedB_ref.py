#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EP01 BGM Bed B「解決」参照トーン (30s) — 方向確認用スケッチ。
BGM-DIRECTION.md §2 Bed B(warm-bright / ①完成形デモ・⑦解決・⑧前向き)の音を耳で確認するため。
  100 BPM / C major(明・希望) / C-G-Am-F-C-G。フェルトピアノ(魂/橙)が主役。
  構成: 前半(0-14s)=ジェントル(ピアノ+パッド) → 後半(14-30s)=ブルーム(上昇arp+柔ビートが加わり膨らむ)。
  =⑥沈黙からの⑦再入(カタルシス)を「builds to a bloom」で体現。
標準ライブラリのみ・正弦波テーブル・固定シード。出力: bgm-bedB-ref-30s.wav (44.1k/16bit/stereo)
"""
import math, wave, array, struct, random, os
random.seed(3)
SR = 44100
BPM = 100.0
beat = 60.0 / BPM            # 0.6
bar = 4 * beat              # 2.4
BLOOM_T = 6 * bar           # 14.4s から後半ブルーム
TOTAL_S = 30.0
N = int(TOTAL_S * SR)
L = array.array('d', bytes(8 * N)); R = array.array('d', bytes(8 * N))
TAB = 4096
SINE = [math.sin(2 * math.pi * i / TAB) for i in range(TAB)]

def add_wt(t0, freq, dur, amp, gl, gr, partials, env):
    s0 = int(t0 * SR); ns = int(dur * SR)
    if s0 >= N or s0 < 0: return
    ph = [0.0] * len(partials); inc = [freq * m * TAB / SR for (m, _a) in partials]
    for i in range(ns):
        idx = s0 + i
        if idx >= N: break
        e = env(i / SR)
        if e <= 0.0:
            if i / SR > 0.02: break
            else: continue
        s = 0.0
        for k in range(len(partials)):
            s += partials[k][1] * SINE[int(ph[k]) & (TAB - 1)]; ph[k] += inc[k]
        v = amp * e * s
        L[idx] += v * gl; R[idx] += v * gr

def env_ar(a, dur, r):
    def f(t):
        if t < a: return t / a
        if t > dur - r: return max(0.0, (dur - t) / r)
        return 1.0
    return f
def env_swell(dur, pk=0.4):
    p = dur * pk
    def f(t):
        x = (t / p) if t < p else max(0.0, (dur - t) / (dur - p))
        return 0.5 - 0.5 * math.cos(math.pi * min(1.0, x))
    return f
def env_pluck(a, tau):
    def f(t):
        if t < a: return t / a
        return math.exp(-(t - a) / tau)
    return f

# ── コード進行(2小節ずつ): C - G - Am - F - C - G ─────────────────
BLOCKS = [
    (0,  dict(pad=[261.63, 329.63, 392.00, 493.88], sub=65.41, arp=[523.25, 659.25, 783.99, 1046.50])),  # C
    (2,  dict(pad=[196.00, 246.94, 293.66, 392.00], sub=98.00, arp=[493.88, 587.33, 783.99, 987.77])),   # G
    (4,  dict(pad=[220.00, 261.63, 329.63, 392.00], sub=110.00, arp=[523.25, 659.25, 880.00, 1046.50])), # Am
    (6,  dict(pad=[174.61, 220.00, 261.63, 329.63], sub=87.31, arp=[523.25, 698.46, 880.00, 1046.50])),  # F  (bloom開始)
    (8,  dict(pad=[261.63, 329.63, 392.00, 493.88], sub=65.41, arp=[523.25, 659.25, 783.99, 1046.50])),  # C
    (10, dict(pad=[196.00, 246.94, 293.66, 392.00], sub=98.00, arp=[493.88, 587.33, 783.99, 987.77])),   # G
]
for (sb, ch) in BLOCKS:
    t0 = sb * bar; dur = 2 * bar
    bloom = t0 >= BLOOM_T - 1e-6
    padamp = 0.040 if bloom else 0.030
    sw = env_swell(dur + 0.6)
    for pf in ch['pad']:
        add_wt(t0, pf * 0.9995, dur + 0.6, padamp, 0.86, 0.30, [(1, 0.60), (2, 0.13), (3, 0.05)], sw)
        add_wt(t0, pf * 1.0005, dur + 0.6, padamp, 0.30, 0.86, [(1, 0.60), (2, 0.13), (3, 0.05)], sw)
    add_wt(t0, ch['sub'], dur + 0.4, 0.26, 0.5, 0.5, [(1, 1.0), (2, 0.05)], env_ar(0.2, dur + 0.4, 0.4))
    # 後半ブルーム: 上昇アルペジオ(8分)を敷く
    if bloom:
        n8 = int(round(dur / (beat / 2)))   # 8分の数
        for st in range(n8):
            t = t0 + st * (beat / 2)
            f = ch['arp'][st % 4]
            gl, gr = (0.62, 0.42) if st % 2 == 0 else (0.42, 0.62)
            add_wt(t, f, 0.30, 0.055, gl, gr, [(1, 0.6), (2, 0.22), (3, 0.08)], env_pluck(0.004, 0.20))

# ── フェルトピアノ(魂/橙) = 主役メロディ ───────────────────────────
# (t, freq, dur)。前半=希望の立ち上がり / 後半=1オクターブ上へ膨らみC(高)へ到達
PIANO = [
    (0.0, 329.63, 0.6), (0.6, 392.00, 0.6), (1.2, 523.25, 1.9),      # C: E4 G4 C5
    (4.8, 587.33, 0.6), (5.4, 493.88, 0.6), (6.0, 392.00, 1.9),      # G: D5 B4 G4
    (9.6, 523.25, 0.6), (10.2, 440.00, 0.6), (10.8, 659.25, 1.9),    # Am: C5 A4 E5
    (14.4, 440.00, 0.6), (15.0, 523.25, 0.6), (15.6, 698.46, 1.9),   # F(bloom): A4 C5 F5
    (19.2, 783.99, 0.6), (19.8, 659.25, 0.6), (20.4, 1046.50, 2.1),  # C: G5 E5 C6(頂点=到達)
    (24.0, 587.33, 0.6), (24.6, 493.88, 0.6), (25.2, 392.00, 2.7),   # G: D5 B4 G4(settle)
]
PIANO_P = [(1, 0.72), (2, 0.16), (3, 0.05)]   # フェルト=柔らかめ
for (t, f, d) in PIANO:
    amp = 0.16 if t < BLOOM_T else 0.195
    if f > 900: amp *= 0.82          # 高音は刺さらないよう控えめ
    add_wt(t, f, d + 1.2, amp, 0.54, 0.46, PIANO_P, env_pluck(0.010, 0.95))

# ── 後半ブルームの柔らかいビート(kick 拍1・3 / hat 裏8分) ───────────
b0 = int(BLOOM_T / bar)
for b in range(b0, 12):
    tb = b * bar
    for bt in (0, 2):
        tk = tb + bt * beat; s0 = int(tk * SR); ns = int(0.2 * SR); ph = 0.0
        for i in range(ns):
            idx = s0 + i
            if idx >= N: break
            tt = i / SR
            fk = 46.0 + (68.0 - 46.0) * math.exp(-tt / 0.05)
            ph += fk * TAB / SR
            v = 0.27 * math.exp(-tt / 0.11) * SINE[int(ph) & (TAB - 1)]
            L[idx] += v * 0.5; R[idx] += v * 0.5
    for bt in range(4):
        th = tb + bt * beat + beat * 0.5; s0 = int(th * SR); ns = int(0.02 * SR)
        gl, gr = (0.6, 0.4) if bt % 2 == 0 else (0.4, 0.6)
        for i in range(ns):
            idx = s0 + i
            if idx >= N: break
            v = 0.038 * math.exp(-(i / SR) / 0.004) * random.uniform(-1, 1)
            L[idx] += v * gl; R[idx] += v * gr

# ── 全体ビルド包絡: ブルームを可聴化(前半0.70 → 後半1.0へ3秒でランプ) ──
_r0, _r1 = BLOOM_T - 1.0, BLOOM_T + 2.0
for i in range(N):
    t = i / SR
    if t < _r0: gain = 0.70
    elif t < _r1: gain = 0.70 + 0.30 * ((t - _r0) / (_r1 - _r0))
    else: gain = 1.0
    L[i] *= gain; R[i] *= gain

# ── マスター: 軽LP(暖かく・ピアノのきらめきは残す) → 正規化 → 端フェード ─
def lowpass(buf, a):
    y = 0.0
    for i in range(N):
        y += a * (buf[i] - y); buf[i] = y
lowpass(L, 0.68); lowpass(R, 0.68)
peak = max(1e-9, max(abs(L[i]) for i in range(N)), max(abs(R[i]) for i in range(N)))
g = (10 ** (-3.0 / 20)) / peak
fade = int(0.015 * SR)
frames = bytearray()
for i in range(N):
    fe = 1.0
    if i < fade: fe = i / fade
    elif i > N - fade: fe = max(0.0, (N - i) / fade)
    for buf in (L, R):
        s = max(-1.0, min(1.0, buf[i] * g * fe))
        frames += struct.pack('<h', int(s * 32767))
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bgm-bedB-ref-30s.wav')
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(bytes(frames))
print('wrote', out)
