import os
from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(
    page_title="스마트팜 생육·환경 분석 대시보드",
    page_icon="🌱",
    layout="wide",
)

# 스크립트 파일이 위치한 폴더 기준으로 CSV 경로 자동 탐색
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_GROWTH = BASE_DIR / "24_생육정보.csv"
DEFAULT_ENV = BASE_DIR / "24_환경정보.csv"


def load_csv(source) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            if hasattr(source, "seek"):
                source.seek(0)
            df = pd.read_csv(source, encoding=enc)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception:
            continue
    raise ValueError("CSV 인코딩을 읽을 수 없습니다.")


@st.cache_data
def prepare_data(growth_src, env_src):
    df_g = load_csv(growth_src)
    df_e = load_csv(env_src)

    # 생육정보 전처리
    df_g["측정일자"] = pd.to_datetime(df_g["측정일자"], errors="coerce")
    df_g["조사항목값"] = pd.to_numeric(df_g["조사항목값"], errors="coerce")
    df_g = df_g.dropna(subset=["측정일자", "조사항목명", "조사항목값"]).copy()

    # 환경정보 전처리
    df_e["측정일시"] = pd.to_datetime(df_e["측정일시"], errors="coerce")
    df_e["측정데이터"] = pd.to_numeric(df_e["측정데이터"], errors="coerce")
    df_e = df_e.dropna(subset=["측정일시", "항목명", "측정데이터"]).copy()
    df_e["측정일자"] = df_e["측정일시"].dt.floor("D")

    return df_g, df_e


# 사이드바 (기본은 자동 로드, 필요할 때만 다른 CSV 교체 가능)
st.sidebar.title("🌱 스마트팜 대시보드")
st.sidebar.caption("기본으로 `24_생육정보.csv`, `24_환경정보.csv`가 자동 적용되어 있습니다.")

with st.sidebar.expander("다른 CSV 파일로 교체하기 (선택)"):
    up_g = st.file_uploader("생육정보 CSV", type=["csv"])
    up_e = st.file_uploader("환경정보 CSV", type=["csv"])

if up_g is not None and up_e is not None:
    df_g, df_e = prepare_data(up_g, up_e)
elif DEFAULT_GROWTH.exists() and DEFAULT_ENV.exists():
    df_g, df_e = prepare_data(DEFAULT_GROWTH, DEFAULT_ENV)
else:
    st.error("같은 폴더에 `24_생육정보.csv`와 `24_환경정보.csv`가 있는지 확인해주세요.")
    st.stop()

# 필터
greenhouses = sorted(df_g["온실명"].dropna().unique().tolist())
sel_gh = st.sidebar.multiselect("온실 선택", greenhouses, default=greenhouses)
if not sel_gh:
    st.warning("최소 1개 온실을 선택해주세요.")
    st.stop()

min_d = df_g["측정일자"].min().date()
max_d = df_g["측정일자"].max().date()
d_range = st.sidebar.date_input("생육 조사 기간", value=(min_d, max_d), min_value=min_d, max_value=max_d)
if isinstance(d_range, (tuple, list)) and len(d_range) == 2:
    s_dt, e_dt = pd.to_datetime(d_range[0]), pd.to_datetime(d_range[1])
else:
    single = d_range[0] if isinstance(d_range, (tuple, list)) else d_range
    s_dt = e_dt = pd.to_datetime(single)

fg = df_g[(df_g["온실명"].isin(sel_gh)) & (df_g["측정일자"].between(s_dt, e_dt))].copy()
fe_all = df_e[(df_e["온실명"].isin(sel_gh)) & (df_e["측정일자"].between(s_dt - pd.Timedelta(days=7), e_dt))].copy()
fe = fe_all[fe_all["측정일자"].between(s_dt, e_dt)].copy()

# 메인 타이틀 & 핵심 지표
st.title("🍓 스마트팜 생육·환경 통합 분석 대시보드")
st.caption(f"기간: {s_dt.strftime('%Y-%m-%d')} ~ {e_dt.strftime('%Y-%m-%d')} | 선택 온실: {', '.join(sel_gh)}")

def mean_of(df, name_col, target, val_col):
    s = df[df[name_col] == target][val_col]
    return s.mean() if not s.empty else np.nan

m1, m2, m3, m4, m5 = st.columns(5)
v_h = mean_of(fg, "조사항목명", "초장", "조사항목값")
v_f = mean_of(fg, "조사항목명", "착과수", "조사항목값")
v_t = mean_of(fe, "항목명", "내부온도", "측정데이터")
v_hu = mean_of(fe, "항목명", "내부습도", "측정데이터")
v_c = mean_of(fe, "항목명", "내부CO2", "측정데이터")

m1.metric("평균 초장", f"{v_h:.1f} cm" if pd.notna(v_h) else "-")
m2.metric("평균 착과수", f"{v_f:.2f} 개" if pd.notna(v_f) else "-")
m3.metric("평균 내부온도", f"{v_t:.1f} ℃" if pd.notna(v_t) else "-")
m4.metric("평균 내부습도", f"{v_hu:.1f} %" if pd.notna(v_hu) else "-")
m5.metric("평균 내부CO2", f"{v_c:.0f} ppm" if pd.notna(v_c) else "-")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs([
    "🌿 생육 추이 비교",
    "🌡️ 환경 데이터 추이",
    "🔗 생육-환경 상관관계",
    "📋 통계 요약 & 다운로드"
])

