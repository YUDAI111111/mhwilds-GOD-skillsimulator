import Papa from 'papaparse';

export const CSV = {
  Armor: 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTFURDrVGsrk4gmvxF7eBqfOuh9R3lZ_4xpufeFDMX7mfwJ_JHNBoS0zLEajF1XNBnhYbhUEs0H3Unn/pub?gid=171945967&single=true&output=csv',
  Weapons: 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTFURDrVGsrk4gmvxF7eBqfOuh9R3lZ_4xpufeFDMX7mfwJ_JHNBoS0zLEajF1XNBnhYbhUEs0H3Unn/pub?gid=2069897853&single=true&output=csv',
  Skills: 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTFURDrVGsrk4gmvxF7eBqfOuh9R3lZ_4xpufeFDMX7mfwJ_JHNBoS0zLEajF1XNBnhYbhUEs0H3Unn/pub?gid=1812009195&single=true&output=csv',
  Series: 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTFURDrVGsrk4gmvxF7eBqfOuh9R3lZ_4xpufeFDMX7mfwJ_JHNBoS0zLEajF1XNBnhYbhUEs0H3Unn/pub?gid=887441816&single=true&output=csv',
  Decos: 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTFURDrVGsrk4gmvxF7eBqfOuh9R3lZ_4xpufeFDMX7mfwJ_JHNBoS0zLEajF1XNBnhYbhUEs0H3Unn/pub?gid=2138222154&single=true&output=csv',
  TalismanTable: 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTFURDrVGsrk4gmvxF7eBqfOuh9R3lZ_4xpufeFDMX7mfwJ_JHNBoS0zLEajF1XNBnhYbhUEs0H3Unn/pub?gid=0&single=true&output=csv',
  GroupSkills: 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTFURDrVGsrk4gmvxF7eBqfOuh9R3lZ_4xpufeFDMX7mfwJ_JHNBoS0zLEajF1XNBnhYbhUEs0H3Unn/pub?gid=6018657&single=true&output=csv'
};

export async function loadCsv(url: string){
  return new Promise<Record<string,string>[]>((resolve,reject)=>{
    Papa.parse(url,{download:true,header:true,skipEmptyLines:true,
      complete: (res)=> resolve(res.data as any), error: reject});
  });
}

export async function loadSkills(){
  const rows = await loadCsv(CSV.Skills);
  const keys = rows.length? Object.keys(rows[0]) : [];
  const kName = keys.find(k => /スキル|name/i.test(k)) || keys[0] || 'name';
  return Array.from(new Set(rows.map(r => (r[kName]||'').toString().trim()).filter(Boolean)));
}

export async function loadDecoKinds(){
  const rows = await loadCsv(CSV.Decos);
  const keys = rows.length? Object.keys(rows[0]) : [];
  const kSkill = keys.find(k => /スキル|skill/i.test(k)) || keys[0];
  const kSlot  = keys.find(k => /スロ|slot/i.test(k)) || keys[0];
  const kLv    = keys.find(k => /lv|レベル|level/i.test(k)) || keys[0];
  const map = new Map<string,{skill:string,slot:number,level:number}>();
  for(const r of rows){
    const sk=(r[kSkill]||'').toString().trim();
    const sl=Number((r[kSlot]||'').toString().replace(/[^0-9]/g,''))||0;
    const lv=Number((r[kLv]||'').toString().replace(/[^0-9]/g,''))||1;
    if(!sk||!sl) continue;
    const key=sk+':'+sl;
    const cur=map.get(key);
    if(!cur || lv>(cur.level||0)) map.set(key,{skill:sk,slot:sl,level:lv});
  }
  return Array.from(map.values());
}
