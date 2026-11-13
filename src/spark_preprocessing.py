"""
PySpark version of the cleaning pipeline in preprocessing.py.

Same rules, same output columns, so the two can be compared row for row
(tests/test_spark_parity.py and scripts/benchmark_etl.py do exactly that).

Written with Spark's built-in column functions only. Python UDFs would send
every row out of the JVM to a Python worker and back, which is the usual reason
"Spark is slower than pandas" on a laptop.

Run it:
    python -m src.spark_preprocessing --input Traffic_Violations.csv \
        --output data/cleaned_traffic_violations_spark.parquet
"""

import argparse
import os
import time
from datetime import date
from itertools import chain

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F

from src.preprocessing import COLOR_MAPPING, MAKE_MAPPING

COLUMN_MAP = {
    'Date Of Stop': 'Date_Of_Stop', 'Time Of Stop': 'Time_Of_Stop',
    'Personal Injury': 'Personal_Injury', 'Property Damage': 'Property_Damage',
    'Commercial License': 'Commercial_License', 'Commercial Vehicle': 'Commercial_Vehicle',
    'Work Zone': 'Work_Zone', 'Search Conducted': 'Search_Conducted',
    'Search Disposition': 'Search_Disposition', 'Search Outcome': 'Search_Outcome',
    'Search Reason': 'Search_Reason', 'Search Reason For Stop': 'Search_Reason_For_Stop',
    'Search Type': 'Search_Type', 'Search Arrest Reason': 'Search_Arrest_Reason',
    'Violation Type': 'Violation_Type', 'Contributed To Accident': 'Contributed_To_Accident',
    'Driver City': 'Driver_City', 'Driver State': 'Driver_State', 'DL State': 'DL_State',
    'Arrest Type': 'Arrest_Type',
}

TEXT_UPPER = ['Agency', 'SubAgency', 'Description', 'Location', 'State', 'Driver_City',
              'Driver_State', 'DL_State', 'Arrest_Type', 'Charge', 'Article']
BOOL_COLS = ['Accident', 'Belts', 'Personal_Injury', 'Property_Damage', 'Fatal',
             'Commercial_License', 'HAZMAT', 'Commercial_Vehicle', 'Alcohol',
             'Work_Zone', 'Search_Conducted', 'Contributed_To_Accident']
SEARCH_COLS = ['Search_Disposition', 'Search_Outcome', 'Search_Reason',
               'Search_Reason_For_Stop', 'Search_Type', 'Search_Arrest_Reason']
MISSING = ['NAN', 'NONE', 'NULL', '']

# Strings pandas.read_csv turns into missing values by default. The pandas pipeline
# never sees them as text (a Color of "N/A" arrives as missing and becomes UNKNOWN),
# so Spark has to treat them the same way. Found by the parity test: 570 of 5,873
# sample rows had Color "N/A" in Spark but UNKNOWN in pandas.
PANDAS_NA = ['#N/A', '#N/A N/A', '#NA', '-1.#IND', '-1.#QNAN', '-NaN', '-nan', '1.#IND', '1.#QNAN',
             '<NA>', 'N/A', 'NA', 'NULL', 'NaN', 'None', 'n/a', 'nan', 'null']

# Same keyword buckets, in the same order, as preprocessing.categorize_description
CATEGORIES = [
    ('Speeding', ['SPEED']),
    ('License / Registration / Documentation',
     ['LICENSE', 'REGISTR', 'REGISTER', 'UNREGISTER', 'TITLE', 'PLATE', 'TAG', 'PERMIT', 'INSURANCE']),
    ('Seatbelt & Safety Restraint', ['BELT', 'CHILD', 'RESTRICT', 'SEAT']),
    ('Traffic Signal & Control', ['SIGNAL', 'RED LIGHT', 'STOP SIGN', 'LANE', 'YIELD', 'TURN', 'PASSING']),
    ('Vehicle Equipment & Maintenance',
     ['HEADLIGHT', 'TAILLIGHT', 'TIRE', 'WINDOW', 'TINT', 'MIRROR', 'EQUIP', 'LAMP', 'MUFFLER', 'EXHAUST', 'LIGHT']),
    ('DUI / Alcohol / Substance',
     ['ALCOHOL', 'DRUG', 'INTOXICATED', 'UNDER THE INFLUENCE', 'DUI', 'DWI', 'DRINK']),
    ('Distracted / Reckless Driving',
     ['PHONE', 'CELL', 'HANDHELD', 'RECKLESS', 'NEGLIGENT', 'FOLLOWING', 'DISTRACTED', 'ACCIDENT']),
]


