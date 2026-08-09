"""
Traffic Violations Preprocessing & Data Cleaning Module
Optimized for processing large-scale datasets (~2M+ rows).
"""

import os
import re
import numpy as np
import pandas as pd


# Brand mapping dictionary for vehicle make normalization
MAKE_MAPPING = {
    'CHEV': 'CHEVROLET', 'CHEVY': 'CHEVROLET', 'CHEVROLET': 'CHEVROLET',
    'FORD': 'FORD', 'FRD': 'FORD',
    'TOYT': 'TOYOTA', 'TOYOTA': 'TOYOTA', 'TOYO': 'TOYOTA',
    'HONDA': 'HONDA', 'HOND': 'HONDA',
    'NISS': 'NISSAN', 'NISSAN': 'NISSAN', 'NIS': 'NISSAN',
    'DODG': 'DODGE', 'DODGE': 'DODGE',
    'BMW': 'BMW', 'B.M.W.': 'BMW',
    'HYUN': 'HYUNDAI', 'HYUNDAI': 'HYUNDAI', 'HYUN': 'HYUNDAI',
    'MERC': 'MERCEDES-BENZ', 'MERCEDES': 'MERCEDES-BENZ', 'BENZ': 'MERCEDES-BENZ', 'MB': 'MERCEDES-BENZ',
    'VOLK': 'VOLKSWAGEN', 'VW': 'VOLKSWAGEN', 'VOLKSWAGEN': 'VOLKSWAGEN',
    'LEXS': 'LEXUS', 'LEXU': 'LEXUS', 'LEXUS': 'LEXUS',
    'ACUR': 'ACURA', 'ACURA': 'ACURA',
    'JEEP': 'JEEP', 'JEP': 'JEEP',
    'SUBU': 'SUBARU', 'SUB': 'SUBARU', 'SUBARU': 'SUBARU',
    'MAZD': 'MAZDA', 'MAZDA': 'MAZDA',
    'KIA': 'KIA', 'KIA ': 'KIA',
    'AUDI': 'AUDI',
    'GMC': 'GMC', 'G.M.C.': 'GMC',
    'CADI': 'CADILLAC', 'CAD': 'CADILLAC', 'CADILLAC': 'CADILLAC',
    'INFI': 'INFINITI', 'INFINITI': 'INFINITI', 'INF': 'INFINITI',
    'PONT': 'PONTIAC', 'PONTIAC': 'PONTIAC',
    'SATU': 'SATURN', 'SATURN': 'SATURN',
    'VOLV': 'VOLVO', 'VOLVO': 'VOLVO',
    'BUIC': 'BUICK', 'BUICK': 'BUICK',
    'CHRY': 'CHRYSLER', 'CHRYSLER': 'CHRYSLER',
    'SCIO': 'SCION', 'SCION': 'SCION',
    'LNDR': 'LAND ROVER', 'ROVER': 'LAND ROVER', 'LAND ROVER': 'LAND ROVER',
    'MINI': 'MINI',
    'MITS': 'MITSUBISHI', 'MITSUBISHI': 'MITSUBISHI',
    'TESL': 'TESLA', 'TESLA': 'TESLA',
    'RAM': 'RAM',
    'FREI': 'FREIGHTLINER', 'FREIGHTLINER': 'FREIGHTLINER'
}

# Color mapping dictionary
COLOR_MAPPING = {
    'BLK': 'BLACK', 'BLACK': 'BLACK',
    'SILV': 'SILVER', 'SILVER': 'SILVER', 'SLV': 'SILVER',
    'WHI': 'WHITE', 'WHITE': 'WHITE', 'WHT': 'WHITE',
    'RED': 'RED',
    'BLUE': 'BLUE', 'BLU': 'BLUE',
    'GREY': 'GRAY', 'GRAY': 'GRAY', 'GRY': 'GRAY',
    'GRN': 'GREEN', 'GREEN': 'GREEN',
    'YEL': 'YELLOW', 'YELLOW': 'YELLOW',
    'BRN': 'BROWN', 'BROWN': 'BROWN',
    'GOLD': 'GOLD', 'GLD': 'GOLD',
    'TAN': 'TAN',
    'ORNG': 'ORANGE', 'ORANGE': 'ORANGE',
    'PURP': 'PURPLE', 'PURPLE': 'PURPLE', 'PUR': 'PURPLE',
    'MAROON': 'MAROON', 'BRONZE': 'BRONZE', 'COPPER': 'COPPER',
    'BEIGE': 'BEIGE'
}


