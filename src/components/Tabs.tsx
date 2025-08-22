import React from 'react';
import cn from 'classnames';

export function Tabs({items, active, onChange}:{items:string[], active:string, onChange:(k:string)=>void}){
  return <div className="tabs">
    {items.map(k => <button key={k} className={cn('tab', {active: active===k})} onClick={()=>onChange(k)}>{k}</button>)}
  </div>;
}
