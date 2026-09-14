#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EP01 BGM Bed A「思考」参照トーン (30s) — 方向確認用スケッチ。
本番は生成AI/RFで調達。これは BGM-DIRECTION.md §2 Bed A の音を耳で確認するための試作。
  base-cool / 論理・実装・中立 / 96 BPM / A minor / Am-F-C-G(各3小節=12小節=30s ループ)
  冷シンセ16分アルペジオ(器/紫) + 暖パッド(魂/橙) + sub + 微kick/tick、軽いLPで warm 化。
標準ライブラリのみ・正弦波テーブル合成・乱数は固定シード(再現可能)。
出力: bgm-bedA-ref-30s.wav (44.1k/16bit/stereo)
"""
import math, wave, array, random, struct, os

random.seed(42)
SR = 44100
BPM = 96.0
spb = 60.0 / BPM              # 0.625 s/beat
bar = 4 * spb                 # 2.5 s/bar
TOTAL_S = 30.0
N = int(TOTAL_S * SR)
L = array.array('d', bytes(8 * N))   # N zeros (float64)
R = array.array('d', bytes(8 * N))

TAB = 4096
SINE = [math.sin(2 * math.pi * i / TAB) for i in range(TAB)]

# ── コード進行(各3小節): Am - F - C - G ────────────────────────────
CHORDS = [
    dict(name='Am', arp=[440.00, 523.25, 659.25, 880.00], pad=[220.00, 261.63, 329.63], sub=110.00),
    dict(name='F',  arp=[349.23, 440.00, 523.25, 698.46], pad=[174.61, 220.00, 261.63], sub=87.31),
    dict(name='C',  arp=[392.00, 523.25, 659.25, 783.99], pad=[261.63, 329.63, 392.00], sub=130.81),
    dict(name='G',  arp=[392.00, 493.88, 587.33, 783.99], pad=[196.00, 246.94, 293.66], sub=98.00),
]
BARS_PER_CHORD = 3
ARP_PAT = [0, 2, 3, 1]        # 16分でこの順にコード音を回す(転がるアルペジオ)

def add_wt(t0, freq, dur, amp, gl, gr, partials, env):
    """波形テーブルで partials を合成し env(関数) を掛けて L/R に加算。"""
    s0 = int(t0 * SR); ns = int(dur * SR)
    if s0 >= N: return
    phases = [0.0] * len(partials)
    incs = [freq * m * TAB / SR for (m, _a) in partials]
    for i in range(ns):
        idx = s0 + i
        if idx >= N: break
        e = env(i / SR)
        if e <= 0.0:
            if i / SR > 0.02: break
            else: continue
        s = 0.0
        for k in range(len(partials)):
            ph = phases[k]
            s += partials[k][1] * SINE[int(ph) & (TAB - 1)]
            phases[k] = ph + incs[k]
        v = amp * e * s
        L[idx] += v * gl; R[idx] += v * gr

def env_pluck(attack, tau):
    def f(t):
        if t < attack: return t / attack
        return math.exp(-(t - attack) / tau)
    return f

def env_ar(attack, dur, release):
    def f(t):
        if t < attack: return t / attack
        if t > dur - release: return max(0.0, (dur - t) / release)
        return 1.0
    return f

# ── 各コードのブロックを敷く ──────────────────────────────────────
for ci, ch in enumerate(CHORDS):
    t_chord = ci * BARS_PER_CHORD * bar
    dur_chord = BARS_PER_CHORD * bar

    # pad(魂/橙): 三和音、各音を±デチューン2声で左右に広げる。warm(倍音少なめ)
    for vi, pf in enumerate(ch['pad']):
        env = env_ar(0.6, dur_chord + 0.5, 0.7)
        add_wt(t_chord, pf * 0.9994, dur_chord + 0.4, 0.052, 0.85, 0.30,
               [(1, 0.62), (2, 0.10)], env)
        add_wt(t_chord, pf * 1.0006, dur_chord + 0.4, 0.052, 0.30, 0.85,
               [(1, 0.62), (2, 0.10)], env)

    # sub(器の底): root 1声、中央、ゆっくり
    add_wt(t_chord, ch['sub'], dur_chord + 0.3, 0.34, 0.5, 0.5,
           [(1, 1.0), (2, 0.06)], env_ar(0.15, dur_chord + 0.3, 0.28))

    # arp(器/紫): 16分。cold(倍音そこそこ)・短いプラック・左右に微振り
    steps = int(round(dur_chord / (spb / 4)))   # 16分の数 = 3小節×16 = 48
    for st in range(steps):
        t = t_chord + st * (spb / 4)
        f = ch['arp'][ARP_PAT[st % 4]]
        if st % 2 == 0: gl, gr = 0.64, 0.40
        else:          gl, gr = 0.40, 0.64
        add_wt(t, f, 0.42, 0.115, gl, gr,
               [(1, 0.72), (2, 0.20), (3, 0.07)], env_pluck(0.004, 0.14))

# ── kick(微・拍1と3) & tick(微・裏8分) ────────────────────────────
n_bars = int(round(TOTAL_S / bar))
for b in range(n_bars):
    tb = b * bar
    # kick: 拍0と2、ピッチドロップ 66→44Hz
    for beat in (0, 2):
        tk = tb + beat * spb
        s0 = int(tk * SR); ns = int(0.22 * SR)
        ph = 0.0
        for i in range(ns):
            idx = s0 + i
            if idx >= N: break
            tt = i / SR
            fk = 44.0 + (66.0 - 44.0) * math.exp(-tt / 0.045)
            ph += fk * TAB / SR
            e = math.exp(-tt / 0.11)
            click = 0.5 * math.exp(-tt / 0.004) * SINE[int(ph * 30) & (TAB - 1)]
            v = 0.46 * e * (SINE[int(ph) & (TAB - 1)] + click)
            L[idx] += v * 0.5; R[idx] += v * 0.5
    # tick: 裏8分(各拍の+0.5)、フィルタ無しノイズの短バースト
    for beat in range(4):
        tt0 = tb + beat * spb + spb * 0.5
        s0 = int(tt0 * SR); ns = int(0.018 * SR)
        gl, gr = (0.66, 0.34) if beat % 2 == 0 else (0.34, 0.66)
        for i in range(ns):
            idx = s0 + i
            if idx >= N: break
            e = math.exp(-(i / SR) / 0.004)
            v = 0.05 * e * random.uniform(-1, 1)
            L[idx] += v * gl; R[idx] += v * gr

# ── マスター: 1極ローパスで warm 化 → ピーク正規化 → 端フェード ──────
def lowpass(buf, a):
    y = 0.0
    for i in range(N):
        y += a * (buf[i] - y)
        buf[i] = y
lowpass(L, 0.42); lowpass(R, 0.42)

peak = max(1e-9, max(abs(L[i]) for i in range(N)), max(abs(R[i]) for i in range(N)))
g = (10 ** (-3.0 / 20)) / peak     # peak を -3 dBFS へ
fade = int(0.012 * SR)
frames = bytearray()
for i in range(N):
    fenv = 1.0
    if i < fade: fenv = i / fade
    elif i > N - fade: fenv = max(0.0, (N - i) / fade)
    for buf in (L, R):
        s = max(-1.0, min(1.0, buf[i] * g * fenv))
        frames += struct.pack('<h', int(s * 32767))

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bgm-bedA-ref-30s.wav')
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(bytes(frames))
print('wrote', out)
