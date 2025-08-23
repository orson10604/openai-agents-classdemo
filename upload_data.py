import os
# 匯入必要套件
import pandas as pd  # 資料處理
import numpy as np   # 數值運算
from datetime import datetime, timedelta  # 處理時間
import random
import matplotlib.pyplot as plt
#   user="user_class",
#   password="password1234",
# 資料檔案路徑
CSV_PATH = 'data/equipment_data_with_11days.csv'

# MySQL 連線參數（可改從環境變數讀取）
MYSQL_HOST = os.getenv('MYSQL_HOST', '140.134.60.218')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', '8306'))
MYSQL_USER = os.getenv('MYSQL_USER', 'user_class')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'password1234')
MYSQL_DB = os.getenv('MYSQL_DB', 'phm')  # 若不存在會自動建立
MYSQL_TABLE = os.getenv('MYSQL_TABLE', 'equipment_data')

# 讀取完整數據
# df_loaded = pd.read_csv(CSV_PATH, parse_dates=['Time'])

# # 顯示數據的前幾行
# print('Data preview:')
# print(df_loaded.head())

# 上傳至 MySQL
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


def get_engine(database: str | None = None):
	"""建立 SQLAlchemy engine，若 database 為 None，連線到不含 DB 的伺服器。"""
	if database:
		url = URL.create(
			drivername='mysql+pymysql',
			username=MYSQL_USER,
			password=MYSQL_PASSWORD,
			host=MYSQL_HOST,
			port=MYSQL_PORT,
			database=database,
		)
	else:
		url = URL.create(
			drivername='mysql+pymysql',
			username=MYSQL_USER,
			password=MYSQL_PASSWORD,
			host=MYSQL_HOST,
			port=MYSQL_PORT,
		)
	return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


def ensure_database_exists(db_name: str):
	engine = get_engine(None)
	with engine.connect() as conn:
		conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
		conn.commit()


def upload_dataframe(df: pd.DataFrame, db_name: str, table_name: str):
	ensure_database_exists(db_name)
	engine = get_engine(db_name)

	# 標準化欄位名稱（避免空白與特殊字元）
	df = df.copy()
	df.columns = [str(c).strip().replace(' ', '_').replace('-', '_') for c in df.columns]

	# 將 numpy 型別轉為 Python 原生型別以避免 to_sql 警告
	df = df.where(pd.notnull(df), None)

	# 寫入資料（若表存在則附加）
	print(f'Uploading {len(df)} rows to {db_name}.{table_name} ...')
	with engine.begin() as conn:
		df.to_sql(table_name, con=conn, if_exists='append', index=False)
	print('Upload done.')


if __name__ == '__main__':
	try:
		upload_dataframe(df_loaded, MYSQL_DB, MYSQL_TABLE)
	except Exception as e:
		print('Upload failed:', e)
		raise

