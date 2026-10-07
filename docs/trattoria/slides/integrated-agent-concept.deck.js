const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.layout = "LAYOUT_WIDE"; // 13.3 x 7.5
p.author = "KofPro";
p.title = "3業態統合 経営AIエージェント構想";

// ---- palette ----
const INK   = "26211D"; // deep espresso (dark bg)
const INK2  = "35302A"; // dark surface / card on dark
const INK3  = "413A33"; // lighter dark surface
const PAPER = "FBFAF8"; // near-white content bg (barely warm)
const CARD  = "FFFFFF";
const CARD2 = "F1ECE4"; // subtle tinted card on light
const TDARK = "2A2521"; // text on light
const TLITE = "F5EFE6"; // text on dark
const MUT_L = "6E655B"; // muted on light
const MUT_D = "B9AE9E"; // muted on dark
const AMBER = "C1841C"; // accent for text/lines on light
const AMBER2= "E0A73E"; // brighter amber on dark
const TRAT  = "BC5A3C"; // trattoria - terracotta
const CAKE  = "B76E85"; // patisserie - rose
const BAKE  = "7C9A54"; // bakery+deli - olive/green
const GOOD  = "5E8C5A";

const SANS = "Yu Gothic";
const MINCHO = "Yu Mincho";

const biz = [
  { name: "Baker's Dozen", jp: "トラットリア", c: TRAT },
  { name: "Baton",         jp: "ケーキ屋",     c: CAKE },
  { name: "新店舗",         jp: "ベーカリー&デリ", c: BAKE },
];

function footer(s, n, dark) {
  s.addText("3業態統合 経営AIエージェント構想", {
    isTextBox: true, x: 0.5, y: 7.05, w: 8, h: 0.3, align: "left",
    fontFace: SANS, fontSize: 9, color: dark ? MUT_D : MUT_L, margin: 0,
  });
  s.addText(String(n), {
    isTextBox: true, x: 12.3, y: 7.05, w: 0.5, h: 0.3, align: "right",
    fontFace: SANS, fontSize: 9, color: dark ? MUT_D : MUT_L, margin: 0,
  });
}
// three-dot business motif
function motif(s, x, y, r) {
  biz.forEach((b, i) => {
    s.addShape(p.ShapeType.ellipse, { x: x + i * (r * 1.5), y: y, w: r, h: r, fill: { color: b.c } });
  });
}

// =================================================================
// Slide 1 — Title (dark)
// =================================================================
let s = p.addSlide();
s.background = { color: INK };
motif(s, 0.9, 1.5, 0.34);
s.addText("OWNER MEETING ／ 2026.09.14", {
  isTextBox: true, x: 0.9, y: 2.15, w: 9, h: 0.4, fontFace: SANS, fontSize: 12,
  color: AMBER2, charSpacing: 3, margin: 0,
});
s.addText("3業態を、ひとつの頭脳で。", {
  isTextBox: true, x: 0.85, y: 2.55, w: 11.5, h: 1.4, fontFace: MINCHO, fontSize: 52,
  bold: true, color: TLITE, margin: 0,
});
s.addText("トラットリア・ケーキ屋・新店舗を統合管理する経営AIエージェント構想", {
  isTextBox: true, x: 0.9, y: 3.95, w: 11, h: 0.6, fontFace: SANS, fontSize: 20,
  color: MUT_D, margin: 0,
});
// business chips row
biz.forEach((b, i) => {
  const bx = 0.9 + i * 3.05;
  s.addShape(p.ShapeType.roundRect, { x: bx, y: 5.15, w: 2.8, h: 1.0, rectRadius: 0.1, fill: { color: INK2 }, line: { color: b.c, width: 1.5 } });
  s.addShape(p.ShapeType.ellipse, { x: bx + 0.25, y: 5.5, w: 0.3, h: 0.3, fill: { color: b.c } });
  s.addText([
    { text: b.name + "\n", options: { fontSize: 15, bold: true, color: TLITE, fontFace: SANS } },
    { text: b.jp, options: { fontSize: 11, color: MUT_D, fontFace: SANS } },
  ], { isTextBox: true, x: bx + 0.62, y: 5.28, w: 2.05, h: 0.75, margin: 0, valign: "middle", lineSpacingMultiple: 1.0 });
});
s.addText("KofPro 基盤の拡張構想 ／ オーナー会議用ドラフト", {
  isTextBox: true, x: 0.9, y: 6.45, w: 10, h: 0.35, fontFace: SANS, fontSize: 11, color: MUT_D, italic: true, margin: 0,
});