def clean_boolean_value(val) -> bool:
    """Convert heterogeneous Yes/No, Y/N, TRUE/FALSE, 1/0 values to boolean."""
    if pd.isna(val):
        return False
    val_str = str(val).strip().upper()
    return val_str in ['YES', 'Y', 'TRUE', '1', 'T']


def categorize_description(desc: str) -> str:
    """Categorize violation description into standard functional buckets."""
    if pd.isna(desc):
        return 'Other Violation'
    d = str(desc).upper()
    if 'SPEED' in d:
        return 'Speeding'
    elif any(k in d for k in ['LICENSE', 'REGISTR', 'REGISTER', 'UNREGISTER', 'TITLE', 'PLATE', 'TAG', 'PERMIT', 'INSURANCE']):
        return 'License / Registration / Documentation'
    elif any(k in d for k in ['BELT', 'CHILD', 'RESTRICT', 'SEAT']):
        return 'Seatbelt & Safety Restraint'
    elif any(k in d for k in ['SIGNAL', 'RED LIGHT', 'STOP SIGN', 'LANE', 'YIELD', 'TURN', 'PASSING']):
        return 'Traffic Signal & Control'
    elif any(k in d for k in ['HEADLIGHT', 'TAILLIGHT', 'TIRE', 'WINDOW', 'TINT', 'MIRROR', 'EQUIP', 'LAMP', 'MUFFLER', 'EXHAUST', 'LIGHT']):
        return 'Vehicle Equipment & Maintenance'
    elif any(k in d for k in ['ALCOHOL', 'DRUG', 'INTOXICATED', 'UNDER THE INFLUENCE', 'DUI', 'DWI', 'DRINK']):
        return 'DUI / Alcohol / Substance'
    elif any(k in d for k in ['PHONE', 'CELL', 'HANDHELD', 'RECKLESS', 'NEGLIGENT', 'FOLLOWING', 'DISTRACTED', 'ACCIDENT']):
        return 'Distracted / Reckless Driving'
    return 'Other Violation'


def clean_time_string(time_val) -> str:
    """Fix time formatting (e.g. 23.11.00 -> 23:11:00)."""
    if pd.isna(time_val):
        return '00:00:00'
    t_str = str(time_val).strip().replace('.', ':')
    parts = t_str.split(':')
    if len(parts) == 3:
        try:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            return f"{h:02d}:{m:02d}:{s:02d}"
        except ValueError:
            pass
    elif len(parts) == 2:
        try:
            h, m = int(parts[0]), int(parts[1])
            return f"{h:02d}:{m:02d}:00"
        except ValueError:
            pass
    return '00:00:00'


