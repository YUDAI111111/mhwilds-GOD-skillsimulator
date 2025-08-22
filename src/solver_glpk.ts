import GLPKFactory from 'glpk.js';
export type SlotCap = { c1:number; c2:number; c3:number; c4:number };
export type DecoKind = { skill: string; slot: 1|2|3|4; level: number };

export function buildDecoKinds(rows: Record<string,string>[]): DecoKind[] {
  const out: Record<string, DecoKind> = {};
  for (const r of rows || []){
    const keys = Object.keys(r);
    const get = (names: string[]) => keys.find(k => names.some(n => k.toLowerCase().includes(n))) || '';
    const kSkill = get(['スキル','skill']);
    const kSlot  = get(['スロ','slot']);
    const kLv    = get(['lv','レベル','level']);
    const skill = (r[kSkill]||'').trim();
    const slot  = Number((r[kSlot]||'').toString().replace(/[^0-9]/g,'')) as any;
    const level = Number((r[kLv]||'').toString().replace(/[^0-9]/g,'')) || 1;
    if (!skill || !slot) continue;
    const key = skill+':'+slot;
    if (!out[key] || level > out[key].level){
      out[key] = { skill, slot: Math.min(Math.max(slot,1),4) as any, level };
    }
  }
  return Object.values(out);
}

type SolveInput = { targets: Record<string, number>; baseSkills: Record<string, number>; decos: DecoKind[]; cap: SlotCap; };

export async function solveDecorOnly(input: SolveInput){
  const glpk = await GLPKFactory();
  const { targets, baseSkills, decos, cap } = input;
  const kinds = decos.filter(d => targets[d.skill] && (targets[d.skill] - (baseSkills[d.skill]||0) > 0));
  if (kinds.length === 0){ return { summary: '不足スキルなし（護石で既に満たしています）', vars: {} }; }

  const varNames: string[] = []; const subjectTo: any[] = []; const bounds: any[] = []; const generals: string[] = [];
  for (const k of kinds){ const name = `y_${k.skill}_${k.slot}`.replace(/[^\w\u0080-\uFFFF]/g,'_'); if(!varNames.includes(name)){ varNames.push(name); bounds.push({ name, bnds: { type: glpk.GLP_LO, lb: 0, ub: 0 } }); generals.push(name); } }
  for (const sk of Object.keys(targets)){
    const need = Math.max(0, (targets[sk]||0) - (baseSkills[sk]||0)); if (need<=0) continue;
    const vars = kinds.filter(k=>k.skill===sk).map(k=>({ name:`y_${k.skill}_${k.slot}`.replace(/[^\w\u0080-\uFFFF]/g,'_'), coef:k.level }));
    if (vars.length) subjectTo.push({ name:`skill_${sk}`.replace(/[^\w\u0080-\uFFFF]/g,'_'), vars, bnds:{ type: glpk.GLP_LO, lb: need, ub: 0 } });
  }
  const sumRow = (slotMin:number)=> kinds.filter(k=>k.slot>=slotMin).map(k=>({ name:`y_${k.skill}_${k.slot}`.replace(/[^\w\u0080-\uFFFF]/g,'_'), coef:1 }));
  if (kinds.some(k=>k.slot>=1)) subjectTo.push({ name:'cap_s1', vars: sumRow(1), bnds:{ type: glpk.GLP_UP, lb:0, ub:cap.c1 } });
  if (kinds.some(k=>k.slot>=2)) subjectTo.push({ name:'cap_s2', vars: sumRow(2), bnds:{ type: glpk.GLP_UP, lb:0, ub:cap.c2 } });
  if (kinds.some(k=>k.slot>=3)) subjectTo.push({ name:'cap_s3', vars: sumRow(3), bnds:{ type: glpk.GLP_UP, lb:0, ub:cap.c3 } });
  if (kinds.some(k=>k.slot>=4)) subjectTo.push({ name:'cap_s4', vars: sumRow(4), bnds:{ type: glpk.GLP_UP, lb:0, ub:cap.c4 } });

  const objectiveVars = varNames.map(n=>({ name:n, coef:1 }));
  const lp = { name:'decor-only', objective:{ direction: glpk.GLP_MIN, name:'obj', vars: objectiveVars }, subjectTo, bounds, generals };
  const res = glpk.solve(lp, { msglev: glpk.GLP_MSG_OFF });
  const varsOut: Record<string, number> = {}; for (const n of varNames){ const v=(res.result.vars as any)[n]; if (v && v.value) varsOut[n]=Math.round(v.value); }
  const lines: string[] = []; lines.push('=== 装飾品割当（最小個数） ===');
  const used = Object.entries(varsOut).filter(([,v])=>v>0);
  if (!used.length){ lines.push('装飾品は不要です。'); } else {
    for (const [n,v] of used){ const m=n.match(/^y_(.+)_(\d+)$/); const skill=m?m[1]:n; const slot=m?m[2]:'?'; lines.push(`${skill} : スロ${slot} × ${v}`); }
  }
  lines.push('--- 容量 ---'); lines.push(`S1<=${cap.c1}, S2<=${cap.c2}, S3<=${cap.c3}, S4<=${cap.c4}`);
  return { summary: lines.join('\n'), vars: varsOut, res };
}
