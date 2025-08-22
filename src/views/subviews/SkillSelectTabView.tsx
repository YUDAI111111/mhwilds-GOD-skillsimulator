import React, { useEffect, useState } from 'react';
import { loadSkills } from '../../data';

type SkillRow = { name: string; cmp: '以上'|'='; level: number };
const GROUPS = [
  { title: '武器スキル(攻撃力)', rows: 4 },
  { title: '武器スキル(会心率)', rows: 3 },
  { title: '武器スキル(斬れ味)', rows: 4 },
  { title: '武器スキル(属性・異常)', rows: 6 },
  { title: '武器スキル(ガード)', rows: 3 }
];

export default function SkillSelectTabView({onSearch}:{onSearch:()=>void}){
  const [options, setOptions] = useState<string[]>([]);
  const [groups, setGroups] = useState(GROUPS.map(g=>({title:g.title, rows:Array.from({length:g.rows}).map(()=>({name:'',cmp:'以上' as const,level:1}))})));

  useEffect(()=>{ loadSkills().then(setOptions).catch(()=>setOptions([])); },[]);

  return (
    <div className="main" style={{marginTop:8}}>
      <div>
        {groups.map((g,gi)=>(
          <div className="group" key={gi}>
            <div className="group-header"><div className="group-title">{g.title}</div></div>
            {g.rows.map((r,ri)=>(
              <div className="row" key={ri}>
                <select className="select" value={r.name} onChange={e=>{ const v=[...groups]; v[gi].rows[ri].name=e.target.value; setGroups(v); }}>
                  <option value="">（スキル）</option>
                  {options.map(s=><option key={s} value={s}>{s}</option>)}
                </select>
                <select className="select" value={r.cmp} onChange={e=>{ const v=[...groups]; v[gi].rows[ri].cmp=e.target.value as any; setGroups(v); }}>
                  <option>以上</option><option>=</option>
                </select>
                <select className="select" value={r.level} onChange={e=>{ const v=[...groups]; v[gi].rows[ri].level=Number(e.target.value); setGroups(v); }}>
                  {Array.from({length:10},(_,i)=><option key={i+1} value={i+1}>{i+1}</option>)}
                </select>
                <select className="select" disabled><option>（サブ条件）</option></select>
                <select className="select" disabled><option>以上</option></select>
                <select className="select" disabled><option>1</option></select>
              </div>
            ))}
          </div>
        ))}
        <div className="group">
          <div className="footerbtns">
            <button className="btn">検索条件をリセット</button>
            <button className="btn">追加スキル検索する</button>
            <button className="btn primary" onClick={onSearch}>検索する</button>
          </div>
        </div>
      </div>
      <div className="sidebar">
        <h3>説明</h3>
        <div className="kv">
          <div>使い方</div><div>左でスキル条件を設定し「検索する」。右タブで護石・装飾品・除外固定を編集可能。</div>
        </div>
      </div>
    </div>
  );
}
