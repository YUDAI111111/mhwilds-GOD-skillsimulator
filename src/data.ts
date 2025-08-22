import Papa from 'papaparse';

const CSV = {
  Armor: 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTFURDrVGsrk4gmvxF7eBqfOuh9R3lZ_4xpufeFDMX7mfwJ_JHNBoS0zLEajF1XNBnhYbhUEs0H3Unn/pub?gid=171945967&single=true&output=csv',
  Weapons: 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTFURDrVGsrk4gmvxF7eBqfOuh9R3lZ_4xpufeFDMX7mfwJ_JHNBoS0zLEajF1XNBnhYbhUEs0H3Unn/pub?gid=2069897853&single=true&output=csv',
  Skills: 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTFURDrVGsrk4gmvxF7eBqfOuh9R3lZ_4xpufeFDMX7mfwJ_JHNBoS0zLEajF1XNBnhYbhUEs0H3Unn/pub?gid=1812009195&single=true&output=csv',
  Series: 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTFURDrVGsrk4gmvxF7eBqfOuh9R3lZ_4xpufeFDMX7mfwJ_JHNBoS0zLEajF1XNBnhYbhUEs0H3Unn/pub?gid=887441816&single=true&output=csv',
  Decos: 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTFURDrVGsrk4gmvxF7eBqfOuh9R3lZ_4xpufeFDMX7mfwJ_JHNBoS0zLEajF1XNBnhYbhUEs0H3Unn/pub?gid=2138222154&single=true&output=csv',
  TalismanTable: 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTFURDrVGsrk4gmvxF7eBqfOuh9R3lZ_4xpufeFDMX7mfwJ_JHNBoS0zLEajF1XNBnhYbhUEs0H3Unn/pub?gid=0&single=true&output=csv',
  GroupSkills: 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTFURDrVGsrk4gmvxF7eBqfOuh9R3lZ_4xpufeFDMX7mfwJ_JHNBoS0zLEajF1XNBnhYbhUEs0H3Unn/pub?gid=6018657&single=true&output=csv'
};

export async function loadCsv(url: string): Promise<Record<string,string>[]> {
  return new Promise((resolve, reject) => {
    Papa.parse(url, { download: true, header: true, skipEmptyLines: true,
      complete: (res) => resolve(res.data as any), error: reject });
  });
}

export async function loadAll() {
  const [armor, weapons, skills, series, decos, table, groups] = await Promise.all([
    loadCsv(CSV.Armor), loadCsv(CSV.Weapons), loadCsv(CSV.Skills), loadCsv(CSV.Series),
    loadCsv(CSV.Decos), loadCsv(CSV.TalismanTable), loadCsv(CSV.GroupSkills)
  ]);
  return { armor, weapons, skills, series, decos, table, groups };
}
