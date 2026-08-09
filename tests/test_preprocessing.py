"""
Unit tests for data preprocessing module.
"""

import pytest
import pandas as pd
import numpy as np
from src.preprocessing import (
    clean_boolean_value,
    categorize_description,
    clean_time_string,
    process_traffic_violations_df
)


def test_clean_boolean_value():
    assert clean_boolean_value('Yes') is True
    assert clean_boolean_value('Y') is True
    assert clean_boolean_value('TRUE') is True
    assert clean_boolean_value('1') is True
    assert clean_boolean_value('No') is False
    assert clean_boolean_value('N') is False
    assert clean_boolean_value('FALSE') is False
    assert clean_boolean_value(None) is False
    assert clean_boolean_value(np.nan) is False


def test_categorize_description():
    assert categorize_description('EXCEEDING POSTED SPEED LIMIT 45 MPH') == 'Speeding'
    assert categorize_description('DRIVING UNREGISTERED VEHICLE ON HIGHWAY') == 'License / Registration / Documentation'
    assert categorize_description('FAILURE TO WEAR SEAT BELT') == 'Seatbelt & Safety Restraint'
    assert categorize_description('FAILURE TO STOP AT RED SIGNAL LIGHT') == 'Traffic Signal & Control'
    assert categorize_description('DRIVING VEHICLE WHILE UNDER THE INFLUENCE OF ALCOHOL') == 'DUI / Alcohol / Substance'
    assert categorize_description('SOME UNKNOWN INFRACTION') == 'Other Violation'


def test_clean_time_string():
    assert clean_time_string('23.11.00') == '23:11:00'
    assert clean_time_string('16:41:00') == '16:41:00'
    assert clean_time_string('08:30') == '08:30:00'
    assert clean_time_string(None) == '00:00:00'


def test_process_traffic_violations_df_sample():
    raw_data = {
        'SeqID': ['seq-001', 'seq-002', 'seq-002'],
        'Date Of Stop': ['05/01/2023', '08/31/2023', '08/31/2023'],
        'Time Of Stop': ['23.11.00', '16.41.00', '16.41.00'],
        'Agency': ['MCP', 'MCP', 'MCP'],
        'SubAgency': ['3rd District', '6th District', '6th District'],
        'Description': ['SPEEDING', 'NO LICENSE', 'EXPIRED REGISTRATION'],
        'Location': ['MAIN ST', 'OAKMONT AVE', 'OAKMONT AVE'],
        'Latitude': [0, 39.097965, 39.097965],
        'Longitude': [0, -77.15301, -77.15301],
        'Accident': ['No', 'Yes', 'Yes'],
        'Belts': ['No', 'No', 'No'],
        'Personal Injury': ['No', 'No', 'No'],
        'Property Damage': ['No', 'Yes', 'Yes'],
        'Fatal': ['No', 'No', 'No'],
        'Commercial License': ['No', 'No', 'No'],
        'HAZMAT': ['No', 'No', 'No'],
        'Commercial Vehicle': ['No', 'No', 'No'],
        'Alcohol': ['No', 'No', 'No'],
        'Work Zone': ['No', 'No', 'No'],
        'Search Conducted': ['No', 'No', 'No'],
        'Search Disposition': ['', '', ''],
        'Search Outcome': ['', '', ''],
        'Search Reason': ['', '', ''],
        'Search Reason For Stop': ['', '', ''],
        'Search Type': ['', '', ''],
        'Search Arrest Reason': ['', '', ''],
        'State': ['MD', 'MD', 'MD'],
        'VehicleType': ['02 - Automobile', '02 - Automobile', '02 - Automobile'],
        'Year': [2007, 2005, 2005],
        'Make': ['CHEV', 'FORD', 'FORD'],
        'Model': ['CRUZ', 'EXPLORER', 'EXPLORER'],
        'Color': ['BLK', 'SILV', 'SILV'],
        'Violation Type': ['Citation', 'Citation', 'Warning'],
        'Charge': ['13-401', '16-101', '13-409'],
        'Article': ['Transportation', 'Transportation', 'Transportation'],
        'Contributed To Accident': ['False', 'True', 'True'],
        'Race': ['WHITE', 'HISPANIC', 'HISPANIC'],
        'Gender': ['M', 'M', 'M'],
        'Driver City': ['GAITHERSBURG', 'GAITHERSBURG', 'GAITHERSBURG'],
        'Driver State': ['MD', 'MD', 'MD'],
        'DL State': ['MD', 'MD', 'MD'],
        'Arrest Type': ['A - Marked Patrol', 'A - Marked Patrol', 'A - Marked Patrol'],
        'Geolocation': ['(0.0, 0.0)', '(39.097965, -77.15301)', '(39.097965, -77.15301)']
    }
    df_raw = pd.DataFrame(raw_data)
    df_clean = process_traffic_violations_df(df_raw)

    assert len(df_clean) == 3
    assert 'Datetime_Of_Stop' in df_clean.columns
    assert 'Violation_Category' in df_clean.columns
    assert df_clean['Make'].iloc[0] == 'CHEVROLET'
    assert df_clean['Color'].iloc[0] == 'BLACK'
    assert df_clean['Color'].iloc[1] == 'SILVER'
    assert df_clean['Accident'].iloc[1] == True
    assert np.isnan(df_clean['Latitude'].iloc[0])  # (0,0) converted to NaN
    assert df_clean['Is_Multi_Charge'].iloc[1] == True  # seq-002 appears twice
