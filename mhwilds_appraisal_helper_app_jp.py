import streamlit as st
import pandas as pd
from collections import defaultdict, Counter
from itertools import product, islice
from pathlib import Path
import re

st.set_page_config(page_title="MHWilds 補助シミュ（ビルトインDB＋護石提案）", layout="wide")
st.title("MHWilds 補助シミュレーター（護石提案）— ビルトインDB同梱版")

DATA_DIR = Path(__file__).parent / "data"  # ← リポジトリ内の data/ を参照

# ---------- helpers ----------
def to_int(x, default=0):
    try:
        if pd.isna(x): return default
        return int(x)
    except Exception:
        try:
            return 10**9 if str(x).strip() in ["∞","inf","INF"] else int(float(x))
        except Exception:
            return default

def parse_slot_patterns(cell):
    if pd.isna(cell): return []
    s = str(cell)
    pats = re.findall(r"\[([^\]]+)\]", s)
    out = []
    for p in pats:
        items = [x.strip() for x in p.split(",")]
        out.append(items)
    return out

def sum_skills(records, skill_cols=3, prefix_skill="skill", prefix_lv="lv"):
    total = defaultdict(int)
    for rec in records:
        for i in range(1, skill_cols+1):
            sk = rec.get(f"{prefix_skill}{i}")
            lv = to_int(rec.get(f"{prefix_lv}{i}"), 0)
            if sk and not pd.isna(sk) and lv>0:
                total[sk] += lv
    return total

def slots_from_row(row, slot_cols=("slot1","slot2","slot3")):
    return [to_int(row.get(c,0)) for c in slot_cols if c in row]

def collect_slots(wep_slots, gear_slots_list, charm_slot_tokens, weapon_l1_available):
    slot_counts = Counter()
    for s in wep_slots:
        if s in (1,2,3): slot_counts[s]+=1
    w1_need = sum(1 for t in charm_slot_tokens if str(t).upper()=="W1")
    if weapon_l1_available < w1_need:
        return None
    if w1_need>0:
        if slot_counts[1] < w1_need:
            return None
        slot_counts[1] -= w1_need
    for gs in gear_slots_list:
        for s in gs:
            if s in (1,2,3): slot_counts[s]+=1
    for t in charm_slot_tokens:
        if str(t).upper()=="W1": 
            continue
        s = to_int(t,0)
        if s in (1,2,3): slot_counts[s]+=1
    return slot_counts

def assign_decorations(required, decorations_df, slot_counts):
    filled = defaultdict(int)
    used = []
    pool = []
    for _, row in decorations_df.iterrows():
        skill = str(row["skill"])
        lv = to_int(row["lv"], 1)
        slot = to_int(row["slot"], 1)
        cnt = row.get("count", 10**9)
        cnt = to_int(cnt, 10**9)
        pool.append({"skill":skill,"lv":lv,"slot":slot,"count":cnt,"name":row.get("name", f"{skill}_jewel_{slot}")})
    by_skill = defaultdict(list)
    for d in pool:
        by_skill[d["skill"]].append(d)
    for k in by_skill:
        by_skill[k].sort(key=lambda d: (d["slot"], -d["lv"]))  # 小さいスロ優先、同Lvなら高Lv優先
    for skill, need in required.items():
        remain = need
        options = by_skill.get(skill, [])
        for d in options:
            while remain>0 and d["count"]>0:
                possible_levels = [s for s in (1,2,3) if s>=d["slot"] and slot_counts[s]>0]
                if not possible_levels:
                    break
                s = min(possible_levels)
                slot_counts[s]-=1
                d["count"]-=1
                remain -= d["lv"]
                used.append((skill, d["lv"], d["slot"], d["name"]))
            if remain<=0:
                break
        if remain>0:
            filled[skill] = required[skill]-remain
        else:
            filled[skill] = required[skill]
    return filled, slot_counts, used

def score_build(targets_df, totals):
    """
    priority: 1=変更なし(必須), 2=下げても良い, 3=無くしても良い（妥協）
    """
    score = 0
    hard_fail = []
    p2_deficits = []
    insuff = []
    surplus = []
    for _, r in targets_df.iterrows():
        sk = r["skill"]; t = int(r["target_level"]); p = int(r["priority"])
        cur = int(totals.get(sk, 0))
        diff = cur - t
        if p==1 and diff<0:
            hard_fail.append((sk, -diff))
        elif p==2:
            if diff<0:
                p2_deficits.append((sk, -diff))
                score -= (-diff)
            else:
                if diff>0: surplus.append((sk, diff))
        else:
            if diff<0:
                insuff.append((sk, -diff))
            else:
                if diff>0: surplus.append((sk, diff))
    return score, hard_fail, p2_deficits, insuff, surplus

