// smoke test: roda o componente da vila em node com canvas falso
const fs = require('fs');
const html = JSON.parse(fs.readFileSync(process.argv[2], 'utf8').split('\n').find(l => l.startsWith('"<!DOCTYPE html>')));
const js = html.match(/<script type="text\/x-dc"[^>]*>([\s\S]*?)<\/script>/)[1];
const fake = () => new Proxy(function () {}, { get: (o, k) => k === Symbol.toPrimitive ? () => 0 : fake(), apply: () => fake(), set: () => true });
const ctxLog = []; let fillCount = 0;
const ctx = new Proxy({}, { get: (o, k) => { if (k === 'fillRect') return () => { fillCount++; }; if (k in o) return o[k]; return (...a) => fake(); }, set: (o, k, v) => { o[k] = v; return true; } });
global.document = { createElement: () => ({ getContext: () => ctx, width: 0, height: 0 }), addEventListener() {}, removeEventListener() {}, hidden: false };
global.window = { addEventListener() {}, removeEventListener() {}, open() {} };
global.location = { pathname: '/', search: process.argv[3] || '' };
global.requestAnimationFrame = () => 0; global.cancelAnimationFrame = () => {};
global.fetch = async () => ({ ok: false });
global.setInterval = () => 0; global.clearInterval = () => {};
class DCLogic { constructor() { this.props = {}; } setState(u) { const p = typeof u === 'function' ? u(this.state) : u; if (p) this.state = { ...this.state, ...p }; } }
global.DCLogic = DCLogic; global.React = { createRef: () => ({ current: null }) };
const Component = eval(js + '\n;Component');
const comp = new Component(); comp.canvasRef = { current: { getContext: () => ctx } };
comp.componentDidMount();
const humores = []; comp.v5Humor = r => humores.push(r);
const passo = n => { for (let i = 0; i < n; i++) { comp.frame++; comp.update(); comp.draw(); } };
passo(100);
console.log('v5', JSON.stringify({ ...comp.v5, params: comp.v5.params }));
console.log('erros de camada', JSON.stringify(comp.v5erros));
// plano: ir até a caixa de areia (coluna 4, linha 12) e cochilar
comp.v5.rotina = { ir: [4, 12], idle: 'cochilar', dir: 'left' };
passo(1500);
const F = comp.fa; console.log('Orelha', F.x / 16 - 80, F.y / 16, F.dir, JSON.stringify(F.idle), F.pose);
comp.v5.humor = { pose: 'jatem', balao: 'ok' }; passo(5); console.log('humor manda:', F.pose, F.bubble, F.x / 16 - 80, F.y / 16);
comp.v5.humor = null; passo(5); console.log('volta à rotina:', F.pose, F.bubble, JSON.stringify(F.idle));
comp.v5.rotina = { ir: [16, 5] }; passo(5); console.log('alvo bloqueado: fica', F.x / 16 - 80, F.y / 16, comp.v5seg && comp.v5seg.chegou);
comp.v5.rotina = null; passo(3); console.log('sem plano, passeio:', F.wait, comp.v5seg);
// execução simulada inteira
comp.femitMock(); passo(20000);
console.log('humores', JSON.stringify(humores), 'fase', comp.state.fphase, 'ocioso?', comp.v5Livre());
console.log('fillRects', fillCount);
