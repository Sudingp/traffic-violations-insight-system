"""
Writes a messy CSV in the same shape as the raw county file (same 43 column names,
same kinds of dirt: mixed time formats, 0/0 coordinates, Yes/Y/TRUE/1 flags,
abbreviated makes, blanks, padded text, duplicate rows, multi-charge stops).

Used by the parity tests and to try the Spark job / Airflow DAG without the
880 MB real file:
    python scripts/make_sample_csv.py --rows 200000 --out data/sample_raw.csv
"""

import argparse
import csv
import os
import random
import uuid

COLUMNS = ['SeqID', 'Date Of Stop', 'Time Of Stop', 'Agency', 'SubAgency', 'Description', 'Location',
           'Latitude', 'Longitude', 'Accident', 'Belts', 'Personal Injury', 'Property Damage', 'Fatal',
           'Commercial License', 'HAZMAT', 'Commercial Vehicle', 'Alcohol', 'Work Zone',
           'Search Conducted', 'Search Disposition', 'Search Outcome', 'Search Reason',
           'Search Reason For Stop', 'Search Type', 'Search Arrest Reason', 'State', 'VehicleType',
           'Year', 'Make', 'Model', 'Color', 'Violation Type', 'Charge', 'Article',
           'Contributed To Accident', 'Race', 'Gender', 'Driver City', 'Driver State', 'DL State',
           'Arrest Type', 'Geolocation']

DESCRIPTIONS = ['EXCEEDING THE POSTED SPEED LIMIT OF 40 MPH', 'DRIVING VEHICLE ON HIGHWAY WITH SUSPENDED REGISTRATION',
                'FAILURE TO DISPLAY REGISTRATION CARD', 'DRIVER FAILURE TO STOP AT STOP SIGN LINE',
                'FAILURE OF VEHICLE DRIVER TO WEAR SEAT BELT', 'DRIVING UNDER THE INFLUENCE OF ALCOHOL',
                'DRIVER USING HANDHELD TELEPHONE WHILE MOTOR VEHICLE IS IN MOTION', 'HEADLIGHT INOPERATIVE',
                'FAILURE TO YIELD RIGHT OF WAY', 'OPERATING UNINSURED VEHICLE', 'UNSAFE LANE CHANGE', 'LITTERING', '']
MAKES = ['TOYT', 'TOYOTA', 'HOND', 'honda', 'CHEV', 'FORD', 'NISS', 'VW', 'BMW', 'B.M.W.', 'MERC', 'TESL',
         'SUBARU', 'XYZ', '', 'UNKNOWN', ' DODG ']
COLORS = ['BLK', 'BLACK', 'SILV', 'WHT', 'GREY', 'RED', 'BLUE, DARK', '', 'N/A', 'GLD']
FLAGS = ['Yes', 'No', 'No', 'No', 'Y', 'N', 'TRUE', 'false', '1', '0', '', ' yes ']
SUBAGENCIES = ['1st District, Rockville', '3rd District, Silver Spring', '4th District, Wheaton',
               'Headquarters and Special Operations', '']
TIMES = ['23.11.00', '16:41:00', '08:30', '7:5', '', 'abc', '25:00:00', '00:00:00', '12.30']
VTYPES = ['Warning', 'Citation', 'ESERO', 'SERO', 'warning', '', 'citation ']
RACES = ['WHITE', 'BLACK', 'HISPANIC', 'ASIAN', 'OTHER', '', 'NATIVE AMERICAN']
GENDERS = ['M', 'F', 'U', 'male', '', 'Female']


def _date(r: random.Random, realistic: bool = False) -> str:
    roll = r.random()
    if roll < (0.0 if realistic else 0.02):
        return r.choice(['', '13/45/2020', 'not a date', '01/01/1985', '06/15/2031'])
    return f"{r.randint(1, 12):02d}/{r.randint(1, 28):02d}/{r.randint(2012, 2025)}"


