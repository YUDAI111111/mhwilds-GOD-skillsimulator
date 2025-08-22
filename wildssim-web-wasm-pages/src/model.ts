export type Part = '頭'|'胴'|'腕'|'腰'|'脚';
export type SkillReq = Record<string, number>;

export type CandidateArmor = { id: string; part: Part; name: string; slots: number[]; skills: Record<string,number>; series?: string };
export type CandidateWeapon = { id: string; name: string; slots: number[]; skills: Record<string,number> };
export type Decoration = { name: string; slot: 1|2|3|4; skill: string; level: number };
export type FixedTalisman = { slots: number[]; skills: Record<string,number> };

export type ModelInput = {
  armors: CandidateArmor[];
  weapon: CandidateWeapon;
  decos: Decoration[];              // 在庫MAXを前提（在庫制約は拡張）
  talisman?: FixedTalisman;         // 単一or複数は拡張
  targets: SkillReq;                // 目標
  priority: { P1: string[]; P2: string[]; P3: string[]; weights: {P2:number; P3:number} };
};

// スロット制約（大は小を兼ねる）を扱うため、size>=k の累積使用量で締める
export function slotCapacity(slots: number[]) {
  const c1 = slots.filter(s=>s>=1).length;
  const c2 = slots.filter(s=>s>=2).length;
  const c3 = slots.filter(s=>s>=3).length;
  const c4 = slots.filter(s=>s>=4).length;
  return { c1, c2, c3, c4 };
}
