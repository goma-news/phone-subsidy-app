# -------------------- (1) 파일 읽기: 업로드 없으면 기본 파일 사용 --------------------
upl = st.sidebar.file_uploader("엑셀 업로드 (xlsx)")
try:
    if upl:
        df = pd.read_excel(upl)
        st.caption("📄 업로드 파일 사용")
    else:
        # <- 여기에 올리신 엑셀 파일명을 정확히 넣으세요
        df = pd.read_excel("subsidies_minimal.xlsx")
        st.caption("📄 리포지토리 기본 파일 사용: subsidies_minimal.xlsx")
except Exception as e:
    st.error(f"엑셀 읽기 오류: {e}")
    st.stop()

# -------------------- (2) 컬럼 자동 매핑: 한글/영문/다양한 표기 허용 --------------------
orig_cols = list(df.columns)

# 소문자/공백제거 맵
lower_map = {c: c.strip().lower() for c in df.columns}
rev_map = {v: k for k, v in lower_map.items()}

def pick(*cands):
    for key in cands:
        if key in rev_map:
            return rev_map[key]
    return None

col_carrier = pick("carrier","통신사")
col_model = pick("model","모델","모델명")
col_plan = pick("plan","요금제")
col_contract = pick("contract_type","가입유형","가입 유형","가입-유형")
col_msrp = pick("msrp_won","msrp","출고가(원)","출고가")
col_subsidy = pick("subsidy_won","공시지원금(원)","공시지원금","지원금")

need = [col_carrier, col_model, col_plan, col_contract, col_msrp, col_subsidy]
names = ["carrier","model","plan","contract_type","msrp_won","subsidy_won"]
if any(x is None for x in need):
    st.error(f"엑셀 헤더를 확인하세요.\n필수 컬럼: {names}\n현재 헤더: {orig_cols}")
    st.stop()

df = df.rename(columns={
    col_carrier:"carrier", col_model:"model", col_plan:"plan",
    col_contract:"contract_type", col_msrp:"msrp_won", col_subsidy:"subsidy_won"
})

# -------------------- (3) 데이터 정규화: 공백/콤마/원/대소문자/불필요 문자 제거 --------------------
for c in ["carrier","model","plan","contract_type"]:
    df[c] = (
        df[c].astype(str)
              .str.strip()
              .str.replace(r"\s+", " ", regex=True)   # 연속 공백 1칸으로
              .str.replace("5g","5G", regex=False)    # 5g/5G 혼용 방지
    )

for c in ["msrp_won","subsidy_won"]:
    df[c] = (
        df[c].astype(str)
             .str.replace(r"[^\d]", "", regex=True)   # 숫자만 남김(콤마/원 등 제거)
    )
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

# -------------------- (4) 선택값으로 매칭 확인(디버그 패널) --------------------
with st.expander("🔎 디버그 보기", expanded=False):
    st.write("유니크 컬럼 상태:")
    st.write({
        "carrier": sorted(df["carrier"].unique().tolist())[:10],
        "model_count": df["model"].nunique(),
        "plan_count": df["plan"].nunique(),
        "contract_type": sorted(df["contract_type"].unique().tolist())
    })
