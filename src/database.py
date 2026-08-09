"""
SQLite Database & Query Management Module
Manages database initialization, indexing, and high-performance SQL analytics.
"""

import os
import sqlite3
import pandas as pd


class TrafficViolationsDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    def get_connection(self):
        """Returns SQLite database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def load_data_from_parquet(self, parquet_path: str):
        """Loads cleaned Parquet dataset into SQLite database and builds optimized indexes."""
        if not os.path.exists(parquet_path):
            raise FileNotFoundError(f"Parquet file not found: {parquet_path}")

        print(f"Reading Parquet dataset from: {parquet_path}...")
        df = pd.read_parquet(parquet_path)

        # Convert category columns to string for SQLite compatibility
        category_cols = df.select_dtypes(include=['category']).columns
        for col in category_cols:
            df[col] = df[col].astype(str)

        # Datetime to string ISO format
        if 'Date_Of_Stop' in df.columns:
            df['Date_Of_Stop'] = df['Date_Of_Stop'].dt.strftime('%Y-%m-%d')
        if 'Datetime_Of_Stop' in df.columns:
            df['Datetime_Of_Stop'] = df['Datetime_Of_Stop'].dt.strftime('%Y-%m-%d %H:%M:%S')

        with self.get_connection() as conn:
            print("Writing data into SQLite table `traffic_violations`...")
            df.to_sql('traffic_violations', conn, if_exists='replace', index=False)
            
            print("Building database indexes for fast query performance...")
            cursor = conn.cursor()
            
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_seqid ON traffic_violations(SeqID);",
                "CREATE INDEX IF NOT EXISTS idx_date ON traffic_violations(Date_Of_Stop);",
                "CREATE INDEX IF NOT EXISTS idx_agency ON traffic_violations(Agency);",
                "CREATE INDEX IF NOT EXISTS idx_subagency ON traffic_violations(SubAgency);",
                "CREATE INDEX IF NOT EXISTS idx_violation_type ON traffic_violations(Violation_Type);",
                "CREATE INDEX IF NOT EXISTS idx_violation_category ON traffic_violations(Violation_Category);",
                "CREATE INDEX IF NOT EXISTS idx_make ON traffic_violations(Make);",
                "CREATE INDEX IF NOT EXISTS idx_accident ON traffic_violations(Accident);",
                "CREATE INDEX IF NOT EXISTS idx_demographics ON traffic_violations(Gender, Race);"
            ]
            
            for idx_sql in indexes:
                cursor.execute(idx_sql)
            
            conn.commit()
            print("Database setup & indexing completed successfully!")

    def execute_query(self, query: str, params: tuple = ()) -> pd.DataFrame:
        """Executes a SQL query and returns results as a pandas DataFrame."""
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)

    def get_summary_kpis(self) -> dict:
        """Fetches high-level executive KPIs via SQL aggregation."""
        query = """
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT SeqID) as total_stops,
            SUM(CASE WHEN Accident = 1 THEN 1 ELSE 0 END) as accident_count,
            SUM(CASE WHEN Personal_Injury = 1 THEN 1 ELSE 0 END) as injury_count,
            SUM(CASE WHEN Fatal = 1 THEN 1 ELSE 0 END) as fatal_count,
            SUM(CASE WHEN Alcohol = 1 THEN 1 ELSE 0 END) as alcohol_count,
            SUM(CASE WHEN Search_Conducted = 1 THEN 1 ELSE 0 END) as search_count
        FROM traffic_violations;
        """
        df_kpi = self.execute_query(query)
        if len(df_kpi) > 0:
            row = df_kpi.iloc[0].to_dict()
            row['accident_rate_pct'] = round((row['accident_count'] / row['total_records']) * 100, 2) if row['total_records'] > 0 else 0.0
            return row
        return {}


if __name__ == '__main__':
    parquet_file = r"c:\Users\sudin\OneDrive\Desktop\traffic violation system\data\cleaned_traffic_violations.parquet"
    db_file = r"c:\Users\sudin\OneDrive\Desktop\traffic violation system\data\traffic_violations.db"
    db = TrafficViolationsDB(db_file)
    db.load_data_from_parquet(parquet_file)
    kpis = db.get_summary_kpis()
    print("Summary KPIs via SQL:", kpis)
