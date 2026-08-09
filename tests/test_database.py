"""
Unit tests for database module.
"""

import os
import sqlite3
import pandas as pd
import pytest
from src.database import TrafficViolationsDB


@pytest.fixture
def test_db_setup(tmp_path):
    db_file = tmp_path / "test_traffic.db"
    parquet_file = tmp_path / "test_traffic.parquet"

    # Create dummy DataFrame
    dummy_data = {
        'SeqID': ['s1', 's2'],
        'Date_Of_Stop': pd.to_datetime(['2023-05-01', '2023-08-31']),
        'Time_Of_Stop': ['23:11:00', '16:41:00'],
        'Agency': ['MCP', 'MCP'],
        'SubAgency': ['3rd District', '6th District'],
        'Description': ['SPEEDING', 'NO LICENSE'],
        'Location': ['MAIN ST', 'OAKMONT AVE'],
        'Latitude': [39.0, 39.1],
        'Longitude': [-77.1, -77.2],
        'Accident': [False, True],
        'Belts': [False, False],
        'Personal_Injury': [False, False],
        'Property_Damage': [False, True],
        'Fatal': [False, False],
        'Commercial_License': [False, False],
        'HAZMAT': [False, False],
        'Commercial_Vehicle': [False, False],
        'Alcohol': [False, False],
        'Work_Zone': [False, False],
        'Search_Conducted': [False, False],
        'Search_Disposition': ['N/A', 'N/A'],
        'Search_Outcome': ['N/A', 'N/A'],
        'Search_Reason': ['N/A', 'N/A'],
        'Search_Reason_For_Stop': ['N/A', 'N/A'],
        'Search_Type': ['N/A', 'N/A'],
        'Search_Arrest_Reason': ['N/A', 'N/A'],
        'State': ['MD', 'MD'],
        'VehicleType': ['02 - Automobile', '02 - Automobile'],
        'Year': [2007, 2005],
        'Make': ['CHEVROLET', 'FORD'],
        'Model': ['CRUZ', 'EXPLORER'],
        'Color': ['BLACK', 'SILVER'],
        'Violation_Type': ['Citation', 'Citation'],
        'Charge': ['13-401', '16-101'],
        'Article': ['Transportation', 'Transportation'],
        'Contributed_To_Accident': [False, True],
        'Race': ['WHITE', 'HISPANIC'],
        'Gender': ['M', 'M'],
        'Driver_City': ['GAITHERSBURG', 'GAITHERSBURG'],
        'Driver_State': ['MD', 'MD'],
        'DL_State': ['MD', 'MD'],
        'Arrest_Type': ['A - Marked Patrol', 'A - Marked Patrol'],
        'Geolocation': ['(39.0, -77.1)', '(39.1, -77.2)'],
        'Is_Multi_Charge': [False, False],
        'Datetime_Of_Stop': pd.to_datetime(['2023-05-01 23:11:00', '2023-08-31 16:41:00']),
        'Stop_Hour': [23, 16],
        'Time_Of_Day': ['Evening (18:00-24:00)', 'Afternoon (12:00-18:00)'],
        'Day_Of_Week': ['Monday', 'Thursday'],
        'Month_Name': ['May', 'August'],
        'Stop_Year': [2023, 2023],
        'District_Number': ['3', '6'],
        'Violation_Category': ['Speeding', 'License / Registration / Documentation'],
        'Make_Raw': ['CHEV', 'FORD'],
        'Color_Raw': ['BLK', 'SILV'],
        'Accident_Severity_Index': [0, 1]
    }
    df = pd.DataFrame(dummy_data)
    df.to_parquet(parquet_file, index=False)

    db = TrafficViolationsDB(str(db_file))
    db.load_data_from_parquet(str(parquet_file))
    return db


def test_db_kpis(test_db_setup):
    db = test_db_setup
    kpis = db.get_summary_kpis()

    assert kpis['total_records'] == 2
    assert kpis['total_stops'] == 2
    assert kpis['accident_count'] == 1
    assert kpis['accident_rate_pct'] == 50.0


def test_db_query(test_db_setup):
    db = test_db_setup
    res = db.execute_query("SELECT * FROM traffic_violations WHERE Make = 'CHEVROLET';")
    assert len(res) == 1
    assert res.iloc[0]['Make'] == 'CHEVROLET'
