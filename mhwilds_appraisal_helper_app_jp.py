import streamlit as st
import pandas as pd
from collections import defaultdict, Counter
from itertools import product, islice
from urllib.parse import quote
import urllib.error, urllib.request
import re

st.set_page_config(page_title="MHWilds 補助シミュ（スプシ直読＋護石提案）", layout="wide")
st.title("MHWilds 補助シミュレーター（護石提案）— Googleスプレッドシート直読版")

# =========================================================
# 小物ユーティリティ
# =========================================================
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
    """"[W1,0] [W1,1] [W1,1,1]" → [["W1","0"], ["W1","1"], ["W1","1","1"]]"""
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
    """
    wep_slots: [1/2/3/0,...]
    gear_slots_list: [[...part slots...], ...]
    charm_slot_tokens: ["W1","1","1"] etc
    weapon_l1_available: count of Lv1 slots on weapon
    """
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
    """
    required: {skill: levels_needed}
    decorations_df: columns [name,skill,lv,slot,count]
    slot_counts: Counter {1:n1,2:n2,3:n3}
    """
    filled = defaultdict(int)
    used = []
    pool = []
    if len(decorations_df)==0:
        return filled, slot_counts, used

    # 正規化（念のため）
    decorations_df = normalize_decorations_df(decorations_df)

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
                # 3には1～3、2には1～2、1には1
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
    if len(targets_df)==0:
        return 0, [], [], [], []
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

# =========================================================
# スプシ直読（シート名で読める）
# =========================================================
def read_gsheet_csv_by_sheetname(sheet_id: str, sheet_name: str) -> pd.DataFrame:
    if not sheet_id or not sheet_name:
        return pd.DataFrame()
    base = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={quote(sheet_name)}"
    try:
        return pd.read_csv(base)
    except Exception:
        # 失敗時は空で返す（エラーメッセージは呼び出し側でUI通知）
        return pd.DataFrame()

# =========================================================
# 日本語ヘッダーの正規化（各テーブル）
# =========================================================
def normalize_group_df(df):
    if len(df)==0: return df
    cols = {c.strip():c for c in df.columns}
    mapping = {}
    for cand in ["Group","グループ","group","グループ番号","グループID"]:
        if cand in cols: mapping[cols[cand]] = "Group"; break
    for cand in ["Skill Name","スキル名","skill","スキル"]:
        if cand in cols: mapping[cols[cand]] = "Skill Name"; break
    for cand in ["Skill Level","レベル","lv","LV"]:
        if cand in cols: mapping[cols[cand]] = "Skill Level"; break
    if mapping: df = df.rename(columns=mapping)
    return df

def normalize_appraisal_df(df):
    if len(df)==0: return df
    cols = {c.strip():c for c in df.columns}
    mapping = {}
    for cand in ["rarity","レア度","Rare","RARE","RARE度"]:
        if cand in cols: mapping[cols[cand]] = "rarity"; break
    for cc in ["1個目スキルGroup","g1","一つ目","first_group","first"]:
        if cc in cols: mapping[cols[cc]] = "g1"; break
    for cc in ["2個目スキルGroup","g2","二つ目","second_group","second"]:
        if cc in cols: mapping[cols[cc]] = "g2"; break
    for cc in ["3個目スキルGroupe","3個目スキルGroup","g3","三つ目","third_group","third"]:
        if cc in cols: mapping[cols[cc]] = "g3"; break
    for cand in ["slots","空きスロット","空スロ","スロット","スロ構成"]:
        if cand in cols: mapping[cols[cand]] = "slots"; break
    if mapping: df = df.rename(columns=mapping)
    return df

