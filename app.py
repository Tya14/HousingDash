import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import json

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SG HDB Resale Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown("""
<style>
    [data-testid="stSidebar"] { min-width: 230px; max-width: 270px; }
    .kpi-card {
        background: #f7f8fa;
        border-radius: 10px;
        padding: 14px 18px;
        border: 1px solid #e8eaed;
    }
    .kpi-label  { font-size: 12px; color: #6b7280; margin-bottom: 4px; }
    .kpi-value  { font-size: 26px; font-weight: 600; color: #111827; line-height: 1.1; }
    .kpi-note   { font-size: 12px; color: #9ca3af; margin-top: 4px; }
    .section-header {
        font-size: 12px; font-weight: 600; color: #374151;
        letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 6px;
    }
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="
    background: linear-gradient(135deg, #3b82f6, #6366f1);
    padding: 28px 32px;
    border-radius: 14px;
    color: white;
    margin-bottom: 18px;
">
    <div style="font-size: 28px; font-weight: 700; margin-bottom: 6px;">
        🏠 Singapore HDB Resale Dashboard
    </div>
    <div style="font-size: 15px; opacity: 0.9; margin-bottom: 14px;">
        Explore resale flat prices, transaction patterns, and housing trends across towns and flat types.
    </div>
    <div style="font-size: 13px; opacity: 0.8;">
        📊 Data range: 2000 – Feb 2012 &nbsp;&nbsp;•&nbsp;&nbsp; 🔍 Filter by town, price, size & flat type
    </div>
</div>
""", unsafe_allow_html=True)


@st.cache_data
def load_geojson():
    with open("planning_area.geojson") as f:
        return json.load(f)

geojson = load_geojson()

# ── Load CSV → SQLite (runs once, cached) ─────────────────────────────────────
@st.cache_resource
def get_connection():
    """
    Load the CSV into an in-memory SQLite database.
    Returns a sqlite3.Connection. All aggregation queries go through here.
    """
    raw = pd.read_csv("ResaleFlatPricesBasedonApprovalDate2000Feb2012_truncated.csv")

    # Parse month → year and quarter strings so SQL can GROUP BY them
    raw["year"] = pd.to_datetime(raw["month"]).dt.year
    # Store quarter as a YYYY-MM-DD string (first day of each quarter)
    # so SQLite ORDER BY quarter sorts chronologically, not as a garbled string
    raw["quarter"] = pd.to_datetime(raw["month"]).dt.to_period("Q").dt.to_timestamp().dt.strftime("%Y-%m-%d")

    con = sqlite3.connect(":memory:", check_same_thread=False)
    raw.to_sql("resale", con, index=False, if_exists="replace")

    # Indexes speed up repeated filtered queries on large sidebar selections
    con.execute("CREATE INDEX idx_town      ON resale(town)")
    con.execute("CREATE INDEX idx_flat_type ON resale(flat_type)")
    con.execute("CREATE INDEX idx_year      ON resale(year)")
    con.commit()
    return con

con = get_connection()