// =================================================================
// Slide 2 — 現状と課題 (light)
// =================================================================
s = p.addSlide();
s.background = { color: PAPER };
s.addText("いま、3つの店が「別々に」回っている", {
  isTextBox: true, x: 0.5, y: 0.45, w: 12.3, h: 0.7, fontFace: SANS, fontSize: 32, bold: true, color: TDARK, margin: 0,
});
s.addText("それぞれ独立して管理され、データも人も在庫もつながっていない。", {
  isTextBox: true, x: 0.5, y: 1.15, w: 12.3, h: 0.4, fontFace: SANS, fontSize: 15, color: MUT_L, margin: 0,
});
const pains = [
  ["売上・数字は店ごとにレジ締め", "手作業の転記。全体像が月末まで見えない"],
  ["在庫・仕入れは店ごとに発注", "食材やパンの融通が効かず、廃棄も各店で発生"],
  ["シフトも店ごとに勘で作成", "人手の余剰・不足が店をまたいで調整できない"],
];
biz.forEach((b, i) => {
  const bx = 0.5 + i * 4.13;
  s.addShape(p.ShapeType.roundRect, { x: bx, y: 1.85, w: 3.9, h: 3.5, rectRadius: 0.08, fill: { color: CARD }, line: { color: "E5DFD5", width: 1 }, shadow: { type: "outer", color: "C9C0B2", blur: 6, offset: 2, angle: 90, opacity: 0.5 } });
  s.addShape(p.ShapeType.ellipse, { x: bx + 0.3, y: 2.15, w: 0.55, h: 0.55, fill: { color: b.c } });
  s.addText(b.jp, { isTextBox: true, x: bx + 0.3, y: 2.75, w: 3.3, h: 0.3, fontFace: SANS, fontSize: 11, color: b.c, bold: true, margin: 0 });
  s.addText(b.name, { isTextBox: true, x: bx + 0.3, y: 3.0, w: 3.3, h: 0.5, fontFace: SANS, fontSize: 20, bold: true, color: TDARK, margin: 0 });
  s.addText([
    { text: pains[i][0] + "\n", options: { fontSize: 13, bold: true, color: TDARK, fontFace: SANS, breakLine: true } },
    { text: pains[i][1], options: { fontSize: 12, color: MUT_L, fontFace: SANS } },
  ], { isTextBox: true, x: bx + 0.3, y: 3.65, w: 3.3, h: 1.5, margin: 0, valign: "top", lineSpacingMultiple: 1.1 });
});
s.addShape(p.ShapeType.roundRect, { x: 0.5, y: 5.65, w: 12.3, h: 1.05, rectRadius: 0.06, fill: { color: "F3E7D4" } });
s.addText([
  { text: "共通する根っこの課題　", options: { fontSize: 14, bold: true, color: AMBER, fontFace: SANS } },
  { text: "データの分断 ／ 属人化 ／ 手作業の多さ ／ 店をまたいだシナジーが未活用", options: { fontSize: 14, color: TDARK, fontFace: SANS } },
], { isTextBox: true, x: 0.85, y: 5.65, w: 11.6, h: 1.05, margin: 0, valign: "middle" });
footer(s, 2, false);

