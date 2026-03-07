import pandas as pd
import sqlite3
import os

def generate_report(session_id):

    os.makedirs("reports", exist_ok=True)

    conn = sqlite3.connect("database/attendance.db")

    attendance = pd.read_sql_query(
        "SELECT roll,name,ip FROM attendance WHERE session_id=?",
        conn,
        params=(session_id,)
    )

    conn.close()

    # Load full class roster
    roster_path = "utils/roll_list.csv"

    if not os.path.exists(roster_path):
        raise Exception("roll_list.csv not found")

    roster = pd.read_csv(roster_path)

    roster["roll"] = roster["roll"].astype(str)

    attendance["roll"] = attendance["roll"].astype(str)

    # Mark attendance status
    roster["Status"] = roster["roll"].apply(
        lambda r: "Present" if r in attendance["roll"].values else "Absent"
    )

    # Merge IP addresses
    roster = roster.merge(
        attendance[["roll","ip"]],
        on="roll",
        how="left"
    )

    roster.rename(columns={
        "roll": "Roll Number",
        "name": "Name",
        "ip": "IP Address"
    }, inplace=True)

    file_path = f"reports/session_{session_id}.xlsx"

    roster.to_excel(file_path, index=False)

    return file_path
