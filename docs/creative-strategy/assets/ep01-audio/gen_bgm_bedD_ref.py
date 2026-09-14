#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EP01 BGM Bed D「夢」参照トーン (30s) — 方向確認用スケッチ。
BGM-DIRECTION.md §2 Bed D(dream-bookend / ①夢OP・⑧夢回帰・⑨まとめ)の音を耳で確認するため。
  72 BPM / C major(暖・淡リディア) / Cmaj7-Am7-Fmaj7-G-(C) / ドラム無し・floaty。
  主役=leitmotif「コフのテーマ」= G4 C5 D5 E5 C5 (sol-do-re-mi-do:育つ相棒の上昇→home着地)。
  オルゴール/セレスタ音(倍音+速い減衰)で提示、warmパッド+subの上に。同一旋律で和声だけ移ろう=主題の照り返し。
標準ライブラリのみ・正弦波テーブル合成・固定シード。出力: bgm-bedD-ref-30s.wav (44.1k/16bit/stereo)
"""
import math, wave, array, struct, random, os
random.seed(7)
SR = 44100
BPM = 72.0
spb = 60.0 / BPM          # 0.8333
bar = 4 * spb             # 3.3333
TOTAL_S = 30.0
N = int(TOTAL_S * SR)
L = array.array('d', bytes(8 * N)); R = array.array('d', bytes(8 * N))
TAB = 4096
SINE = [math.sin(2 * math.pi * i / TAB) for i in range(TAB)]

def add_wt(t0, freq, dur, amp, gl, gr, partials, env):
    s0 = int(t0 * SR); ns = int(dur * SR)
    if s0 >= N: return
    ph = [0.0] * len(partials)
    inc = [freq * m * TAB / SR for (m, _a) in partials]
    for i in range(ns):
        idx = s0 + i
        if idx >= N: break
        e = env(i / SR)
        if e <= 0.0:
            if i / SR > 0.02: break
            else: continue
        s = 0.0
        for k in range(len(partials)):
            s += partials[k][1] * SINE[int(ph[k]) & (TAB - 1)]
            ph[k] += inc[k]
        v = amp * e * s
        L[idx] += v * gl; R[idx] += v * gr

def env_ar(attack, dur, release):
    def f(t):
        if t < attack: return t / attack
        if t > dur - release: return max(0.0, (dur - t) / release)
        return 1.0
    return f

def env_bell(attack, tau):
    def f(t):
        if t < attack: return t / attack
        return math.exp(-(t - attack) / tau)
    return f

def env_swell(dur, peak_frac=0.38):
    # 各コードを ふわっと膨らませて引く(呼吸)。両端0・途中1のなめらか山。
    pk = dur * peak_frac
    def f(t):
        x = (t / pk) if t < pk else max(0.0, (dur - t) / (dur - pk))
        return 0.5 - 0.5 * math.cos(math.pi * min(1.0, x))
    return f

# ── コード進行(2小節ずつ + 最後にC 1小節) ──────────────────────────
# pad は octave3-4 の warm ボイシング。sub は root。
BLOCKS = [
    (0, 2, dict(pad=[261.63, 329.63, 392.00, 493.88], sub=65.41)),   # Cmaj7 (C E G B)
    (2, 2, dict(pad=[220.00, 261.63, 329.63, 392.00], sub=110.00)),  # Am7  (A C E G)
    (4, 2, dict(pad=[174.61, 220.00, 261.63, 329.63], sub=87.31)),   # Fmaj7(F A C E)
    (6, 2, dict(pad=[196.00, 246.94, 293.66, 440.00], sub=98.00)),   # G add9(G B D A)
    (8, 1, dict(pad=[261.63, 329.63, 392.00, 493.88], sub=65.41)),   # C (着地)
]
for (sb, nb, ch) in BLOCKS:
    t0 = sb * bar; dur = nb * bar
    # pad: 各音を±デチューン2声で左右へ。warm(倍音少)。コードごとに swell=呼吸させる
    swell = env_swell(dur + 0.6)
    for pf in ch['pad']:
        add_wt(t0, pf * 0.9995, dur + 0.6, 0.030, 0.86, 0.30, [(1, 0.60), (2, 0.11), (3, 0.04)], swell)
        add_wt(t0, pf * 1.0005, dur + 0.6, 0.030, 0.30, 0.86, [(1, 0.60), (2, 0.11), (3, 0.04)], swell)
    # sub: root、ゆっくり(低域は安定させる)
    add_wt(t0, ch['sub'], dur + 0.4, 0.26, 0.5, 0.5, [(1, 1.0), (2, 0.05)], env_ar(0.25, dur + 0.4, 0.5))

# ── leitmotif「コフのテーマ」= G4 C5 D5 E5 C5 (sol-do-re-mi-do) ──────
# 同一旋律を bar0(C)/bar4(F)/bar8(C最終) で提示。セレスタ音(倍音+速い減衰)。
THEME = [392.00, 523.25, 587.33, 659.25, 523.25]     # G4 C5 D5 E5 C5
DUR   = [0.83,   0.83,   0.83,   1.55,   1.9]         # mi と終do を長めに響かせ
CEL_P = [(1, 0.58), (2, 0.30), (3, 0.13), (4.15, 0.06)]   # 鐘/セレスタ的
def play_theme(tstart, final=False):
    t = tstart
    notes = list(zip(THEME, DUR))
    if final:
        # 最終は home(C5)へ解決して長く残す
        notes = [(392.00,0.83),(523.25,0.83),(587.33,0.83),(659.25,1.4),(523.25,2.6)]
    for (f, d) in notes:
        add_wt(t, f, d + 1.4, 0.175, 0.56, 0.44, CEL_P, env_bell(0.003, 0.9))
        # echo(夢の空間): +0.42s・逆パン・小さく短く
        add_wt(t + 0.42, f, d + 1.0, 0.175 * 0.36, 0.42, 0.58, CEL_P, env_bell(0.003, 0.6))
        t += d

play_theme(0 * bar + 0.10)          # bar0 over C
play_theme(4 * bar + 0.10)          # bar4 over F (E5=maj7=最も夢っぽい照り)
play_theme(8 * bar + 0.10, final=True)   # bar8 over C: home 解決

# ── マスター: 軽いLP(鐘のきらめきは残す) → 正規化 → 端フェード ──────
def lowpass(buf, a):
    y = 0.0
    for i in range(N):
        y += a * (buf[i] - y); buf[i] = y
lowpass(L, 0.72); lowpass(R, 0.72)
peak = max(1e-9, max(abs(L[i]) for i in range(N)), max(abs(R[i]) for i in range(N)))
g = (10 ** (-3.0 / 20)) / peak
fade = int(0.02 * SR)
frames = bytearray()
for i in range(N):
    fe = 1.0
    if i < fade: fe = i / fade
    elif i > N - fade: fe = max(0.0, (N - i) / fade)
    for buf in (L, R):
        s = max(-1.0, min(1.0, buf[i] * g * fe))
        frames += struct.pack('<h', int(s * 32767))
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bgm-bedD-ref-30s.wav')
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(bytes(frames))
print('wrote', out)
