// 見出しを「ことばのかたまり」に分ける（改行が ことばの途中に来ないように）。入力：文字列の配列(JSON)　出力：かたまりの配列の配列
const seg = new Intl.Segmenter('ja', { granularity: 'word' });
const AFTER = new Set(['は','が','を','に','へ','で','と','も','や','から','まで','より','たら','なら','ので','のに','けど','には','では','とは','でも','にも','って','、','。','・','？','！','）','」','｜','／']);
const NOSTART = /^[、。・？！）」』】〉》ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮー…‥：；のはがをにへでともやかねよ]/;
function chunks(t) {
  const s = [...seg.segment(t)].map(x => x.segment); const out = []; let cur = '';
  for (let i = 0; i < s.length; i++) {
    const p = s[i - 1], c = s[i];
    if (cur && AFTER.has(p) && !AFTER.has(c) && !NOSTART.test(c) && !/^\s*$/.test(c)) { out.push(cur); cur = ''; }
    cur += c;
  }
  if (cur) out.push(cur);
  // 短すぎるかたまり（2文字まで）は 次とくっつける。最後が短いときは 前とくっつける
  const m = [];
  for (const x of out) { if (m.length && [...m[m.length - 1].trim()].length <= 2 && !/[、。・？！]$/.test(m[m.length - 1])) m[m.length - 1] += x; else m.push(x); }
  if (m.length > 1 && [...m[m.length - 1].trim()].length <= 2) { const l = m.pop(); m[m.length - 1] += l; }
  // 長いかたまり（10文字以上）は「の」のあとでも分けられるようにする（前後3文字以上のとき）
  const r = [];
  for (const x of m) {
    if ([...x].length < 10) { r.push(x); continue; }
    const ss = [...seg.segment(x)].map(y => y.segment); let c = '';
    for (let i = 0; i < ss.length; i++) {
      c += ss[i];
      const rest = ss.slice(i + 1).join('');
      if (ss[i] === 'の' && [...c].length >= 3 && [...rest].length >= 3 && !NOSTART.test(ss[i + 1] || '') ) { r.push(c); c = ''; }
    }
    if (c) r.push(c);
  }
  return r;
}
let d = ''; process.stdin.on('data', x => d += x).on('end', () => process.stdout.write(JSON.stringify(JSON.parse(d).map(chunks))));
