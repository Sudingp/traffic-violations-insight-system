"""
PowerPoint Presentation Generator for Traffic Violations Insight System.
Generates a modern widescreen (16:9) .pptx presentation file.
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE


# Theme Colors (Dark Modern Palette)
COLOR_BG = RGBColor(15, 23, 42)       # #0f172a (Dark Slate)
COLOR_CARD = RGBColor(30, 41, 59)     # #1e293b (Card Slate)
COLOR_ACCENT = RGBColor(56, 189, 248) # #38bdf8 (Sky Blue)
COLOR_TEXT_MAIN = RGBColor(248, 250, 252) # #f8fafc (Off White)
COLOR_TEXT_MUTED = RGBColor(148, 163, 184) # #94a3b8 (Muted Gray)
COLOR_GREEN = RGBColor(52, 211, 153)  # #34d399 (Emerald Green)


def apply_background(slide):
    """Sets dark slate background for slide."""
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = COLOR_BG


def add_header(slide, title_text, category_text="TRAFFIC VIOLATIONS INSIGHT SYSTEM"):
    """Adds standardized header to slides."""
    # Category / Subtitle Tracker
    cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.5), Inches(0.4))
    tf_cat = cat_box.text_frame
    tf_cat.word_wrap = True
    p_cat = tf_cat.paragraphs[0]
    p_cat.text = category_text.upper()
    p_cat.font.size = Pt(11)
    p_cat.font.bold = True
    p_cat.font.color.rgb = COLOR_ACCENT

    # Main Slide Title
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.5), Inches(0.7))
    tf_title = title_box.text_frame
    tf_title.word_wrap = True
    p_title = tf_title.paragraphs[0]
    p_title.text = title_text
    p_title.font.size = Pt(26)
    p_title.font.bold = True
    p_title.font.color.rgb = COLOR_TEXT_MAIN


def create_card_shape(slide, left, top, width, height, fill_color=COLOR_CARD, border_color=COLOR_ACCENT):
    """Adds a modern rounded rectangle card."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1.5)
    else:
        shape.line.fill.background()
    return shape


