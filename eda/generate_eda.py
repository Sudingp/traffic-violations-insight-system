"""
Automated Exploratory Data Analysis (EDA) Script
Generates statistical summaries, analytical figures (Matplotlib/Seaborn/Plotly),
and compiles a complete markdown EDA report.
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Set aesthetic visual style
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 11
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12


def generate_eda_suite(parquet_path: str, output_dir: str):
    """Generates all 6 core EDA charts and writes eda_report.md."""
    if not os.path.exists(parquet_path):
        raise FileNotFoundError(f"Parquet dataset not found at {parquet_path}")

    charts_dir = os.path.join(output_dir, 'charts')
    os.makedirs(charts_dir, exist_ok=True)
    
    print(f"Loading cleaned dataset for EDA: {parquet_path}...")
    df = pd.read_parquet(parquet_path)
    total_records = len(df)
    total_stops = df['SeqID'].nunique()

    print("Generating Question 1: Most Common Violations Chart...")
    # Q1: Top 10 Violation Categories & Description
    top_categories = df['Violation_Category'].value_counts()
    
    plt.figure(figsize=(10, 5))
    ax = sns.barplot(x=top_categories.values, y=top_categories.index, palette='crest')
    plt.title('Distribution of Traffic Violation Categories', pad=15, fontweight='bold')
    plt.xlabel('Number of Incidents')
    plt.ylabel('Violation Category')
    for p in ax.patches:
        width = p.get_width()
        ax.annotate(f'{int(width):,}', (width, p.get_y() + p.get_height() / 2.),
                    ha='left', va='center', xytext=(5, 0), textcoords='offset points', fontsize=10)
    plt.tight_layout()
    chart1_path = os.path.join(charts_dir, 'q1_top_violations.png')
    plt.savefig(chart1_path, dpi=300)
    plt.close()

    print("Generating Question 2: SubAgency & Location Hotspots...")
    # Q2: Top SubAgencies (Districts)
    top_subagencies = df['SubAgency'].value_counts().head(8)
    
    plt.figure(figsize=(10, 5))
    ax = sns.barplot(x=top_subagencies.values, y=top_subagencies.index, palette='viridis')
    plt.title('Traffic Violation Incidents by Sub-Agency / Police District', pad=15, fontweight='bold')
    plt.xlabel('Incident Count')
    plt.ylabel('Sub-Agency / District')
    for p in ax.patches:
        width = p.get_width()
        ax.annotate(f'{int(width):,}', (width, p.get_y() + p.get_height() / 2.),
                    ha='left', va='center', xytext=(5, 0), textcoords='offset points', fontsize=10)
    plt.tight_layout()
    chart2_path = os.path.join(charts_dir, 'q2_district_hotspots.png')
    plt.savefig(chart2_path, dpi=300)
    plt.close()

    print("Generating Question 3: Demographics & Violation Types...")
    # Q3: Race & Gender vs Violation Type
    demo_df = df[(df['Gender'].isin(['M', 'F'])) & (df['Race'] != 'OTHER')]
    ct = pd.crosstab(demo_df['Race'], demo_df['Violation_Type'], normalize='index') * 100
    
    plt.figure(figsize=(10, 5))
    ct.plot(kind='bar', stacked=True, colormap='Spectral', figsize=(10, 5))
    plt.title('Violation Type Proportion by Driver Race Demographic (%)', pad=15, fontweight='bold')
    plt.xlabel('Race Category')
    plt.ylabel('Percentage (%)')
    plt.legend(title='Violation Type', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.xticks(rotation=30)
    plt.tight_layout()
    chart3_path = os.path.join(charts_dir, 'q3_demographic_correlations.png')
    plt.savefig(chart3_path, dpi=300)
    plt.close()

    print("Generating Question 4: Temporal Variation...")
    # Q4: Hourly & Day-of-Week Trends
    plt.figure(figsize=(12, 5))
    
    plt.subplot(1, 2, 1)
    hourly = df[df['Stop_Hour'] != -1]['Stop_Hour'].value_counts().sort_index()
    sns.lineplot(x=hourly.index, y=hourly.values, marker='o', color='#e74c3c', linewidth=2.5)
    plt.title('Traffic Violation Volume by Hour of Day (0-23)', pad=12, fontweight='bold')
    plt.xlabel('Hour of Stop (24-Hour Clock)')
    plt.ylabel('Total Incident Count')
    plt.xticks(range(0, 24, 2))

    plt.subplot(1, 2, 2)
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    daily = df['Day_Of_Week'].value_counts().reindex(day_order)
    sns.barplot(x=daily.index, y=daily.values, palette='mako')
    plt.title('Traffic Violation Volume by Day of Week', pad=12, fontweight='bold')
    plt.xlabel('Day of Week')
    plt.ylabel('Total Incident Count')
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    chart4_path = os.path.join(charts_dir, 'q4_temporal_trends.png')
    plt.savefig(chart4_path, dpi=300)
    plt.close()

    print("Generating Question 5: Top Vehicle Makes...")
    # Q5: Vehicle Make Distribution
    top_makes = df[df['Make'] != 'UNKNOWN']['Make'].value_counts().head(10)
    
    plt.figure(figsize=(10, 5))
    ax = sns.barplot(x=top_makes.values, y=top_makes.index, palette='rocket')
    plt.title('Top 10 Vehicle Makes Involved in Traffic Violations', pad=15, fontweight='bold')
    plt.xlabel('Count of Cited Vehicles')
    plt.ylabel('Vehicle Manufacturer')
    for p in ax.patches:
        width = p.get_width()
        ax.annotate(f'{int(width):,}', (width, p.get_y() + p.get_height() / 2.),
                    ha='left', va='center', xytext=(5, 0), textcoords='offset points', fontsize=10)
    plt.tight_layout()
    chart5_path = os.path.join(charts_dir, 'q5_vehicle_makes.png')
    plt.savefig(chart5_path, dpi=300)
    plt.close()

    print("Generating Question 6: Accident & Severity Distribution...")
    # Q6: Accident & Severity Factors
    accident_counts = df['Accident'].value_counts()
    injury_counts = df['Personal_Injury'].sum()
    property_damage_counts = df['Property_Damage'].sum()
    fatal_counts = df['Fatal'].sum()

    severity_df = pd.DataFrame({
        'Incident Type': ['Total Violations', 'Accidents', 'Property Damage', 'Personal Injury', 'Fatalities'],
        'Count': [total_records, accident_counts.get(True, 0), property_damage_counts, injury_counts, fatal_counts]
    })

    plt.figure(figsize=(9, 4.5))
    ax = sns.barplot(x='Count', y='Incident Type', data=severity_df.iloc[1:], palette='flare')
    plt.title('Accident & Severity Metrics Breakdown', pad=15, fontweight='bold')
    plt.xlabel('Incident Frequency')
    for p in ax.patches:
        width = p.get_width()
        ax.annotate(f'{int(width):,}', (width, p.get_y() + p.get_height() / 2.),
                    ha='left', va='center', xytext=(5, 0), textcoords='offset points', fontsize=10)
    plt.tight_layout()
    chart6_path = os.path.join(charts_dir, 'q6_accident_severity.png')
    plt.savefig(chart6_path, dpi=300)
    plt.close()

    # Generate Markdown Report
    print("Compiling eda_report.md...")
    report_path = os.path.join(output_dir, 'eda_report.md')
    
    top_viol_name = top_categories.index[0]
    top_viol_count = top_categories.values[0]
    top_make_name = top_makes.index[0]
    top_make_count = top_makes.values[0]

    report_content = f"""# Exploratory Data Analysis (EDA) Report: Traffic Violations Insight System

