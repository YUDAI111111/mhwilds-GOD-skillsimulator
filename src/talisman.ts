export type Talisman = { skills: { name: string; level: number }[]; slots: [number,number,number] };

export function parseLine(line: string){
  const arr=line.split(',').map(s=>s.trim()); if(arr.length<12) return null;
  const s=[] as {name:string; level:number}[];
  if(arr[0]) s.push({name:arr[0], level:Number(arr[1]||'0')});
  if(arr[2]) s.push({name:arr[2], level:Number(arr[3]||'0')});
  if(arr[4]) s.push({name:arr[4], level:Number(arr[5]||'0')});
  const g=[Number(arr[6]||'0'),Number(arr[7]||'0'),Number(arr[8]||'0')].sort((a,b)=>b-a) as [number,number,number];
  const w=[Number(arr[9]||'0'),Number(arr[10]||'0'),Number(arr[11]||'0')] as [number,number,number];
  return { talisman:{skills:s, slots:g}, weaponSlots:w };
}

export function exportLine(t: Talisman, weaponSlots=[1,0,0] as [number,number,number]){
  const s=[t.skills[0]?.name||'',t.skills[0]?.level||0,
           t.skills[1]?.name||'',t.skills[1]?.level||0,
           t.skills[2]?.name||'',t.skills[2]?.level||0,
           t.slots[0]||0,t.slots[1]||0,t.slots[2]||0,
           weaponSlots[0]||0,weaponSlots[1]||0,weaponSlots[2]||0];
  return s.join(',');
}

export function toLvString(sl:[number,number,number]){ return `LV${sl[0]}-${sl[1]}-${sl[2]}`; }
