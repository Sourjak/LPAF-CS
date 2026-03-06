import pandas as pd
import sqlite3
import os


def generate_report(session_id):

    conn = sqlite3.connect("database/attendance.db")

    query = """
    SELECT name, roll, ip
    FROM attendance
    WHERE session_id=?
    """

    df = pd.read_sql_query(query, conn, params=(session_id,))

    conn.close()

    if df.empty:
        return None

    os.makedirs("reports", exist_ok=True)

    file_path = f"reports/attendance_{session_id}.xlsx"

    df.to_excel(file_path, index=False)

    return file_path