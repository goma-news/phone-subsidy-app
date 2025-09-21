# app_subsidy_simple.py
import re
import pandas as pd
import streamlit as st

# ---------------- Page 설정 ----------------
st.set_page_config(page_title="힘폰 웹용 계산기", page_icon="📱", layout="wide")
st.title("📱 힘폰 웹용 계산기")
st.caption("통신사 → 모델 → 요금제 → (자동 계산) → 매장 할인 입력 → 최종가 계산")

# -------------- 데이터 로딩 --------------
upl = st.sidebar.file_uploader("엑셀 업로드 (xlsx)", type=["xlsx"])
try:
    if upl:
        df = pd.read_excel(upl)
        st.sidebar.success("업로드 파일로 계산 중")
    else:
        # 👉 리포지토리에 올려둔 기본 파일명과 일치해야 함
        df = pd.read_excel("subsidies_minimal.xlsx")
        st.sidebar.info("기본 파일(subsidies_minimal.xlsx)로 계산 중")
except Exception as e:
    st.error(f"엑셀 읽기 오류: {e}")
    st.stop()

# -------------- 컬럼 표준화/매핑 --------------
orig_cols = list(df.columns)
lower = {c: c.strip().lower() for c in df.columns}
rev   = {v: k for k, v in lower.items()}

def pick(*cands):
    for k in cands:
        if k in rev: return rev[k]
    return None

col_carrier  = pick("carrier","통신사")
col_model    = pick("model","모델","모델명")
col_plan     = pick("plan","요금제")
col_contract = pick("contract_type","가입유형","가입 유형","가입-유형")
col_msrp     = pick("msrp_won","msrp","출고가(원)","출고가")
col_subsidy  = pick("subsidy_won","공시지원금(원)","공시지원금","지원금")

need = [col_carrier,col_model,col_plan,col_contract,col_msrp,col_subsidy]
names= ["carrier","model","plan","contract_type","msrp_won","subsidy_won"]
if any(x is None for x in need):
    st.error(f"엑셀 헤더가 부족합니다.\n필수 컬럼: {names}\n현재 헤더: {orig_cols}")
    st.stop()

df = df.rename(columns={
    col_carrier:"carrier", col_model:"model", col_plan:"plan",
    col_contract:"contract_type", col_msrp:"msrp_won", col_subsidy:"subsidy_won"
})

# -------------- 값 정규화(공백/콤마/빈칸) --------------
for c in ["carrier","model","plan","contract_type"]:
    df[c] = (df[c].astype(str)
                  .str.strip()
                  .str.replace(r"\s+", " ", regex=True))

for c in ["msrp_won","subsidy_won"]:
    # 콤마/원/문자 제거 → 숫자, 빈칸은 NaN → 0 → int
    df[c] = (df[c].astype(str)
                   .str.replace(r"[^\d]", "", regex=True))
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

# -------------- 요금제 표준화(표기 통일) --------------
def canon_plan(s: str) -> str:
    s = str(s).strip()
    s = re.sub(r"\s+", " ", s)
    # 9.9~12.5 → 10만원 등, 빈번한 표기 통일
    s = re.sub(r"9\.9\s*~\s*12\.5", "10만원", s)
    s = s.replace("청년 99","청년99").replace("청년 89","청년89").replace("청년 79","청년79")
    s = s.replace("5g","5G")  # 5g/5G 혼용 방지
    return s

df["plan_c"] = df["plan"].map(canon_plan)

# -------------- 선택 상태 리셋(먹통 방지) --------------
def _reset_after_carrier():
    st.session_state.model = None
    st.session_state.plan = None
    st.session_state.contract = None

def _reset_after_model():
    st.session_state.plan = None
    st.session_state.contract = None

def _reset_after_plan():
    st.session_state.contract = None

# -------------- UI: 단계별 선택 --------------
left, right = st.columns([1.2, 1])

with left:
    carriers = sorted(df["carrier"].dropna().unique().tolist())
    carrier = st.selectbox("1. 통신사 선택", carriers, key="carrier", on_change=_reset_after_carrier)

    models = []
    if carrier:
        models = sorted(df[df["carrier"]==carrier]["model"].dropna().unique().tolist())
    model = st.selectbox("2. 모델명 선택", models, key="model", on_change=_reset_after_model, disabled=not models)

    plans = []
    if carrier and model:
        plans = sorted(df[(df["carrier"]==carrier) & (df["model"]==model)]["plan_c"].dropna().unique().tolist())
    plan_c = st.selectbox("3. 요금제 선택", plans, key="plan", on_change=_reset_after_plan, disabled=not plans)

    contracts = []
    if carrier and model and plan_c:
        contracts = sorted(df[(df["carrier"]==carrier) & (df["model"]==model) & (df["plan_c"]==plan_c)]["contract_type"].dropna().unique().tolist())
    contract_type = st.selectbox("3-1. 가입유형 선택", contracts, key="contract", disabled=not contracts)

    # 선택 미완료면 안내 후 중단
    if not (carrier and model and plan_c and contract_type):
        st.info("통신사 → 모델 → 요금제 → 가입유형 순서대로 선택해 주세요.")
        st.stop()

    # -------------- 매칭 & 계산 --------------
    row_df = df[
        (df["carrier"]==carrier) &
        (df["model"]==model) &
        (df["plan_c"]==plan_c) &
        (df["contract_type"]==contract_type)
    ]

    if row_df.empty:
        st.error("⚠️ 일치하는 데이터가 없습니다. (엑셀 철자/띄어쓰기/표기 확인)")
        sub = df[(df["carrier"]==carrier) & (df["model"]==model)]
        st.write("가능한 요금제 목록:", sorted(sub["plan"].unique().tolist()))
        st.stop()

    # 중복 시 지원금 큰 값 우선
    row_df = row_df.sort_values("subsidy_won", ascending=False).head(1)

    msrp    = int(row_df["msrp_won"].iloc[0])
    subsidy = int(row_df["subsidy_won"].iloc[0])
    base    = max(msrp - subsidy, 0)

    st.subheader("4. 자동 계산 결과")
    c1, c2, c3 = st.columns(3)
    c1.metric("출고가(원)", f"{msrp:,}")
    c2.metric("공시지원금(원)", f"{subsidy:,}")
    c3.metric("기본 계산가(원)", f"{base:,}")

    st.subheader("5. 매장 할인 입력")
    store_discount = st.number_input("매장 할인(원)", min_value=0, step=10_000, value=0, help="추가로 깎아주는 금액을 입력하세요")

    final_price = max(base - int(store_discount), 0)
    st.subheader("6. 최종가")
    st.success(f"최종 결제 금액: **{final_price:,}원**")

with right:
    with st.expander("🔎 디버그/데이터 확인", expanded=False):
        st.write("현재 선택:", dict(carrier=carrier, model=model, plan_c=plan_c, contract_type=contract_type))
        st.dataframe(row_df.reset_index(drop=True))
        st.caption(f"행 수: {len(df):,} / 모델 수: {df['model'].nunique():,} / 요금제 수(표준화): {df['plan_c'].nunique():,}")