def normalize_weapons_df(df):
    if len(df)==0: return df
    cols = {c.strip():c for c in df.columns}
    mapping = {}
    for cand in ["name","武器名","名前"]:
        if cand in cols: mapping[cols[cand]] = "name"; break
    for cand in ["slot1","スロ1","スロット1","スロLv1","スロットLv1"]:
        if cand in cols: mapping[cols[cand]] = "slot1"; break
    for cand in ["slot2","スロ2","スロット2","スロLv2","スロットLv2"]:
        if cand in cols: mapping[cols[cand]] = "slot2"; break
    for cand in ["slot3","スロ3","スロット3","スロLv3","スロットLv3"]:
        if cand in cols: mapping[cols[cand]] = "slot3"; break
    # skills (最大3まで想定)
    for i in range(1,4):
        for cand in [f"skill{i}", f"スキル{i}", f"スキル{i}名"]:
            if cand in cols: mapping[cols[cand]] = f"skill{i}"; break
        for cand in [f"lv{i}", f"Lv{i}", f"レベル{i}"]:
            if cand in cols: mapping[cols[cand]] = f"lv{i}"; break
    if mapping: df = df.rename(columns=mapping)
    return df

def _normalize_part_value(v):
    s = str(v).strip()
    jp2en = {"頭":"Head","胴":"Chest","腕":"Arms","腰":"Waist","脚":"Legs",
             "ヘッド":"Head","ボディ":"Chest","アーム":"Arms","ウエスト":"Waist","レッグ":"Legs"}
    return jp2en.get(s, s)

def normalize_armor_df(df):
    if len(df)==0: return df
    cols = {c.strip():c for c in df.columns}
    mapping = {}
    for cand in ["name","防具名","名前"]:
        if cand in cols: mapping[cols[cand]] = "name"; break
    for cand in ["part","部位","パート"]:
        if cand in cols: mapping[cols[cand]] = "part"; break
    for i in range(1,4):
        for cand in [f"skill{i}", f"スキル{i}", f"スキル{i}名"]:
            if cand in cols: mapping[cols[cand]] = f"skill{i}"; break
        for cand in [f"lv{i}", f"Lv{i}", f"レベル{i}"]:
            if cand in cols: mapping[cols[cand]] = f"lv{i}"; break
    for i,cands in [(1,["slot1","スロ1","スロット1"]), (2,["slot2","スロ2","スロット2"]), (3,["slot3","スロ3","スロット3"])]:
        for cand in cands:
            if cand in cols: mapping[cols[cand]] = f"slot{i}"; break
    if mapping: df = df.rename(columns=mapping)
    if "part" in df.columns:
        df["part"] = df["part"].map(_normalize_part_value)
    return df

def normalize_decorations_df(df):
    if len(df)==0: return df
    cols = {c.strip():c for c in df.columns}
    mapping = {}
    for cand in ["name","装飾品名","名前"]:
        if cand in cols: mapping[cols[cand]] = "name"; break
    for cand in ["skill","スキル","skill_name"]:
        if cand in cols: mapping[cols[cand]] = "skill"; break
    for cand in ["lv","LV","レベル","level"]:
        if cand in cols: mapping[cols[cand]] = "lv"; break
    for cand in ["slot","スロ","スロット","slot_level"]:
        if cand in cols: mapping[cols[cand]] = "slot"; break
    for cand in ["count","所持数","個数","stock"]:
        if cand in cols: mapping[cols[cand]] = "count"; break
    if mapping: df = df.rename(columns=mapping)
    return df

def normalize_charms_owned_df(df):
    if len(df)==0: return df
    cols = {c.strip():c for c in df.columns}
    mapping = {}
    for cand in ["name","護石名","お守り名","名前"]:
        if cand in cols: mapping[cols[cand]] = "name"; break
    for i in range(1,3+1):
        for cand in [f"skill{i}", f"スキル{i}", f"スキル{i}名"]:
            if cand in cols: mapping[cols[cand]] = f"skill{i}"; break
        for cand in [f"lv{i}", f"Lv{i}", f"レベル{i}"]:
            if cand in cols: mapping[cols[cand]] = f"lv{i}"; break
    for i,cands in [(1,["slot1","スロ1","スロット1"]), (2,["slot2","スロ2","スロット2"]), (3,["slot3","スロ3","スロット3"])]:
        for cand in cands:
            if cand in cols: mapping[cols[cand]] = f"slot{i}"; break
    if mapping: df = df.rename(columns=mapping)
    return df

