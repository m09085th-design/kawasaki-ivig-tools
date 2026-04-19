import streamlit as st
import pandas as pd

# ページ設定
st.set_page_config(page_title="川崎病 IVIg不応予測ツール", layout="wide")

st.title("川崎病 IVIg不応予測計算ツール")
st.markdown("各検査値を入力すると、3種類の主要な予測スコアを自動算出します。")

# --- サイドバー：データ入力 ---
st.sidebar.header("【1】患者データ入力")
age_months = st.sidebar.number_input("月齢 (ヶ月)", min_value=0, value=12)
illness_day = st.sidebar.number_input("治療開始病日 (日)", min_value=1, max_value=20, value=4)
ast = st.sidebar.number_input("AST (IU/L)", min_value=0, value=100)
alt = st.sidebar.number_input("ALT (IU/L)", min_value=0, value=80)
crp = st.sidebar.number_input("CRP (mg/dL)", min_value=0.0, value=10.0, step=0.1)
plt = st.sidebar.number_input("血小板数 (x 10^4/μL)", min_value=0.0, value=25.0, step=0.1)
na = st.sidebar.number_input("血清Na値 (mmol/L)", min_value=100, value=133)
neutro = st.sidebar.number_input("好中球分画 (%)", min_value=0, max_value=100, value=85)
t_bil = st.sidebar.number_input("総ビリルビン (mg/dL)", min_value=0.0, value=1.0, step=0.1)

# --- スコア計算ロジック ---

# 1. 群馬スコア (Kobayashi Score) - RAISE基準
# 項目: Na<=133(2), 病日<=4(2), AST>=100(2), 好中球>=80(2), CRP>=10(1), 月齢<=12(1), PLT<=30(1)
gunma_score = 0
gunma_score += 2 if na <= 133 else 0
gunma_score += 2 if illness_day <= 4 else 0
gunma_score += 2 if ast >= 100 else 0
gunma_score += 2 if neutro >= 80 else 0
gunma_score += 1 if crp >= 10 else 0
gunma_score += 1 if age_months <= 12 else 0
gunma_score += 1 if plt <= 30 else 0
gunma_judge = "High Risk" if gunma_score >= 5 else "-"

# 2. 久留米スコア (Egami Score)
# 項目: 月齢<6(1), 病日<=4(1), PLT<=30(1), CRP>=8(1), ALT>=80(2)
kurume_score = 0
kurume_score += 1 if age_months < 6 else 0
kurume_score += 1 if illness_day <= 4 else 0
kurume_score += 1 if plt <= 30 else 0
kurume_score += 1 if crp >= 8 else 0
kurume_score += 2 if alt >= 80 else 0
kurume_judge = "High Risk" if kurume_score >= 3 else "-"

# 3. 大阪スコア (Sano Score)
# 項目: AST>=200(1), T-Bil>=0.9(1), CRP>=7(1)
osaka_score = 0
osaka_score += 1 if ast >= 200 else 0
osaka_score += 1 if t_bil >= 0.9 else 0
osaka_score += 1 if crp >= 7 else 0
osaka_judge = "High Risk" if osaka_score >= 2 else "-"

# --- メイン画面：結果表示 ---
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("群馬スコア (Kobayashi)")
    st.metric("Score", f"{gunma_score} 点")
    st.write(f"判定: **{gunma_judge}**")
    st.caption("カットオフ: 5点以上 (RAISE)")

with col2:
    st.subheader("久留米スコア (Egami)")
    st.metric("Score", f"{kurume_score} 点")
    st.write(f"判定: **{kurume_judge}**")
    st.caption("カットオフ: 3点以上")

with col3:
    st.subheader("大阪スコア (Sano)")
    st.metric("Score", f"{osaka_score} 点")
    st.write(f"判定: **{osaka_judge}**")
    st.caption("カットオフ: 2点以上")

# --- 文献情報の表示 ---
st.divider()
st.subheader("参考文献")
st.markdown("""
1. **Kobayashi T, et al.** Lancet. 2012;379(9826):1613-20. (RAISE study / 群馬スコア)
2. **Egami K, et al.** J Pediatr. 2006;149(2):237-40. (久留米スコア)
3. **Sano T, et al.** Eur J Pediatr. 2007;166(2):131-7. (大阪スコア)
""")