# ---- column normalization for Japanese headers ----
def normalize_group_df(df):
    cols = {c.strip():c for c in df.columns}
    mapping = {}
    for cand in ["Group","グループ","group","グループ番号"]:
        if cand in cols: mapping[cols[cand]] = "Group"; break
    for cand in ["Skill Name","スキル名","skill","スキル"]:
        if cand in cols: mapping[cols[cand]] = "Skill Name"; break
    for cand in ["Skill Level","レベル","lv","LV"]:
        if cand in cols: mapping[cols[cand]] = "Skill Level"; break
    if mapping:
        df = df.rename(columns=mapping)
    return df

def normalize_appraisal_df(df):
    cols = {c.strip():c for c in df.columns}
    mapping = {}
    for cand in ["rarity","レア度","Rare","RARE","RARE度"]:
        if cand in cols: mapping[cols[cand]] = "rarity"; break
    for cc in ["1個目スキルGroup","g1","一つ目"]:
        if cc in cols: mapping[cols[cc]] = "g1"; break
    for cc in ["2個目スキルGroup","g2","二つ目"]:
        if cc in cols: mapping[cols[cc]] = "g2"; break
    for cc in ["3個目スキルGroupe","3個目スキルGroup","g3","三つ目"]:
        if cc in cols: mapping[cols[cc]] = "g3"; break
    for cand in ["slots","空きスロット","空スロ","スロット"]:
        if cand in cols: mapping[cols[cand]] = "slots"; break
    if mapping:
        df = df.rename(columns=mapping)
    return df

# ---------- data loaders (built-in + override) ----------
def read_csv_builtin(name):
    path = DATA_DIR / name
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()

def use_or_override(builtin_df, uploader_label, hint):
    up = st.sidebar.file_uploader(uploader_label, type=["csv"], help=hint)
    if up:
        df = pd.read_csv(up)
        st.sidebar.caption(f"→ {uploader_label} は **アップロードで上書き中**")
        return df
    st.sidebar.caption(f"→ {uploader_label} は **ビルトインDB** を使用")
    return builtin_df

# ---- load all datasets ----
weapons_df  = use_or_override(read_csv_builtin("weapons.csv"),  "武器CSV", "列: name, slot1, slot2, slot3, skill1, lv1, ...")
armor_df    = use_or_override(read_csv_builtin("armor.csv"),    "防具CSV", "列: name, part, skill1, lv1, skill2, lv2, slot1, slot2, slot3")
charms_df   = use_or_override(read_csv_builtin("charms_seed.csv"), "初期護石CSV（任意）", "列: name, skill1, lv1, skill2, lv2, slot1, slot2, slot3")
decor_df    = use_or_override(read_csv_builtin("decorations.csv"), "装飾品CSV", "列: name, skill, lv, slot, count")
targets_df  = use_or_override(read_csv_builtin("targets.csv"),  "目標スキルCSV", "列: skill, target_level, priority(1/2/3)")
group_df    = use_or_override(read_csv_builtin("group_skills.csv"), "Group→スキルCSV", "列: Group, Skill Name, Skill Level")
ac_df       = use_or_override(read_csv_builtin("appraisal_combos.csv"), "鑑定護石テーブルCSV", "列: rarity, g1, g2, g3, slots")

group_df = normalize_group_df(group_df)
ac_df = normalize_appraisal_df(ac_df)

# ---- minimal fallbacks if DBが空 ----
def ensure_weapons(df):
    if len(df): return df
    return pd.DataFrame([{"name":"太刀","slot1":1,"slot2":0,"slot3":0,"skill1":"見切り","lv1":2}])
def ensure_armor(df):
    if len(df): return df
    return pd.DataFrame([
        {"name":"頭A","part":"Head","skill1":"攻撃","lv1":2,"slot1":1,"slot2":0,"slot3":0},
        {"name":"胴A","part":"Chest","skill1":"見切り","lv1":1,"slot1":2,"slot2":0,"slot3":0},
        {"name":"腕A","part":"Arms","skill1":"体力","lv1":1,"slot1":1,"slot2":0,"slot3":0},
        {"name":"腰A","part":"Waist","skill1":"納刀術","lv1":1,"slot1":2,"slot2":0,"slot3":0},
        {"name":"脚A","part":"Legs","skill1":"体力","lv1":2,"slot1":1,"slot2":0,"slot3":0},
    ])
