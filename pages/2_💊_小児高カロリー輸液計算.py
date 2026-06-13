import streamlit as st
import pandas as pd

st.set_page_config(page_title="小児高カロリー輸液計算", layout="wide")

st.title("💊 小児高カロリー輸液 成分計算ツール")

with st.expander("⚠️ 免責事項（必ずお読みください）", expanded=False):
    st.warning(
        "本ツールは医療従事者向けの参考情報提供を目的としています。"
        "記載の製剤成分値は概算であり、使用前に必ず最新の添付文書を確認してください。"
        "実際の処方は主治医の判断と責任のもとで行い、調製は薬剤師と連携して実施してください。"
        "Ca・P配合時の配合変化（沈殿形成）に十分注意してください。"
    )

# ─────────────────────────────────────────────────────────────
# 製剤データベース（1本あたりの成分量）
# ※値はメーカー添付文書に基づく概算値。使用前に添付文書を必ず確認すること。
# ─────────────────────────────────────────────────────────────
MAIN_PRODUCTS = {
    "グルアセト35 (250 mL/本)": {
        "vol": 250, "glucose": 87.5, "aa": 0.0, "fat": 0.0,
        "Na": 34.0, "K": 14.5, "Ca": 4.5, "Mg": 4.0, "P": 10.0,
    },
    "ハイカリックNC-N (700 mL/本)": {
        "vol": 700, "glucose": 175.0, "aa": 30.0, "fat": 0.0,
        "Na": 35.0, "K": 20.0, "Ca": 4.5, "Mg": 5.0, "P": 10.0,
    },
    "ハイカリックNC-L (700 mL/本)": {
        "vol": 700, "glucose": 200.0, "aa": 30.0, "fat": 0.0,
        "Na": 35.0, "K": 20.0, "Ca": 4.5, "Mg": 5.0, "P": 10.0,
    },
    "フルカリック1号 (903 mL/本)": {
        "vol": 903, "glucose": 150.0, "aa": 20.0, "fat": 20.0,
        "Na": 35.0, "K": 20.0, "Ca": 5.0, "Mg": 4.0, "P": 10.0,
    },
    "フルカリック2号 (1103 mL/本)": {
        "vol": 1103, "glucose": 200.0, "aa": 40.0, "fat": 30.0,
        "Na": 50.0, "K": 27.0, "Ca": 7.5, "Mg": 6.0, "P": 15.0,
    },
    "フルカリック3号 (1103 mL/本)": {
        "vol": 1103, "glucose": 250.0, "aa": 60.0, "fat": 40.0,
        "Na": 60.0, "K": 34.0, "Ca": 10.0, "Mg": 8.0, "P": 20.0,
    },
}

AA_OPTIONS = {
    "なし": {"vol": 200, "aa": 0.0, "Na": 0.0, "K": 0.0, "Ca": 0.0, "Mg": 0.0, "P": 0.0},
    "プレアミンP 10% (200 mL/本)": {
        "vol": 200, "aa": 20.0, "Na": 4.0, "K": 3.0, "Ca": 0.0, "Mg": 0.0, "P": 0.0,
    },
    "アミパレン 10% (200 mL/本)": {
        "vol": 200, "aa": 20.0, "Na": 0.0, "K": 0.0, "Ca": 0.0, "Mg": 0.0, "P": 0.0,
    },
    "モリプロン F 10% (200 mL/本)": {
        "vol": 200, "aa": 20.0, "Na": 0.0, "K": 0.0, "Ca": 0.0, "Mg": 0.0, "P": 0.0,
    },
}

