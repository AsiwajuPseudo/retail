import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import time
import uuid

class Database:
    def __init__(self, db_path='../accounts.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        c = self.conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                name TEXT,
                surname TEXT,
                address TEXT,
                email TEXT UNIQUE,
                phone TEXT,
                password TEXT,
                eth_address TEXT,
                eth_key TEXT,
                verified TEXT DEFAULT 'false',
                fiat_balance REAL DEFAULT 0,
                tether_balance REAL DEFAULT 0,
                market_maker TEXT DEFAULT 'false'
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT,
                amount REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT,
                phone TEXT,
                amount REAL,
                processed TEXT DEFAULT 'open',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT,
                type TEXT,  -- 'buy' or 'sell'
                amount REAL,
                price REAL,
                is_market_order TEXT,
                status TEXT DEFAULT 'open',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS market (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT,
                price REAL,
                volume REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    # =====================
    # Account Management
    # =====================
    def register_user(self, name, surname, address, email, phone, password, eth_address, eth_key):
        try:
            hashed = generate_password_hash(password)
            new_id = str(uuid.uuid4()) 
            self.conn.execute('''
                INSERT INTO accounts (id, name, surname, address, email, phone, password, eth_address, eth_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (new_id, name, surname, address, email, phone, hashed, eth_address, eth_key))
            self.conn.commit()
            return {'status':'success','user_id':new_id,'name':name}
        except sqlite3.IntegrityError:
            return {'status':'Email already exists'}  # Email already exists

    def login_user(self, email, password):
        c = self.conn.cursor()
        c.execute('SELECT id, name, password FROM accounts WHERE email = ?', (email,))
        row = c.fetchone()
        if row:
            if check_password_hash(row[2], password):
                return {'status': row}
            else:
                return {'status':'Incorrect password'}
        return {'status':'Email does not exist'}

    def update_account(self, account_id, name, surname, email, phone,):
        self.conn.execute('UPDATE accounts SET name =?,surname=?,email=?,phone=? WHERE id = ?',(name,surname,email,phone,account_id))
        self.conn.commit()
        return {'status':'success'}

    def verify(self, account_id):
        self.conn.execute('UPDATE accounts SET verified ="true" WHERE id = ?',(account_id,))
        self.conn.commit()
        return {'status':'success'}

    def delete_account(self, account_id):
        self.conn.execute('DELETE FROM accounts WHERE id = ?',(account_id,))
        self.conn.commit()
        return {'status':'success'}

    def change_password(self, account_id, old, new_pass):
        c = self.conn.cursor()
        c.execute('SELECT id, name, password FROM accounts WHERE id = ?', (account_id,))
        row = c.fetchone()
        if row and check_password_hash(row[2], old):
            self.conn.execute('UPDATE accounts SET password =? WHERE id = ?',(new_pass, account_id))
            return {'status':'success'}
        else:
            return {'status':'Incorrect old password'}

    def user_account(self, account_id):
        c = self.conn.cursor()
        c.execute('SELECT eth_address, eth_key FROM accounts WHERE id = ?', (account_id,))
        return c.fetchone()

    def account(self, account_id):
        c = self.conn.cursor()
        c.execute('SELECT name, surname, email, phone, verified FROM accounts WHERE id = ?', (account_id,))
        return c.fetchone()

    def is_market_maker(self, account_id):
        c = self.conn.cursor()
        c.execute('SELECT market_maker FROM accounts WHERE id = ?', (account_id,))
        row = c.fetchone()
        if row[0]=='false':
            return False
        else:
            return True

    def user_accounts(self):
        c = self.conn.cursor()
        c.execute('SELECT * FROM accounts')
        return c.fetchall()

    def get_balances(self, account_id):
        c = self.conn.cursor()
        c.execute('SELECT fiat_balance, tether_balance FROM accounts WHERE id = ?', (account_id,))
        return c.fetchone()

    def get_total_balances(self):
        c = self.conn.cursor()
        c.execute('SELECT SUM(fiat_balance), SUM(tether_balance) FROM accounts')
        return c.fetchone()

    # =====================
    # Deposits and Withdrawals
    # =====================
    def deposit_fiat(self, account_id, amount):
        self.conn.execute('INSERT INTO deposits (account_id, amount) VALUES (?, ?)', (account_id, amount))
        self.conn.execute('UPDATE accounts SET fiat_balance = fiat_balance + ? WHERE id = ?', (amount, account_id))
        self.conn.commit()

    def deposit_tether(self, account_id, amount):
        self.conn.execute('INSERT INTO deposits (account_id, amount) VALUES (?, ?)', (account_id, amount))
        self.conn.execute('UPDATE accounts SET tether_balance = tether_balance + ? WHERE id = ?', (amount, account_id))
        self.conn.commit()

    def get_user_deposits(self, account_id):
        c = self.conn.cursor()
        c.execute('SELECT * FROM deposits WHERE account_id=? ORDER BY timestamp DESC',(account_id,))
        return c.fetchall()

    def withdraw_fiat(self, account_id, phone, amount):
        c = self.conn.cursor()
        c.execute('SELECT fiat_balance FROM accounts WHERE id = ?', (account_id,))
        balance = c.fetchone()[0]
        if balance >= amount:
            self.conn.execute('INSERT INTO withdrawals (account_id, phone, amount) VALUES (?, ?, ?)', (account_id, phone, amount))
            self.conn.execute('UPDATE accounts SET fiat_balance = fiat_balance - ? WHERE id = ?', (amount, account_id))
            self.conn.commit()
            return True
        return False

    def withdraw_tether(self, account_id, amount):
        c = self.conn.cursor()
        c.execute('SELECT tether_balance FROM accounts WHERE id = ?', (account_id,))
        balance = c.fetchone()[0]
        if balance >= amount:
            self.conn.execute('INSERT INTO withdrawals (account_id, amount) VALUES (?, ?)', (account_id, amount))
            self.conn.execute('UPDATE accounts SET tether_balance = tether_balance - ? WHERE id = ?', (amount, account_id))
            self.conn.commit()
            return True
        return False

    def withdraw_process(self, id_):
        c = self.conn.cursor()
        self.conn.execute('UPDATE withdrawals SET processed = ? WHERE id = ?', ('closed', id_))
        return True

    def withdrawals(self):
        c = self.conn.cursor()
        c.execute('SELECT * FROM withdrawals ORDER BY timestamp ASC')
        return c.fetchall()

    def get_user_withdrawals(self, account_id):
        c = self.conn.cursor()
        c.execute('SELECT * FROM withdrawals WHERE account_id=? ORDER BY timestamp DESC',(account_id,))
        return c.fetchall()

    # =====================
    # Orders
    # =====================
    def place_order(self, account_id, order_type, amount, price=None, is_market_order="market"):
        if order_type == 'buy':
            if is_market_order=='limit':
                return self._place_buy_order(account_id, amount, price, is_market_order)
            else:
                return self.market_buy_order(account_id, amount)
        elif order_type == 'sell':
            if is_market_order=='limit':
                return self._place_sell_order(account_id, amount, price, is_market_order)
            else:
                return self.market_sell_order(account_id, amount)

    def market_buy_order(self, account_id, amount):
        c = self.conn.cursor()

        # Match with existing SELL orders
        c.execute('''SELECT * FROM orders WHERE type = 'sell' AND status = 'open' ORDER BY price ASC, timestamp ASC''')
        sell_orders = c.fetchall()

        remaining = amount

        for order in sell_orders:
            sell_id, seller_id, _, sell_amount, sell_price, _, sell_status, _ = order
            match_amount = min(remaining, sell_amount)
            #check balance
            c.execute('SELECT fiat_balance FROM accounts WHERE id = ?', (account_id,))
            balance = c.fetchone()[0]
            total_cost = match_amount * sell_price
            match_volume=min(total_cost, balance)
            match_amount= match_volume / sell_price

            # Update buyer
            self.conn.execute('''
                UPDATE accounts SET fiat_balance = fiat_balance - ?, tether_balance = tether_balance + ?
                WHERE id = ?
            ''', (match_amount * sell_price, match_amount * sell_price, account_id))

            # Update seller
            self.conn.execute('''
                UPDATE accounts SET fiat_balance = fiat_balance + ?
                WHERE id = ?
            ''', (match_amount * sell_price, seller_id))

            # Update sell order
            if match_amount == sell_amount:
                self.conn.execute('UPDATE orders SET status = ? WHERE id = ?', ('filled', sell_id))
            else:
                self.conn.execute('''
                    UPDATE orders SET amount = amount - ? WHERE id = ?
                ''', (match_amount, sell_id))

            remaining -= match_amount

            if remaining == 0:
                break

        self.conn.commit()
        return {'status': 'success'}

    def _place_buy_order(self, account_id, amount, price, is_market_order):
        c = self.conn.cursor()
        c.execute('SELECT fiat_balance FROM accounts WHERE id = ?', (account_id,))
        balance = c.fetchone()[0]
        total_cost = amount * price

        if balance < total_cost:
            return {'status': 'Insufficient cash balance'}

        # Match with existing SELL orders at or below price
        c.execute('''
            SELECT * FROM orders
            WHERE type = 'sell' AND price <= ? AND status = 'open'
            ORDER BY price ASC, timestamp ASC
        ''', (price,))
        sell_orders = c.fetchall()

        remaining = amount

        for order in sell_orders:
            sell_id, seller_id, _, sell_amount, sell_price, _, sell_status, _ = order
            match_amount = min(remaining, sell_amount)

            # Update buyer
            self.conn.execute('''
                UPDATE accounts SET fiat_balance = fiat_balance - ?, tether_balance = tether_balance + ?
                WHERE id = ?
            ''', (match_amount * sell_price, match_amount * sell_price, account_id))

            # Update seller
            self.conn.execute('''
                UPDATE accounts SET fiat_balance = fiat_balance + ?
                WHERE id = ?
            ''', (match_amount * sell_price, seller_id))

            # Update sell order
            if match_amount == sell_amount:
                self.conn.execute('UPDATE orders SET status = ? WHERE id = ?', ('filled', sell_id))
            else:
                self.conn.execute('''
                    UPDATE orders SET amount = amount - ? WHERE id = ?
                ''', (match_amount, sell_id))

            remaining -= match_amount

            if remaining == 0:
                break

        # If unmatched amount remains, add to order book
        if remaining > 0:
            self.conn.execute('''
                INSERT INTO orders (account_id, type, amount, price, is_market_order)
                VALUES (?, 'buy', ?, ?, ?)
            ''', (account_id, remaining, price, is_market_order))

            # Reserve fiat for unmatched amount
            self.conn.execute('''
                UPDATE accounts SET fiat_balance = fiat_balance - ? WHERE id = ?
            ''', (remaining * price, account_id))

        self.conn.commit()
        return {'status': 'success'}

    def market_sell_order(self, account_id, amount):
        c = self.conn.cursor()

        # Match with existing BUY orders
        c.execute('''SELECT * FROM orders WHERE type = 'buy' AND status = 'open' ORDER BY price DESC, timestamp ASC''')
        buy_orders = c.fetchall()

        remaining = amount

        for order in buy_orders:
            buy_id, buyer_id, _, buy_amount, buy_price, _, buy_status, _ = order
            match_amount = min(remaining, buy_amount)
            #check balance
            c.execute('SELECT tether_balance FROM accounts WHERE id = ?', (account_id,))
            balance = c.fetchone()[0]
            total_cost = match_amount * buy_price
            match_volume=min(total_cost, balance)
            match_amount= match_volume / buy_price

            # Update seller
            self.conn.execute('''
                UPDATE accounts SET fiat_balance = fiat_balance + ?, tether_balance = tether_balance - ?
                WHERE id = ?
            ''', (match_amount * buy_price, match_amount * buy_price, account_id))

            # Update buyer
            self.conn.execute('''
                UPDATE accounts SET tether_balance = tether_balance + ?
                WHERE id = ?
            ''', (match_amount * buy_price, buyer_id))

            # Update buy order
            if match_amount == buy_amount:
                self.conn.execute('UPDATE orders SET status = ? WHERE id = ?', ('filled', buy_id))
            else:
                self.conn.execute('''
                    UPDATE orders SET amount = amount - ? WHERE id = ?
                ''', (match_amount, buy_id))

            remaining -= match_amount

            if remaining == 0:
                break

        self.conn.commit()
        return {'status': 'success'}

    def _place_sell_order(self, account_id, amount, price, is_market_order):
        c = self.conn.cursor()

        # Get user's tether balance
        c.execute('SELECT tether_balance FROM accounts WHERE id = ?', (account_id,))
        balance = c.fetchone()[0]
        total_cost=amount * price

        if balance < total_cost:
            return {'status': 'Insufficient crypto balance'}

        # Match with existing BUY orders at or above price
        c.execute('''
            SELECT * FROM orders
            WHERE type = 'buy' AND price >= ? AND status = 'open'
            ORDER BY price DESC, timestamp ASC
        ''', (price,))
        buy_orders = c.fetchall()

        remaining = amount

        for order in buy_orders:
            buy_id, buyer_id, _, buy_amount, buy_price, _, buy_status, _ = order
            match_amount = min(remaining, buy_amount)

            # Update seller
            self.conn.execute('''
                UPDATE accounts SET fiat_balance = fiat_balance + ?, tether_balance = tether_balance - ?
                WHERE id = ?
            ''', (match_amount * buy_price, match_amount * buy_price, account_id))

            # Update buyer
            self.conn.execute('''
                UPDATE accounts SET tether_balance = tether_balance + ?
                WHERE id = ?
            ''', (match_amount * buy_price, buyer_id))

            # Update buy order
            if match_amount == buy_amount:
                self.conn.execute('UPDATE orders SET status = ? WHERE id = ?', ('filled', buy_id))
            else:
                self.conn.execute('''
                    UPDATE orders SET amount = amount - ? WHERE id = ?
                ''', (match_amount, buy_id))

            remaining -= match_amount

            if remaining == 0:
                break

        # If unmatched amount remains, add to order book
        if remaining > 0:
            self.conn.execute('''
                INSERT INTO orders (account_id, type, amount, price, is_market_order)
                VALUES (?, 'sell', ?, ?, ?)
            ''', (account_id, remaining, price, is_market_order))

            # Reserve tether for unmatched amount
            self.conn.execute('''
                UPDATE accounts SET tether_balance = tether_balance - ? WHERE id = ?
            ''', (remaining * price, account_id))

        self.conn.commit()
        return {'status': 'success'}

    def cancel_order(self, account_id, order_id):
        c = self.conn.cursor()
        order_=self.conn.execute('SELECT amount, price, type FROM orders WHERE id = ? AND account_id = ?', (order_id, account_id))
        order=order_.fetchone()
        if order[2]=='buy':
            self.conn.execute('''
                UPDATE accounts SET fiat_balance = fiat_balance + ? WHERE id = ?
            ''', (order[0] * order[1], account_id))
        else:
            self.conn.execute('''
                UPDATE accounts SET tether_balance = tether_balance + ? WHERE id = ?
            ''', (order[0] * order[1], account_id))
        self.conn.execute('DELETE FROM orders WHERE id = ? AND account_id = ?', (order_id, account_id))
        self.conn.commit()

    # =====================
    # Order Queries
    # =====================
    def get_user_buy_orders(self, account_id):
        c = self.conn.cursor()
        c.execute('''
            SELECT * FROM orders
            WHERE account_id = ? AND type = 'buy' AND status='open'
            ORDER BY timestamp DESC
        ''', (account_id,))
        return c.fetchall()

    def get_user_sell_orders(self, account_id):
        c = self.conn.cursor()
        c.execute('''
            SELECT * FROM orders
            WHERE account_id = ? AND type = 'sell' AND status='open'
            ORDER BY timestamp DESC
        ''', (account_id,))
        return c.fetchall()

    def get_all_orders(self):
        c = self.conn.cursor()
        c.execute('SELECT * FROM orders ORDER BY price DESC')
        return c.fetchall()

    def close(self):
        self.conn.close()