// =================================================================
// Slide 3 — 全体像 hub & spoke (dark)
// =================================================================
s = p.addSlide();
s.background = { color: INK };
s.addText("構想の全体像 ── ひとつの頭脳が、3店を束ねる", {
  isTextBox: true, x: 0.5, y: 0.45, w: 12.3, h: 0.7, fontFace: SANS, fontSize: 30, bold: true, color: TLITE, margin: 0,
});
// central hub
const hubX = 5.15, hubY = 2.9, hubW = 3.0, hubH = 1.7;
// spokes (lines drawn first, under nodes)
const nodeCenters = [ {x:2.0,y:1.75}, {x:11.0,y:1.75}, {x:6.65,y:6.15} ];
const hubCx = hubX + hubW/2, hubCy = hubY + hubH/2;
nodeCenters.forEach((nc) => {
  s.addShape(p.ShapeType.line, { x: hubCx, y: hubCy, w: nc.x - hubCx, h: nc.y - hubCy, line: { color: "5A5148", width: 1.5, dashType: "dash" } });
});
// hub
s.addShape(p.ShapeType.roundRect, { x: hubX, y: hubY, w: hubW, h: hubH, rectRadius: 0.1, fill: { color: AMBER }, line: { color: AMBER2, width: 1 }, shadow:{type:"outer",color:"140F0B",blur:10,offset:3,angle:90,opacity:0.55} });
s.addText([
  { text: "統合AIエージェント\n", options: { fontSize: 19, bold: true, color: "241A08", fontFace: SANS, breakLine: true } },
  { text: "KofPro 基盤", options: { fontSize: 12, color: "5A430F", fontFace: SANS } },
], { isTextBox: true, x: hubX, y: hubY, w: hubW, h: hubH, align: "center", valign: "middle", margin: 0, lineSpacingMultiple: 1.1 });
// nodes
const nodeInfo = [
  { b: biz[0], nx: 0.75, ny: 1.1 },
  { b: biz[1], nx: 9.75, ny: 1.1 },
  { b: biz[2], nx: 5.4,  ny: 5.5 },
];
nodeInfo.forEach((n) => {
  s.addShape(p.ShapeType.roundRect, { x: n.nx, y: n.ny, w: 2.5, h: 1.3, rectRadius: 0.1, fill: { color: INK2 }, line: { color: n.b.c, width: 2 } });
  s.addShape(p.ShapeType.ellipse, { x: n.nx + 0.22, y: n.ny + 0.28, w: 0.32, h: 0.32, fill: { color: n.b.c } });
  s.addText([
    { text: n.b.name + "\n", options: { fontSize: 15, bold: true, color: TLITE, fontFace: SANS, breakLine: true } },
    { text: n.b.jp, options: { fontSize: 11, color: MUT_D, fontFace: SANS } },
  ], { isTextBox: true, x: n.nx + 0.62, y: n.ny + 0.2, w: 1.75, h: 0.9, margin: 0, valign: "middle", lineSpacingMultiple: 1.0 });
});
// data flow caption
s.addText("売上・在庫・人・顧客の4データを1か所に集約し、店をまたいで最適化する", {
  isTextBox: true, x: 0.5, y: 6.55, w: 12.3, h: 0.4, fontFace: SANS, fontSize: 14, color: AMBER2, align: "center", margin: 0,
});
footer(s, 3, true);

// =================================================================
// Slide 4 — 統合の価値 / シナジー (light)
// =================================================================
s = p.addSlide();
s.background = { color: PAPER };
s.addText("統合して初めて生まれる価値 ── シナジー", {
  isTextBox: true, x: 0.5, y: 0.45, w: 12.3, h: 0.7, fontFace: SANS, fontSize: 30, bold: true, color: TDARK, margin: 0,
});
s.addText("3店を1つの頭脳でつなぐと、単体では出せない循環が回り始める。", {
  isTextBox: true, x: 0.5, y: 1.15, w: 12.3, h: 0.4, fontFace: SANS, fontSize: 15, color: MUT_L, margin: 0,
});
const syn = [
  ["食材・在庫の融通", "余ったパンは総菜やトラットリアへ、生地や焼き菓子は店をまたいで活用。廃棄(食材ロス)を全体で最小化。"],
  ["クロスセル", "ケーキ×ディナー、パン×総菜のセット販売。1人のお客様の来店単価と回数を、店をまたいで引き上げる。"],
  ["需要の相互補完", "雨で弱い店を、天候に強い店(焼き菓子・総菜・デリバリー)が支える。売上の谷を全体でならす。"],
  ["共通の顧客基盤", "3店共通の会員(ダズンクラブ)。どの店に来ても記録が貯まり、次の一手を打てる。"],
];
syn.forEach((item, i) => {
  const col = i % 2, row = Math.floor(i / 2);
  const bx = 0.5 + col * 6.25, by = 1.9 + row * 2.35;
  s.addShape(p.ShapeType.roundRect, { x: bx, y: by, w: 6.0, h: 2.1, rectRadius: 0.08, fill: { color: CARD }, line: { color: "E5DFD5", width: 1 }, shadow: { type: "outer", color: "C9C0B2", blur: 6, offset: 2, angle: 90, opacity: 0.45 } });
  s.addShape(p.ShapeType.ellipse, { x: bx + 0.35, y: by + 0.35, w: 0.7, h: 0.7, fill: { color: AMBER } });
  s.addText(String(i + 1), { isTextBox: true, x: bx + 0.35, y: by + 0.35, w: 0.7, h: 0.7, align: "center", valign: "middle", fontFace: MINCHO, fontSize: 24, bold: true, color: "FFFFFF", margin: 0 });
  s.addText(item[0], { isTextBox: true, x: bx + 1.3, y: by + 0.32, w: 4.4, h: 0.5, fontFace: SANS, fontSize: 18, bold: true, color: TDARK, margin: 0 });
  s.addText(item[1], { isTextBox: true, x: bx + 1.3, y: by + 0.85, w: 4.45, h: 1.1, fontFace: SANS, fontSize: 12.5, color: MUT_L, margin: 0, lineSpacingMultiple: 1.15 });
});
footer(s, 4, false);

