import React, { useEffect, useState } from 'react';
import { loadAll } from './data';
import { parseLine, exportLine, toLvString, Talisman } from './talisman';

export default function App(){
  const [weaponSlots, setWeaponSlots] = useState([1,0,0]);
  const [talismans, setTalismans] = useState<Talisman[]>([]);
  const [log, setLog] = useState('');

  useEffect(()=>{ loadAll().then(()=>setLog('データ読込OK')); },[]);

  return (
    <div style={{padding:16,fontFamily:'system-ui'}}>
      <h1>WildsSim Web-Only (WASM)</h1>
      <p>mhwilds互換の護石I/O。武器スロは装備設定の既定として保持。</p>
      <div>
        武器スロ: <input value={toLvString(weaponSlots)} onChange={e=>{
          const m=e.target.value.match(/(\d)-(\d)-(\d)/); if(m){ setWeaponSlots([+m[1],+m[2],+m[3]]); }
        }} />
      </div>
      <h2>護石（固定）</h2>
      <textarea id="imp" rows={6} style={{width:'100%'}} placeholder="S1,S1Lv,S2,S2Lv,S3,S3Lv,G1,G2,G3,W1,W2,W3"/>
      <div style={{display:'flex',gap:8,marginTop:8}}>
        <button onClick={()=>{
          const ta=document.getElementById('imp') as HTMLTextAreaElement;
          for (const line of ta.value.split(/\n+/)){
            const r=parseLine(line.trim()); if(!r) continue; setTalismans(prev=>[...prev,r.talisman]); setWeaponSlots(r.weaponSlots);
          }
        }}>インポート</button>
        <button onClick={()=>{
          const txt = talismans.map(t=>exportLine(t, weaponSlots)).join('\n');
          navigator.clipboard.writeText(txt); setLog('コピーしました');
        }}>エクスポート（コピー）</button>
        <button onClick={()=>setTalismans([])}>全削除</button>
      </div>
      <ul>
        {talismans.map((t,i)=>(<li key={i} style={{fontFamily:'monospace'}}>{t.skills.map(s=>`${s.name}+${s.level}`).join(', ')} / {toLvString(t.slots)}</li>))}
      </ul>
      <h2>ログ</h2>
      <pre style={{whiteSpace:'pre-wrap',background:'#f6f8fa',padding:12}}>{log}</pre>
    </div>
  );
}