# =========================================================
# サイドバー：スプシ設定 & 読み込み
# =========================================================
st.sidebar.header("Googleスプレッドシート設定")
sheet_id = st.sidebar.text_input(
    "Sheet ID（/d/ と /edit の間の文字列）",
    value="",  # ここは空でOK。実運用でIDを入れてください。
    help="例: https://docs.google.com/spreadsheets/d/XXXXX/edit → XXXXX が Sheet ID"
)
st.sidebar.caption("※リンク共有は『リンクを知っている全員が閲覧可』にしてください。")

st.sidebar.markdown("**タブ名（シート名）**")
name_appraisal = st.sidebar.text_input("鑑定護石テーブル（talisman_ja）", value="talisman_ja")
name_groups    = st.sidebar.text_input("Group→スキル表（talisman_group_ja）", value="talisman_group_ja")
name_weapons   = st.sidebar.text_input("武器（weapons_ja）", value="weapons_ja")
name_armor     = st.sidebar.text_input("防具（armor_ja）", value="armor_ja")
name_decor     = st.sidebar.text_input("装飾品（decorations_ja）", value="decorations_ja")
name_targets   = st.sidebar.text_input("目標スキル（任意。なければ下の手入力を使用）", value="")
name_charms    = st.sidebar.text_input("配布用初期護石（任意）", value="")

use_sheets = st.sidebar.checkbox("上記スプレッドシートから読み込む（指定があれば優先）", value=True)

# CSVアップロードでの上書きも可能
st.sidebar.markdown("---")
st.sidebar.header("（任意）CSVで上書き")
up_weapons = st.sidebar.file_uploader("武器CSV", type=["csv"])
up_armor   = st.sidebar.file_uploader("防具CSV", type=["csv"])
up_decor   = st.sidebar.file_uploader("装飾品CSV", type=["csv"])
up_targets = st.sidebar.file_uploader("目標スキルCSV", type=["csv"])
up_groups  = st.sidebar.file_uploader("Group→スキルCSV", type=["csv"])
up_apprais = st.sidebar.file_uploader("鑑定護石テーブルCSV", type=["csv"])
up_charms  = st.sidebar.file_uploader("初期護石CSV", type=["csv"])

