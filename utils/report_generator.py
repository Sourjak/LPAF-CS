import pandas as pd
import sqlite3
import os

def generate_report(session_id):

    conn = sqlite3.connect("database/attendance.db")

    attendance = pd.read_sql_query(
        "SELECT roll,name,ip FROM attendance WHERE session_id=?",
        conn,
        params=(session_id,)
    )

    conn.close()

    roster = pd.read_csv("utils/roll_list.csv")

    roster["roll"] = roster["roll"].astype(str)

    attendance["roll"] = attendance["roll"].astype(str)

    roster["Status"] = roster["roll"].apply(
        lambda x: "Present" if x in attendance["roll"].values else "Absent"
    )

    roster = roster.merge(attendance[["roll","ip"]], on="roll", how="left")

    roster.rename(columns={
        "roll": "Roll Number",
        "name": "Name",
        "ip": "IP Address"
    }, inplace=True)

    file_path = f"reports/session_{session_id}.xlsx"

    os.makedirs("reports", exist_ok=True)

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        roster.to_excel(writer, index=False)

    return file_path
