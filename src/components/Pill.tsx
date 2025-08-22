import React from 'react';
export function Pill({children}:{children:React.ReactNode}){
  return <span className="badge">{children}</span>;
}