def process_traffic_violations_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Main processing pipeline for raw traffic violations DataFrame.
    Applies standardization, missing value strategies, validation, and feature engineering.
    """
    print(f"Starting cleaning on dataset with {len(df):,} rows...")
    
    # 1. Standardize column names (remove leading/trailing whitespace)
    df.columns = [c.strip() for c in df.columns]

    # Map raw column names to standardized snake_case internal names
    col_mapping = {
        'SeqID': 'SeqID',
        'Date Of Stop': 'Date_Of_Stop',
        'Time Of Stop': 'Time_Of_Stop',
        'Agency': 'Agency',
        'SubAgency': 'SubAgency',
        'Description': 'Description',
        'Location': 'Location',
        'Latitude': 'Latitude',
        'Longitude': 'Longitude',
        'Accident': 'Accident',
        'Belts': 'Belts',
        'Personal Injury': 'Personal_Injury',
        'Property Damage': 'Property_Damage',
        'Fatal': 'Fatal',
        'Commercial License': 'Commercial_License',
        'HAZMAT': 'HAZMAT',
        'Commercial Vehicle': 'Commercial_Vehicle',
        'Alcohol': 'Alcohol',
        'Work Zone': 'Work_Zone',
        'Search Conducted': 'Search_Conducted',
        'Search Disposition': 'Search_Disposition',
        'Search Outcome': 'Search_Outcome',
        'Search Reason': 'Search_Reason',
        'Search Reason For Stop': 'Search_Reason_For_Stop',
        'Search Type': 'Search_Type',
        'Search Arrest Reason': 'Search_Arrest_Reason',
        'State': 'State',
        'VehicleType': 'VehicleType',
        'Year': 'Year',
        'Make': 'Make',
        'Model': 'Model',
        'Color': 'Color',
        'Violation Type': 'Violation_Type',
        'Charge': 'Charge',
        'Article': 'Article',
        'Contributed To Accident': 'Contributed_To_Accident',
        'Race': 'Race',
        'Gender': 'Gender',
        'Driver City': 'Driver_City',
        'Driver State': 'Driver_State',
        'DL State': 'DL_State',
        'Arrest Type': 'Arrest_Type',
        'Geolocation': 'Geolocation'
    }
    df = df.rename(columns=col_mapping)

    # 2. SeqID - String type, clean whitespace
    df['SeqID'] = df['SeqID'].astype(str).str.strip()

    # 3. Deduplicate exact duplicate rows
    initial_rows = len(df)
    df = df.drop_duplicates()
    dedup_count = initial_rows - len(df)
    if dedup_count > 0:
        print(f"Removed {dedup_count:,} exact duplicate rows.")

    # 4. Multi-charge flag per stop (SeqID frequency)
    seq_counts = df['SeqID'].value_counts()
    multi_charge_ids = set(seq_counts[seq_counts > 1].index)
    df['Is_Multi_Charge'] = df['SeqID'].isin(multi_charge_ids)

    # 5. Date & Time Standardization
    print("Processing Dates & Times...")
    df['Date_Of_Stop'] = pd.to_datetime(df['Date_Of_Stop'], errors='coerce')
    
    # Filter out absurd years (< 1990 or > current year 2026)
    valid_date_mask = df['Date_Of_Stop'].dt.year.between(1990, 2026)
    df.loc[~valid_date_mask, 'Date_Of_Stop'] = pd.NaT

    df['Time_Of_Stop'] = df['Time_Of_Stop'].apply(clean_time_string)

    # Combined datetime timestamp
    date_str = df['Date_Of_Stop'].dt.strftime('%Y-%m-%d').fillna('1970-01-01')
    df['Datetime_Of_Stop'] = pd.to_datetime(date_str + ' ' + df['Time_Of_Stop'], errors='coerce')

    # Time-based Feature Engineering
    df['Stop_Hour'] = df['Datetime_Of_Stop'].dt.hour.fillna(-1).astype('int8')
    
    # Time of Day Buckets
    bins = [-1, 5, 11, 17, 23]
    labels = ['Night (00:00-06:00)', 'Morning (06:00-12:00)', 'Afternoon (12:00-18:00)', 'Evening (18:00-24:00)']
    df['Time_Of_Day'] = pd.cut(df['Stop_Hour'], bins=bins, labels=labels, right=True).astype(str)
    df.loc[df['Stop_Hour'] == -1, 'Time_Of_Day'] = 'Unknown'

    df['Day_Of_Week'] = df['Datetime_Of_Stop'].dt.day_name().fillna('Unknown')
    df['Month_Name'] = df['Datetime_Of_Stop'].dt.month_name().fillna('Unknown')
    df['Stop_Year'] = df['Datetime_Of_Stop'].dt.year.fillna(0).astype('int16')

    # 6. Text Columns Cleaning & Normalization
    print("Normalizing Text & Categoricals...")
    text_cols_upper = ['Agency', 'SubAgency', 'Description', 'Location', 'State', 'Driver_City', 'Driver_State', 'DL_State', 'Arrest_Type', 'Charge', 'Article']
    for col in text_cols_upper:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
            df.loc[df[col].isin(['NAN', 'NONE', 'NULL', '']), col] = 'UNKNOWN'

    # Extract SubAgency District Number if available
    df['District_Number'] = df['SubAgency'].str.extract(r'(\d+)', expand=False).fillna('N/A')

    # Categorize Description into Violation Category
    df['Violation_Category'] = df['Description'].apply(categorize_description)

    # 7. Coordinates Validation (Latitude, Longitude, Geolocation)
    print("Validating Geographic Coordinates...")
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')

    # Replace (0.0, 0.0) coordinates with NaN
    zero_coord_mask = (df['Latitude'] == 0.0) & (df['Longitude'] == 0.0)
    df.loc[zero_coord_mask, ['Latitude', 'Longitude']] = np.nan

    # US Maryland Bounding Box check (~ Lat 24-50 N, Lon -125 to -65 W)
    valid_lat = df['Latitude'].between(24.0, 50.0)
    valid_lon = df['Longitude'].between(-125.0, -65.0)
    df.loc[~(valid_lat & valid_lon), ['Latitude', 'Longitude']] = np.nan

    # Sync Geolocation column
    df['Geolocation'] = np.where(
        df['Latitude'].notna() & df['Longitude'].notna(),
        '(' + df['Latitude'].round(5).astype(str) + ', ' + df['Longitude'].round(5).astype(str) + ')',
        'N/A'
    )

    # 8. Standardize Boolean Columns
    print("Standardizing Boolean Fields...")
    bool_cols = [
        'Accident', 'Belts', 'Personal_Injury', 'Property_Damage', 'Fatal',
        'Commercial_License', 'HAZMAT', 'Commercial_Vehicle', 'Alcohol',
        'Work_Zone', 'Search_Conducted', 'Contributed_To_Accident'
    ]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_boolean_value)

    # 9. Search Outcome Metadata
    search_cols = [
        'Search_Disposition', 'Search_Outcome', 'Search_Reason',
        'Search_Reason_For_Stop', 'Search_Type', 'Search_Arrest_Reason'
    ]
    for col in search_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
            df.loc[df[col].isin(['NAN', 'NONE', 'NULL', '']), col] = 'NOT APPLICABLE'

    # 10. Vehicle Year & Make & Model & Color
    print("Cleaning Vehicle Attributes...")
    df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
    valid_year_mask = df['Year'].between(1960, 2026)
    df.loc[~valid_year_mask, 'Year'] = np.nan

    # Vehicle Make Normalization
    df['Make_Raw'] = df['Make'].astype(str).str.strip().str.upper()
    df['Make'] = df['Make_Raw'].map(MAKE_MAPPING).fillna(df['Make_Raw'])
    df.loc[df['Make'].isin(['NAN', 'NONE', 'NULL', '', 'UNKNOWN']), 'Make'] = 'UNKNOWN'

    # Vehicle Color Normalization
    df['Color_Raw'] = df['Color'].astype(str).str.strip().str.upper()
    df['Color'] = df['Color_Raw'].map(COLOR_MAPPING).fillna(df['Color_Raw'])
    df.loc[df['Color'].isin(['NAN', 'NONE', 'NULL', '']), 'Color'] = 'UNKNOWN'

    # Vehicle Model
    df['Model'] = df['Model'].astype(str).str.strip().str.upper()
    df.loc[df['Model'].isin(['NAN', 'NONE', 'NULL', '']), 'Model'] = 'UNKNOWN'

    # Vehicle Type
    df['VehicleType'] = df['VehicleType'].astype(str).str.strip()
    df.loc[df['VehicleType'].isin(['nan', 'None', '']), 'VehicleType'] = 'Unknown'

    # 11. Demographic Columns (Race & Gender)
    print("Cleaning Demographics...")
    df['Race'] = df['Race'].astype(str).str.strip().str.upper()
    df.loc[df['Race'].isin(['NAN', 'NONE', 'NULL', '']), 'Race'] = 'OTHER'

    df['Gender'] = df['Gender'].astype(str).str.strip().str.upper()
    gender_map = {'M': 'M', 'MALE': 'M', 'F': 'F', 'FEMALE': 'F'}
    df['Gender'] = df['Gender'].map(gender_map).fillna('Unknown')

    # 12. Violation Type
    df['Violation_Type'] = df['Violation_Type'].astype(str).str.strip().str.title()
    df.loc[df['Violation_Type'].isin(['Nan', 'None', '']), 'Violation_Type'] = 'Citation'

    # 13. Feature Engineering: Accident Severity Index
    # 0 = No accident, 1 = Property Damage, 2 = Personal Injury, 3 = Fatal
    severity = np.zeros(len(df), dtype=int)
    severity[df['Property_Damage']] = 1
    severity[df['Personal_Injury']] = 2
    severity[df['Fatal']] = 3
    df['Accident_Severity_Index'] = severity

    # 14. Convert High-Cardinality Repeating Strings to Categorical dtypes for Memory Optimization
    category_cols = [
        'Agency', 'SubAgency', 'District_Number', 'Violation_Type', 'Violation_Category',
        'State', 'Driver_State', 'DL_State', 'Gender', 'Race', 'Make', 'Color',
        'Time_Of_Day', 'Day_Of_Week', 'Month_Name', 'Arrest_Type'
    ]
    for col in category_cols:
        df[col] = df[col].astype('category')

    print(f"Data cleaning finished successfully! Final row count: {len(df):,}")
    return df


def execute_etl_pipeline(input_csv_path: str, output_parquet_path: str):
    """Executes chunked ETL process from raw CSV to optimized Parquet format."""
    if not os.path.exists(input_csv_path):
        raise FileNotFoundError(f"Input file not found: {input_csv_path}")

    print(f"Reading raw CSV: {input_csv_path}...")
    # Read in chunks to prevent high memory spikes
    chunk_size = 500000
    chunks = []
    
    for i, chunk in enumerate(pd.read_csv(input_csv_path, chunksize=chunk_size, low_memory=False)):
        print(f"Processing chunk {i+1} ({len(chunk):,} rows)...")
        cleaned_chunk = process_traffic_violations_df(chunk)
        chunks.append(cleaned_chunk)

    print("Concatenating processed chunks...")
    final_df = pd.concat(chunks, ignore_index=True)
    
    # Final global deduplication across chunk boundaries
    final_rows = len(final_df)
    final_df = final_df.drop_duplicates()
    if len(final_df) < final_rows:
        print(f"Removed additional {final_rows - len(final_df):,} cross-chunk duplicate rows.")

    # Re-calculate Is_Multi_Charge globally
    seq_counts = final_df['SeqID'].value_counts()
    multi_charge_ids = set(seq_counts[seq_counts > 1].index)
    final_df['Is_Multi_Charge'] = final_df['SeqID'].isin(multi_charge_ids)

    os.makedirs(os.path.dirname(output_parquet_path), exist_ok=True)
    print(f"Saving cleaned dataset to Parquet: {output_parquet_path}...")
    final_df.to_parquet(output_parquet_path, index=False)
    print(f"Successfully saved Parquet file! Size: {os.path.getsize(output_parquet_path) / (1024*1024):.2f} MB")
    return final_df


if __name__ == '__main__':
    raw_csv = r"c:\Users\sudin\OneDrive\Desktop\traffic violation system\Traffic_Violations.csv"
    out_parquet = r"c:\Users\sudin\OneDrive\Desktop\traffic violation system\data\cleaned_traffic_violations.parquet"
    execute_etl_pipeline(raw_csv, out_parquet)