def _load_df(sheet_name, uploader):
    # 1) CSVアップロードがあれば最優先
    if uploader is not None:
        try:
            df = pd.read_csv(uploader)
            st.sidebar.caption(f"→ {sheet_name}: CSVで上書き読込中")
            return df
        except Exception as e:
            st.sidebar.caption(f"→ {sheet_name}: CSV読込失敗 ({e})")

    # 2) スプレッドシート直読
    if use_sheets and sheet_id and sheet_name:
        df = read_gsheet_csv_by_sheetname(sheet_id, sheet_name)
        if len(df):
            st.sidebar.caption(f"→ {sheet_name}: スプレッドシートから読込中")
            return df
        else:
            st.sidebar.caption(f"→ {sheet_name}: スプレッドシート読込失敗、サンプルにフォールバック")

    # 3) フォールバック（最小サンプル）
    st.sidebar.caption(f"→ {sheet_name}: サンプル使用中")
    if sheet_name == name_weapons:
        return pd.DataFrame([{"name":"太刀","slot1":1,"slot2":0,"slot3":0,"skill1":"見切り","lv1":2}])
    if sheet_name == name_armor:
        return pd.DataFrame([
            {"name":"頭A","part":"Head","skill1":"攻撃","lv1":2,"slot1":1,"slot2":0,"slot3":0},
            {"name":"胴A","part":"Chest","skill1":"見切り","lv1":1,"slot1":2,"slot2":0,"slot3":0},
            {"name":"腕A","part":"Arms","skill1":"体力","lv1":1,"slot1":1,"slot2":0,"slot3":0},
            {"name":"腰A","part":"Waist","skill1":"納刀術","lv1":1,"slot1":2,"slot2":0,"slot3":0},
            {"name":"脚A","part":"Legs","skill1":"体力","lv1":2,"slot1":1,"slot2":0,"slot3":0},
        ])
    if sheet_name == name_decor:
        return pd.DataFrame([
            {"name":"攻撃珠1","skill":"攻撃","lv":1,"slot":1,"count":"∞"},
            {"name":"見切り珠2","skill":"見切り","lv":1,"slot":2,"count":"∞"},
            {"name":"体力珠1","skill":"体力","lv":1,"slot":1,"count":"∞"},
        ])
    if sheet_name == name_targets:
        return pd.DataFrame([
            {"skill":"攻撃","target_level":4,"priority":1},
            {"skill":"見切り","target_level":3,"priority":2},
            {"skill":"体力","target_level":3,"priority":3},
        ])
    if sheet_name == name_groups:
        return pd.DataFrame([
            {"Group":10,"Skill Name":"弱点特効","Skill Level":1},
            {"Group":1,"Skill Name":"攻撃","Skill Level":1},
            {"Group":2,"Skill Name":"攻撃","Skill Level":2},
            {"Group":3,"Skill Name":"攻撃","Skill Level":3},
            {"Group":4,"Skill Name":"超会心","Skill Level":1},
        ])
    if sheet_name == name_appraisal:
        return pd.DataFrame([
            {"rarity":"RARE[8]","g1":4,"g2":1,"g3":1,"slots":"[W1,0] [W1,1] [W1,1,1]"},
            {"rarity":"RARE[8]","g1":3,"g2":10,"g3":"-","slots":"[W1,0] [W1,1] [W1,1,1]"},
            {"rarity":"RARE[7]","g1":3,"g2":10,"g3":"-","slots":"[1,0] [1,1] [2,0]"},
        ])
    if sheet_name == name_charms:
        return pd.DataFrame([
            {"name":"攻撃護石+1","skill1":"攻撃","lv1":1,"slot1":1,"slot2":0,"slot3":0},
            {"name":"見切り護石+2","skill1":"見切り","lv1":2,"slot1":1,"slot2":1,"slot3":0},
        ])
    return pd.DataFrame()

# 実読み込み
weapons_df = _load_df(name_weapons, up_weapons)
armor_df   = _load_df(name_armor,   up_armor)
decor_df   = _load_df(name_decor,   up_decor)
targets_df = _load_df(name_targets, up_targets) if name_targets else pd.DataFrame()
groups_df  = _load_df(name_groups,  up_groups)
apprais_df = _load_df(name_appraisal, up_apprais)
charms_df  = _load_df(name_charms,  up_charms) if name_charms else pd.DataFrame()

# 正規化
weapons_df = normalize_weapons_df(weapons_df)
armor_df   = normalize_armor_df(armor_df)
decor_df   = normalize_decorations_df(decor_df)
groups_df  = normalize_group_df(groups_df)
apprais_df = normalize_appraisal_df(apprais_df)
charms_df  = normalize_charms_owned_df(charms_df)

# =========================================================
# 画面：武器・防具・護石の選択
# =========================================================
st.sidebar.markdown("---")
st.sidebar.subheader("武器・装備の選択")

weapon_name = st.sidebar.selectbox("武器", weapons_df["name"].tolist() if "name" in weapons_df.columns and len(weapons_df) else ["太刀"])
sel_weapon = weapons_df[weapons_df["name"]==weapon_name].iloc[0].to_dict() if "name" in weapons_df.columns and len(weapons_df) else {"slot1":1,"slot2":0,"slot3":0,"skill1":"見切り","lv1":2}
wep_slots = [to_int(sel_weapon.get("slot1",0)), to_int(sel_weapon.get("slot2",0)), to_int(sel_weapon.get("slot3",0))]
weapon_l1_available = wep_slots.count(1)

parts = ["Head","Chest","Arms","Waist","Legs"]
selected_gear = {}
for p in parts:
    opts = armor_df[armor_df["part"]==p]["name"].tolist() if "part" in armor_df.columns else []
    if not opts:
        st.sidebar.warning(f"{p} の防具がテーブルにありません")
        continue
    choice = st.sidebar.selectbox(p, opts, key=f"part_{p}")
    selected_gear[p] = armor_df[(armor_df['part']==p) & (armor_df['name']==choice)].iloc[0].to_dict()

