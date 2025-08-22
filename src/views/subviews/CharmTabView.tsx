import React, { useEffect, useState } from 'react';
import { parseLine, exportLine, toLvString, Talisman } from '../../talisman';

export default function CharmTabView(){
  const [weaponSlots, setWeaponSlots] = useState<[number,number,number]>([1,0,0]);
  const [talismans, setTalismans] = useState<Talisman[]>([]);

  useEffect(()=>{
    const s=localStorage.getItem('ws_weaponSlots'); if(s) setWeaponSlots(JSON.parse(s));
    const t=localStorage.getItem('ws_talismans'); if(t) setTalismans(JSON.parse(t));
  },[]);
  useEffect(()=>{ localStorage.setItem('ws_weaponSlots', JSON.stringify(weaponSlots)); },[weaponSlots]);
  useEffect(()=>{ localStorage.setItem('ws_talismans', JSON.stringify(talismans)); },[talismans]);

  return (
    <div className="main" style={{marginTop:8}}>
      <div>
        <div className="group">
          <div className="group-header"><div className="group-title">お守り追加</div></div>
          <div className="flex">
            <span className="small">武器スロ</span>
            <select className="select" onChange={e=>{ const m=e.target.value.match(/(\d)-(\d)-(\d)/); if(m) setWeaponSlots([+m[1],+m[2],+m[3]] as any); }}>
              {['0-0-0','1-0-0','1-1-0','1-1-1','2-1-0','2-1-1','3-2-1','4-3-2'].map(s=>(<option key={s} value={s}>{'LV'+s.replace(/-/g,'-')}</option>))}
            </select>
            <span className="badge">現在: {toLvString(weaponSlots)}</span>
          </div>
        </div>

        <div className="group">
          <div className="group-header"><div className="group-title">お守り一覧</div></div>
          <table className="table">
            <thead><tr><th>#</th><th>スキル</th><th>スロット</th><th></th></tr></thead>
            <tbody>
              {talismans.map((t,i)=>(<tr key={i}>
                <td>{i+1}</td>
                <td>{t.skills.map(s=>`${s.name}+${s.level}`).join(', ')||'-'}</td>
                <td>{toLvString(t.slots)}</td>
                <td><button className="btn" onClick={()=>{ const v=[...talismans]; v.splice(i,1); setTalismans(v); }}>削除</button></td>
              </tr>))}
              {talismans.length===0 && <tr><td colSpan={4} style={{color:'#556'}}>未登録</td></tr>}
            </tbody>
          </table>
          <div className="flex" style={{marginTop:6}}>
            <button className="btn" onClick={()=>setTalismans([])}>お守りを全て削除</button>
            <span className="badge">お守りコピペ インポート/エクスポート</span>
          </div>
          <textarea id="imp" className="input" rows={5} placeholder="環境利用の知識,1,飛び込み,1,植生学,1,1,1,0,1,0,0"></textarea>
          <div className="footerbtns">
            <button className="btn" onClick={()=>{
              const ta=document.getElementById('imp') as HTMLTextAreaElement;
              for(const line of ta.value.split(/\n+/)){ const r=parseLine(line.trim()); if(!r) continue; setTalismans(prev=>[...prev,r.talisman]); setWeaponSlots(r.weaponSlots as any); }
            }}>インポート</button>
            <button className="btn" onClick={()=>{
              const txt=talismans.map(t=>exportLine(t, weaponSlots)).join('\n'); navigator.clipboard.writeText(txt);
            }}>エクスポート（コピー）</button>
          </div>
        </div>
      </div>
      <div className="sidebar">
        <h3>説明</h3>
        <p className="small">mhwilds互換の行を貼り付けて「インポート」。ブラウザ（localStorage）に保存されます。</p>
      </div>
    </div>
  );
}