# 年齢別推奨参考値（/kg/日）
# 出典: ESPGHAN/ESPEN/ESPR/CSPEN ガイドライン (2018)、日本静脈経腸栄養学会ガイドライン
AGE_REFS = {
    "早産児": {
        "fluid": (120, 180), "kcal": (100, 120), "aa": (3.0, 4.0),
        "Na": (3.0, 5.0), "K": (2.0, 4.0), "Ca": (1.0, 3.0), "P": (1.5, 2.5),
        "Mg": (0.2, 0.3), "GIR": (4, 10),
    },
    "正期産新生児 (0〜1ヶ月)": {
        "fluid": (100, 150), "kcal": (90, 110), "aa": (2.5, 3.5),
        "Na": (2.0, 4.0), "K": (2.0, 3.0), "Ca": (1.0, 2.0), "P": (1.0, 2.0),
        "Mg": (0.2, 0.3), "GIR": (4, 8),
    },
    "乳児 (1〜12ヶ月)": {
        "fluid": (100, 150), "kcal": (90, 110), "aa": (2.0, 3.0),
        "Na": (2.0, 4.0), "K": (2.0, 3.0), "Ca": (0.5, 1.5), "P": (0.5, 1.5),
        "Mg": (0.2, 0.4), "GIR": (3, 8),
    },
    "幼児 (1〜3歳)": {
        "fluid": (80, 100), "kcal": (75, 90), "aa": (1.5, 2.5),
        "Na": (2.0, 3.0), "K": (2.0, 3.0), "Ca": (0.5, 1.0), "P": (0.5, 1.0),
        "Mg": (0.2, 0.4), "GIR": (3, 6),
    },
    "学童 (3〜10歳)": {
        "fluid": (60, 80), "kcal": (60, 75), "aa": (1.0, 2.0),
        "Na": (1.5, 3.0), "K": (1.5, 3.0), "Ca": (0.2, 0.5), "P": (0.2, 0.5),
        "Mg": (0.1, 0.3), "GIR": (2, 5),
    },
    "思春期 (10歳以上)": {
        "fluid": (50, 60), "kcal": (50, 60), "aa": (0.8, 1.5),
        "Na": (1.0, 2.0), "K": (1.0, 2.0), "Ca": (0.2, 0.5), "P": (0.2, 0.5),
        "Mg": (0.1, 0.3), "GIR": (2, 4),
    },
}

# 電解質補正液の標準濃度
ADDITIVES = {
    "10% NaCl": {"Na_per_mL": 1.71, "K": 0, "Ca": 0, "Mg": 0, "P": 0, "Na_extra": 0},
    "KCl (2 mEq/mL)": {"Na_per_mL": 0, "K": 2.0, "Ca": 0, "Mg": 0, "P": 0, "Na_extra": 0},
    "グルコン酸Ca 10%": {"Na_per_mL": 0, "K": 0, "Ca": 0.45, "Mg": 0, "P": 0, "Na_extra": 0},
    "リン酸Na液 (1 mmol P/mL)": {"Na_per_mL": 2.0, "K": 0, "Ca": 0, "Mg": 0, "P": 1.0, "Na_extra": 0},
    "MgSO4 (1 mEq/mL)": {"Na_per_mL": 0, "K": 0, "Ca": 0, "Mg": 1.0, "P": 0, "Na_extra": 0},
}


def status_icon(val_per_kg: float, lo: float, hi: float) -> str:
    if val_per_kg < lo * 0.8:
        return "🔴 不足"
    elif val_per_kg > hi * 1.2:
        return "🔴 過剰"
    elif val_per_kg < lo:
        return "🟡 やや不足"
    elif val_per_kg > hi:
        return "🟡 やや過剰"
    else:
        return "🟢 適正"


# ─────────────────────────────────────────────────────────────
# サイドバー：患者情報
# ─────────────────────────────────────────────────────────────
st.sidebar.header("【患者情報】")
weight = st.sidebar.number_input("体重 (kg)", min_value=0.3, max_value=150.0, value=10.0, step=0.1)
age_group = st.sidebar.selectbox("年齢区分", list(AGE_REFS.keys()), index=2)
ref = AGE_REFS[age_group]

