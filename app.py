"""
Traffic Violations Insight System - Streamlit Interactive Dashboard
Full-featured analytics web app for Montgomery County Traffic Violations (~2.07M rows).
"""

import os
import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Set page configuration
st.set_page_config(
    page_title="Traffic Violations Insight System",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich aesthetics, dark glassmorphism, and responsive cards
CUSTOM_CSS = """
<style>
    /* Global Styling */
    .main {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    
    /* Header Container */
    .header-box {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1fr solid #334155;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .header-title {
        color: #38bdf8;
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0;
    }
    .header-subtitle {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-top: 6px;
    }
    
    /* Metric Cards */
    .metric-card {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 18px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        transition: transform 0.2s ease-in-out;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        border-color: #38bdf8;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f8fafc;
        margin-top: 4px;
    }
    .metric-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #38bdf8;
        margin-top: 4px;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #1e293b;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# Load dataset safely with caching
@st.cache_data(show_spinner="Loading Traffic Violations Dataset (~2.07M rows)...")
def load_data():
    parquet_path = r"data/cleaned_traffic_violations.parquet"
    if os.path.exists(parquet_path):
        df = pd.read_parquet(parquet_path)
        return df
    st.error(f"Cleaned dataset not found at `{parquet_path}`. Please run `python src/preprocessing.py` first.")
    return pd.DataFrame()


def get_db_connection():
    db_path = r"data/traffic_violations.db"
    if os.path.exists(db_path):
        return sqlite3.connect(db_path)
    return None


def main():
    df_raw = load_data()
    if df_raw.empty:
        st.stop()

    # Title & Header
    st.markdown("""
    <div class="header-box">
        <h1 class="header-title">🚦 Traffic Violations Insight System</h1>
        <div class="header-subtitle">
            Transportation Safety Analytics • Data Preprocessing • Spatial Hotspots • Interactive Dashboard
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar Filter Section
    st.sidebar.markdown("## ⚙️ Filter Controls")
    
    # Date Range Filter
    min_date = df_raw['Date_Of_Stop'].min()
    max_date = df_raw['Date_Of_Stop'].max()
    
    if pd.notna(min_date) and pd.notna(max_date):
        date_range = st.sidebar.date_input(
            "📅 Select Date Range",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date()
        )
    else:
        date_range = []

    # Filter Options
    agencies = sorted(df_raw['Agency'].dropna().unique().tolist())
    selected_agencies = st.sidebar.multiselect("🏛️ Law Enforcement Agency", options=agencies, default=agencies)

    subagencies = sorted(df_raw['SubAgency'].dropna().unique().tolist())
    selected_subagencies = st.sidebar.multiselect("🏢 Police Sub-Agency / District", options=subagencies)

    violation_categories = sorted(df_raw['Violation_Category'].dropna().unique().tolist())
    selected_categories = st.sidebar.multiselect("📋 Violation Category", options=violation_categories)

    violation_types = sorted(df_raw['Violation_Type'].dropna().unique().tolist())
    selected_types = st.sidebar.multiselect("📜 Violation Type (Citation/Warning)", options=violation_types)

    top_makes = df_raw[df_raw['Make'] != 'UNKNOWN']['Make'].value_counts().head(20).index.tolist()
    selected_makes = st.sidebar.multiselect("🚘 Vehicle Make (Top Brands)", options=top_makes)

    genders = ['M', 'F', 'Unknown']
    selected_genders = st.sidebar.multiselect("👤 Driver Gender", options=genders, default=genders)

    races = sorted(df_raw['Race'].dropna().unique().tolist())
    selected_races = st.sidebar.multiselect("🌐 Driver Race Demographic", options=races, default=races)

    accident_filter = st.sidebar.radio("💥 Accident Filter", options=["All Incidents", "Accidents Only", "Non-Accidents Only"])

    # Apply Filters to DataFrame
    filtered_df = df_raw.copy()
    
    if len(date_range) == 2:
        start_d, end_d = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        filtered_df = filtered_df[filtered_df['Date_Of_Stop'].between(start_d, end_d)]

    if selected_agencies:
        filtered_df = filtered_df[filtered_df['Agency'].isin(selected_agencies)]
        
    if selected_subagencies:
        filtered_df = filtered_df[filtered_df['SubAgency'].isin(selected_subagencies)]
        
    if selected_categories:
        filtered_df = filtered_df[filtered_df['Violation_Category'].isin(selected_categories)]
        
    if selected_types:
        filtered_df = filtered_df[filtered_df['Violation_Type'].isin(selected_types)]
        
    if selected_makes:
        filtered_df = filtered_df[filtered_df['Make'].isin(selected_makes)]
        
    if selected_genders:
        filtered_df = filtered_df[filtered_df['Gender'].isin(selected_genders)]
        
    if selected_races:
        filtered_df = filtered_df[filtered_df['Race'].isin(selected_races)]

    if accident_filter == "Accidents Only":
        filtered_df = filtered_df[filtered_df['Accident'] == True]
    elif accident_filter == "Non-Accidents Only":
        filtered_df = filtered_df[filtered_df['Accident'] == False]

    total_records = len(filtered_df)
    total_stops = filtered_df['SeqID'].nunique()
    accident_count = filtered_df['Accident'].sum()
    accident_pct = (accident_count / total_records * 100) if total_records > 0 else 0.0
    injury_count = filtered_df['Personal_Injury'].sum()
    fatal_count = filtered_df['Fatal'].sum()

    # Main Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Overview & KPIs",
        "🗺️ Spatial Hotspots",
        "📈 Temporal Trends",
        "🚘 Vehicle & Demographics",
        "🔍 Enforcement Analytics",
        "💻 SQL Explorer"
    ])

    # TAB 1: OVERVIEW & KPIs
    with tab1:
        st.markdown("### 📌 Key Performance Metrics")
        m1, m2, m3, m4, m5 = st.columns(5)
        
        with m1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Violations</div>
                <div class="metric-value">{total_records:,}</div>
                <div class="metric-sub">Filtered Records</div>
            </div>
            """, unsafe_allow_html=True)
            
        with m2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Unique Traffic Stops</div>
                <div class="metric-value">{total_stops:,}</div>
                <div class="metric-sub">Distinct SeqIDs</div>
            </div>
            """, unsafe_allow_html=True)
            
        with m3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Accident Rate</div>
                <div class="metric-value">{accident_pct:.2f}%</div>
                <div class="metric-sub">{accident_count:,} Crashes</div>
            </div>
            """, unsafe_allow_html=True)
            
        with m4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Injuries Recorded</div>
                <div class="metric-value">{injury_count:,}</div>
                <div class="metric-sub">{fatal_count} Fatalities</div>
            </div>
            """, unsafe_allow_html=True)

        top_brand_name = filtered_df[filtered_df['Make'] != 'UNKNOWN']['Make'].mode()
        top_brand_str = top_brand_name.iloc[0] if len(top_brand_name) > 0 else "N/A"
        
        with m5:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Top Cited Brand</div>
                <div class="metric-value">{top_brand_str}</div>
                <div class="metric-sub">Most Frequency</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("#### 📋 Violation Category Breakdown")
            cat_counts = filtered_df['Violation_Category'].value_counts().reset_index()
            cat_counts.columns = ['Category', 'Count']
            fig_cat = px.bar(
                cat_counts,
                x='Count',
                y='Category',
                orientation='h',
                color='Count',
                color_continuous_scale='Blues',
                text='Count'
            )
            fig_cat.update_layout(template="plotly_dark", height=380, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_cat, use_container_width=True)

        with col_right:
            st.markdown("#### 📜 Violation Disposition Type")
            type_counts = filtered_df['Violation_Type'].value_counts().reset_index()
            type_counts.columns = ['Type', 'Count']
            fig_type = px.pie(
                type_counts,
                names='Type',
                values='Count',
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_type.update_layout(template="plotly_dark", height=380, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_type, use_container_width=True)

    # TAB 2: GEOSPATIAL HOTSPOTS
    with tab2:
        st.markdown("### 🗺️ Incident Hotspot Geospatial Visualization")
        
        geo_df = filtered_df[filtered_df['Latitude'].notna() & filtered_df['Longitude'].notna()]
        st.info(f"Displaying **{len(geo_df):,}** incidents with valid GPS coordinates in Montgomery County, MD.")

        if len(geo_df) > 0:
            # Sample for ultra-fast responsive interactive map if large
            sample_map_df = geo_df.sample(min(25000, len(geo_df)), random_state=42)
            
            map_type = st.radio("Map Style", ["Scatter Density Map", "Accident Hotspots"], horizontal=True)
            
            if map_type == "Scatter Density Map":
                fig_map = px.scatter_mapbox(
                    sample_map_df,
                    lat="Latitude",
                    lon="Longitude",
                    color="Violation_Category",
                    hover_name="Location",
                    hover_data=["Description", "Violation_Type", "Make"],
                    zoom=10,
                    height=600
                )
                fig_map.update_layout(mapbox_style="open-street-map", template="plotly_dark", margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig_map, use_container_width=True)
            else:
                accident_geo = sample_map_df[sample_map_df['Accident'] == True]
                fig_acc = px.density_mapbox(
                    accident_geo,
                    lat="Latitude",
                    lon="Longitude",
                    radius=12,
                    zoom=10,
                    height=600
                )
                fig_acc.update_layout(mapbox_style="open-street-map", template="plotly_dark", margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig_acc, use_container_width=True)
        else:
            st.warning("No valid GPS coordinates available for the current filter selection.")

    # TAB 3: TEMPORAL TRENDS
    with tab3:
        st.markdown("### 📈 Temporal Variance & Peak Hours")
        
        t_col1, t_col2 = st.columns(2)
        
        with t_col1:
            st.markdown("#### 🕒 Hourly Violation Volume (0-23 Hour)")
            hourly_df = filtered_df[filtered_df['Stop_Hour'] != -1]['Stop_Hour'].value_counts().sort_index().reset_index()
            hourly_df.columns = ['Hour', 'Incidents']
            fig_hour = px.line(
                hourly_df,
                x='Hour',
                y='Incidents',
                markers=True,
                line_shape='spline',
                color_discrete_sequence=['#38bdf8']
            )
            fig_hour.update_layout(template="plotly_dark", height=380)
            st.plotly_chart(fig_hour, use_container_width=True)

        with t_col2:
            st.markdown("#### 📅 Day of Week Distribution")
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_df = filtered_df['Day_Of_Week'].value_counts().reindex(day_order).reset_index()
            day_df.columns = ['Day', 'Incidents']
            fig_day = px.bar(
                day_df,
                x='Day',
                y='Incidents',
                color='Incidents',
                color_continuous_scale='Viridis',
                text='Incidents'
            )
            fig_day.update_layout(template="plotly_dark", height=380)
            st.plotly_chart(fig_day, use_container_width=True)

        st.markdown("#### 🗓️ Time-of-Day Category Matrix")
        tod_df = filtered_df.groupby(['Time_Of_Day', 'Violation_Category'], observed=False).size().unstack(fill_value=0)
        fig_tod = px.imshow(
            tod_df,
            labels=dict(x="Violation Category", y="Time of Day", color="Incident Count"),
            color_continuous_scale='Magma'
        )
        fig_tod.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig_tod, use_container_width=True)

    # TAB 4: VEHICLE & DEMOGRAPHICS
    with tab4:
        st.markdown("### 🚘 Vehicle Profiles & Demographics")
        
        v_col1, v_col2 = st.columns(2)
        
        with v_col1:
            st.markdown("#### 🏎️ Top 15 Most Cited Vehicle Makes")
            top_m = filtered_df[filtered_df['Make'] != 'UNKNOWN']['Make'].value_counts().head(15).reset_index()
            top_m.columns = ['Make', 'Count']
            fig_m = px.bar(top_m, x='Count', y='Make', orientation='h', color='Count', color_continuous_scale='Plasma')
            fig_m.update_layout(template="plotly_dark", height=420)
            st.plotly_chart(fig_m, use_container_width=True)

        with v_col2:
            st.markdown("#### 👥 Driver Demographics (Gender & Race)")
            demo_count = filtered_df.groupby(['Race', 'Gender']).size().reset_index(name='Count')
            fig_demo = px.bar(demo_count, x='Race', y='Count', color='Gender', barmode='group', color_discrete_map={'M':'#00b4d8', 'F':'#ff4d6d', 'Unknown':'#6c757d'})
            fig_demo.update_layout(template="plotly_dark", height=420)
            st.plotly_chart(fig_demo, use_container_width=True)

    # TAB 5: ENFORCEMENT ANALYTICS
    with tab5:
        st.markdown("### 🔍 Enforcement & Search Analytics")
        
        e_col1, e_col2 = st.columns(2)
        
        with e_col1:
            st.markdown("#### 👮 Patrol Type (Arrest Type)")
            arrest_df = filtered_df['Arrest_Type'].value_counts().reset_index()
            arrest_df.columns = ['Arrest Type', 'Count']
            fig_arr = px.pie(arrest_df, names='Arrest Type', values='Count', color_discrete_sequence=px.colors.sequential.Teal)
            fig_arr.update_layout(template="plotly_dark", height=380)
            st.plotly_chart(fig_arr, use_container_width=True)

        with e_col2:
            st.markdown("#### 🔎 Searches Conducted & Outcomes")
            search_cond = filtered_df['Search_Conducted'].value_counts().reset_index()
            search_cond.columns = ['Search Conducted', 'Count']
            fig_search = px.bar(search_cond, x='Search Conducted', y='Count', color='Search Conducted', color_discrete_map={True: '#e74c3c', False: '#2ecc71'})
            fig_search.update_layout(template="plotly_dark", height=380)
            st.plotly_chart(fig_search, use_container_width=True)

    # TAB 6: SQL EXPLORER
    with tab6:
        st.markdown("### 💻 Interactive SQL Query Engine")
        st.info("Execute custom SQL queries against the indexed SQLite database table `traffic_violations`.")

        conn = get_db_connection()
        if conn:
            sample_query = "SELECT SeqID, Date_Of_Stop, Agency, SubAgency, Violation_Category, Make, Accident FROM traffic_violations WHERE Accident = 1 LIMIT 50;"
            query = st.text_area("SQL Query", value=sample_query, height=120)
            
            if st.button("🚀 Run SQL Query"):
                try:
                    res_df = pd.read_sql_query(query, conn)
                    st.success(f"Query returned **{len(res_df):,}** rows.")
                    st.dataframe(res_df, use_container_width=True)
                    
                    csv_data = res_df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Query Results CSV", data=csv_data, file_name="query_results.csv", mime="text/csv")
                except Exception as e:
                    st.error(f"SQL Execution Error: {e}")
        else:
            st.warning("Database file `data/traffic_violations.db` not found. Please run `python src/database.py` first.")


if __name__ == '__main__':
    main()