// =================================================================
// Slides 5-8 — basic features (light, consistent template)
// =================================================================
const features = [
  {
    no: "01", title: "数値の統合ダッシュボード", accent: AMBER,
    lead: "3店の売上・客数・原価を自動で集約し、毎日ひとつの画面で見る。",
    rows: [
      ["レジ締めの自動化", "会計と同時に集計。手作業の転記をなくす(既製ツールが土台)"],
      ["店横断の売上比較", "時間帯・曜日・天候別に3店を並べて把握。強弱がすぐ分かる"],
      ["原価率・粗利の可視化", "つけ払い・関係者売掛・後日訂正も台帳で管理し「本当の利益」を掴む"],
    ],
  },
  {
    no: "02", title: "在庫・仕入れ・食材の一元管理", accent: BAKE,
    lead: "3店の在庫を1つの台帳に。発注を最適化し、廃棄を全体で減らす。",
    rows: [
      ["共通在庫の見える化", "冷蔵・冷凍を含む在庫を店横断で把握。二重発注・欠品を防ぐ"],
      ["店間の食材融通", "余剰を別の店へ回す提案。パン→総菜→トラットリアの循環を回す"],
      ["発注点アラート", "売上実績から必要量を予測し、発注のタイミングを自動で通知"],
    ],
  },
  {
    no: "03", title: "人・シフトの最適化", accent: TRAT,
    lead: "売上に見合った人員を、店をまたいで配置する。",
    rows: [
      ["売上連動のシフト提案", "実績から「その日・その店に何人要るか」を提案(既製シフトと連携)"],
      ["店間の人員融通", "暇な店から忙しい店へ。3店合算で人件費のムダを抑える"],
      ["法令・社保の自動チェック", "休憩・連続勤務・扶養の壁を提案時に確認(最終判断は人)"],
    ],
  },
  {
    no: "04", title: "顧客・販促の統合", accent: CAKE,
    lead: "3店共通の顧客基盤で、来店単価と再来店を引き上げる。",
    rows: [
      ["共通会員(ダズンクラブ)", "どの店の利用も1つの記録に。回数券・月額会員でリピートを固定化"],
      ["販促チャネルの一元管理", "LINE・Instagram・デリバリーを横断。天候連動の配信も自動化"],
      ["クロスセルの提案", "ケーキ×ディナー、パン×総菜など、店をまたぐおすすめを自動生成"],
    ],
  },
];
features.forEach((f, fi) => {
  s = p.addSlide();
  s.background = { color: PAPER };
  s.addText([
    { text: "基本機能 ", options: { fontSize: 14, color: MUT_L, fontFace: SANS } },
    { text: f.no, options: { fontSize: 14, color: f.accent, bold: true, fontFace: SANS } },
  ], { isTextBox: true, x: 0.5, y: 0.42, w: 6, h: 0.35, margin: 0 });
  s.addText(f.title, { isTextBox: true, x: 0.5, y: 0.72, w: 12.3, h: 0.7, fontFace: SANS, fontSize: 32, bold: true, color: TDARK, margin: 0 });
  s.addText(f.lead, { isTextBox: true, x: 0.5, y: 1.5, w: 12.3, h: 0.45, fontFace: SANS, fontSize: 16, color: AMBER, margin: 0 });
  // left: three feature rows
  f.rows.forEach((r, ri) => {
    const ry = 2.25 + ri * 1.35;
    s.addShape(p.ShapeType.roundRect, { x: 0.5, y: ry, w: 7.7, h: 1.15, rectRadius: 0.06, fill: { color: CARD }, line: { color: "E5DFD5", width: 1 } });
    s.addShape(p.ShapeType.ellipse, { x: 0.8, y: ry + 0.33, w: 0.5, h: 0.5, fill: { color: f.accent } });
    s.addText(String(ri + 1), { isTextBox: true, x: 0.8, y: ry + 0.33, w: 0.5, h: 0.5, align: "center", valign: "middle", fontFace: SANS, fontSize: 16, bold: true, color: "FFFFFF", margin: 0 });
    s.addText([
      { text: r[0] + "\n", options: { fontSize: 15, bold: true, color: TDARK, fontFace: SANS, breakLine: true } },
      { text: r[1], options: { fontSize: 12, color: MUT_L, fontFace: SANS } },
    ], { isTextBox: true, x: 1.55, y: ry + 0.15, w: 6.5, h: 0.9, margin: 0, valign: "middle", lineSpacingMultiple: 1.1 });
  });
  // right: which stores benefit
  s.addShape(p.ShapeType.roundRect, { x: 8.45, y: 2.25, w: 4.35, h: 4.1, rectRadius: 0.08, fill: { color: INK }, });
  s.addText("対象の3業態", { isTextBox: true, x: 8.75, y: 2.5, w: 3.8, h: 0.4, fontFace: SANS, fontSize: 13, bold: true, color: AMBER2, margin: 0 });
  biz.forEach((b, bi) => {
    const yy = 3.1 + bi * 1.0;
    s.addShape(p.ShapeType.ellipse, { x: 8.8, y: yy, w: 0.42, h: 0.42, fill: { color: b.c } });
    s.addText([
      { text: b.name + "  ", options: { fontSize: 14, bold: true, color: TLITE, fontFace: SANS } },
      { text: b.jp, options: { fontSize: 11, color: MUT_D, fontFace: SANS } },
    ], { isTextBox: true, x: 9.4, y: yy - 0.05, w: 3.3, h: 0.5, margin: 0, valign: "middle" });
  });
  s.addText("すべての店で同じ仕組みが働く", { isTextBox: true, x: 8.75, y: 5.95, w: 3.9, h: 0.3, fontFace: SANS, fontSize: 10.5, italic: true, color: MUT_D, margin: 0 });
  footer(s, 5 + fi, false);
});