st.sidebar.markdown("---")
st.sidebar.markdown("**推奨輸液量（参考）**")
st.sidebar.markdown(
    f"🔹 {ref['fluid'][0]*weight:.0f} 〜 {ref['fluid'][1]*weight:.0f} mL/日"
)
st.sidebar.markdown("**推奨カロリー（参考）**")
st.sidebar.markdown(
    f"🔹 {ref['kcal'][0]*weight:.0f} 〜 {ref['kcal'][1]*weight:.0f} kcal/日"
)
st.sidebar.markdown("**推奨アミノ酸（参考）**")
st.sidebar.markdown(
    f"🔹 {ref['aa'][0]*weight:.1f} 〜 {ref['aa'][1]*weight:.1f} g/日"
)
st.sidebar.markdown("**推奨GIR（参考）**")
st.sidebar.markdown(f"🔹 {ref['GIR'][0]} 〜 {ref['GIR'][1]} mg/kg/min")

# ─────────────────────────────────────────────────────────────
# 【1】目標量参考値テーブル
# ─────────────────────────────────────────────────────────────
st.header("【1】 目標成分量（参考値）")

ref_rows = [
    ("輸液量",   "mL/kg/日",    ref["fluid"], weight),
    ("カロリー", "kcal/kg/日",  ref["kcal"],  weight),
    ("アミノ酸", "g/kg/日",     ref["aa"],    weight),
    ("GIR",      "mg/kg/min",   ref["GIR"],   1),
    ("Na",       "mEq/kg/日",   ref["Na"],    weight),
    ("K",        "mEq/kg/日",   ref["K"],     weight),
    ("Ca",       "mEq/kg/日",   ref["Ca"],    weight),
    ("P",        "mmol/kg/日",  ref["P"],     weight),
    ("Mg",       "mEq/kg/日",   ref["Mg"],    weight),
]
ref_df = pd.DataFrame([
    {
        "成分": name,
        "単位": unit,
        f"目標 (min)": lo,
        f"目標 (max)": hi,
        f"絶対量 min ({weight} kg)": round(lo * mult, 1),
        f"絶対量 max ({weight} kg)": round(hi * mult, 1),
    }
    for name, unit, (lo, hi), mult in ref_rows
])
st.dataframe(ref_df, hide_index=True, use_container_width=True)

st.divider()

# ─────────────────────────────────────────────────────────────
# 【2】製剤・補液の設定
# ─────────────────────────────────────────────────────────────
st.header("【2】 製剤・補液の設定")

col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("主製剤")
    prod_name = st.selectbox("製剤を選択", list(MAIN_PRODUCTS.keys()))
    prod = MAIN_PRODUCTS[prod_name]

    input_mode = st.radio("投与量の入力方法", ["mL/日で指定", "本数で指定"], horizontal=True, key="main_mode")
    if input_mode == "mL/日で指定":
        prod_vol = float(st.number_input(
            f"使用量 (mL/日)　※1本 = {prod['vol']} mL",
            min_value=0, max_value=int(prod["vol"] * 3), value=int(prod["vol"]), step=10,
        ))
    else:
        bags = st.number_input("本数 (本/日)", min_value=0.0, max_value=5.0, value=1.0, step=0.25)
        prod_vol = bags * prod["vol"]
        st.markdown(f"→ **{prod_vol:.0f} mL/日**")

    # アミノ酸製剤（グルアセト35使用時のみ必要）
    aa_vol = 0.0
    aa_sol = AA_OPTIONS["なし"]
    aa_name = "なし"
    if "グルアセト35" in prod_name:
        st.markdown("---")
        st.subheader("アミノ酸製剤")
        st.info("グルアセト35にはアミノ酸が含まれません。別途アミノ酸製剤を追加してください。")
        aa_name = st.selectbox("アミノ酸製剤を選択", list(AA_OPTIONS.keys()))
        aa_sol = AA_OPTIONS[aa_name]
        if aa_name != "なし":
            aa_mode = st.radio("投与量", ["mL/日で指定", "本数で指定"], horizontal=True, key="aa_mode")
            if aa_mode == "mL/日で指定":
                aa_vol = float(st.number_input(
                    f"使用量 (mL/日)　※1本 = {aa_sol['vol']} mL",
                    min_value=0, max_value=int(aa_sol["vol"] * 3), value=int(aa_sol["vol"]), step=10,
                    key="aa_vol",
                ))
            else:
                aa_bags = st.number_input("本数", min_value=0.0, max_value=5.0, value=1.0, step=0.25, key="aa_bags")
                aa_vol = aa_bags * aa_sol["vol"]
                st.markdown(f"→ **{aa_vol:.0f} mL/日**")

    st.markdown("---")
    st.subheader("希釈液（任意）")
    tg5_vol = float(st.number_input("5%ブドウ糖液 (mL/日)", min_value=0, max_value=2000, value=0, step=10))
    ns_vol = float(st.number_input("生理食塩液 0.9% (mL/日)", min_value=0, max_value=1000, value=0, step=10))