def _coords(r: random.Random):
    roll = r.random()
    if roll < 0.04:
        return '0', '0'
    if roll < 0.06:
        return '', ''
    if roll < 0.07:
        return '91.5', '-77.1'          # impossible latitude
    if roll < 0.08:
        return '39.1', '12.5'           # outside the US box
    return f"{r.uniform(38.9, 39.3):.6f}", f"{r.uniform(-77.5, -76.9):.6f}"


def make_rows(n: int, seed: int = 7, realistic: bool = False):
    """realistic=True keeps the dirt at the rates seen in the real file (no bad dates or
    times, few bad years) so the quality gate passes; the default is much dirtier, to
    exercise every cleaning rule."""
    r = random.Random(seed)
    times = ['23.11.00', '16:41:00', '08:30', '12.30', '07:05:00'] if realistic else TIMES
    years = ['2015', '2019', '2008', '2021', '2012', '2017', '2010'] if realistic else \
        ['2015', '2019', '2027', '1950', '0', '', '2008', 'abcd']
    rows = []
    while len(rows) < n:
        seq = str(uuid.UUID(int=r.getrandbits(128)))
        lat, lon = _coords(r)
        base = {
            'SeqID': seq if r.random() > 0.01 else f" {seq} ",
            'Date Of Stop': _date(r, realistic), 'Time Of Stop': r.choice(times),
            'Agency': r.choice(['MCP', 'MCP', ' mcp', '']), 'SubAgency': r.choice(SUBAGENCIES),
            'Location': r.choice(['GEORGIA AVE @ RANDOLPH RD', 'rt 29 / tech rd', '', 'I-270']),
            'Latitude': lat, 'Longitude': lon,
            'Search Conducted': r.choice(FLAGS),
            'Search Disposition': r.choice(['', '', 'Nothing', 'Contraband Only']),
            'Search Outcome': r.choice(['', '', 'Warning', 'Arrest']), 'Search Reason': r.choice(['', 'Incident to Arrest']),
            'Search Reason For Stop': r.choice(['', '21-801(a)']), 'Search Type': r.choice(['', 'Both', 'Person']),
            'Search Arrest Reason': '', 'State': r.choice(['MD', 'VA', 'DC', 'XX', '']),
            'VehicleType': r.choice(['02 - Automobile', '05 - Light Duty Truck', '', '28 - Other']),
            'Year': r.choice(years),
            'Make': r.choice(MAKES), 'Model': r.choice(['CAMRY', 'civic', '4S', '', 'TK']),
            'Color': r.choice(COLORS), 'Violation Type': r.choice(VTYPES),
            'Article': r.choice(['Transportation Article', '', 'Maryland Rules']),
            'Race': r.choice(RACES), 'Gender': r.choice(GENDERS),
            'Driver City': r.choice(['SILVER SPRING', 'rockville', '', 'GAITHERSBURG']),
            'Driver State': r.choice(['MD', 'VA', '']), 'DL State': r.choice(['MD', 'NY', '']),
            'Arrest Type': r.choice(['A - Marked Patrol', 'Q - Marked Laser', '']),
            'Geolocation': f"({lat}, {lon})" if lat else '',
        }
        for flag in ['Accident', 'Belts', 'Personal Injury', 'Property Damage', 'Fatal', 'Commercial License',
                     'HAZMAT', 'Commercial Vehicle', 'Alcohol', 'Work Zone', 'Contributed To Accident']:
            base[flag] = r.choice(FLAGS)
        # 1-3 charges per stop (multi-charge stops share a SeqID)
        for _ in range(r.choice([1, 1, 1, 2, 3])):
            row = dict(base, Description=r.choice(DESCRIPTIONS), Charge=r.choice(['21-801.1', '13-401(h)', '']))
            rows.append(row)
            if r.random() < 0.01:          # exact duplicate row
                rows.append(dict(row))
    return rows[:n]


def write_csv(path: str, n: int, seed: int = 7, realistic: bool = False) -> str:
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(make_rows(n, seed, realistic))
    return path


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--rows', type=int, default=200_000)
    ap.add_argument('--out', default='data/sample_raw.csv')
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--realistic', action='store_true', help='dirt at real-file rates (passes the quality gate)')
    a = ap.parse_args()
    print(write_csv(a.out, a.rows, a.seed, a.realistic))
