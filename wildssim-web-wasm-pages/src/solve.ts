import highs from 'highs-js';
import { ModelInput, slotCapacity } from './model';

// 簡略:
//  - 各部位は候補から1つ選択 (x_{p,i} ∈ {0,1})
//  - デコはスキル別に合算して個数変数 y_{skill,slot} (整数) とし、累積スロ制約で締める
//  - 目標は P1を達成、P2/P3不足はスラックにペナルティ（下げ幅×重み）

export async function solveILP(input: ModelInput) {
  const H = await highs();
  const { armors, weapon, decos, talisman, targets, priority } = input;

  // 変数
  const x: string[] = []; // armor pick
  const y: string[] = []; // deco counts by (skill,slot)
  const s: string[] = []; // slack for P2/P3

  const armorByPart: Record<string, string[]> = {};
  for (const a of armors) {
    const name = `x_${a.part}_${a.id}`;
    x.push(name); armorByPart[a.part] = armorByPart[a.part] || []; armorByPart[a.part].push(name);
    H.addVariable(name, 0, 1, 0, true); // binary
  }

  // 装備スロ合計
  const slotsAll = [
    ...armors.flatMap(a=>a.slots),
    ...weapon.slots,
    ...(talisman?.slots||[])
  ];
  const cap = slotCapacity(slotsAll);

  // デコ（スキル×要求スロ）
  const decoKinds = Array.from(new Set(decos.map(d=>`${d.skill}:${d.slot}`)));
  for (const key of decoKinds) {
    const name = `y_${key.replace(':','_')}`;
    y.push(name);
    H.addVariable(name, 0, 999, 0, false); // integer count
  }

  // スキル制約: base(防具/武器/護石) + Σ(deco) - slack >= target (P1はslack禁止)
  const skillsAll = Array.from(new Set([
    ...Object.keys(targets),
    ...armors.flatMap(a=>Object.keys(a.skills)),
    ...Object.keys(weapon.skills),
    ...(talisman ? Object.keys(talisman.skills) : [])
  ]));

  function baseSkillCoeff(skill: string, varName: string): number {
    // x_{p,i} が選ばれたときの寄与は armor側のスキル。
    const m = varName.match(/^x_(.+)_(.+)$/); if (!m) return 0;
    const a = armors.find(z=>`x_${z.part}_${z.id}`===varName)!;
    return a.skills[skill] || 0;
  }

  for (const sk of skillsAll) {
    const t = targets[sk] || 0;
    if (t === 0) continue;

    // left side: Σ a_ij x_ij + weapon + talisman + Σ deco
    const row: Record<string, number> = {};
    for (const xi of x) {
      const c = baseSkillCoeff(sk, xi);
      if (c) row[xi] = (row[xi]||0)+c;
    }
    const w = weapon.skills[sk]||0; if (w) row['const_weapon_'+sk]=(row['const_weapon_'+sk]||0)+w;
    if (talisman && talisman.skills[sk]) row['const_talis_'+sk]=(row['const_talis_'+sk]||0)+talisman.skills[sk];

    // デコ寄与
    for (const key of decoKinds) {
      const [skillName, slotStr] = key.split(':');
      if (skillName !== sk) continue;
      const lvPerDeco = decos.find(d=>d.skill===sk && String(d.slot)===slotStr)?.level || 0;
      if (!lvPerDeco) continue;
      const varName = `y_${skillName}_${slotStr}`;
      row[varName] = (row[varName]||0) + lvPerDeco;
    }

    // P1: >= t (slack禁止)
    if ((priority.P1||[]).includes(sk)) {
      H.addConstraint(row, ">=", t, `skill_${sk}_P1`);
    } else {
      // P2/P3: slackを許容
      const slack = `s_${sk}`; s.push(slack); H.addVariable(slack, 0, 999, 0, false);
      row[slack] = 1; // (t - achieved) = slack
      H.addConstraint(row, ">=", t, `skill_${sk}_soft`);
      const wP = (priority.P2||[]).includes(sk) ? ((priority.weights?.P2)||1) : ((priority.P3||[]).includes(sk) ? ((priority.weights?.P3)||0.5) : 0.1);
      H.setObjectiveCoefficient(slack, wP); // minimize slack weighted
    }
  }

  // 部位ごとに1つ選択
  for (const part of Object.keys(armorByPart)) {
    const row: Record<string, number> = {};
    for (const xi of armorByPart[part]) row[xi] = 1;
    H.addConstraint(row, "=", 1, `pick_${part}`);
  }

  // スロット容量（累積）: 使用数 <= 容量
  function sumY(slotMin: number) {
    const row: Record<string, number> = {};
    for (const key of decoKinds) {
      const [, slotStr] = key.split(':');
      const s = Number(slotStr);
      if (s >= slotMin) {
        const name = `y_${key.replace(':','_')}`;
        row[name] = (row[name]||0) + 1;
      }
    }
    return row;
  }
  H.addConstraint(sumY(1), "<=", cap.c1, "cap_s1");
  H.addConstraint(sumY(2), "<=", cap.c2, "cap_s2");
  H.addConstraint(sumY(3), "<=", cap.c3, "cap_s3");
  H.addConstraint(sumY(4), "<=", cap.c4, "cap_s4");

  // 目的関数: minimize（既に slack に係数設定済み）
  H.setObjectiveSense("minimize");

  const res = H.solve();
  return res; // TODO: 変数値を読んでUIへ反映する整形
}