// =================================================================
// Slide 9 — Roadmap / 拡張性 (dark)
// =================================================================
s = p.addSlide();
s.background = { color: INK };
s.addText("将来的な拡張性 ── 小さく始め、賢くしていく", {
  isTextBox: true, x: 0.5, y: 0.45, w: 12.3, h: 0.7, fontFace: SANS, fontSize: 30, bold: true, color: TLITE, margin: 0,
});
s.addText("いきなり全部作らない。効果を確かめながら段階的に育てる。", {
  isTextBox: true, x: 0.5, y: 1.15, w: 12.3, h: 0.4, fontFace: SANS, fontSize: 15, color: MUT_D, margin: 0,
});
const phases = [
  ["PHASE 1", "数値の見える化", "3店の売上・原価を集約。まず「今どうなっているか」を1画面に。", GOOD],
  ["PHASE 2", "在庫・シフトの最適化", "食材の融通・発注最適化・売上連動シフトで、日々のムダを削る。", AMBER2],
  ["PHASE 3", "顧客・販促の統合", "共通会員とクロスセル。来店単価と再来店を店横断で伸ばす。", CAKE],
  ["PHASE 4", "自律エージェント化", "需要予測・自動発注・シフト交渉まで、AIが先回りして提案・実行。", TRAT],
];
const timelineY = 2.7;
s.addShape(p.ShapeType.line, { x: 0.9, y: timelineY, w: 11.5, h: 0, line: { color: "5A5148", width: 2 } });
phases.forEach((ph, i) => {
  const cx = 1.2 + i * 3.05;
  s.addShape(p.ShapeType.ellipse, { x: cx - 0.16, y: timelineY - 0.16, w: 0.32, h: 0.32, fill: { color: ph[3] }, line: { color: INK, width: 2 } });
  s.addShape(p.ShapeType.roundRect, { x: cx - 0.1, y: timelineY + 0.45, w: 2.75, h: 3.0, rectRadius: 0.08, fill: { color: INK2 }, line: { color: ph[3], width: 1.5 } });
  s.addText(ph[0], { isTextBox: true, x: cx + 0.1, y: timelineY + 0.65, w: 2.4, h: 0.35, fontFace: SANS, fontSize: 12, bold: true, color: ph[3], charSpacing: 2, margin: 0 });
  s.addText(ph[1], { isTextBox: true, x: cx + 0.1, y: timelineY + 1.05, w: 2.4, h: 0.9, fontFace: SANS, fontSize: 17, bold: true, color: TLITE, margin: 0, lineSpacingMultiple: 1.05 });
  s.addText(ph[2], { isTextBox: true, x: cx + 0.1, y: timelineY + 1.95, w: 2.45, h: 1.4, fontFace: SANS, fontSize: 11.5, color: MUT_D, margin: 0, lineSpacingMultiple: 1.15 });
});
s.addText([
  { text: "その先へ　", options: { fontSize: 13, bold: true, color: AMBER2, fontFace: SANS } },
  { text: "EC・オンライン通販 ／ ふるさと納税返礼品 ／ 多店舗・FC展開　── 同じ基盤に積み増すだけで広げられる。", options: { fontSize: 13, color: MUT_D, fontFace: SANS } },
], { isTextBox: true, x: 0.5, y: 6.55, w: 12.3, h: 0.4, margin: 0, align: "center" });
footer(s, 9, true);