def ensure_decor(df):
    if len(df): return df
    return pd.DataFrame([
        {"name":"攻撃珠1","skill":"攻撃","lv":1,"slot":1,"count":"∞"},
        {"name":"見切り珠2","skill":"見切り","lv":1,"slot":2,"count":"∞"},
        {"name":"体力珠1","skill":"体力","lv":1,"slot":1,"count":"∞"},
    ])
def ensure_targets(df):
    if len(df): return df
    return pd.DataFrame([
        {"skill":"攻撃","target_level":4,"priority":1},
        {"skill":"見切り","target_level":3,"priority":2},
        {"skill":"体力","target_level":3,"priority":3},
    ])

weapons_df = ensure_weapons(weapons_df)
armor_df   = ensure_armor(armor_df)
decor_df   = ensure_decor(decor_df)
targets_df = ensure_targets(targets_df)

# ---------- manual selection ----------
st.sidebar.subheader("武器・装備の選択")
weapon_name = st.sidebar.selectbox("武器", weapons_df["name"].tolist())
sel_weapon = weapons_df[weapons_df["name"]==weapon_name].iloc[0].to_dict()
wep_slots = [to_int(sel_weapon.get("slot1",0)), to_int(sel_weapon.get("slot2",0)), to_int(sel_weapon.get("slot3",0))]
weapon_l1_available = wep_slots.count(1)

parts = ["Head","Chest","Arms","Waist","Legs"]
selected_gear = {}
for p in parts:
    options = armor_df[armor_df["part"]==p]["name"].tolist()
    if not options:
        st.sidebar.warning(f"{p} の装備がDBにありません")
        continue
    choice = st.sidebar.selectbox(p, options, key=f"part_{p}")
    selected_gear[p] = armor_df[(armor_df['part']==p) & (armor_df['name']==choice)].iloc[0].to_dict()

own_charm_opt = ["（未使用）"] + (charms_df["name"].tolist() if "name" in charms_df.columns and len(charms_df) else [])
own_charm_name = st.sidebar.selectbox("護石（所持）", own_charm_opt)
sel_own_charm = None if own_charm_name=="（未使用）" else charms_df[charms_df["name"]==own_charm_name].iloc[0].to_dict()

# ---------- base totals ----------
base_skills = defaultdict(int)
base_skills.update(sum_skills([sel_weapon], 3))
for g in selected_gear.values():
    for k,v in sum_skills([g],3).items():
        base_skills[k]+=v
own_slots = []
if sel_own_charm:
    for k,v in sum_skills([sel_own_charm],2).items():
        base_skills[k]+=v
    own_slots = slots_from_row(sel_own_charm)

# ---------- assign decos (owned charm case) ----------
req = {}
for _, r in targets_df.iterrows():
    need = int(r["target_level"]) - int(base_skills.get(r["skill"],0))
    if need>0:
        req[r["skill"]] = need

gear_slots_list = [slots_from_row(g) for g in selected_gear.values()]
slot_counts_owned = collect_slots(wep_slots, gear_slots_list, own_slots, weapon_l1_available) if sel_own_charm else collect_slots(wep_slots, gear_slots_list, [], weapon_l1_available)

with st.expander("所持護石での判定", expanded=True):
    totals_owned = dict(base_skills)
    if slot_counts_owned is None:
        st.error("所持護石のW1要件が武器スロ不足で満たせません")
    else:
        filled, rem_slots, used = assign_decorations(req, decor_df, slot_counts_owned.copy())
        for sk, filled_lv in filled.items():
            totals_owned[sk] = totals_owned.get(sk, 0) + filled_lv
        score, hard_fail, p2_def, insuff, surplus = score_build(targets_df, totals_owned)
        st.write("スキル合計:", dict(sorted(totals_owned.items())))
        st.write("不足(P1):", hard_fail, "不足(P2):", p2_def, "不足(P3):", insuff, "余剰:", surplus)
        st.write("使用装飾品:", used)
        if hard_fail:
            st.warning("所持護石では必須(P1)を満たせません")
        else:
            st.success("所持護石で必須(P1)は満たせます")

# ---------- appraisal suggestion ----------
st.subheader("鑑定護石の提案（所持護石で不可のとき）")
if not len(ac_df):
    st.info("鑑定護石テーブルがDBにありません（data/appraisal_combos.csv を用意するか、CSVをアップロードしてください）。")