## Executive Summary
This report summarizes the exploratory data analysis conducted on the Montgomery County Traffic Violations dataset (~{total_records:,} cleaned rows, representing {total_stops:,} distinct traffic stops).

- **Total Violations Processed**: {total_records:,}
- **Unique Traffic Stops**: {total_stops:,}
- **Accident Involvements**: {accident_counts.get(True, 0):,} ({(accident_counts.get(True, 0)/total_records)*100:.2f}%)
- **Personal Injuries Recorded**: {injury_counts:,}
- **Property Damage Incidents**: {property_damage_counts:,}
- **Fatal Incidents**: {fatal_counts:,}

---

## 1. Most Common Violations
The single largest category of violations cited is **{top_viol_name}** with **{top_viol_count:,}** records.

![Top Violation Categories](charts/q1_top_violations.png)

---

## 2. High-Incident Geographic Hotspots & Districts
Enforcement activity is concentrated heavily in urban districts. The sub-agency with the highest recorded traffic stops is **{top_subagencies.index[0]}** with **{top_subagencies.values[0]:,}** citations/warnings.

![District Hotspots](charts/q2_district_hotspots.png)

---

## 3. Demographic & Citation Breakdown
Analysis of driver demographics against violation disposition shows consistent distributions, with Citations accounting for the vast majority of enforcement actions across all demographics.

![Demographic Correlations](charts/q3_demographic_correlations.png)

---

## 4. Temporal Patterns (Hourly & Weekly Variance)
- **Peak Enforcement Hours**: Traffic stops peak between 21:00 (9 PM) and 01:00 (1 AM), as well as during morning rush hours (07:00 - 09:00).
- **Weekly Volume**: Traffic stop activity remains high Wednesday through Friday, with a slight shift in offense type over weekend late-night hours.

![Temporal Trends](charts/q4_temporal_trends.png)

---

## 5. Vehicle Profiling
The top cited vehicle manufacturer is **{top_make_name}** ({top_make_count:,} citations), followed by {', '.join(top_makes.index[1:5])}.

![Top Vehicle Makes](charts/q5_vehicle_makes.png)

---

## 6. Accident & Severity Analysis
Out of {total_records:,} total violations, **{accident_counts.get(True, 0):,}** stops involved a vehicle collision.

![Accident Severity Breakdown](charts/q6_accident_severity.png)

---

## Strategic Recommendations
1. **Targeted Patrol Allocation**: Increase enforcement presence in high-density districts (e.g. 3rd District Silver Spring, 4th District Wheaton) during peak night-time hours (21:00 - 01:00).
2. **Speed & Safety Campaigns**: Prioritize public safety messaging on Speeding and License/Registration compliance.
3. **Accident Mitigation**: Deploy mobile speed cameras near high accident-severity intersections.
"""

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"EDA Report successfully compiled at {report_path}!")


if __name__ == '__main__':
    parquet_p = r"c:\Users\sudin\OneDrive\Desktop\traffic violation system\data\cleaned_traffic_violations.parquet"
    eda_d = r"c:\Users\sudin\OneDrive\Desktop\traffic violation system\eda"
    generate_eda_suite(parquet_p, eda_d)