# Column order of the pandas output, so both Parquet files line up
OUTPUT_COLUMNS = (
    'SeqID', 'Date_Of_Stop', 'Time_Of_Stop', 'Agency', 'SubAgency',
    'Description', 'Location', 'Latitude', 'Longitude', 'Accident',
    'Belts', 'Personal_Injury', 'Property_Damage', 'Fatal', 'Commercial_License',
    'HAZMAT', 'Commercial_Vehicle', 'Alcohol', 'Work_Zone', 'Search_Conducted',
    'Search_Disposition', 'Search_Outcome', 'Search_Reason', 'Search_Reason_For_Stop', 'Search_Type',
    'Search_Arrest_Reason', 'State', 'VehicleType', 'Year', 'Make',
    'Model', 'Color', 'Violation_Type', 'Charge', 'Article',
    'Contributed_To_Accident', 'Race', 'Gender', 'Driver_City', 'Driver_State',
    'DL_State', 'Arrest_Type', 'Geolocation', 'Is_Multi_Charge', 'Datetime_Of_Stop',
    'Stop_Hour', 'Time_Of_Day', 'Day_Of_Week', 'Month_Name', 'Stop_Year',
    'District_Number', 'Violation_Category', 'Make_Raw', 'Color_Raw', 'Accident_Severity_Index',
)


def make_spark(app: str = "traffic-etl", driver_memory: str = None) -> SparkSession:
    memory = driver_memory or os.environ.get("SPARK_DRIVER_MEMORY", "3g")
    return (SparkSession.builder.appName(app).master(os.environ.get("SPARK_MASTER", "local[*]"))
            .config("spark.driver.memory", memory)
            .config("spark.sql.session.timeZone", "UTC")
            .config("spark.sql.shuffle.partitions", os.environ.get("SPARK_SHUFFLE_PARTITIONS", "16"))
            .config("spark.ui.showConsoleProgress", "false")
            .getOrCreate())


def _text(c):
    """Missing -> '' and surrounding whitespace removed (pandas .str.strip strips tabs too)."""
    return F.regexp_replace(F.coalesce(F.col(c).cast("string"), F.lit("")), r"^\s+|\s+$", "")


def _fill(expr, values, replacement):
    return F.when(expr.isin(values), F.lit(replacement)).otherwise(expr)


def _mapping(d):
    return F.create_map(*[F.lit(x) for x in chain(*d.items())])


def _clean_time(c):
    """23.11.00 -> 23:11:00, 08:30 -> 08:30:00, anything else -> 00:00:00 (clean_time_string)."""
    t = F.replace(_text(c), F.lit("."), F.lit(":"))
    parts = F.split(t, ":")
    n = F.size(parts)
    num = r"^\s*[+-]?\d+\s*$"
    p = [F.trim(F.get(parts, i)) for i in range(3)]
    pad = lambda e: F.lpad(e.cast("int").cast("string"), 2, "0")  # noqa: E731
    ok3 = (n == 3) & p[0].rlike(num) & p[1].rlike(num) & p[2].rlike(num)
    ok2 = (n == 2) & p[0].rlike(num) & p[1].rlike(num)
    return (F.when(F.col(c).isNull(), "00:00:00")
            .when(ok3, F.concat_ws(":", pad(p[0]), pad(p[1]), pad(p[2])))
            .when(ok2, F.concat_ws(":", pad(p[0]), pad(p[1]), F.lit("00")))
            .otherwise("00:00:00"))


