import React, { useState } from 'react';
import cn from 'classnames';
import SkillSelectTabView from './subviews/SkillSelectTabView';
import SimulatorTabView from './subviews/SimulatorTabView';
import CludeTabView from './subviews/CludeTabView';
import CharmTabView from './subviews/CharmTabView';
import DecoTabView from './subviews/DecoTabView';
import SkillsetTabView from './subviews/SkillsetTabView';

const TABS = ['スキル選択','検索結果','除外・固定設定','護石設定','装飾品設定','マイセット','ライセンス・謝辞'] as const;

export default function MainView(){
  const [tab, setTab] = useState<typeof TABS[number]>('スキル選択');
  return (
    <div className="container">
      <div className="topbar">
        {TABS.map(k => <button key={k} className={cn('tab',{active:tab===k})} onClick={()=>setTab(k)}>{k}</button>)}
        <div className="tabspacer"></div>
      </div>
      {tab==='スキル選択' && <SkillSelectTabView onSearch={()=>setTab('検索結果')} />}
      {tab==='検索結果' && <SimulatorTabView />}
      {tab==='除外・固定設定' && <CludeTabView />}
      {tab==='護石設定' && <CharmTabView />}
      {tab==='装飾品設定' && <DecoTabView />}
      {tab==='マイセット' && <SkillsetTabView />}
      {tab==='ライセンス・謝辞' && <div className="group"><div>UIはBAMLの構造を参考にWebで再実装（コードは新規）。</div></div>}
    </div>
  );
}