with col_right:
    st.subheader("電解質補正液")
    st.markdown("各補正液の量（mL/日）を入力してください。")

    st.markdown("##### 10% NaCl　[1.71 mEq Na/mL]")
    nacl_ml = st.number_input("mL/日", min_value=0.0, max_value=100.0, value=0.0, step=0.5, key="nacl")

    st.markdown("##### KCl 2 mEq/mL　[2.0 mEq K/mL]")
    kcl_ml = st.number_input("mL/日", min_value=0.0, max_value=50.0, value=0.0, step=0.5, key="kcl")

    st.markdown("##### グルコン酸Ca 10%　[0.45 mEq Ca/mL]")
    ca_ml = st.number_input("mL/日", min_value=0.0, max_value=50.0, value=0.0, step=0.5, key="ca")

    st.markdown("##### リン酸Na液　[1.0 mmol P + 2.0 mEq Na/mL]")
    p_ml = st.number_input("mL/日", min_value=0.0, max_value=50.0, value=0.0, step=0.5, key="phos")

    st.markdown("##### MgSO4 1 mEq/mL（希釈後）　[1.0 mEq Mg/mL]")
    mg_ml = st.number_input("mL/日", min_value=0.0, max_value=30.0, value=0.0, step=0.5, key="mg")

st.divider()

# ─────────────────────────────────────────────────────────────
# 計算
# ─────────────────────────────────────────────────────────────
p_ratio = prod_vol / prod["vol"] if prod["vol"] > 0 else 0.0
aa_ratio = (aa_vol / aa_sol["vol"]) if (aa_sol["vol"] > 0 and aa_name != "なし") else 0.0

t_glucose = prod["glucose"] * p_ratio + tg5_vol * 0.05
t_aa   = prod["aa"] * p_ratio   + aa_sol["aa"] * aa_ratio
t_fat  = prod["fat"] * p_ratio
t_Na   = (prod["Na"] * p_ratio + aa_sol["Na"] * aa_ratio
          + nacl_ml * 1.71 + p_ml * 2.0 + ns_vol * 0.154)
t_K    = prod["K"] * p_ratio + aa_sol["K"] * aa_ratio + kcl_ml * 2.0
t_Ca   = prod["Ca"] * p_ratio + aa_sol["Ca"] * aa_ratio + ca_ml * 0.45
t_Mg   = prod["Mg"] * p_ratio + aa_sol["Mg"] * aa_ratio + mg_ml * 1.0
t_P    = prod["P"] * p_ratio + aa_sol["P"] * aa_ratio + p_ml * 1.0
t_kcal = t_glucose * 3.4 + t_aa * 4.0 + t_fat * 9.0
t_vol  = prod_vol + aa_vol + tg5_vol + ns_vol + nacl_ml + kcl_ml + ca_ml + p_ml + mg_ml
GIR    = (t_glucose * 1000 / 1440 / weight) if weight > 0 else 0.0

