# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

A single-page Streamlit web app that calculates three IVIG resistance prediction scores for Kawasaki disease (川崎病) simultaneously from patient lab values entered in a sidebar.

## Running the App

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Architecture

The entire application lives in `app.py`. There are no modules, classes, or helper files — all input, scoring logic, and output rendering are written sequentially in one file.

**Flow:**
1. Sidebar collects nine patient parameters via `st.sidebar` widgets
2. Three scoring algorithms run directly against those variables (no functions, just inline arithmetic and conditionals)
3. Results are displayed in three `st.columns`, each showing score, risk judgment, and cutoff caption
4. A references section at the bottom cites the source papers

## The Three Scoring Systems

| Score | Japanese Name | Source Paper | High-Risk Cutoff |
|-------|---------------|--------------|-----------------|
| Kobayashi (RAISE) | 群馬スコア | Lancet 2012 | ≥ 5 |
| Egami | 久留米スコア | J Pediatr 2006 | ≥ 3 |
| Sano | 大阪スコア | Eur J Pediatr 2007 | ≥ 2 |

**Input variables used by each score:**

| Variable | Kobayashi | Egami | Sano |
|----------|-----------|-------|------|
| Na (mmol/L) | ≤133 → +2 | | |
| Illness day | ≤4 → +2 | ≤4 → +1 | |
| AST (IU/L) | ≥100 → +2 | | ≥200 → +1 |
| Neutrophils (%) | ≥80 → +2 | | |
| CRP (mg/dL) | ≥10 → +1 | ≥8 → +1 | ≥7 → +1 |
| Age (months) | ≤12 → +1 | <6 → +1 | |
| Platelets (×10⁴/μL) | ≤30 → +1 | ≤30 → +1 | |
| ALT (IU/L) | | ≥80 → +2 | |
| Total bilirubin (mg/dL) | | | ≥0.9 → +1 |

When modifying scoring logic, verify the point values and cutoffs against the cited papers, as these are clinical thresholds from published research.