def _parse_date(c):
    """Bulk CSV uses MM/dd/yyyy; the live feed uses ISO timestamps."""
    s = _text(c)
    return F.coalesce(
        F.to_date(F.try_to_timestamp(s, F.lit("MM/dd/yyyy"))),
        F.to_date(F.try_to_timestamp(F.substring(s, 1, 10), F.lit("yyyy-MM-dd"))),
    )


def _np_round5(c):
    """Rounds like pandas/NumPy: x * 1e5, round half to even, / 1e5.
    Spark's F.round rounds halves away from zero, so -77.400745 became -77.40075
    in Spark but -77.40074 in pandas (found by the parity test)."""
    return F.rint(F.col(c) * 100000.0) / 100000.0


def _category(desc):
    expr = F.lit('Other Violation')
    for name, keys in reversed(CATEGORIES):
        cond = F.lit(False)
        for k in keys:
            cond = cond | desc.contains(k)
        expr = F.when(cond, F.lit(name)).otherwise(expr)
    return expr


def _to_bool(c):
    return F.upper(_text(c)).isin('YES', 'Y', 'TRUE', '1', 'T')


def clean(raw: DataFrame) -> DataFrame:
    """Applies every cleaning rule from preprocessing.process_traffic_violations_df."""
    current_year = date.today().year
    df = raw.toDF(*[c.strip() for c in raw.columns])
    df = df.select([F.col(f"`{c}`").alias(COLUMN_MAP.get(c, c)) for c in df.columns])
    df = df.withColumn('SeqID', _text('SeqID')).dropDuplicates()

    # Dates and times
    d = _parse_date('Date_Of_Stop')
    df = df.withColumn('Date_Of_Stop', F.when(F.year(d).between(1990, current_year), d))
    df = df.withColumn('Time_Of_Stop', _clean_time('Time_Of_Stop'))
    date_str = F.coalesce(F.date_format('Date_Of_Stop', 'yyyy-MM-dd'), F.lit('1970-01-01'))
    df = df.withColumn('Datetime_Of_Stop',
                       F.try_to_timestamp(F.concat_ws(' ', date_str, F.col('Time_Of_Stop')),
                                          F.lit('yyyy-MM-dd HH:mm:ss')))
    hour = F.coalesce(F.hour('Datetime_Of_Stop'), F.lit(-1))
    df = df.withColumn('Stop_Hour', hour.cast('byte'))
    df = df.withColumn('Time_Of_Day',
                       F.when(F.col('Stop_Hour') == -1, 'Unknown')
                       .when(F.col('Stop_Hour') <= 5, 'Night (00:00-06:00)')
                       .when(F.col('Stop_Hour') <= 11, 'Morning (06:00-12:00)')
                       .when(F.col('Stop_Hour') <= 17, 'Afternoon (12:00-18:00)')
                       .otherwise('Evening (18:00-24:00)'))
    df = df.withColumn('Day_Of_Week', F.coalesce(F.date_format('Datetime_Of_Stop', 'EEEE'), F.lit('Unknown')))
    df = df.withColumn('Month_Name', F.coalesce(F.date_format('Datetime_Of_Stop', 'MMMM'), F.lit('Unknown')))
    df = df.withColumn('Stop_Year', F.coalesce(F.year('Datetime_Of_Stop'), F.lit(0)).cast('short'))

    # Text and categories
    for c in TEXT_UPPER:
        df = df.withColumn(c, _fill(F.upper(_text(c)), MISSING, 'UNKNOWN'))
    district = F.regexp_extract('SubAgency', r'(\d+)', 1)
    df = df.withColumn('District_Number', F.when(district == '', 'N/A').otherwise(district))
    df = df.withColumn('Violation_Category', _category(F.col('Description')))

    # Coordinates: zero pairs and points outside the US box become null (both together)
    lat, lon = F.col('Latitude').try_cast('double'), F.col('Longitude').try_cast('double')
    ok = lat.between(24.0, 50.0) & lon.between(-125.0, -65.0) & ~((lat == 0.0) & (lon == 0.0))
    df = df.withColumn('Latitude', F.when(ok, lat)).withColumn('Longitude', F.when(ok, lon))
    df = df.withColumn('Geolocation', F.when(
        F.col('Latitude').isNotNull(),
        F.concat(F.lit('('), _np_round5('Latitude').cast('string'), F.lit(', '),
                 _np_round5('Longitude').cast('string'), F.lit(')'))).otherwise('N/A'))

    for c in BOOL_COLS:
        df = df.withColumn(c, _to_bool(c))
    for c in SEARCH_COLS:
        df = df.withColumn(c, _fill(F.upper(_text(c)), MISSING, 'NOT APPLICABLE'))

    # Vehicle
    year = F.col('Year').try_cast('double')
    df = df.withColumn('Year', F.when(year.between(1960, current_year + 1), year))
    df = df.withColumn('Make_Raw', F.upper(_text('Make')))
    make = F.coalesce(F.element_at(_mapping(MAKE_MAPPING), F.col('Make_Raw')), F.col('Make_Raw'))
    df = df.withColumn('Make', _fill(make, MISSING + ['UNKNOWN'], 'UNKNOWN'))
    df = df.withColumn('Color_Raw', F.upper(_text('Color')))
    color = F.coalesce(F.element_at(_mapping(COLOR_MAPPING), F.col('Color_Raw')), F.col('Color_Raw'))
    df = df.withColumn('Color', _fill(color, MISSING, 'UNKNOWN'))
    df = df.withColumn('Model', _fill(F.upper(_text('Model')), MISSING, 'UNKNOWN'))
    df = df.withColumn('VehicleType', _fill(_text('VehicleType'), ['nan', 'None', ''], 'Unknown'))

    # People and violation type
    df = df.withColumn('Race', _fill(F.upper(_text('Race')), MISSING, 'OTHER'))
    g = F.upper(_text('Gender'))
    df = df.withColumn('Gender', F.when(g.isin('M', 'MALE'), 'M').when(g.isin('F', 'FEMALE'), 'F').otherwise('Unknown'))
    vt = F.initcap(_text('Violation_Type'))
    df = df.withColumn('Violation_Type', _fill(vt, ['Nan', 'None', ''], 'Citation'))

    df = df.withColumn('Accident_Severity_Index',
                       F.when(F.col('Fatal'), 3).when(F.col('Personal_Injury'), 2)
                       .when(F.col('Property_Damage'), 1).otherwise(0))

    # Cleaning can make two different raw rows identical (e.g. "Y" vs "Yes"), so
    # de-duplicate again, then flag stops with more than one charge.
    df = df.dropDuplicates()
    df = df.withColumn('Is_Multi_Charge', F.count(F.lit(1)).over(Window.partitionBy('SeqID')) > 1)
    # Timestamps without a time zone, so pandas reads them as plain datetime64 like the
    # pandas pipeline writes them (database.py calls .dt.strftime on both columns).
    df = (df.withColumn('Date_Of_Stop', F.col('Date_Of_Stop').cast('timestamp_ntz'))
            .withColumn('Datetime_Of_Stop', F.col('Datetime_Of_Stop').cast('timestamp_ntz')))
    return df.select(*OUTPUT_COLUMNS)


def read_raw_csv(spark: SparkSession, path: str) -> DataFrame:
    # Every column as text, like the raw file; the cleaner decides each type.
    raw = spark.read.csv(path, header=True, inferSchema=False, multiLine=False, escape='"')
    return raw.select([F.when(F.col(f"`{c}`").isin(PANDAS_NA), None).otherwise(F.col(f"`{c}`")).alias(c)
                       for c in raw.columns])


def run(input_csv: str, output_parquet: str, spark: SparkSession = None) -> dict:
    spark = spark or make_spark()
    start = time.time()
    raw = read_raw_csv(spark, input_csv)
    cleaned = clean(raw)
    cleaned.write.mode('overwrite').parquet(output_parquet)
    rows = spark.read.parquet(output_parquet).count()
    return {"engine": "spark", "rows_out": rows, "seconds": round(time.time() - start, 1),
            "output": output_parquet}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description="Clean the raw CSV with PySpark")
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', required=True)
    a = ap.parse_args()
    print(run(a.input, a.output))