// =================================================================
// Slide 10 — 導入アプローチ & 正直な前提 (light)
// =================================================================
s = p.addSlide();
s.background = { color: PAPER };
s.addText("導入アプローチと、正直な前提", {
  isTextBox: true, x: 0.5, y: 0.45, w: 12.3, h: 0.7, fontFace: SANS, fontSize: 30, bold: true, color: TDARK, margin: 0,
});
// left: approach (good)
s.addShape(p.ShapeType.roundRect, { x: 0.5, y: 1.5, w: 6.0, h: 5.0, rectRadius: 0.08, fill: { color: CARD }, line: { color: "E5DFD5", width: 1 } });
s.addText("進め方", { isTextBox: true, x: 0.85, y: 1.75, w: 5.3, h: 0.45, fontFace: SANS, fontSize: 18, bold: true, color: GOOD, margin: 0 });
const appr = [
  ["既製ツールを土台に", "Airレジ/メイト/シフト等の無料ツールで大部分を賄い、足りない所だけ自作する"],
  ["小さく始める", "Phase 1(数値の見える化)から。効果を見て次へ進む"],
  ["人の承認を挟む", "発注・シフト確定はAIが提案し、最終判断はオーナー・店長が行う"],
  ["1つの基盤に積む", "KofProを核に機能を追加。作り直さず育てる"],
];
appr.forEach((a, i) => {
  const ay = 2.3 + i * 1.02;
  s.addShape(p.ShapeType.ellipse, { x: 0.85, y: ay + 0.05, w: 0.4, h: 0.4, fill: { color: GOOD } });
  s.addText("✓", { isTextBox: true, x: 0.85, y: ay + 0.05, w: 0.4, h: 0.4, align: "center", valign: "middle", fontFace: SANS, fontSize: 15, bold: true, color: "FFFFFF", margin: 0 });
  s.addText([
    { text: a[0] + "\n", options: { fontSize: 14, bold: true, color: TDARK, fontFace: SANS, breakLine: true } },
    { text: a[1], options: { fontSize: 11.5, color: MUT_L, fontFace: SANS } },
  ], { isTextBox: true, x: 1.4, y: ay - 0.05, w: 4.9, h: 0.95, margin: 0, valign: "middle", lineSpacingMultiple: 1.1 });
});
// right: honest caveats
s.addShape(p.ShapeType.roundRect, { x: 6.8, y: 1.5, w: 6.0, h: 5.0, rectRadius: 0.08, fill: { color: "F3E7D4" } });
s.addText("正直にお伝えする前提", { isTextBox: true, x: 7.15, y: 1.75, w: 5.3, h: 0.45, fontFace: SANS, fontSize: 18, bold: true, color: AMBER, margin: 0 });
const cav = [
  ["完全な自動化ではない", "一部の既製ツールは外部連携の窓口が無く、データ受け渡しはCSV等の半自動になる"],
  ["事実の入力は人が行う", "つけ払い・訂正などの記録入力は人手。計算・集計・提案は自動"],
  ["初期の開発・設定工数", "自作部分の工数と、一部有料ツールの費用は別途見積りが必要"],
  ["効果はデータが育ってから", "売上・在庫の実データが貯まるほど予測と提案の精度が上がる"],
];
cav.forEach((c, i) => {
  const cy = 2.3 + i * 1.02;
  s.addShape(p.ShapeType.ellipse, { x: 7.15, y: cy + 0.05, w: 0.4, h: 0.4, fill: { color: AMBER } });
  s.addText("!", { isTextBox: true, x: 7.15, y: cy + 0.05, w: 0.4, h: 0.4, align: "center", valign: "middle", fontFace: SANS, fontSize: 15, bold: true, color: "FFFFFF", margin: 0 });
  s.addText([
    { text: c[0] + "\n", options: { fontSize: 14, bold: true, color: TDARK, fontFace: SANS, breakLine: true } },
    { text: c[1], options: { fontSize: 11.5, color: MUT_L, fontFace: SANS } },
  ], { isTextBox: true, x: 7.7, y: cy - 0.05, w: 4.9, h: 0.95, margin: 0, valign: "middle", lineSpacingMultiple: 1.1 });
});
footer(s, 10, false);

