#!/usr/bin/env python3
"""Check SQL database content."""

import sqlite3
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: python check_sql.py <path_to_sql_file>")
    sys.exit(1)

sql_file = Path(sys.argv[1])

if not sql_file.exists():
    print(f"File not found: {sql_file}")
    sys.exit(1)

print(f"Analyzing: {sql_file}")
print(f"File size: {sql_file.stat().st_size:,} bytes")
print("="*80)

try:
    conn = sqlite3.connect(str(sql_file))
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    print(f"\nTables found: {len(tables)}")
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  - {table_name}: {count:,} rows")

    # Check ReportData specifically
    if any(t[0] == 'ReportData' for t in tables):
        print("\n" + "="*80)
        print("ReportData Analysis:")
        print("="*80)

        cursor.execute("SELECT COUNT(*) FROM ReportData")
        total_rows = cursor.fetchone()[0]
        print(f"Total data points: {total_rows:,}")

        if total_rows > 0:
            cursor.execute("""
                SELECT ReportDataDictionary.Name, COUNT(*) as count
                FROM ReportData
                JOIN ReportDataDictionary ON ReportData.ReportDataDictionaryIndex = ReportDataDictionary.ReportDataDictionaryIndex
                GROUP BY ReportDataDictionary.Name
                LIMIT 20
            """)
            variables = cursor.fetchall()

            print("\nTop 20 output variables:")
            for var_name, count in variables:
                print(f"  - {var_name}: {count:,} points")

    # Check Time table
    if any(t[0] == 'Time' for t in tables):
        print("\n" + "="*80)
        print("Time Analysis:")
        print("="*80)

        cursor.execute("SELECT COUNT(*) FROM Time")
        time_rows = cursor.fetchone()[0]
        print(f"Total timesteps: {time_rows:,}")

        if time_rows > 0:
            cursor.execute("SELECT MIN(Year), MAX(Year), MIN(Month), MAX(Month), MIN(Day), MAX(Day) FROM Time")
            result = cursor.fetchone()
            print(f"Time range: {result[2]}/{result[4]}/{result[0]} to {result[3]}/{result[5]}/{result[1]}")

    conn.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
