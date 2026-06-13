#!/usr/bin/env python3
"""小児高カロリー輸液計算 Excelファイル生成スクリプト"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule

# ── データ定義 ──────────────────────────────────────────
AGE_REF_DATA = [
    # name, fluid_min,max, kcal_min,max, aa_min,max, Na_min,max, K_min,max,
    # Ca_min,max, P_min,max, Mg_min,max, GIR_min,max
    ("早産児",               120,180,100,120,3.0,4.0,3.0,5.0,2.0,4.0,1.0,3.0,1.5,2.5,0.2,0.3,4,10),
    ("正期産新生児(0〜1ヶ月)",100,150, 90,110,2.5,3.5,2.0,4.0,2.0,3.0,1.0,2.0,1.0,2.0,0.2,0.3,4, 8),
    ("乳児(1〜12ヶ月)",      100,150, 90,110,2.0,3.0,2.0,4.0,2.0,3.0,0.5,1.5,0.5,1.5,0.2,0.4,3, 8),
    ("幼児(1〜3歳)",          80,100, 75, 90,1.5,2.5,2.0,3.0,2.0,3.0,0.5,1.0,0.5,1.0,0.2,0.4,3, 6),
    ("学童(3〜10歳)",         60, 80, 60, 75,1.0,2.0,1.5,3.0,1.5,3.0,0.2,0.5,0.2,0.5,0.1,0.3,2, 5),
    ("思春期(10歳以上)",      50, 60, 50, 60,0.8,1.5,1.0,2.0,1.0,2.0,0.2,0.5,0.2,0.5,0.1,0.3,2, 4),
]

PROD_DATA = [
    # name, vol, glucose, aa, fat, Na, K, Ca, Mg, P
    ("グルアセト35(250mL/本)",      250, 87.5, 0.0, 0.0,34.0,14.5, 4.5, 4.0,10.0),
    ("ハイカリックNC-N(700mL/本)",  700,175.0,30.0, 0.0,35.0,20.0, 4.5, 5.0,10.0),
    ("ハイカリックNC-L(700mL/本)",  700,200.0,30.0, 0.0,35.0,20.0, 4.5, 5.0,10.0),
    ("フルカリック1号(903mL/本)",   903,150.0,20.0,20.0,35.0,20.0, 5.0, 4.0,10.0),
    ("フルカリック2号(1103mL/本)", 1103,200.0,40.0,30.0,50.0,27.0, 7.5, 6.0,15.0),
    ("フルカリック3号(1103mL/本)", 1103,250.0,60.0,40.0,60.0,34.0,10.0, 8.0,20.0),
]

AA_DATA = [
    # name, vol, aa, Na, K  (vol=1 for "なし" to avoid div/0)
    ("なし",                       1, 0.0, 0.0, 0.0),
    ("プレアミンP 10%(200mL/本)",200,20.0, 4.0, 3.0),
    ("アミパレン 10%(200mL/本)", 200,20.0, 0.0, 0.0),
    ("モリプロンF 10%(200mL/本)",200,20.0, 0.0, 0.0),
]

# ── スタイルユーティリティ ──────────────────────────────
def fill(hex_c):
    return PatternFill(start_color=hex_c, end_color=hex_c, fill_type="solid")

def border():
    t = Side(style="thin")
    return Border(left=t, right=t, top=t, bottom=t)

def meiryo(size=10, bold=False, color="000000", italic=False):
    return Font(name="Meiryo", size=size, bold=bold, color=color, italic=italic)

def center(wrap=False):
    return Alignment(horizontal="center", vertical="center", wrap_text=wrap)

def right_align():
    return Alignment(horizontal="right", vertical="center")

def apply_header(cell, text, bg="2E4057", fg="FFFFFF", size=11):
    cell.value = text
    cell.font = meiryo(size=size, bold=True, color=fg)
    cell.fill = fill(bg)
    cell.alignment = center()
    cell.border = border()

def apply_section(ws, row, text, bg="4A90D9", cols=7):
    ws.merge_cells(f"A{row}:{chr(64+cols)}{row}")
    c = ws.cell(row=row, column=1)
    c.value = text
    c.font = meiryo(size=11, bold=True, color="FFFFFF")
    c.fill = fill(bg)
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[row].height = 22

def apply_label(cell, text):
    cell.value = text
    cell.font = meiryo(size=10)
    cell.alignment = right_align()
    cell.border = border()

def apply_input(cell, val=0, fmt=None):
    cell.value = val
    cell.font = meiryo(size=11, bold=True, color="1A237E")
    cell.fill = fill("FFF9C4")
    cell.alignment = center()
    cell.border = border()
    if fmt:
        cell.number_format = fmt

def apply_calc(cell, formula=None, fmt="0.00"):
    if formula:
        cell.value = formula
    cell.font = meiryo(size=10)
    cell.fill = fill("E3F2FD")
    cell.alignment = center()
    cell.border = border()
    if fmt:
        cell.number_format = fmt

def apply_ref(cell, formula=None, fmt="0.0"):
    if formula:
        cell.value = formula
    cell.font = meiryo(size=10, color="1B5E20")
    cell.fill = fill("E8F5E9")
    cell.alignment = center()
    cell.border = border()
    if fmt:
        cell.number_format = fmt

def note(cell, text):
    cell.value = text
    cell.font = meiryo(size=9, color="757575", italic=True)
    cell.alignment = Alignment(horizontal="left", vertical="center")

# ── ワークブック作成 ────────────────────────────────────
wb = openpyxl.Workbook()

# ── Sheet: 年齢参考値 ──
ws_age = wb.active
ws_age.title = "年齢参考値"
age_cols = ["年齢区分","輸液min","輸液max","kcalmin","kcalmax",
            "AAmin","AAmax","Namin","Namax","Kmin","Kmax",
            "Camin","Camax","Pmin","Pmax","Mgmin","Mgmax","GIRmin","GIRmax"]
for c, h in enumerate(age_cols, 1):
    ws_age.cell(row=1, column=c).value = h
for r, row in enumerate(AGE_REF_DATA, 2):
    for c, v in enumerate(row, 1):
        ws_age.cell(row=r, column=c).value = v

# ── Sheet: 製剤データ ──
ws_prod = wb.create_sheet("製剤データ")
prod_cols = ["製剤名","容量mL","糖質g","AAg","脂質g","Na","K","Ca","Mg","P"]
for c, h in enumerate(prod_cols, 1):
    ws_prod.cell(row=1, column=c).value = h
for r, row in enumerate(PROD_DATA, 2):
    for c, v in enumerate(row, 1):
        ws_prod.cell(row=r, column=c).value = v

# ── Sheet: アミノ酸製剤 ──
ws_aa = wb.create_sheet("アミノ酸製剤")
for c, h in enumerate(["製剤名","容量mL","AAg","Na","K"], 1):
    ws_aa.cell(row=1, column=c).value = h
for r, row in enumerate(AA_DATA, 2):
    for c, v in enumerate(row, 1):
        ws_aa.cell(row=r, column=c).value = v

# ── Sheet: 計算シート (main) ──
ws = wb.create_sheet("計算シート", 0)

# 列幅
ws.column_dimensions["A"].width = 30
ws.column_dimensions["B"].width = 32
ws.column_dimensions["C"].width = 14
ws.column_dimensions["D"].width = 14
ws.column_dimensions["E"].width = 14
ws.column_dimensions["F"].width = 14
ws.column_dimensions["G"].width = 16

# ── タイトル (rows 1-2) ──
ws.merge_cells("A1:G1")
ws.row_dimensions[1].height = 36
c = ws["A1"]
c.value = "小児高カロリー輸液 成分計算ツール"
c.font = meiryo(size=16, bold=True, color="FFFFFF")
c.fill = fill("1A237E")
c.alignment = center()

ws.merge_cells("A2:G2")
ws.row_dimensions[2].height = 20
c = ws["A2"]
c.value = "⚠ 成分値は概算です。使用前に必ず添付文書を確認し、医師・薬剤師と連携して処方してください。"
c.font = meiryo(size=9, color="B71C1C", italic=True)
c.fill = fill("FFEBEE")
c.alignment = center()

# ── 【患者情報】 (rows 4-6) ──
apply_section(ws, 4, "■ 患者情報", bg="37474F")

apply_label(ws["A5"], "体重 (kg)")
apply_input(ws["B5"], val=10.0, fmt="0.0")
note(ws["C5"], "kg")

apply_label(ws["A6"], "年齢区分")
apply_input(ws["B6"], val="乳児(1〜12ヶ月)")
note(ws["C6"], "↑ セルをクリックしてリストから選択")

age_names = [r[0] for r in AGE_REF_DATA]
dv_age = DataValidation(type="list", formula1='"' + ",".join(age_names) + '"', allow_blank=False)
ws.add_data_validation(dv_age)
dv_age.add(ws["B6"])

# ── 【目標量】 (rows 8-18) ──
apply_section(ws, 8, "■ 目標成分量（参考値）", bg="455A64")

for c, h in enumerate(["成分","単位(/kg/日)","目標 最小","目標 最大","絶対量 最小","絶対量 最大","絶対単位"],1):
    apply_header(ws.cell(row=9, column=c), h, bg="546E7A", size=10)

# ref_items: (label, unit_per_kg, col_min, col_max, abs_unit)
ref_items = [
    ("輸液量",   "mL/kg/日",    2,  3,  "mL/日"),
    ("カロリー", "kcal/kg/日",  4,  5,  "kcal/日"),
    ("アミノ酸", "g/kg/日",     6,  7,  "g/日"),
    ("Na",       "mEq/kg/日",   8,  9,  "mEq/日"),
    ("K",        "mEq/kg/日",   10, 11, "mEq/日"),
    ("Ca",       "mEq/kg/日",   12, 13, "mEq/日"),
    ("P",        "mmol/kg/日",  14, 15, "mmol/日"),
    ("Mg",       "mEq/kg/日",   16, 17, "mEq/日"),
    ("GIR",      "mg/kg/min",   18, 19, "mg/kg/min"),
]
REF_START = 10
ref_row_map = {}  # label -> row number

for i, (lbl, unit, cmin, cmax, abs_unit) in enumerate(ref_items):
    r = REF_START + i
    ref_row_map[lbl] = r

    apply_label(ws.cell(row=r, column=1), lbl)
    ws.cell(row=r, column=2).value = unit
    ws.cell(row=r, column=2).font = meiryo(size=9, color="546E7A")
    ws.cell(row=r, column=2).alignment = center()
    ws.cell(row=r, column=2).border = border()

    vl = "年齢参考値!$A:$S"
    apply_ref(ws.cell(row=r, column=3), f"=IFERROR(VLOOKUP($B$6,{vl},{cmin},0),\"\")")
    apply_ref(ws.cell(row=r, column=4), f"=IFERROR(VLOOKUP($B$6,{vl},{cmax},0),\"\")")

    if lbl == "GIR":
        apply_ref(ws.cell(row=r, column=5), f"=IFERROR(VLOOKUP($B$6,{vl},{cmin},0),\"\")")
        apply_ref(ws.cell(row=r, column=6), f"=IFERROR(VLOOKUP($B$6,{vl},{cmax},0),\"\")")
    else:
        apply_ref(ws.cell(row=r, column=5), f"=IFERROR(C{r}*$B$5,\"\")")
        apply_ref(ws.cell(row=r, column=6), f"=IFERROR(D{r}*$B$5,\"\")")

    ws.cell(row=r, column=7).value = abs_unit
    ws.cell(row=r, column=7).font = meiryo(size=9, color="546E7A")
    ws.cell(row=r, column=7).alignment = center()
    ws.cell(row=r, column=7).border = border()

# ── 【製剤設定】 (rows 20-30) ──
R = REF_START + len(ref_items) + 1  # = 20
apply_section(ws, R, "■ 製剤設定", bg="1565C0")

PROD_ROW = R + 1    # 製剤選択
VOL_ROW  = R + 2    # 1本の容量 (計算)
USE_ROW  = R + 3    # 使用量入力
BAGS_ROW = R + 4    # 本数換算

apply_label(ws.cell(row=PROD_ROW, column=1), "主製剤")
apply_input(ws.cell(row=PROD_ROW, column=2), val="ハイカリックNC-N(700mL/本)")
note(ws.cell(row=PROD_ROW, column=3), "↑ リストから選択")
dv_prod = DataValidation(type="list", formula1='"' + ",".join(r[0] for r in PROD_DATA) + '"')
ws.add_data_validation(dv_prod)
dv_prod.add(ws.cell(row=PROD_ROW, column=2))

apply_label(ws.cell(row=VOL_ROW, column=1), "1本の容量 (自動)")
apply_calc(ws.cell(row=VOL_ROW, column=2),
           formula=f"=IFERROR(VLOOKUP(B{PROD_ROW},製剤データ!$A:$J,2,0),\"\")", fmt="0")
note(ws.cell(row=VOL_ROW, column=3), "mL/本（自動取得）")

apply_label(ws.cell(row=USE_ROW, column=1), "使用量 (mL/日)")
apply_input(ws.cell(row=USE_ROW, column=2), val=700, fmt="0")
note(ws.cell(row=USE_ROW, column=3), "mL/日 ← ここを変更")

apply_label(ws.cell(row=BAGS_ROW, column=1), "（本数換算）")
apply_calc(ws.cell(row=BAGS_ROW, column=2),
           formula=f"=IFERROR(B{USE_ROW}/B{VOL_ROW},\"\")", fmt="0.00")
note(ws.cell(row=BAGS_ROW, column=3), "本/日")

AA_SEL_ROW = BAGS_ROW + 2
AA_VOL_ROW = AA_SEL_ROW + 1

apply_label(ws.cell(row=AA_SEL_ROW, column=1), "アミノ酸製剤（任意）")
apply_input(ws.cell(row=AA_SEL_ROW, column=2), val="なし")
note(ws.cell(row=AA_SEL_ROW, column=3), "グルアセト35使用時に選択")
dv_aa = DataValidation(type="list", formula1='"' + ",".join(r[0] for r in AA_DATA) + '"')
ws.add_data_validation(dv_aa)
dv_aa.add(ws.cell(row=AA_SEL_ROW, column=2))

apply_label(ws.cell(row=AA_VOL_ROW, column=1), "アミノ酸製剤 使用量 (mL/日)")
apply_input(ws.cell(row=AA_VOL_ROW, column=2), val=0, fmt="0")
note(ws.cell(row=AA_VOL_ROW, column=3), "mL/日")

TG5_ROW = AA_VOL_ROW + 2
NS_ROW  = TG5_ROW + 1

apply_label(ws.cell(row=TG5_ROW, column=1), "5%ブドウ糖液 (mL/日)")
apply_input(ws.cell(row=TG5_ROW, column=2), val=0, fmt="0")
note(ws.cell(row=TG5_ROW, column=3), "mL/日")

apply_label(ws.cell(row=NS_ROW, column=1), "生理食塩液 (mL/日)")
apply_input(ws.cell(row=NS_ROW, column=2), val=0, fmt="0")
note(ws.cell(row=NS_ROW, column=3), "mL/日")

# ── 【電解質補正】 ──
ADD_SEC_ROW = NS_ROW + 2
apply_section(ws, ADD_SEC_ROW, "■ 電解質補正液", bg="00695C")

NACL_ROW = ADD_SEC_ROW + 1
KCL_ROW  = NACL_ROW + 1
CA_ROW   = KCL_ROW + 1
P_ROW    = CA_ROW + 1
MG_ROW   = P_ROW + 1

add_items = [
    (NACL_ROW, "10% NaCl (mL/日)",          "→ Na 1.71 mEq/mL"),
    (KCL_ROW,  "KCl 2mEq/mL (mL/日)",       "→ K 2.0 mEq/mL"),
    (CA_ROW,   "グルコン酸Ca 10% (mL/日)",   "→ Ca 0.45 mEq/mL"),
    (P_ROW,    "リン酸Na液 (mL/日)",          "→ P 1.0 mmol + Na 2.0 mEq/mL"),
    (MG_ROW,   "MgSO4 1mEq/mL (mL/日)",     "→ Mg 1.0 mEq/mL"),
]
for row, lbl, hint in add_items:
    apply_label(ws.cell(row=row, column=1), lbl)
    apply_input(ws.cell(row=row, column=2), val=0, fmt="0.0")
    note(ws.cell(row=row, column=3), hint)

# ── 【計算結果】 ──
RES_SEC_ROW = MG_ROW + 2
apply_section(ws, RES_SEC_ROW, "■ 計算結果", bg="1B5E20")

RES_HDR_ROW = RES_SEC_ROW + 1
for c, h in enumerate(["成分","単位","投与量/日","/ kg/日","目標 最小","目標 最大","判定"], 1):
    apply_header(ws.cell(row=RES_HDR_ROW, column=c), h, bg="2E7D32", size=10)

RES_START = RES_HDR_ROW + 1

# 中間計算式の部品
VL_PROD = "製剤データ!$A:$J"
VL_AA   = "アミノ酸製剤!$A:$E"
VL_AGE  = "年齢参考値!$A:$S"

def prod_comp(col):
    return f"IFERROR((B{USE_ROW}/IFERROR(B{VOL_ROW},1))*VLOOKUP(B{PROD_ROW},{VL_PROD},{col},0),0)"

def aa_comp(col):
    aa_vol_f = f"B{AA_VOL_ROW}"
    aa_vol_per = f"IFERROR(VLOOKUP(B{AA_SEL_ROW},{VL_AA},2,0),1)"
    aa_val = f"VLOOKUP(B{AA_SEL_ROW},{VL_AA},{col},0)"
    return f"IFERROR(({aa_vol_f}/{aa_vol_per})*{aa_val},0)"

# 各成分の合計式
f_glucose = f"={prod_comp(3)}+B{TG5_ROW}*0.05"
f_aa      = f"={prod_comp(4)}+{aa_comp(3)}"
f_fat     = f"={prod_comp(5)}"
f_Na      = f"={prod_comp(6)}+{aa_comp(4)}+B{NACL_ROW}*1.71+B{P_ROW}*2.0+B{NS_ROW}*0.154"
f_K       = f"={prod_comp(7)}+{aa_comp(5)}+B{KCL_ROW}*2.0"
f_Ca      = f"={prod_comp(8)}+B{CA_ROW}*0.45"
f_Mg      = f"={prod_comp(9)}+B{MG_ROW}*1.0"
f_P       = f"={prod_comp(10)}+B{P_ROW}*1.0"
f_kcal    = f"=({f_glucose})*3.4+({f_aa})*4.0+({f_fat})*9.0"
f_vol     = f"=B{USE_ROW}+B{AA_VOL_ROW}+B{TG5_ROW}+B{NS_ROW}+B{NACL_ROW}+B{KCL_ROW}+B{CA_ROW}+B{P_ROW}+B{MG_ROW}"

# (label, unit, formula, ref_min_col, ref_max_col)  ref=None → no target
result_items = [
    ("総輸液量",   "mL",   f_vol,     2,  3),
    ("総カロリー", "kcal", f_kcal,    4,  5),
    ("アミノ酸",  "g",    f_aa,      6,  7),
    ("糖質",      "g",    f_glucose, None, None),
    ("脂質",      "g",    f_fat,     None, None),
    ("Na",        "mEq",  f_Na,      8,  9),
    ("K",         "mEq",  f_K,       10, 11),
    ("Ca",        "mEq",  f_Ca,      12, 13),
    ("P",         "mmol", f_P,       14, 15),
    ("Mg",        "mEq",  f_Mg,      16, 17),
]

res_row_map = {}
for i, (lbl, unit, formula, cmin, cmax) in enumerate(result_items):
    r = RES_START + i
    res_row_map[lbl] = r

    ws.cell(row=r, column=1).value = lbl
    ws.cell(row=r, column=1).font = meiryo(size=10, bold=True)
    ws.cell(row=r, column=1).border = border()
    ws.cell(row=r, column=1).alignment = right_align()

    ws.cell(row=r, column=2).value = unit
    ws.cell(row=r, column=2).font = meiryo(size=9, color="546E7A")
    ws.cell(row=r, column=2).border = border()
    ws.cell(row=r, column=2).alignment = center()

    apply_calc(ws.cell(row=r, column=3), formula=formula)
    apply_calc(ws.cell(row=r, column=4), formula=f"=IFERROR(C{r}/$B$5,\"\")")

    if cmin:
        apply_ref(ws.cell(row=r, column=5), f"=IFERROR(VLOOKUP($B$6,{VL_AGE},{cmin},0),\"\")")
        apply_ref(ws.cell(row=r, column=6), f"=IFERROR(VLOOKUP($B$6,{VL_AGE},{cmax},0),\"\")")
        # 判定
        sf = (f'=IFERROR(IF(D{r}=""  ,"",IF(D{r}<E{r}*0.8,"不足",'
              f'IF(D{r}>F{r}*1.2,"過剰",'
              f'IF(D{r}<E{r},"やや不足",'
              f'IF(D{r}>F{r},"やや過剰","適正"))))),"")' )
        ws.cell(row=r, column=7).value = sf
    else:
        for c in [5, 6]:
            ws.cell(row=r, column=c).value = "—"
            apply_ref(ws.cell(row=r, column=c))
        ws.cell(row=r, column=7).value = "（参考値なし）"
        ws.cell(row=r, column=7).font = meiryo(size=9, color="9E9E9E", italic=True)

    ws.cell(row=r, column=7).alignment = center()
    ws.cell(row=r, column=7).border = border()
    if not cmin:
        pass
    else:
        ws.cell(row=r, column=7).font = meiryo(size=10, bold=True)

# GIR行
GIR_ROW = RES_START + len(result_items)
res_row_map["GIR"] = GIR_ROW
glc_r = res_row_map["糖質"]

ws.cell(row=GIR_ROW, column=1).value = "GIR"
ws.cell(row=GIR_ROW, column=1).font = meiryo(size=10, bold=True, color="B71C1C")
ws.cell(row=GIR_ROW, column=1).border = border()
ws.cell(row=GIR_ROW, column=1).alignment = right_align()
ws.cell(row=GIR_ROW, column=2).value = "mg/kg/min"
ws.cell(row=GIR_ROW, column=2).font = meiryo(size=9, color="B71C1C")
ws.cell(row=GIR_ROW, column=2).border = border()
ws.cell(row=GIR_ROW, column=2).alignment = center()

apply_calc(ws.cell(row=GIR_ROW, column=3),
           formula=f"=IFERROR(C{glc_r}*1000/1440/$B$5,\"\")", fmt="0.00")
ws.cell(row=GIR_ROW, column=3).font = meiryo(size=11, bold=True, color="B71C1C")

ws.cell(row=GIR_ROW, column=4).value = "—"
apply_calc(ws.cell(row=GIR_ROW, column=4), fmt=None)

apply_ref(ws.cell(row=GIR_ROW, column=5), f"=IFERROR(VLOOKUP($B$6,{VL_AGE},18,0),\"\")")
apply_ref(ws.cell(row=GIR_ROW, column=6), f"=IFERROR(VLOOKUP($B$6,{VL_AGE},19,0),\"\")")

gir_sf = (f'=IFERROR(IF(C{GIR_ROW}>F{GIR_ROW}*1.1,"過剰！高血糖注意",'
          f'IF(C{GIR_ROW}>F{GIR_ROW},"やや高め",'
          f'IF(C{GIR_ROW}<E{GIR_ROW},"やや低め","適正"))),"")' )
ws.cell(row=GIR_ROW, column=7).value = gir_sf
ws.cell(row=GIR_ROW, column=7).font = meiryo(size=10, bold=True)
ws.cell(row=GIR_ROW, column=7).alignment = center()
ws.cell(row=GIR_ROW, column=7).border = border()

# CaP積チェック
CAP_ROW = GIR_ROW + 2
vol_r = res_row_map["総輸液量"]
ca_r  = res_row_map["Ca"]
p_r   = res_row_map["P"]

ws.merge_cells(f"A{CAP_ROW}:B{CAP_ROW}")
ws.cell(row=CAP_ROW, column=1).value = "Ca × P 積（配合変化チェック）"
ws.cell(row=CAP_ROW, column=1).font = meiryo(size=10, bold=True)
ws.cell(row=CAP_ROW, column=1).border = border()
ws.cell(row=CAP_ROW, column=1).alignment = right_align()

cap_f = f"=IFERROR((C{ca_r}/C{vol_r}*1000)*(C{p_r}/C{vol_r}*1000),\"\")"
apply_calc(ws.cell(row=CAP_ROW, column=3), formula=cap_f, fmt="0.0")
ws.cell(row=CAP_ROW, column=4).value = "mEq/L × mmol/L"
ws.cell(row=CAP_ROW, column=4).font = meiryo(size=9, color="546E7A")
ws.cell(row=CAP_ROW, column=4).alignment = center()
ws.cell(row=CAP_ROW, column=4).border = border()

ws.merge_cells(f"E{CAP_ROW}:G{CAP_ROW}")
cap_judge = (f'=IFERROR(IF(C{CAP_ROW}>150,"🔴 危険！沈殿リスクあり→薬剤師へ相談",'
             f'IF(C{CAP_ROW}>100,"🟡 注意！薬剤師に配合確認を","🟢 安全範囲")),"")')
ws.cell(row=CAP_ROW, column=5).value = cap_judge
ws.cell(row=CAP_ROW, column=5).font = meiryo(size=10, bold=True)
ws.cell(row=CAP_ROW, column=5).alignment = center()
ws.cell(row=CAP_ROW, column=5).border = border()

# ── 条件付き書式（判定列G） ──────────────────────────────
green_fill  = PatternFill(start_color="C8E6C9", end_color="C8E6C9", fill_type="solid")
yellow_fill = PatternFill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid")
red_fill    = PatternFill(start_color="FFCDD2", end_color="FFCDD2", fill_type="solid")
green_font  = Font(name="Meiryo", size=10, bold=True, color="1B5E20")
yellow_font = Font(name="Meiryo", size=10, bold=True, color="E65100")
red_font    = Font(name="Meiryo", size=10, bold=True, color="B71C1C")

for r in range(RES_START, GIR_ROW + 1):
    rng = f"G{r}"
    ws.conditional_formatting.add(rng, FormulaRule(
        formula=[f'G{r}="適正"'], fill=green_fill, font=green_font))
    ws.conditional_formatting.add(rng, FormulaRule(
        formula=[f'ISNUMBER(SEARCH("やや",G{r}))'], fill=yellow_fill, font=yellow_font))
    ws.conditional_formatting.add(rng, FormulaRule(
        formula=[f'OR(ISNUMBER(SEARCH("不足",G{r})),ISNUMBER(SEARCH("過剰",G{r})),ISNUMBER(SEARCH("高め",G{r})))'],
        fill=yellow_fill, font=yellow_font))
    ws.conditional_formatting.add(rng, FormulaRule(
        formula=[f'OR(G{r}="不足",G{r}="過剰",ISNUMBER(SEARCH("危険",G{r})),ISNUMBER(SEARCH("！",G{r})))'],
        fill=red_fill, font=red_font))

# CaP判定セルのCF
ws.conditional_formatting.add(f"E{CAP_ROW}", FormulaRule(
    formula=[f'ISNUMBER(SEARCH("安全",E{CAP_ROW}))'], fill=green_fill, font=green_font))
ws.conditional_formatting.add(f"E{CAP_ROW}", FormulaRule(
    formula=[f'ISNUMBER(SEARCH("注意",E{CAP_ROW}))'], fill=yellow_fill, font=yellow_font))
ws.conditional_formatting.add(f"E{CAP_ROW}", FormulaRule(
    formula=[f'ISNUMBER(SEARCH("危険",E{CAP_ROW}))'], fill=red_fill, font=red_font))

# ── 注意書き ──
NOTE_ROW = CAP_ROW + 2
ws.merge_cells(f"A{NOTE_ROW}:G{NOTE_ROW}")
ws.row_dimensions[NOTE_ROW].height = 48
c = ws[f"A{NOTE_ROW}"]
c.value = (
    "【参考文献・注意事項】\n"
    "① Jochum F, et al. ESPGHAN/ESPEN/ESPR/CSPEN guidelines on pediatric parenteral nutrition. Clin Nutr. 2018.\n"
    "② 日本静脈経腸栄養学会ガイドライン第3版 (2013)　③ ASPEN Pediatric Nutrition Support Core Curriculum\n"
    "④ Ca×P積>150 で沈殿形成リスクあり。有機リン酸(グリセロリン酸)の使用、またはラインを分離することを検討してください。"
)
c.font = meiryo(size=8, color="546E7A", italic=True)
c.fill = fill("F5F5F5")
c.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

# ── 製剤成分一覧（計算シートの末尾に参考として掲載） ──
COMP_ROW = NOTE_ROW + 3
apply_section(ws, COMP_ROW, "■ 製剤成分一覧（参考値 / 添付文書で要確認）", bg="BF360C", cols=7)
for c, h in enumerate(["製剤名","容量(mL)","糖質(g)","AA(g)","脂質(g)","Na(mEq)","K(mEq)","Ca(mEq)","Mg(mEq)","P(mmol)"],1):
    if c <= 7:
        apply_header(ws.cell(row=COMP_ROW+1, column=c), h, bg="E64A19", size=9)
for r_i, row in enumerate(PROD_DATA, COMP_ROW+2):
    for c_i, v in enumerate(row, 1):
        if c_i <= 7:
            cell = ws.cell(row=r_i, column=c_i)
            cell.value = v
            cell.font = meiryo(size=9)
            cell.border = border()
            cell.alignment = center()
            if c_i == 1:
                cell.alignment = right_align()

# ── 保存 ──
out = "/home/user/kawasaki-ivig-tools/小児高カロリー輸液計算.xlsx"
wb.save(out)
print(f"✓ 保存完了: {out}")
