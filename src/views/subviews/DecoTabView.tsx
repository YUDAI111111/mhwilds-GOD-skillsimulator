import React, { useEffect, useState } from 'react';
import { loadDecoKinds } from '../../data';

export default function DecoTabView(){
  const [kinds, setKinds] = useState<{skill:string,slot:number,level:number}[]>([]);
  useEffect(()=>{ loadDecoKinds().then(setKinds).catch(()=>setKinds([])); },[]);

  return (
    <div className="main" style={{marginTop:8}}>
      <div className="group">
        <div className="group-header"><div className="group-title">装飾品 所持数</div></div>
        <table className="table">
          <thead><tr><th>スキル</th><th>スロ</th><th>Lv/個</th><th>所持数</th></tr></thead>
          <tbody>
            {kinds.slice(0,200).map((k,i)=>(
              <tr key={i}><td>{k.skill}</td><td>{k.slot}</td><td>{k.level}</td><td><input className="input" type="number" min="0" defaultValue="99" /></td></tr>
            ))}
            {kinds.length>200 && <tr><td colSpan={4}>...（+{kinds.length-200}）</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="sidebar"><h3>説明</h3><p className="small">デフォルトMAX。次段で最適化に反映。</p></div>
    </div>
  );
}
