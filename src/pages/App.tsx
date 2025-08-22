import React, { useEffect, useMemo, useState } from 'react';
import { Tabs } from '../components/Tabs';
import { Pill } from '../components/Pill';
import { ButtonRow } from '../components/ButtonRow';
import { loadAll } from '../data';
import { parseLine, exportLine, toLvString, Talisman } from '../talisman';
import { buildDecoKinds, solveDecorOnly, SlotCap } from '../solver_glpk';

type Target = { name: string; level: number; priority: 'P1'|'P2'|'P3' };

const TAB_ITEMS = ['基本条件','スキル目標','護石','飾り','計算','結果'] as const;

export default function App(){
  const [tab, setTab] = useState<typeof TAB_ITEMS[number]>('基本条件');
  const [weaponSlots, setWeaponSlots] = useState<[number,number,number]>([1,0,0]);
  const [talismans, setTalismans] = useState<Talisman[]>([]);
  const [targets, setTargets] = useState<Target[]>([{ name: '攻撃', level: 3, priority: 'P1' }]);
  const [data, setData] = useState<any>(null);
  const [log, setLog] = useState('');
  const [result, setResult] = useState<string>('');

  useEffect(()=>{ loadAll().then(d=>{ setData(d); setLog('データ読込OK');}).catch(e=>setLog('データ読込失敗:'+e)); },[]);
  const decoKinds = useMemo(()=> buildDecoKinds(data?.decos||[]), [data]);

  function slotcap(): SlotCap {
    const talis = talismans.flatMap(t=>t.slots);
    const slotsAll = [...weaponSlots, ...talis];
    const c1 = slotsAll.filter(s=>s>=1).length;
    const c2 = slotsAll.filter(s=>s>=2).length;
    const c3 = slotsAll.filter(s=>s>=3).length;
    const c4 = slotsAll.filter(s=>s>=4).length;
    return { c1,c2,c3,c4 };
  }

  async function runDecorOnly(){
    const baseSkills: Record<string, number> = {};
    talismans.forEach(t => t.skills.forEach(s => baseSkills[s.name] = (baseSkills[s.name]||0)+s.level));
    const tReq: Record<string, number> = {}; targets.forEach(t => tReq[t.name]=(tReq[t.name]||0)+t.level);
    const out = await solveDecorOnly({ targets: tReq, baseSkills, decos: decoKinds, cap: slotcap() });
    setResult(out.summary);
    setTab('結果');
  }

  return (
    <div className="container">
      <div className="header">
        <h1>WildsSim（UI再現MVP）</h1>
        <Pill>Web-only</Pill>
        <Pill>GitHub Pages</Pill>
        <span className="badge">データ: Google Sheets</span>
      </div>
      <Tabs items={[...TAB_ITEMS]} active={tab} onChange={setTab} />

      {tab==='基本条件' && (
        <div className="grid grid-2" style={{marginTop:12}}>
          <div className="panel">
            <h2>武器スロ</h2>
            <div className="row">
              <input className="input" value={toLvString(weaponSlots)} onChange={e=>{
                const m=e.target.value.match(/(\d)-(\d)-(\d)/); if(m){ setWeaponSlots([+m[1] as any,+m[2] as any,+m[3] as any]); }
              }}/>
              <span className="badge">例: LV1-0-0</span>
            </div>
            <div style={{marginTop:8}} className="kv">
              <div>スロ容量（現状）</div>
              <div>S1: {slotcap().c1} / S2: {slotcap().c2} / S3: {slotcap().c3} / S4: {slotcap().c4}</div>
            </div>
          </div>
          <div className="panel">
            <h2>データ状態</h2>
            <div className="kv">
              <div>Armor</div><div>{data?.armor?.length ?? 0} 件</div>
              <div>Weapons</div><div>{data?.weapons?.length ?? 0} 件</div>
              <div>Skills</div><div>{data?.skills?.length ?? 0} 件</div>
              <div>Series</div><div>{data?.series?.length ?? 0} 件</div>
              <div>Decorations</div><div>{data?.decos?.length ?? 0} 種</div>
            </div>
            <div style={{marginTop:8}} className="code">{log||'...'}</div>
          </div>
        </div>
      )}

      {tab==='スキル目標' && (
        <div className="panel" style={{marginTop:12}}>
          <h2>スキル（目標）</h2>
          {targets.map((t,idx)=>(
            <div key={idx} className="row" style={{marginBottom:6}}>
              <input className="input" value={t.name} onChange={e=>{ const v=[...targets]; v[idx]={...t, name:e.target.value}; setTargets(v); }} placeholder="スキル名" />
              <input className="input" style={{maxWidth:100}} value={t.level} type="number" min={0} onChange={e=>{ const v=[...targets]; v[idx]={...t, level:+e.target.value}; setTargets(v); }}/>
              <select className="input" style={{maxWidth:120}} value={t.priority} onChange={e=>{ const v=[...targets]; v[idx]={...t, priority:e.target.value as any}; setTargets(v); }}>
                <option value="P1">P1（必須）</option>
                <option value="P2">P2</option>
                <option value="P3">P3</option>
              </select>
              <button className="btn" onClick={()=>{ const v=[...targets]; v.splice(idx,1); setTargets(v); }}>削除</button>
            </div>
          ))}
          <ButtonRow>
            <button className="btn" onClick={()=>setTargets([...targets, {name:'', level:1, priority:'P2'}])}>＋ 行追加</button>
            <span className="badge">P1は後で厳守に拡張</span>
          </ButtonRow>
        </div>
      )}

      {tab==='護石' && (
        <div className="panel" style={{marginTop:12}}>
          <h2>護石（mhwilds互換）</h2>
          <textarea id="imp" className="input" rows={6} placeholder="S1,S1Lv,S2,S2Lv,S3,S3Lv,G1,G2,G3,W1,W2,W3"></textarea>
          <ButtonRow>
            <button className="btn" onClick={()=>{
              const ta=document.getElementById('imp') as HTMLTextAreaElement;
              for (const line of ta.value.split(/\n+/)){
                const r=parseLine(line.trim()); if(!r) continue; setTalismans(prev=>[...prev,r.talisman]); setWeaponSlots(r.weaponSlots as any);
              }
            }}>インポート</button>
            <button className="btn" onClick={()=>{
              const txt = talismans.map(t=>exportLine(t, weaponSlots)).join('\n');
              navigator.clipboard.writeText(txt);
            }}>エクスポート（コピー）</button>
            <button className="btn" onClick={()=>setTalismans([])}>全削除</button>
          </ButtonRow>
          <table className="table" style={{marginTop:8}}>
            <thead><tr><th>#</th><th>スキル</th><th>スロット</th></tr></thead>
            <tbody>
              {talismans.map((t,i)=>(
                <tr key={i}>
                  <td>{i+1}</td>
                  <td>{t.skills.map(s=>`${s.name}+${s.level}`).join(', ')||'-'}</td>
                  <td>{toLvString(t.slots)}</td>
                </tr>
              ))}
              {talismans.length===0 && <tr><td colSpan={3} style={{color:'#9aa6c4'}}>未登録</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab==='飾り' && (
        <div className="panel" style={{marginTop:12}}>
          <h2>装飾品（種類）</h2>
          <p className="badge">CSVから検出: {decoKinds.length} 種</p>
          <div className="code" style={{maxHeight:220, overflow:'auto'}}>
            {decoKinds.slice(0,200).map(d=>`${d.skill} / スロ${d.slot} / +${d.level}`).join('\n')}
            {decoKinds.length>200 && `\n... (+${decoKinds.length-200} more)`}
          </div>
        </div>
      )}

      {tab==='計算' && (
        <div className="panel" style={{marginTop:12}}>
          <h2>計算（MVP: 装飾品のみ）</h2>
          <p>防具・シリーズは次段で追加。まずは装飾品だけで目標を満たす最小個数を解きます。</p>
          <ButtonRow>
            <button className="btn primary" onClick={runDecorOnly}>装飾品だけで満たす</button>
          </ButtonRow>
        </div>
      )}

      {tab==='結果' && (
        <div className="panel" style={{marginTop:12}}>
          <h2>結果</h2>
          <div className="code">{result || '未計算'}</div>
        </div>
      )}

      <div className="footer">UIは見た目と動線のみ再現（コードは新規実装）。© あなたのプロジェクト / 再配布可。</div>
    </div>
  );
}