else:
    # Build group map
    group_map = defaultdict(list)
    group_df = normalize_group_df(group_df)
    for _, r in group_df.iterrows():
        gid = to_int(r.get("Group",0),0)
        sname = str(r.get("Skill Name",""))
        slv = to_int(r.get("Skill Level",1),1)
        if gid and sname:
            group_map[gid].append((sname, slv))

    missing_skills = set(req.keys())

    def expand_appraisal_candidates(ac_df, missing_skills, limit_per_combo=50):
        cands = []
        ac_df = normalize_appraisal_df(ac_df)
        for _, row in ac_df.iterrows():
            g1 = row.get("g1"); g2 = row.get("g2"); g3 = row.get("g3")
            slot_patterns = parse_slot_patterns(row.get("slots",""))
            groups = []
            for g in (g1,g2,g3):
                if pd.isna(g) or str(g).strip() in ["","-","0"]:
                    groups.append([])
                else:
                    gid = to_int(g, 0)
                    opts = [(s,lv) for (s,lv) in group_map.get(gid, []) if s in missing_skills]
                    groups.append(opts)
            pruned = [g[:6] for g in groups]  # 組合せ爆発対策
            if pruned == [[],[],[]]:
                pruned = [[("",0)]]
            combos = list(product(*(g if g else [("",0)] for g in pruned)))
            combos = combos[:limit_per_combo]
            for (s1, s2, s3) in combos:
                skills = defaultdict(int)
                for s,lv in (s1,s2,s3):
                    if s:
                        skills[s]+=lv
                for pat in slot_patterns if slot_patterns else [[]]:
                    cands.append({"skills": dict(skills), "slot_tokens": pat, "row": row.to_dict()})
        return cands

    cands = expand_appraisal_candidates(ac_df, missing_skills, limit_per_combo=50)

    def evaluate_with_candidate(cand):
        totals = defaultdict(int, base_skills)
        for k,v in cand["skills"].items():
            totals[k]+=v
        slot_counts = collect_slots(wep_slots, [slots_from_row(g) for g in selected_gear.values()], cand["slot_tokens"], weapon_l1_available)
        if slot_counts is None:
            return None
        need = {}
        for _, r in targets_df.iterrows():
            cur = totals.get(r["skill"], 0)
            n = int(r["target_level"]) - int(cur)
            if n>0: need[r["skill"]] = n
        filled, rem, used = assign_decorations(need, decor_df, slot_counts.copy())
        for sk, filled_lv in filled.items():
            totals[sk]+=filled_lv
        score, hard_fail, p2_def, insuff, surplus = score_build(targets_df, totals)
        return {
            "totals": dict(totals),
            "score": score,
            "hard_fail": hard_fail,
            "p2_def": p2_def,
            "insuff_p3": insuff,
            "surplus": surplus,
            "used_decos": used,
            "slot_tokens": cand["slot_tokens"],
            "skills_from_cand": cand["skills"],
            "row": cand["row"]
        }

    evaluated = []
    for c in cands:
        res = evaluate_with_candidate(c)
        if res is None:
            continue
        evaluated.append(res)

    def key_func(r):
        hard = 1 if r["hard_fail"] else 0
        return ( -hard, r["score"], sum(v for _,v in r["surplus"]) )

    evaluated.sort(key=key_func, reverse=True)

    top_n = st.number_input("表示する提案数", min_value=1, max_value=50, value=10)
    if not evaluated:
        st.info("護石候補なし")
    else:
        for i, r in enumerate(islice(evaluated, int(top_n))):
            with st.expander(f"提案#{i+1} | P1満たす: {'OK' if not r['hard_fail'] else 'NG'} | スコア: {r['score']} | cand技能: {r['skills_from_cand']} | スロット: {r['slot_tokens']}", expanded=(i==0)):
                st.write("合計スキル:", r["totals"])
                if r["hard_fail"]:
                    st.error(f"P1不足: {r['hard_fail']}")
                if r["p2_def"]:
                    st.warning(f"P2不足: {r['p2_def']}")
                if r["insuff_p3"]:
                    st.info(f"P3不足: {r['insuff_p3']}")
                st.write("余剰:", r["surplus"])
                st.write("装飾品使用:", r["used_decos"])
                meta = {k:v for k,v in r["row"].items() if k in ("rarity","g1","g2","g3","slots")}
                st.caption(f"ソース行: {meta}")