own_charm_opt = ["（未使用）"] + (charms_df["name"].tolist() if "name" in charms_df.columns and len(charms_df) else [])
own_charm_name = st.sidebar.selectbox("護石（所持）", own_charm_opt)
sel_own_charm = None if own_charm_name=="（未使用）" else charms_df[charms_df["name"]==own_charm_name].iloc[0].to_dict()

# =========================================================
# 目標スキル（Targets）入力（テーブルが無い時の手入力）
# =========================================================
st.sidebar.markdown("---")
st.sidebar.subheader("目標スキル（表が無いとき用）")
if len(targets_df)==0:
    st.sidebar.caption("下で手入力できます。priority: 1=必須, 2=下げても良い, 3=無くしても良い")
    if "targets_buf" not in st.session_state:
        st.session_state.targets_buf = pd.DataFrame([
            {"skill":"攻撃","target_level":4,"priority":1},
            {"skill":"見切り","target_level":3,"priority":2},
            {"skill":"体力","target_level":3,"priority":3},
        ])
    targets_df = st.data_editor(st.session_state.targets_buf, num_rows="dynamic", use_container_width=True)
    st.session_state.targets_buf = targets_df

# =========================================================
# 計算：所持護石での達成可否
# =========================================================
# ベーススキル合算
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

# 不足
req = {}
for _, r in targets_df.iterrows():
    need = int(r["target_level"]) - int(base_skills.get(r["skill"],0))
    if need>0:
        req[r["skill"]] = need

# スロット合算（W1対応）
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
            st.warning("所持護石では必須(P1)は満たせません。下の『鑑定護石の提案』を参照してください。")
        else:
            st.success("所持護石で必須(P1)は満たせます。")

# =========================================================
# 鑑定護石の提案（talisman_ja ＆ talisman_group_ja を使用）
# =========================================================
st.subheader("鑑定護石の提案（所持護石で不可のとき）")

if len(apprais_df)==0 or len(groups_df)==0:
    st.info("鑑定護石テーブル or Group→スキル表が不足しています。talisman_ja / talisman_group_ja を確認してください。")
else:
    # Group→スキル辞書
    group_map = defaultdict(list)
    for _, r in groups_df.iterrows():
        gid = to_int(r.get("Group",0),0)
        sname = str(r.get("Skill Name",""))
        slv = to_int(r.get("Skill Level",1),1)
        if gid and sname:
            group_map[gid].append((sname, slv))

    missing_skills = set(req.keys())

    def expand_appraisal_candidates(ac_df, missing_skills, limit_per_combo=50):
        cands = []
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
            combos = list(product(*(g if g else [("",0)] for g in pruned)))[:limit_per_combo]
            for (s1, s2, s3) in combos:
                skills = defaultdict(int)
                for s,lv in (s1,s2,s3):
                    if s:
                        skills[s]+=lv
                for pat in slot_patterns if slot_patterns else [[]]:
                    cands.append({"skills": dict(skills), "slot_tokens": pat, "row": row.to_dict()})
        return cands

    cands = expand_appraisal_candidates(apprais_df, missing_skills, limit_per_combo=60)

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

    # ソート：P1満たす > P2不足が少ない(=score大) > 余剰多い
    def key_func(r):
        hard = 1 if r["hard_fail"] else 0
        return ( -hard, r["score"], sum(v for _,v in r["surplus"]) )

    evaluated.sort(key=key_func, reverse=True)

    top_n = st.number_input("表示する提案数", min_value=1, max_value=50, value=10)
    if not evaluated:
        st.info("鑑定護石候補なし（talisman_group_ja / talisman_ja を確認してください）。")
    else:
        for i, r in enumerate(islice(evaluated, int(top_n))):
            with st.expander(
                f"提案#{i+1} | P1: {'OK' if not r['hard_fail'] else 'NG'} | スコア: {r['score']} "
                f"| cand技能: {r['skills_from_cand']} | スロット: {r['slot_tokens']}",
                expanded=(i==0)
            ):
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
