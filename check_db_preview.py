"""
確認 MySQL 資料庫與資料表是否存在，並印出前五筆資料。
會沿用 upload_data.py 內的連線設定（可用環境變數覆寫）。

環境變數：
  - MYSQL_HOST (預設 140.134.60.218)
  - MYSQL_PORT (預設 8306)
  - MYSQL_USER (預設 root)
  - MYSQL_PASSWORD (預設於 upload_data.py)
  - MYSQL_DB (預設 phm)
  - MYSQL_TABLE (預設 equipment_data)
"""

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, OperationalError

# 重用既有的連線參數與方法
from upload_data import get_engine, MYSQL_DB, MYSQL_TABLE


def main():
    engine = get_engine(MYSQL_DB)
    try:
        conn = engine.connect()
    except OperationalError as e:
        print(f"無法連線到資料庫 `{MYSQL_DB}`，可能是權限不足或資料庫不存在。\n{e}")
        return
    with conn:
        # 檢查資料表是否存在
        res = conn.execute(text(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = :db AND table_name = :table
            """
        ), {"db": MYSQL_DB, "table": MYSQL_TABLE})
        exists = res.scalar() > 0

        print(f"Database `{MYSQL_DB}` exists: True")
        print(f"Table `{MYSQL_TABLE}` exists: {exists}")

        if not exists:
            print("Table not found; no rows to display.")
            return

        # 查詢前五筆
        res = conn.execute(text(f"SELECT * FROM `{MYSQL_TABLE}` LIMIT 5"))
        rows = res.fetchall()
        cols = res.keys()
        df = pd.DataFrame(rows, columns=cols)
        print("Top 5 rows:")
        print(df)

        # 顯示所有欄位名稱
        res = conn.execute(text(
            """
            SELECT COLUMN_NAME
            FROM information_schema.columns
            WHERE table_schema = :db AND table_name = :table
            ORDER BY ORDINAL_POSITION
            """
        ), {"db": MYSQL_DB, "table": MYSQL_TABLE})
        columns = [row[0] for row in res.fetchall()]
        print("Columns in table:")
        print(columns)
        # 嘗試找出時間欄位（名稱包含 'time' 或 'date'，不區分大小寫）
        time_columns = [col for col in columns if 'time' in col.lower() or 'date' in col.lower()]
        if not time_columns:
            print("No time/date columns found.")
        else:
            for col in time_columns:
                res = conn.execute(text(
                    f"SELECT MIN(`{col}`) AS min_time, MAX(`{col}`) AS max_time FROM `{MYSQL_TABLE}`"
                ))
                min_time, max_time = res.fetchone()
                print(f"Column `{col}`: min = {min_time}, max = {max_time}")

        # 查詢 2025-07-18 當天 vibration 最大值及其時間點
        date_str = "2025-07-18"
        # 嘗試自動找出 vibration 欄位與時間欄位
        vibration_col = next((col for col in columns if 'vibration' in col.lower()), None)
        if not vibration_col:
            print("No vibration column found.")
        elif not time_columns:
            print("No time/date columns found for filtering.")
        else:
            time_col = time_columns[0]
            query = text(
                f"""
                SELECT `{time_col}`, `{vibration_col}`
                FROM `{MYSQL_TABLE}`
                WHERE DATE(`{time_col}`) = :date
                ORDER BY `{vibration_col}` DESC
                LIMIT 1
                """
            )
            res = conn.execute(query, {"date": date_str})
            row = res.fetchone()
            if row:
                print(f"On {date_str}, max `{vibration_col}`: {row[1]}, at `{time_col}`: {row[0]}")
            else:
                print(f"No data found for {date_str}.")
        

if __name__ == "__main__":
    main()