def build_presentation(output_path):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_slide_layout = prs.slide_layouts[6]

    # -------------------------------------------------------------
    # SLIDE 1: Title Slide
    # -------------------------------------------------------------
    slide1 = prs.slides.add_slide(blank_slide_layout)
    apply_background(slide1)
    
    card1 = create_card_shape(slide1, Inches(1.0), Inches(1.2), Inches(11.333), Inches(5.1))
    
    tb1 = slide1.shapes.add_textbox(Inches(1.5), Inches(1.8), Inches(10.333), Inches(3.8))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    
    p1 = tf1.paragraphs[0]
    p1.text = "Traffic Violations Insight System"
    p1.font.size = Pt(38)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_ACCENT
    p1.alignment = PP_ALIGN.LEFT
    
    p2 = tf1.add_paragraph()
    p2.text = "EDA, Data Preprocessing & Interactive Streamlit Dashboard"
    p2.font.size = Pt(22)
    p2.font.color.rgb = COLOR_TEXT_MAIN
    p2.space_before = Pt(12)
    
    p3 = tf1.add_paragraph()
    p3.text = "Domain: Transportation Safety Analytics  |  Dataset: ~2.07 Million Records (880 MB)"
    p3.font.size = Pt(14)
    p3.font.color.rgb = COLOR_TEXT_MUTED
    p3.space_before = Pt(20)

    p4 = tf1.add_paragraph()
    p4.text = "Technologies: Python, SQL, Streamlit, Pandas, NumPy, SQLite, Plotly, Seaborn, Pytest"
    p4.font.size = Pt(13)
    p4.font.bold = True
    p4.font.color.rgb = COLOR_GREEN
    p4.space_before = Pt(30)

    # -------------------------------------------------------------
    # SLIDE 2: Problem Statement & Goal
    # -------------------------------------------------------------
    slide2 = prs.slides.add_slide(blank_slide_layout)
    apply_background(slide2)
    add_header(slide2, "Problem Statement & Project Goal")

    c1 = create_card_shape(slide2, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2))
    tb = slide2.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = "⚠️ The Real-World Challenge"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_ACCENT
    
    points1 = [
        "Urban safety agencies generate millions of enforcement records annually.",
        "Raw data is noisy, duplicate-heavy, and contains format glitches (e.g. 23.11.00 for time).",
        "Invalid GPS tuples (0,0) and out-of-bounds coordinates distort spatial analysis.",
        "High memory overhead (880 MB raw CSV) makes real-time dashboarding slow without optimization."
    ]
    for pt in points1:
        p = tf.add_paragraph()
        p.text = "• " + pt
        p.font.size = Pt(13)
        p.font.color.rgb = COLOR_TEXT_MAIN
        p.space_before = Pt(10)

    c2 = create_card_shape(slide2, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.2))
    tb = slide2.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = "🎯 Core Project Goals"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN
    
    points2 = [
        "Transform 2.07M raw violation rows into structured, actionable intelligence.",
        "Engineered chunked ETL pipeline to compress storage by 77.6% (197 MB Parquet).",
        "Deploy indexed SQLite relational database for sub-second SQL queries.",
        "Conduct systematic EDA answering 6 core transportation mobility questions.",
        "Deliver an aesthetic, dynamic Streamlit web dashboard for public safety stakeholders."
    ]
    for pt in points2:
        p = tf.add_paragraph()
        p.text = "• " + pt
        p.font.size = Pt(13)
        p.font.color.rgb = COLOR_TEXT_MAIN
        p.space_before = Pt(10)

    # -------------------------------------------------------------
    # SLIDE 3: Business Use Cases & Stakeholders
    # -------------------------------------------------------------
    slide3 = prs.slides.add_slide(blank_slide_layout)
    apply_background(slide3)
    add_header(slide3, "Business Use Cases & Target Stakeholders")

    use_cases = [
        ("🚔 Police & Law Enforcement", "Optimize patrol vehicle scheduling and allocate manpower to high-density arterial districts during peak night hours (21:00 - 01:00)."),
        ("🛣️ Department of Transportation (DOT)", "Identify accident collision hotspots and deploy traffic calming measures, automated speed cameras, and signage."),
        ("🏙️ City Safety Boards", "Track violation trends, crash rates, and demographic distributions to evaluate safety program effectiveness."),
        ("📊 Urban Planners & Policy Makers", "Formulate data-backed traffic policies, seatbelt compliance campaigns, and registration enforcement laws.")
    ]
    
    for i, (title, desc) in enumerate(use_cases):
        row = i // 2
        col = i % 2
        left = Inches(0.8 + col * 5.9)
        top = Inches(1.6 + row * 2.7)
        
        create_card_shape(slide3, left, top, Inches(5.6), Inches(2.4))
        tb = slide3.shapes.add_textbox(left + Inches(0.2), top + Inches(0.2), Inches(5.2), Inches(2.0))
        tf = tb.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = COLOR_ACCENT
        
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(13)
        p2.font.color.rgb = COLOR_TEXT_MAIN
        p2.space_before = Pt(8)

    # -------------------------------------------------------------
    # SLIDE 4: End-to-End System Architecture
    # -------------------------------------------------------------
    slide4 = prs.slides.add_slide(blank_slide_layout)
    apply_background(slide4)
    add_header(slide4, "End-to-End System Architecture")

    steps = [
        ("1. Raw Data Ingest", "Traffic_Violations.csv\n(2.07M Rows / 880 MB)"),
        ("2. Chunked Preprocessing", "src/preprocessing.py\nCleaning, Filtering & Feature Eng."),
        ("3. Optimized Storage", "Parquet (197 MB)\nSQLite DB (Indexed Tables)"),
        ("4. Automated EDA", "eda/generate_eda.py\n6 Core Charts & Markdown Report"),
        ("5. Streamlit App", "app.py\nInteractive Dashboard & SQL Engine")
    ]
    
    for i, (stitle, sdesc) in enumerate(steps):
        left = Inches(0.8 + i * 2.38)
        top = Inches(2.2)
        create_card_shape(slide4, left, top, Inches(2.2), Inches(3.8))
        
        tb = slide4.shapes.add_textbox(left + Inches(0.1), top + Inches(0.3), Inches(2.0), Inches(3.2))
        tf = tb.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = stitle
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = COLOR_ACCENT
        p.alignment = PP_ALIGN.CENTER
        
        p2 = tf.add_paragraph()
        p2.text = sdesc
        p2.font.size = Pt(12)
        p2.font.color.rgb = COLOR_TEXT_MAIN
        p2.space_before = Pt(16)
        p2.alignment = PP_ALIGN.CENTER

    # -------------------------------------------------------------
    # SLIDE 5: Data Preprocessing & Cleaning Rules
    # -------------------------------------------------------------
    slide5 = prs.slides.add_slide(blank_slide_layout)
    apply_background(slide5)
    add_header(slide5, "Data Cleaning & Preprocessing Rules")

    rules = [
        ("SeqID & Multi-Charge", "Deduplicated exact row copies (3,821 dropped). Identified multi-charge stops (SeqID appearing >1 time) via Is_Multi_Charge flag."),
        ("Date & Time Standardizing", "Fixed time glitches (23.11.00 -> 23:11:00). Combined into ISO Datetime_Of_Stop. Filtered invalid years outside 1990-2026."),
        ("GPS Coordinates Sanitization", "Converted Lat/Lon to numeric. Mapped invalid (0,0) tuples and coordinates outside US bounds to NaN."),
        ("12-Flag Boolean Normalization", "Converted Yes/No, Y/N, TRUE/FALSE, 1/0 strings into clean bool (True/False) for Accident, Belts, Alcohol, Work_Zone, etc."),
        ("Make & Color Standardization", "Normalized brand typos (CHEV -> CHEVROLET, TOYT -> TOYOTA) and color codes (BLK -> BLACK, SILV -> SILVER) via dict mappers."),
        ("Feature Engineering", "Extracted Stop_Hour, Time_Of_Day buckets, Day_Of_Week, Month_Name, Violation_Category, and Accident_Severity_Index.")
    ]

    for i, (rtitle, rdesc) in enumerate(rules):
        r = i // 2
        c = i % 2
        left = Inches(0.8 + c * 5.9)
        top = Inches(1.5 + r * 1.8)
        
        create_card_shape(slide5, left, top, Inches(5.6), Inches(1.6))
        tb = slide5.shapes.add_textbox(left + Inches(0.2), top + Inches(0.15), Inches(5.2), Inches(1.3))
        tf = tb.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = "🔹 " + rtitle
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = COLOR_ACCENT
        
        p2 = tf.add_paragraph()
        p2.text = rdesc
        p2.font.size = Pt(11)
        p2.font.color.rgb = COLOR_TEXT_MAIN
        p2.space_before = Pt(4)

    # -------------------------------------------------------------
    # SLIDE 6: Data Optimization & Performance Metrics
    # -------------------------------------------------------------
    slide6 = prs.slides.add_slide(blank_slide_layout)
    apply_background(slide6)
    add_header(slide6, "Data Optimization & Performance Metrics")

    metrics = [
        ("880 MB ➔ 197 MB", "77.6% Compression Ratio via Parquet Storage"),
        ("2,067,788", "Final Cleaned Records Processed"),
        ("1,178,080", "Distinct Traffic Stops (SeqIDs) Analyzed"),
        ("500,000", "Chunk Size for RAM-Safe Batch Execution")
    ]
    
    for i, (mval, mlabel) in enumerate(metrics):
        left = Inches(0.8 + i * 2.9)
        top = Inches(1.6)
        create_card_shape(slide6, left, top, Inches(2.7), Inches(2.0))
        
        tb = slide6.shapes.add_textbox(left + Inches(0.1), top + Inches(0.3), Inches(2.5), Inches(1.4))
        tf = tb.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = mval
        p.font.size = Pt(22)
        p.font.bold = True
        p.font.color.rgb = COLOR_GREEN
        p.alignment = PP_ALIGN.CENTER
        
        p2 = tf.add_paragraph()
        p2.text = mlabel
        p2.font.size = Pt(12)
        p2.font.color.rgb = COLOR_TEXT_MAIN
        p2.space_before = Pt(8)
        p2.alignment = PP_ALIGN.CENTER

    c_bot = create_card_shape(slide6, Inches(0.8), Inches(3.9), Inches(11.7), Inches(2.9))
    tb_bot = slide6.shapes.add_textbox(Inches(1.0), Inches(4.1), Inches(11.3), Inches(2.5))
    tf_bot = tb_bot.text_frame
    tf_bot.word_wrap = True
    
    p = tf_bot.paragraphs[0]
    p.text = "💡 Memory Optimization Techniques Applied:"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_ACCENT
    
    opt_list = [
        "Category Downcasting: Converted high-cardinality repeat text (Agency, Make, Color, Gender, Race) to 'category' dtypes.",
        "Numeric Precision: Downcasted Stop_Hour to int8, Year to int16, and GPS coordinates to float32.",
        "Binary Flags: Replaced 12 text columns ('Yes'/'No') with compact 1-byte boolean types.",
        "Streamlit Caching: Cached data loading using @st.cache_data for instant interactive dashboard rendering."
    ]
    for opt in opt_list:
        p = tf_bot.add_paragraph()
        p.text = "• " + opt
        p.font.size = Pt(12)
        p.font.color.rgb = COLOR_TEXT_MAIN
        p.space_before = Pt(6)

    # -------------------------------------------------------------
    # SLIDE 7: SQL Database Design & Indexing
    # -------------------------------------------------------------
    slide7 = prs.slides.add_slide(blank_slide_layout)
    apply_background(slide7)
    add_header(slide7, "SQL Database Design & Indexing Strategy")

    c_sql = create_card_shape(slide7, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2))
    tb = slide7.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = "🗄️ SQLite Database Architecture"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = COLOR_ACCENT
    
    sql_points = [
        "Database File: data/traffic_violations.db",
        "Main Table: traffic_violations (2,067,788 indexed records).",
        "Performance Indexing: Created 9 B-Tree indexes on high-frequency query columns.",
        "Indexed Columns: SeqID, Date_Of_Stop, Agency, SubAgency, Violation_Type, Violation_Category, Make, Accident, Demographics.",
        "Complexity Gain: Converted full table scans O(N) to log-time lookups O(log N)."
    ]
    for s in sql_points:
        p = tf.add_paragraph()
        p.text = "• " + s
        p.font.size = Pt(12)
        p.font.color.rgb = COLOR_TEXT_MAIN
        p.space_before = Pt(8)

    c_kpi = create_card_shape(slide7, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.2))
    tb = slide7.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = "📊 Key SQL Aggregation Statistics"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN
    
    kpis = [
        "Total Violations: 2,067,788",
        "Distinct Stop Events: 1,178,080",
        "Accident Crashes: 56,478 (2.73% Collision Rate)",
        "Personal Injuries: 25,108",
        "Fatal Incidents: 567",
        "Alcohol-Involved Stops: 2,615",
        "Searches Conducted: 89,243"
    ]
    for k in kpis:
        p = tf.add_paragraph()
        p.text = "✔ " + k
        p.font.size = Pt(13)
        p.font.color.rgb = COLOR_TEXT_MAIN
        p.space_before = Pt(10)

    # -------------------------------------------------------------
    # SLIDE 8: Exploratory Data Analysis (EDA) - Key Findings
    # -------------------------------------------------------------
    slide8 = prs.slides.add_slide(blank_slide_layout)
    apply_background(slide8)
    add_header(slide8, "Exploratory Data Analysis (EDA) - Core Findings")

    eda_q = [
        ("Q1: Top Violations", "License/Registration/Documentation (32.4%), Speeding (24.1%), and Equipment Maintenance (18.6%) account for over 75% of citations."),
        ("Q2: Hotspot Districts", "Sub-Agencies 3rd District (Silver Spring) and 4th District (Wheaton) experience highest enforcement volume."),
        ("Q3: Temporal Patterns", "Stops peak twice daily: morning rush hours (07:00-09:00) and heavily late at night (21:00 - 01:00 AM)."),
        ("Q4: Accident Factors", "2.73% of stops involved collisions. Night-time stops showed 3.4x higher correlation with severe accidents & alcohol."),
        ("Q5: Vehicle Profiling", "Top cited manufacturers: Chevrolet, Ford, Toyota, Honda, and Nissan."),
        ("Q6: Enforcement Outcome", "Citations account for majority of stops, followed by Warnings and ESERO safety notices.")
    ]
    
    for i, (qtitle, qdesc) in enumerate(eda_q):
        r = i // 2
        c = i % 2
        left = Inches(0.8 + c * 5.9)
        top = Inches(1.5 + r * 1.8)
        
        create_card_shape(slide8, left, top, Inches(5.6), Inches(1.6))
        tb = slide8.shapes.add_textbox(left + Inches(0.2), top + Inches(0.15), Inches(5.2), Inches(1.3))
        tf = tb.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = qtitle
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = COLOR_ACCENT
        
        p2 = tf.add_paragraph()
        p2.text = qdesc
        p2.font.size = Pt(11)
        p2.font.color.rgb = COLOR_TEXT_MAIN
        p2.space_before = Pt(4)

    # -------------------------------------------------------------
    # SLIDE 9: Streamlit Interactive Dashboard Features
    # -------------------------------------------------------------
    slide9 = prs.slides.add_slide(blank_slide_layout)
    apply_background(slide9)
    add_header(slide9, "Interactive Streamlit Dashboard Features")

    features = [
        ("🎛️ Dynamic Sidebar Filters", "Filter by Date Range, Agency, SubAgency, Violation Category, Type, Vehicle Make, Race, Gender, and Accident toggle."),
        ("📊 Executive KPI Cards", "Real-time cards displaying Total Violations, Unique Stops, Accident Rate %, Injury counts, and Top Brand."),
        ("🗺️ Geospatial Mapbox Heatmap", "Interactive Mapbox scatter and density heatmaps displaying GPS incident coordinates and crash hotspots."),
        ("📈 Temporal & Vehicle Analytics", "Hourly line plots, day-of-week bar charts, time-of-day matrices, and vehicle brand breakdown."),
        ("💻 Interactive SQL Engine", "Built-in SQL editor executing custom queries directly against SQLite DB with CSV download support.")
    ]

    for i, (ftitle, fdesc) in enumerate(features):
        left = Inches(0.8)
        top = Inches(1.5 + i * 1.1)
        create_card_shape(slide9, left, top, Inches(11.7), Inches(0.95))
        
        tb = slide9.shapes.add_textbox(left + Inches(0.2), top + Inches(0.1), Inches(11.3), Inches(0.75))
        tf = tb.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = ftitle + " — "
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = COLOR_ACCENT
        
        p_desc = p.add_run()
        p_desc.text = fdesc
        p_desc.font.bold = False
        p_desc.font.color.rgb = COLOR_TEXT_MAIN

    # -------------------------------------------------------------
    # SLIDE 10: Code Quality & Testing Suite
    # -------------------------------------------------------------
    slide10 = prs.slides.add_slide(blank_slide_layout)
    apply_background(slide10)
    add_header(slide10, "Software Engineering & Testing Suite")

    c_qual = create_card_shape(slide10, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2))
    tb = slide10.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = "PEP 8 & Clean Code Standards"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = COLOR_ACCENT
    
    qual_list = [
        "Modular Architecture: Decoupled into src/preprocessing.py, src/database.py, eda/generate_eda.py, and app.py.",
        "PEP 8 Formatting: Meaningful variable naming, docstrings, and robust error handling.",
        "Version Control: Fully tracked git repository pushed to GitHub."
    ]
    for q in qual_list:
        p = tf.add_paragraph()
        p.text = "✔ " + q
        p.font.size = Pt(12)
        p.font.color.rgb = COLOR_TEXT_MAIN
        p.space_before = Pt(12)

    c_test = create_card_shape(slide10, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.2))
    tb = slide10.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = "🧪 Pytest Automated Test Suite"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN
    
    test_list = [
        "Unit Test Coverage: 6/6 tests passing in 0.79s.",
        "test_preprocessing.py: Tests boolean parser, time cleaner, description classifier, and sample ETL output.",
        "test_database.py: Tests SQLite table creation, data loading, indexing, and KPI query output."
    ]
    for t in test_list:
        p = tf.add_paragraph()
        p.text = "✔ " + t
        p.font.size = Pt(12)
        p.font.color.rgb = COLOR_TEXT_MAIN
        p.space_before = Pt(12)

    # -------------------------------------------------------------
    # SLIDE 11: Policy Recommendations & Impact
    # -------------------------------------------------------------
    slide11 = prs.slides.add_slide(blank_slide_layout)
    apply_background(slide11)
    add_header(slide11, "Strategic Policy & Safety Recommendations")

    recs = [
        ("1. Dynamic Patrol Allocation", "Shift active patrol vehicles to top incident districts (3rd & 4th Districts) during late-night peak hours (21:00 - 01:00) when collision severity spikes."),
        ("2. Automated Infrastructure", "Deploy mobile speed and red-light enforcement cameras near identified geographic crash hotspots."),
        ("3. Target Outreach Programs", "Launch public education campaigns focusing on registration compliance, seatbelt usage, and night-time impaired driving risks.")
    ]
    
    for i, (rtitle, rdesc) in enumerate(recs):
        top = Inches(1.6 + i * 1.7)
        create_card_shape(slide11, Inches(0.8), top, Inches(11.7), Inches(1.4))
        
        tb = slide11.shapes.add_textbox(Inches(1.0), top + Inches(0.15), Inches(11.3), Inches(1.1))
        tf = tb.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = rtitle
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = COLOR_ACCENT
        
        p2 = tf.add_paragraph()
        p2.text = rdesc
        p2.font.size = Pt(12)
        p2.font.color.rgb = COLOR_TEXT_MAIN
        p2.space_before = Pt(4)

    # -------------------------------------------------------------
    # SLIDE 12: Conclusion & Q&A
    # -------------------------------------------------------------
    slide12 = prs.slides.add_slide(blank_slide_layout)
    apply_background(slide12)

    c_end = create_card_shape(slide12, Inches(1.5), Inches(1.5), Inches(10.333), Inches(4.5))
    tb_end = slide12.shapes.add_textbox(Inches(1.8), Inches(2.2), Inches(9.733), Inches(3.1))
    tf_end = tb_end.text_frame
    tf_end.word_wrap = True
    
    p = tf_end.paragraphs[0]
    p.text = "Thank You!"
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = COLOR_ACCENT
    p.alignment = PP_ALIGN.CENTER
    
    p2 = tf_end.add_paragraph()
    p2.text = "Traffic Violations Insight System"
    p2.font.size = Pt(22)
    p2.font.color.rgb = COLOR_TEXT_MAIN
    p2.space_before = Pt(12)
    p2.alignment = PP_ALIGN.CENTER
    
    p3 = tf_end.add_paragraph()
    p3.text = "GitHub: https://github.com/Sudingp/traffic-violations-insight-system"
    p3.font.size = Pt(14)
    p3.font.color.rgb = COLOR_GREEN
    p3.space_before = Pt(20)
    p3.alignment = PP_ALIGN.CENTER

    p4 = tf_end.add_paragraph()
    p4.text = "Questions & Evaluation Discussion"
    p4.font.size = Pt(18)
    p4.font.bold = True
    p4.font.color.rgb = COLOR_TEXT_MUTED
    p4.space_before = Pt(16)
    p4.alignment = PP_ALIGN.CENTER

    # Save presentation
    prs.save(output_path)
    print(f"PowerPoint presentation generated successfully at: {output_path}")


if __name__ == '__main__':
    out_ppt = r"c:\Users\sudin\OneDrive\Desktop\traffic violation system\Traffic_Violations_Insight_System.pptx"
    build_presentation(out_ppt)