# ── Helper: SQL query → DataFrame ────────────────────────────────────────────
def sql(query: str, params: tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(query, con, params=params)

# ── Helper: format a number as a price string ─────────────────────────────────
def fmt(v):
    if v >= 1_000_000: return f"S${v / 1_000_000:.2f}M"
    if v >= 1_000:     return f"S${v / 1_000:.0f}K"
    return f"S${v:,.0f}"

COLORS = px.colors.qualitative.Set2

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏠 HousingDash")
    st.markdown("---")

    towns = ["All"] + [r[0] for r in con.execute(
        "SELECT DISTINCT town FROM resale ORDER BY town").fetchall()]
    selected_town = st.selectbox("**Town**", towns)

    flat_types = [r[0] for r in con.execute(
        "SELECT DISTINCT flat_type FROM resale ORDER BY flat_type").fetchall()]
    selected_flats = st.multiselect("**Flat type**", flat_types, default=flat_types)

    yr_min, yr_max = con.execute("SELECT MIN(year), MAX(year) FROM resale").fetchone()
    selected_years = st.slider("**Year range**", yr_min, yr_max, (yr_min, yr_max))

    p_min, p_max = con.execute(
        "SELECT MIN(resale_price), MAX(resale_price) FROM resale").fetchone()
    selected_price = st.slider("**Price range (S$)**", int(p_min), int(p_max),
                               (int(p_min), int(p_max)), step=5000, format="$%d")

    a_min, a_max = con.execute(
        "SELECT MIN(floor_area_sqm), MAX(floor_area_sqm) FROM resale").fetchone()
    selected_area = st.slider("**Floor area (m²)**", int(a_min), int(a_max),
                              (int(a_min), int(a_max)))

    st.markdown("---")
    st.caption("Dataset: 2000 – Feb 2012")

# ── Shared WHERE clause + params ──────────────────────────────────────────────
#
#   Every chart uses this exact WHERE snippet so all aggregations are
#   computed by SQLite — zero pandas filtering on the results.
#
flat_in = ", ".join(f"'{f}'" for f in selected_flats) if selected_flats else "''"

WHERE = f"""
    WHERE year             BETWEEN ? AND ?
      AND resale_price     BETWEEN ? AND ?
      AND floor_area_sqm   BETWEEN ? AND ?
      {'AND town = ?' if selected_town != 'All' else ''}
      {'AND flat_type IN (' + flat_in + ')' if selected_flats else ''}
"""

base_params: tuple = (
    selected_years[0], selected_years[1],
    selected_price[0], selected_price[1],
    selected_area[0],  selected_area[1],
)
if selected_town != "All":
    base_params += (selected_town,)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_overview, tab_trends, tab_geo, tab_data = st.tabs(
    ["📊 Overview", "📈 Trends", "🗺 By Town / Type", "🗃 Raw Data"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with tab_overview:

    # ── KPI cards ─────────────────────────────────────────────────────────────
    kpi = sql(f"""
        SELECT
            COUNT(*)                               AS total_txn,
            AVG(resale_price)                      AS avg_price,
            AVG(resale_price / floor_area_sqm)     AS avg_psm,
            AVG(floor_area_sqm)                    AS avg_area,
            SQRT(AVG(floor_area_sqm * floor_area_sqm) - AVG(floor_area_sqm) * AVG(floor_area_sqm)) AS std_area
        FROM resale
        {WHERE}
    """, base_params)

    # SQLite has no MEDIAN function — use the ORDER BY + OFFSET trick
    n_rows = int(kpi["total_txn"].iloc[0])
    median_price = sql(f"""
        SELECT resale_price
        FROM   resale
        {WHERE}
        ORDER  BY resale_price
        LIMIT  1 OFFSET {max(0, (n_rows - 1) // 2)}
    """, base_params)["resale_price"].iloc[0] if n_rows > 0 else 0

    k1, k2, k3, k4 = st.columns(4)
    for col, label, val, note in [
        (k1, "Median resale price",   fmt(median_price),                "50th percentile"),
        (k2, "Avg price / m²",        fmt(kpi["avg_psm"].iloc[0]),      "across filtered set"),
        (k3, "Total transactions",    f"{n_rows:,}",                    "matching filters"),
        (k4, "Avg floor area",
             f"{kpi['avg_area'].iloc[0]:.0f} m²",
             f"σ ≈ {kpi['std_area'].iloc[0]:.0f} m²"),
    ]:
        with col:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{val}</div>
                <div class="kpi-note">{note}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Trend + flat-type bar ─────────────────────────────────────────────────
    col_trend, col_bar = st.columns([2, 1])

    with col_trend:
        st.markdown('<div class="section-header">Avg resale price — quarterly</div>',
                    unsafe_allow_html=True)
        trend = sql(f"""
            SELECT
                quarter,
                AVG(resale_price) AS avg_price,
                COUNT(*)          AS txn_count
            FROM   resale
            {WHERE}
            GROUP  BY quarter
            ORDER  BY quarter
        """, base_params)
        # Cast to datetime so Plotly renders a proper continuous time axis
        trend["quarter"] = pd.to_datetime(trend["quarter"])
        fig = px.area(trend, x="quarter", y="avg_price",
                      labels={"quarter": "", "avg_price": "Avg price (S$)"},
                      color_discrete_sequence=["#3b82f6"],
                      custom_data=["txn_count"])
        fig.update_traces(
            line_width=2,
            fillcolor="rgba(59,130,246,0.12)",
            hovertemplate="<b>%{x|%Y Q%q}</b><br>Avg price: S$%{y:,.0f}<br>Transactions: %{customdata[0]:,}<extra></extra>",
        )
        fig.update_layout(height=260, plot_bgcolor="white", paper_bgcolor="white",
                          margin=dict(l=0, r=0, t=0, b=0),
                          yaxis=dict(tickformat="$,.0f", gridcolor="#f0f0f0"),
                          xaxis=dict(tickangle=35, gridcolor="#f0f0f0"))
        st.plotly_chart(fig, use_container_width=True)

    with col_bar:
        st.markdown('<div class="section-header">Avg price by flat type</div>',
                    unsafe_allow_html=True)
        by_type = sql(f"""
            SELECT
                flat_type,
                AVG(resale_price) AS avg_price
            FROM   resale
            {WHERE}
            GROUP  BY flat_type
            ORDER  BY avg_price ASC
        """, base_params)
        fig2 = px.bar(by_type, x="avg_price", y="flat_type", orientation="h",
                      color="avg_price", color_continuous_scale="Blues",
                      labels={"avg_price": "Avg price (S$)", "flat_type": ""})
        fig2.update_layout(height=260, plot_bgcolor="white", paper_bgcolor="white",
                           margin=dict(l=0, r=0, t=0, b=0),
                           coloraxis_showscale=False,
                           xaxis=dict(tickformat="$,.0f", gridcolor="#f0f0f0"))
        st.plotly_chart(fig2, use_container_width=True)

    # ── Bottom row: scatter sample + price histogram + heatmap ───────────────
    col_sc, col_hist, col_heat = st.columns(3)

    with col_sc:
        st.markdown('<div class="section-header">Floor area vs price (3k sample)</div>',
                    unsafe_allow_html=True)
        scatter = sql(f"""
            SELECT floor_area_sqm, resale_price, flat_type
            FROM   resale
            {WHERE}
            ORDER  BY RANDOM()
            LIMIT  3000
        """, base_params)
        fig3 = px.scatter(scatter, x="floor_area_sqm", y="resale_price",
                          color="flat_type", opacity=0.45, trendline="ols",
                          labels={"floor_area_sqm": "Area (m²)",
                                  "resale_price": "Price (S$)", "flat_type": "Type"},
                          color_discrete_sequence=COLORS)
        fig3.update_traces(marker_size=4)
        fig3.update_layout(height=240, plot_bgcolor="white", paper_bgcolor="white",
                           margin=dict(l=0, r=0, t=0, b=0),
                           legend=dict(orientation="h", y=-0.3, font_size=10),
                           yaxis=dict(tickformat="$,.0f", gridcolor="#f0f0f0"),
                           xaxis=dict(gridcolor="#f0f0f0"))
        st.plotly_chart(fig3, use_container_width=True)

    with col_hist:
        st.markdown('<div class="section-header">Price distribution (S$20K buckets)</div>',
                    unsafe_allow_html=True)
        hist = sql(f"""
            SELECT
                CAST(resale_price / 20000 AS INTEGER) * 20000 AS price_bucket,
                COUNT(*) AS txn_count
            FROM   resale
            {WHERE}
            GROUP  BY price_bucket
            ORDER  BY price_bucket
        """, base_params)
        fig4 = px.bar(hist, x="price_bucket", y="txn_count",
                      labels={"price_bucket": "Price (S$)", "txn_count": "Transactions"},
                      color_discrete_sequence=["#6366f1"])
        fig4.update_layout(height=240, plot_bgcolor="white", paper_bgcolor="white",
                           margin=dict(l=0, r=0, t=0, b=0), bargap=0.05,
                           xaxis=dict(tickformat="$,.0f", gridcolor="#f0f0f0"),
                           yaxis=dict(gridcolor="#f0f0f0"))
        st.plotly_chart(fig4, use_container_width=True)

    with col_heat:
        st.markdown('<div class="section-header">Transactions by year & flat type</div>',
                    unsafe_allow_html=True)
        heat = sql(f"""
            SELECT
                year,
                flat_type,
                COUNT(*) AS txn_count
            FROM   resale
            {WHERE}
            GROUP  BY year, flat_type
            ORDER  BY year, flat_type
        """, base_params)
        heat_pivot = heat.pivot(index="flat_type", columns="year",
                                values="txn_count").fillna(0)
        fig5 = px.imshow(heat_pivot, color_continuous_scale="Blues", aspect="auto",
                         labels=dict(x="Year", y="", color="Transactions"))
        fig5.update_layout(height=240, plot_bgcolor="white", paper_bgcolor="white",
                           margin=dict(l=0, r=0, t=0, b=0),
                           coloraxis_showscale=False)
        st.plotly_chart(fig5, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TRENDS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_trends:

    st.markdown('<div class="section-header">Annual avg price by flat type</div>',
                unsafe_allow_html=True)
    yearly = sql(f"""
        SELECT
            year,
            flat_type,
            AVG(resale_price)   AS avg_price,
            COUNT(*)            AS txn_count,
            AVG(floor_area_sqm) AS avg_area
        FROM   resale
        {WHERE}
        GROUP  BY year, flat_type
        ORDER  BY year, flat_type
    """, base_params)
    fig6 = px.line(yearly, x="year", y="avg_price", color="flat_type", markers=True,
                   labels={"year": "Year", "avg_price": "Avg price (S$)", "flat_type": "Flat type"},
                   color_discrete_sequence=COLORS,
                   hover_data={"txn_count": True, "avg_area": ":.0f"})
    fig6.update_layout(height=340, plot_bgcolor="white", paper_bgcolor="white",
                       yaxis=dict(tickformat="$,.0f", gridcolor="#f0f0f0"),
                       xaxis=dict(gridcolor="#f0f0f0"),
                       legend=dict(orientation="h", y=-0.18))
    st.plotly_chart(fig6, use_container_width=True)

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-header">Avg price by storey range</div>',
                    unsafe_allow_html=True)
        storey = sql(f"""
            SELECT
                storey_range,
                AVG(resale_price) AS avg_price,
                COUNT(*)          AS txn_count
            FROM   resale
            {WHERE}
            GROUP  BY storey_range
            ORDER  BY avg_price ASC
        """, base_params)
        fig7 = px.bar(storey, x="storey_range", y="avg_price",
                      color="avg_price", color_continuous_scale="Blues",
                      hover_data={"txn_count": True},
                      labels={"storey_range": "Storey range",
                              "avg_price": "Avg price (S$)", "txn_count": "Transactions"})
        fig7.update_layout(height=300, plot_bgcolor="white", paper_bgcolor="white",
                           coloraxis_showscale=False,
                           yaxis=dict(tickformat="$,.0f", gridcolor="#f0f0f0"),
                           xaxis=dict(tickangle=40))
        st.plotly_chart(fig7, use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">Avg price by lease commencement year</div>',
                    unsafe_allow_html=True)
        lease = sql(f"""
            SELECT
                lease_commence_date,
                AVG(resale_price) AS avg_price,
                COUNT(*)          AS txn_count
            FROM   resale
            {WHERE}
            GROUP  BY lease_commence_date
            ORDER  BY lease_commence_date
        """, base_params)
        fig8 = px.scatter(lease, x="lease_commence_date", y="avg_price",
                          size="txn_count", trendline="lowess",
                          labels={"lease_commence_date": "Lease start year",
                                  "avg_price": "Avg price (S$)", "txn_count": "Transactions"},
                          color_discrete_sequence=["#f59e0b"])
        fig8.update_layout(height=300, plot_bgcolor="white", paper_bgcolor="white",
                           yaxis=dict(tickformat="$,.0f", gridcolor="#f0f0f0"),
                           xaxis=dict(gridcolor="#f0f0f0"))
        st.plotly_chart(fig8, use_container_width=True)

    # Year-over-year change using a SQL window function (LAG)
    st.markdown('<div class="section-header">Year-over-year avg price change</div>',
                unsafe_allow_html=True)
    yoy = sql(f"""
        WITH annual AS (
            SELECT
                year,
                AVG(resale_price) AS avg_price,
                COUNT(*)          AS txn_count
            FROM   resale
            {WHERE}
            GROUP  BY year
        )
        SELECT
            a.year,
            ROUND(a.avg_price, 0)                                               AS avg_price,
            a.txn_count,
            ROUND(a.avg_price - LAG(a.avg_price) OVER (ORDER BY a.year), 0)    AS price_change,
            ROUND(
                100.0 * (a.avg_price - LAG(a.avg_price) OVER (ORDER BY a.year))
                      / LAG(a.avg_price) OVER (ORDER BY a.year),
                2
            )                                                                   AS pct_change
        FROM annual a
        ORDER BY a.year
    """, base_params)
    yoy["avg_price"]    = yoy["avg_price"].apply(fmt)
    yoy["price_change"] = yoy["price_change"].apply(
        lambda x: f"+{fmt(x)}" if pd.notna(x) and x >= 0 else (fmt(x) if pd.notna(x) else "—"))
    yoy["pct_change"]   = yoy["pct_change"].apply(
        lambda x: f"{x:+.2f}%" if pd.notna(x) else "—")
    yoy.columns = ["Year", "Avg price", "Transactions", "Δ vs prev year", "% change"]
    st.dataframe(yoy, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — BY TOWN / TYPE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_geo:

    st.markdown("### Top towns by price")

    towns_agg = sql(f"""
        SELECT town, AVG(resale_price) AS avg_price
        FROM resale
        {WHERE}
        GROUP BY town
        ORDER BY avg_price DESC
        LIMIT 20
    """, base_params)

    fig = px.bar(towns_agg, x="town", y="avg_price")
    st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — RAW DATA
# ═══════════════════════════════════════════════════════════════════════════════
with tab_data:

    st.markdown('<div class="section-header">Filtered transactions — SQL paginated (top 5,000)</div>',
                unsafe_allow_html=True)

    sort_col = st.selectbox("Sort by", [
        "resale_price DESC", "resale_price ASC",
        "year DESC", "year ASC",
        "floor_area_sqm DESC",
    ])

    raw_view = sql(f"""
        SELECT
            month,
            town,
            flat_type,
            flat_model,
            storey_range,
            ROUND(floor_area_sqm, 0)                         AS floor_area_sqm,
            lease_commence_date,
            ROUND(resale_price, 0)                           AS resale_price,
            ROUND(resale_price / floor_area_sqm, 0)          AS price_per_sqm
        FROM   resale
        {WHERE}
        ORDER  BY {sort_col}
        LIMIT  5000
    """, base_params)

    raw_view["resale_price"]  = raw_view["resale_price"].apply(lambda x: f"S${int(x):,}")
    raw_view["price_per_sqm"] = raw_view["price_per_sqm"].apply(lambda x: f"S${int(x):,}")
    raw_view.columns = ["Month", "Town", "Flat type", "Model",
                        "Storey", "Area (m²)", "Lease start", "Price", "Price/m²"]
    st.dataframe(raw_view, use_container_width=True, height=420)

    col_dl, col_info = st.columns([1, 3])
    with col_dl:
        # Export query also runs through SQLite — no pandas filtering
        export = sql(f"""
            SELECT
                month, town, flat_type, flat_model, storey_range,
                floor_area_sqm, lease_commence_date, resale_price,
                ROUND(resale_price / floor_area_sqm, 0) AS price_per_sqm
            FROM   resale
            {WHERE}
            ORDER  BY {sort_col}
        """, base_params)
        st.download_button(
            "⬇ Download filtered CSV",
            export.to_csv(index=False).encode("utf-8"),
            "hdb_resale_filtered.csv", "text/csv",
        )
    with col_info:
        total = sql(f"SELECT COUNT(*) AS n FROM resale {WHERE}", base_params)["n"].iloc[0]
        st.caption(f"Showing top 5,000 of **{total:,}** filtered records.")