# ─────────────────────────────────────────────────────────────
# 【3】計算結果
# ─────────────────────────────────────────────────────────────
st.header("【3】 計算結果")

# サマリーメトリクス
mc1, mc2, mc3, mc4, mc5 = st.columns(5)
mc1.metric("総輸液量",   f"{t_vol:.0f} mL/日",    f"{t_vol/weight:.1f} mL/kg/日")
mc2.metric("総カロリー", f"{t_kcal:.0f} kcal/日", f"{t_kcal/weight:.1f} kcal/kg/日")
mc3.metric("アミノ酸",   f"{t_aa:.1f} g/日",      f"{t_aa/weight:.2f} g/kg/日")
mc4.metric("糖質",       f"{t_glucose:.1f} g/日", f"GIR: {GIR:.2f} mg/kg/min")
mc5.metric("脂質",       f"{t_fat:.1f} g/日",     f"{t_fat/weight:.2f} g/kg/日")

# GIR アラート
gir_lo, gir_hi = ref["GIR"]
if GIR > gir_hi * 1.1:
    st.error(
        f"⚠️ GIR ({GIR:.2f} mg/kg/min) が推奨上限 ({gir_hi} mg/kg/min) を大幅に超えています！"
        "高血糖・脂肪肝に注意し、糖質量を減らしてください。"
    )
elif GIR > gir_hi:
    st.warning(f"🟡 GIR ({GIR:.2f} mg/kg/min) がやや高めです (推奨上限: {gir_hi} mg/kg/min)。血糖モニタリングを強化してください。")
elif GIR < gir_lo and t_glucose > 0:
    st.info(f"ℹ️ GIR ({GIR:.2f} mg/kg/min) が推奨下限 ({gir_lo} mg/kg/min) 未満です。糖質量の増加を検討してください。")

# CaP 配合変化チェック
if t_vol > 0 and (t_Ca > 0 or t_P > 0):
    ca_conc = t_Ca / t_vol * 1000   # mEq/L
    p_conc  = t_P  / t_vol * 1000   # mmol/L
    cap_product = ca_conc * p_conc
    if cap_product > 150:
        st.error(
            f"⚠️ Ca×P積 = Ca {ca_conc:.1f} mEq/L × P {p_conc:.1f} mmol/L = **{cap_product:.0f}** (>150)。"
            "沈殿形成リスクあり。有機リン酸（グリセロリン酸）の使用、Ca・P投与ラインの分離、"
            "または薬剤師への相談を検討してください。"
        )
    elif cap_product > 100:
        st.warning(
            f"🟡 Ca×P積 = {cap_product:.0f} (100〜150)。配合変化に注意し、薬剤師と相談してください。"
        )

st.markdown("---")

# 成分別詳細テーブル
def make_row(name, unit, actual, lo, hi, w):
    per_kg = actual / w if w > 0 else 0
    return {
        "成分": name,
        "単位 (/日)": unit,
        "投与量/日": round(actual, 2),
        "/kg/日": round(per_kg, 2),
        "目標 min (/kg)": lo,
        "目標 max (/kg)": hi,
        "判定": status_icon(per_kg, lo, hi),
    }

rows = [
    make_row("輸液量",   "mL",   t_vol,   *ref["fluid"], weight),
    make_row("カロリー", "kcal", t_kcal,  *ref["kcal"],  weight),
    make_row("アミノ酸", "g",    t_aa,    *ref["aa"],    weight),
    make_row("Na",       "mEq",  t_Na,    *ref["Na"],    weight),
    make_row("K",        "mEq",  t_K,     *ref["K"],     weight),
    make_row("Ca",       "mEq",  t_Ca,    *ref["Ca"],    weight),
    make_row("P",        "mmol", t_P,     *ref["P"],     weight),
    make_row("Mg",       "mEq",  t_Mg,    *ref["Mg"],    weight),
]
results_df = pd.DataFrame(rows)
st.dataframe(results_df, hide_index=True, use_container_width=True)

