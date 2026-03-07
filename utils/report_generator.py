import pandas as pd
import sqlite3
import os


def generate_report(session_id):

    # Ensure report directory exists
    os.makedirs("reports", exist_ok=True)

    db_path = "database/attendance.db"

    if not os.path.exists(db_path):
        raise Exception("Database file not found.")

    conn = sqlite3.connect(db_path)

    attendance = pd.read_sql_query(
        "SELECT roll, name, ip FROM attendance WHERE session_id=?",
        conn,
        params=(session_id,)
    )

    conn.close()

    # If no attendance yet
    if attendance.empty:
        raise Exception("No attendance records found.")

    # Sort by roll number
    attendance["roll"] = attendance["roll"].astype(str)
    attendance = attendance.sort_values(by="roll")

    attendance.rename(columns={
        "roll": "Roll Number",
        "name": "Name",
        "ip": "IP Address"
    }, inplace=True)

    file_path = f"reports/attendance_{session_id}.xlsx"

    attendance.to_excel(file_path, index=False)

    return file_path
