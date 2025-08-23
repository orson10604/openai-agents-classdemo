import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, OperationalError

# 重用既有的連線參數與方法
from upload_data import get_engine, MYSQL_DB, MYSQL_TABLE
import sys, os

from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()
#SQL connectation inf
MYSQL_HOST = os.getenv('MYSQL_HOST', '140.134.60.218')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', '8306'))
MYSQL_USER = os.getenv('MYSQL_USER', 'user_class')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'password1234')
MYSQL_DB = os.getenv('MYSQL_DB', 'phm')
MYSQL_TABLE = os.getenv('MYSQL_TABLE', 'equipment_data')


def get_vibration_all_on_date(date_str: str):
    print(f"[debug] getting all vibration data for date: {date_str}")
    import mysql.connector

    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        print("[debug] MySQL connection established:", conn.is_connected())
        cursor = conn.cursor()
        # Get column names
        cursor.execute(f"SHOW COLUMNS FROM {MYSQL_TABLE}")
        columns = [row[0] for row in cursor.fetchall()]
        vibration_col = next((col for col in columns if 'vibration' in col.lower()), None)
        time_columns = [col for col in columns if 'time' in col.lower() or 'date' in col.lower()]
        if not vibration_col:
            return "No vibration column found."
        if not time_columns:
            return "No time/date columns found for filtering."
        time_col = time_columns[0]
        query = (
            f"SELECT `{time_col}`, `{vibration_col}` "
            f"FROM `{MYSQL_TABLE}` "
            f"WHERE DATE(`{time_col}`) = %s "
            f"ORDER BY `{time_col}` ASC"
        )
        cursor.execute(query, (date_str,))
        rows = cursor.fetchall()
        if rows:
            result = [f"{time_col}: {row[0]}, {vibration_col}: {row[1]}" for row in rows]
            return "\n".join(result)
        else:
            return f"{date_str} 沒有資料。"
    except Exception as e:
        return f"Error retrieving vibration data: {e}"
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_sql.py <YYYY-MM-DD>")
        sys.exit(1)
    date_str = sys.argv[1]
    result = get_vibration_all_on_date(date_str)
    print(result)