# -*- coding: utf-8 -*-
# 실행 방법:
#   streamlit run app_subsidy_simple.py

import pandas as pd
import streamlit as st
from pathlib import Path

# 페이지 설정
st.set_page_config(page_title="힙폰 웹용 계산기", page_icon="📱", layout="centered")
st.title("📱 힙폰 웹용 계산기")
st.caption("통신사 → 모델 → 요금제 → (자동 계산) → 매장 할인 입력 → 최종가 계산")


# 데이터 불러오기 함수
@st.cache_data
def load_data(path: str):
    try:
        if path.endswith(".xlsx"):
            return pd.read_excel(path)
        else:
            return pd.read_csv(path, encoding="utf-8-sig")
    except Exception as e:
        st.error(f"데이터 불러오기 실패: {e}")
        return pd.DataFrame()

# 사이드바 (데이터 소스)
with st.sidebar:
    st.subheader("데이터 소스")
    upl = st.file_uploader("CSV 또는 XLSX 업로드", type=["csv", "xlsx"])
    file_path = st.text_input("로컬 파일 경로", value="subsidies_minimal.xlsx")
    st.caption("업로드가 있으면 업로드 우선, 없으면 로컬 파일 사용")

# 데이터 불러오기
if upl is not None:
    if upl.name.endswith(".xlsx"):
        df = pd.read_excel(upl)
    else:
        df = pd.read_csv(upl, encoding="utf-8-sig")
elif Path(file_path).exists():
    if file_path.endswith(".xlsx"):
        df = pd.read_excel(file_path)
    else:
        df = pd.read_csv(file_path, encoding="utf-8-sig")
else:
    st.error("CSV/XLSX 파일을 업로드하거나 올바른 경로를 입력하세요.")
    st.stop()

# 숫자 컬럼 보정
for c in ["msrp_won", "subsidy_won"]:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

# 1) 통신사 선택
carriers = sorted(df["carrier"].dropna().unique().tolist())
carrier = st.selectbox("1. 통신사 선택", carriers)

# 2) 모델명 선택
df_c = df[df["carrier"] == carrier]
models = sorted(df_c["model"].dropna().unique().tolist())
model = st.selectbox("2. 모델명 선택", models)

# 3) 요금제 선택
df_cm = df_c[df_c["model"] == model]
plans = sorted(df_cm["plan"].dropna().unique().tolist())
plan = st.selectbox("3. 요금제 선택", plans)

# 3-1) 가입유형 선택 (번이/기변)
df_cmp = df_cm[df_cm["plan"] == plan]
contract_types = sorted(df_cmp["contract_type"].dropna().unique().tolist())
contract_type = st.selectbox("3-1. 가입유형 선택", contract_types)

# 선택된 조건으로 최종 데이터 행 가져오기
row_df = df_cmp[df_cmp["contract_type"] == contract_type]


# 4) 자동 계산 결과
row_df = df_cm[df_cm["plan"] == plan]
if row_df.empty:
    st.error("일치하는 데이터가 없습니다. 파일을 확인하세요.")
    st.stop()

row = row_df.iloc[0].to_dict()
msrp = int(row["msrp_won"])
subsidy = int(row["subsidy_won"])
calc_price = msrp - subsidy

st.markdown("---")
st.subheader("4. 자동 계산 결과")
col1, col2, col3 = st.columns(3)
col1.metric("출고가(원)", f"{msrp:,}")
col2.metric("공시지원금(원)", f"{subsidy:,}")
col3.metric("기본 계산가(원)", f"{calc_price:,}")

# 5) 매장 할인 입력
st.subheader("5. 매장 할인 입력")
store_discount = st.number_input("매장 할인(원)", min_value=0, step=1000, value=0)

# 6) 최종 값 계산
final_price = max(0, calc_price - int(store_discount))
st.markdown("---")
st.subheader("6. 최종 가격")
st.success(f"최종가: **{final_price:,} 원**")

# 메모/복사용
with st.expander("선택 요약 / 복사용 메모"):
    memo = f"""{row['carrier']} | {row['model']} | {row['plan']}
출고가 {msrp:,}원 - 공시 {subsidy:,}원 - 매장할인 {int(store_discount):,}원
= 최종가 {final_price:,}원"""
    st.text_area("메모", memo, height=100)
