import streamlit as st
import pandas as pd
from collections import defaultdict, Counter
from itertools import product, islice
import re

st.set_page_config(page_title="MHWilds 補助シミュ（JP列名対応）", layout="wide")
st.title("MHWilds 補助シミュレーター（護石提案）— JP列名自動対応版")

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
    for _, row in decorations_df.iterrows():
        skill = str(row["ski]()