# GIR詳細
st.markdown("---")
col_g, col_f = st.columns(2)
with col_g:
    st.subheader("GIR (Glucose Infusion Rate)")
    st.markdown(f"**GIR = {GIR:.2f} mg/kg/min**")
    st.markdown(f"推奨範囲: {ref['GIR'][0]} 〜 {ref['GIR'][1]} mg/kg/min")
    st.markdown(
        "```\n"
        f"GIR = 糖質 {t_glucose:.1f} g × 1000 ÷ 1440 min ÷ {weight} kg\n"
        f"    = {GIR:.2f} mg/kg/min\n"
        "```"
    )
with col_f:
    st.subheader("エネルギー内訳")
    kcal_glc = t_glucose * 3.4
    kcal_aa  = t_aa * 4.0
    kcal_fat = t_fat * 9.0
    st.markdown(f"- 糖質:   {kcal_glc:.0f} kcal  ({t_glucose:.1f} g × 3.4)")
    st.markdown(f"- アミノ酸: {kcal_aa:.0f} kcal  ({t_aa:.1f} g × 4.0)")
    st.markdown(f"- 脂質:   {kcal_fat:.0f} kcal  ({t_fat:.1f} g × 9.0)")
    st.markdown(f"- **合計: {t_kcal:.0f} kcal/日**")
    if t_fat > 0:
        npc_kcal = kcal_glc + kcal_fat
        npc_ratio = npc_kcal / (t_aa * 0.16 * 6.25) if t_aa > 0 else 0
        st.markdown(f"- NPC/N比: {npc_ratio:.0f}  (目標: 150〜250)")

# ─────────────────────────────────────────────────────────────
# 参考情報
# ─────────────────────────────────────────────────────────────
st.divider()
with st.expander("製剤成分一覧（概算値・添付文書で要確認）"):
    prod_table = pd.DataFrame([
        {"製剤": k, "容量(mL)": v["vol"], "糖質(g)": v["glucose"],
         "AA(g)": v["aa"], "脂質(g)": v["fat"],
         "Na(mEq)": v["Na"], "K(mEq)": v["K"],
         "Ca(mEq)": v["Ca"], "Mg(mEq)": v["Mg"], "P(mmol)": v["P"]}
        for k, v in MAIN_PRODUCTS.items()
    ])
    st.dataframe(prod_table, hide_index=True, use_container_width=True)

with st.expander("参考ガイドライン・文献"):
    st.markdown("""
**推奨参考値の出典**
1. Jochum F, et al. ESPGHAN/ESPEN/ESPR/CSPEN guidelines on pediatric parenteral nutrition. *Clin Nutr.* 2018.
2. 日本静脈経腸栄養学会. 静脈経腸栄養ガイドライン 第3版. 2013.
3. Koletzko B, et al. 1. Guidelines on Paediatric Parenteral Nutrition of the ESPGHAN. *J Pediatr Gastroenterol Nutr.* 2005.
4. ASPEN Pediatric Nutrition Support Core Curriculum, 2nd Ed.

**電解質補正液の標準濃度（本ツールで使用）**
| 製剤 | 濃度 |
|------|------|
| 10% NaCl | Na 1.71 mEq/mL |
| KCl 注射液 | K 2.0 mEq/mL |
| グルコン酸Ca 10% | Ca 0.45 mEq/mL |
| リン酸Na液 | P 1.0 mmol/mL、Na 2.0 mEq/mL |
| MgSO4（希釈後） | Mg 1.0 mEq/mL |

**Ca・P配合変化について**

Ca (mEq/L) × P (mmol/L) > **150** で沈殿形成リスクあり。
有機リン酸（グリセロリン酸Na）の使用、またはCa・Pを分離投与することを検討してください。
""")