// =================================================================
// Slide 11 — まとめ・意思決定 (dark closing)
// =================================================================
s = p.addSlide();
s.background = { color: INK };
motif(s, 0.9, 0.85, 0.3);
s.addText("本日ご判断いただきたいこと", {
  isTextBox: true, x: 0.85, y: 1.35, w: 12, h: 0.9, fontFace: MINCHO, fontSize: 38, bold: true, color: TLITE, margin: 0,
});
const asks = [
  ["方向性の承認", "「3店を1つの頭脳で統合管理する」という構想の方向性にGoを出すか"],
  ["Phase 1 の着手", "まずは数値の見える化(投資小・リスク小)から始めることの承認"],
  ["体制と予算の検討", "自作部分の工数・費用の見積りを次回までに用意することの承認"],
];
asks.forEach((a, i) => {
  const ay = 2.5 + i * 1.25;
  s.addShape(p.ShapeType.roundRect, { x: 0.9, y: ay, w: 11.5, h: 1.05, rectRadius: 0.08, fill: { color: INK2 } });
  s.addShape(p.ShapeType.ellipse, { x: 1.2, y: ay + 0.27, w: 0.5, h: 0.5, fill: { color: AMBER } });
  s.addText(String(i + 1), { isTextBox: true, x: 1.2, y: ay + 0.27, w: 0.5, h: 0.5, align: "center", valign: "middle", fontFace: MINCHO, fontSize: 20, bold: true, color: "241A08", margin: 0 });
  s.addText([
    { text: a[0] + "　", options: { fontSize: 18, bold: true, color: TLITE, fontFace: SANS } },
    { text: a[1], options: { fontSize: 13, color: MUT_D, fontFace: SANS } },
  ], { isTextBox: true, x: 2.0, y: ay, w: 10.2, h: 1.05, margin: 0, valign: "middle", lineSpacingMultiple: 1.1 });
});
s.addText("小さく始めて、確かめながら、賢く育てる。", {
  isTextBox: true, x: 0.9, y: 6.5, w: 11.5, h: 0.5, fontFace: MINCHO, fontSize: 18, italic: true, color: AMBER2, margin: 0,
});

p.writeFile({ fileName: "/tmp/claude-0/-home-user-kofpro/918cf382-3066-50a1-b924-aefbc13be275/scratchpad/integrated-agent.pptx" }).then((f) => console.log("wrote", f));
