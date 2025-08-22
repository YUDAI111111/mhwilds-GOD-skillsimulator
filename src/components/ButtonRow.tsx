import React from 'react';
export function ButtonRow({children}:{children:React.ReactNode}){
  return <div style={{display:'flex', gap:8, flexWrap:'wrap'}}>{children}</div>;
}
