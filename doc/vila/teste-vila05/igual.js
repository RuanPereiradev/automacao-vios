// grava a sequência de fillRect/fillStyle de N frames (com Date fixo) para comparar dois vila.html
const fs = require('fs'), crypto = require('crypto');
const html = JSON.parse(fs.readFileSync(process.argv[2], 'utf8').split('\n').find(l => l.startsWith('"<!DOCTYPE html>')));
const js = html.match(/<script type="text\/x-dc"[^>]*>([\s\S]*?)<\/script>/)[1];
const RealDate = Date; global.Date = class extends RealDate { constructor(...a) { super(...(a.length ? a : [2026, 10, 6, 10, 0, 0])); } static now() { return new RealDate(2026, 10, 6, 10, 0, 0).getTime(); } };
const h = crypto.createHash('sha1'); let n = 0;
const fake = () => new Proxy(function () {}, { get: (o, k) => k === Symbol.toPrimitive ? () => 0 : fake(), apply: () => fake(), set: () => true });
const ctx = new Proxy({}, { get: (o, k) => { if (k === 'fillRect') return (...a) => { n++; h.update(String(o.fillStyle) + a.join(',') + ';'); }; if (k in o) return o[k]; return () => fake(); }, set: (o, k, v) => { o[k] = v; return true; } });
global.document = { createElement: () => ({ getContext: () => ctx }), addEventListener() {}, removeEventListener() {}, hidden: false };
global.window = { addEventListener() {}, removeEventListener() {}, open() {} };
global.location = { pathname: process.argv[3] || '/', search: '' };
global.requestAnimationFrame = () => 0; global.cancelAnimationFrame = () => {}; global.fetch = async () => ({ ok: false });
global.setInterval = () => 0; global.clearInterval = () => {}; global.setTimeout = () => 0;
class DCLogic { constructor() { this.props = {}; } setState(u) { const p = typeof u === 'function' ? u(this.state) : u; if (p) this.state = { ...this.state, ...p }; } }
global.DCLogic = DCLogic; global.React = { createRef: () => ({ current: null }) };
const Component = eval(js + '\n;Component');
const comp = new Component(); comp.canvasRef = { current: { getContext: () => ctx } };
comp.componentDidMount();
for (let i = 0; i < 3000; i++) { comp.frame++; comp.update(); comp.draw(); if (i === 200) comp.femitMock(); }
if (process.argv[4]) { // servidor: cena nula e cena real com campos faltando
  comp.setState({ fsrv: { configurado: true, cena: null } }); comp.update(); console.log('servidor, sem relatório:', comp.v5.cena, comp.v5.real);
  comp.setState({ fsrv: { configurado: true, cena: { data: '2026-11-05', atrasadas: '7', graves: null, funcoes: ['prazos'] } } }); comp.update(); console.log('servidor, cena:', JSON.stringify(comp.v5.cena), comp.v5.real);
}
console.log(n, h.digest('hex'), comp.fa.x, comp.fa.y);
