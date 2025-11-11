#!/usr/bin/env python3
"""Read errors from SQL database."""

import sqlite3
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: python read_errors.py <path_to_sql_file>")
    sys.exit(1)

sql_file = Path(sys.argv[1])

try:
    conn = sqlite3.connect(str(sql_file))
    cursor = conn.cursor()

    print("="*80)
    print("ERRORS FROM SQL DATABASE")
    print("="*80)

    cursor.execute("SELECT * FROM Errors")
    errors = cursor.fetchall()

    print(f"\nFound {len(errors)} errors:")
    print("")

    for i, error in enumerate(errors, 1):
        print(f"Error {i}:")
        print(f"  {error}")
        print("")

    conn.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