with tab1:
    g_items = sorted(fg["조사항목명"].unique().tolist())
    c1, c2 = st.columns([1, 3])
    with c1:
        sel_g_item = st.selectbox("생육 항목", g_items, index=g_items.index("초장") if "초장" in g_items else 0)
        lines = sorted(fg["측정라인"].unique().tolist())
        sel_lines = st.multiselect("측정라인", lines, default=lines)

    g_sub = fg[(fg["조사항목명"] == sel_g_item) & (fg["측정라인"].isin(sel_lines))]
    unit_g = g_sub["단위"].iloc[0] if not g_sub.empty else ""

    with c2:
        if not g_sub.empty:
            piv_g = g_sub.pivot_table(index="측정일자", columns="온실명", values="조사항목값", aggfunc="mean")
            st.markdown(f"**온실별 평균 {sel_g_item} ({unit_g}) 변화 추이**")
            st.line_chart(piv_g)

    if not g_sub.empty:
        st.markdown(f"**온실별 {sel_g_item} ({unit_g}) 요약 비교**")
        gh_stat = g_sub.groupby("온실명")["조사항목값"].agg(["count", "mean", "std", "min", "max"]).round(2)
        st.dataframe(gh_stat, use_container_width=True)

with tab2:
    e_items = sorted(fe["항목명"].unique().tolist())
    ec1, ec2 = st.columns([1, 3])
    with ec1:
        sel_e_item = st.selectbox("환경 항목", e_items, index=e_items.index("내부온도") if "내부온도" in e_items else 0)
        agg_mode = st.radio("집계 단위", ["일평균", "시간별 원본"], index=0)

    e_sub = fe[fe["항목명"] == sel_e_item].copy()
    unit_e = e_sub["단위"].iloc[0] if not e_sub.empty else ""

    with ec2:
        if not e_sub.empty:
            idx_col = "측정일자" if agg_mode == "일평균" else "측정일시"
            piv_e = e_sub.pivot_table(index=idx_col, columns="온실명", values="측정데이터", aggfunc="mean")
            st.markdown(f"**온실별 {sel_e_item} ({unit_e}) 추이 ({agg_mode})**")
            st.line_chart(piv_e)

    if not e_sub.empty:
        e_sub["시각(0~23시)"] = e_sub["측정일시"].dt.hour
        piv_hr = e_sub.pivot_table(index="시각(0~23시)", columns="온실명", values="측정데이터", aggfunc="mean")
        st.markdown(f"**시간대별 평균 {sel_e_item} ({unit_e}) 일중 변화 패턴**")
        st.line_chart(piv_hr)

with tab3:
    st.markdown("각 생육 조사일 직전 **7일간의 온실별 환경 평균값**과 생육 결과 간의 피어슨 상관계수입니다.")
    g_piv = fg.pivot_table(index=["온실명", "측정일자"], columns="조사항목명", values="조사항목값", aggfunc="mean").reset_index()
    e_day = fe_all.pivot_table(index=["온실명", "측정일자"], columns="항목명", values="측정데이터", aggfunc="mean").reset_index()

    env_cols = [c for c in e_day.columns if c not in ["온실명", "측정일자"]]
    gro_cols = [c for c in g_piv.columns if c not in ["온실명", "측정일자"]]

    rows = []
    for _, r in g_piv.iterrows():
        win = e_day[
            (e_day["온실명"] == r["온실명"]) &
            (e_day["측정일자"] > r["측정일자"] - pd.Timedelta(days=7)) &
            (e_day["측정일자"] <= r["측정일자"])
        ]
        e_mean = win[env_cols].mean().to_dict() if not win.empty else {c: np.nan for c in env_cols}
        rows.append({**r.to_dict(), **e_mean})

    merged = pd.DataFrame(rows)
    if len(merged) >= 3 and env_cols and gro_cols:
        corr = merged[gro_cols + env_cols].corr().loc[gro_cols, env_cols].round(3)
        st.dataframe(corr.style.background_gradient(cmap="RdBu_r", vmin=-1, vmax=1), use_container_width=True)

        sc1, sc2 = st.columns(2)
        with sc1:
            x_col = st.selectbox("X축 (직전 7일 평균 환경)", env_cols)
        with sc2:
            y_col = st.selectbox("Y축 (생육 지표)", gro_cols)

        st.scatter_chart(merged.dropna(subset=[x_col, y_col]), x=x_col, y=y_col, color="온실명")
    else:
        st.info("상관관계를 계산할 데이터가 부족합니다.")

with tab4:
    st.subheader("온실별 생육 통계 요약")
    st.dataframe(
        fg.groupby(["온실명", "조사항목명", "단위"], as_index=False)["조사항목값"].agg(
            건수="count", 평균="mean", 표준편차="std", 최소="min", 최대="max"
        ).round(2),
        use_container_width=True,
    )

    st.subheader("온실별 환경 통계 요약")
    st.dataframe(
        fe.groupby(["온실명", "항목명", "단위"], as_index=False)["측정데이터"].agg(
            건수="count", 평균="mean", 표준편차="std", 최소="min", 최대="max"
        ).round(2),
        use_container_width=True,
    )

    if not merged.empty:
        st.download_button(
            "📥 생육-환경 통합 분석 CSV 다운로드",
            data=merged.to_csv(index=False).encode("utf-8-sig"),
            file_name="smartfarm_merged.csv",
            mime="text/csv",
        )
