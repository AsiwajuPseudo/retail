import sqlite3
from datetime import datetime

class Market:
    def __init__(self, db_name = "../market.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_table()

    def create_table(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    price REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def add_price(self, ticker, price, timestamp = None):
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()
        with self.conn:
            self.conn.execute("""
                INSERT INTO market_data (ticker, price)
                VALUES (?, ?)
            """, (ticker.upper(), price))

    def get_market_data(self, ticker):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT price, timestamp
            FROM market_data
            WHERE ticker = ?
            ORDER BY timestamp ASC
        """, (ticker.upper(),))
        return cursor.fetchall()

    def close(self):
        self.conn.close()