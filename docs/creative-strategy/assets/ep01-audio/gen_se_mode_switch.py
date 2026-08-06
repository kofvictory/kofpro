#!/usr/bin/env python3
# =============================================================================
# EP01 SE試作: ①ビートC「賢いモード」切替音
#   紫(ローカル/Ollama) → オレンジ(Claude) の "役者交代" を一音で。
#   台本: 「切り替えの瞬間にSE一音。少しグレードアップした印象のトーンへ」
#
# ★pure-python(標準ライブラリのみ)の加算合成。numpy不要=依存ゼロ。
# ★マスター = このコード(音の真実源)。派生 = *.wav / *.mp3。
# ★共通の狙い: 低→高への上昇 + 倍音が増える(=明るく/格上げ)で「グレードアップ」。
#   出力: se-mode-switch-A/B/C.wav  (44.1kHz / 16bit / stereo)
# =============================================================================
import wave, struct, math, os

SR  = 44100
OUT = os.path.dirname(os.path.abspath(__file__))

def add_voice(buf, freq, start, dur, amp, attack=0.004, decay=0.4,
              partials=((1, 1.0), (2, 0.35), (3, 0.12)), glide=1.0, vib=0.0):
    """加算合成の一声を buf に足し込む.
       glide = 終端/始端の周波数比(1.0=固定, 7.0=7倍まで上昇スイープ).
       vib   = ビブラート深さ(0で無効)."""
    s = int(SR * start); n = int(SR * dur)
    phases = [0.0] * len(partials)
    for i in range(n):
        idx = s + i
        if idx >= len(buf):
            break
        t = i / SR
        f = freq * (glide ** (t / dur))
        if vib:
            f *= (1.0 + vib * math.sin(2 * math.pi * 5.5 * t))
        val = 0.0
        for k, (mult, pa) in enumerate(partials):
            phases[k] += 2 * math.pi * f * mult / SR
            val += pa * math.sin(phases[k])
        e = (min(1.0, t / attack) if attack > 0 else 1.0) * math.exp(-t / decay)
        buf[idx] += amp * e * val

def write_wav(buf, name, target_dbfs=-1.2, haas_ms=7.0):
    """ピーク正規化(-1.2dBFS)して16bitステレオwav化(Haasで軽くステレオ化)."""
    n = len(buf)
    peak = max(1e-9, max(abs(x) for x in buf))
    g = (10 ** (target_dbfs / 20.0)) / peak
    haas = int(SR * haas_ms / 1000.0)
    path = os.path.join(OUT, name)
    with wave.open(path, 'w') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        fr = bytearray()
        for i in range(n):
            l = buf[i] * g
            r = (buf[i - haas] * g) if i - haas >= 0 else 0.0
            fr += struct.pack('<hh',
                              int(max(-1, min(1, l)) * 32767),
                              int(max(-1, min(1, r)) * 32767))
        w.writeframes(bytes(fr))
    rms = (sum(x * x for x in buf) / n) ** 0.5 * g
    print(f"{name}: dur={n/SR:.2f}s peak={20*math.log10(peak*g):.1f}dBFS "
          f"rms={20*math.log10(max(1e-9, rms)):.1f}dBFS")

# ---- 案A: 上昇チャイム(明るい/ポジティブ)  C5 → G5 → C6 -----------------------
A = [0.0] * int(SR * 1.25)
add_voice(A, 523.25, 0.000, 0.95, 0.50, decay=0.50)
add_voice(A, 783.99, 0.085, 0.95, 0.45, decay=0.50)
add_voice(A, 1046.5, 0.170, 1.05, 0.42, decay=0.58,
          partials=((1, 1.0), (2, 0.3), (3, 0.1), (4, 0.04)))
write_wav(A, "se-mode-switch-A.wav")

# ---- 案B: 完全5度シマー(洗練/据わり)  A4 + E5 + 高倍音の揺れ ------------------
B = [0.0] * int(SR * 1.35)
add_voice(B, 440.00, 0.00, 1.15, 0.45, decay=0.72, partials=((1, 1.0), (2, 0.28), (3, 0.08)))
add_voice(B, 659.25, 0.10, 1.15, 0.40, decay=0.72, partials=((1, 1.0), (2, 0.25), (3, 0.07)))
add_voice(B, 1318.5, 0.10, 1.20, 0.10, decay=0.95, vib=0.012, partials=((1, 1.0), (2, 0.2)))
write_wav(B, "se-mode-switch-B.wav")

# ---- 案C: テック・スイープ + 鈴(エンジニア感)  300→~2kHz 上昇 → chime --------
C = [0.0] * int(SR * 1.00)
add_voice(C, 300.0, 0.00, 0.50, 0.30, attack=0.008, decay=0.42, glide=7.0,
          partials=((1, 1.0), (2, 0.2)))
add_voice(C, 1318.5, 0.32, 0.62, 0.34, decay=0.34,
          partials=((1, 1.0), (2, 0.3), (3, 0.1)))
write_wav(C, "se-mode-switch-C.wav")

print("done.")
