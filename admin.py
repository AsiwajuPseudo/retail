import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import time
import uuid

class Admin:
    def __init__(self, db_path='../admin.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()
        self.register_user('Munyaradzi', 'Togarepi', 'munya@gmail.com', '@munya1')

    def create_tables(self):
        c = self.conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                name TEXT,
                surname TEXT,
                email TEXT UNIQUE,
                password TEXT
            )
        ''')

        self.conn.commit()

    # =====================
    # Account Management
    # =====================
    def register_user(self, name, surname, email, password):
        try:
            hashed = generate_password_hash(password)
            new_id = str(uuid.uuid4()) 
            self.conn.execute('''
                INSERT INTO accounts (id, name, surname, email, password)
                VALUES (?, ?, ?, ?, ?)
            ''', (new_id, name, surname, email, hashed))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Email already exists

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

    def check(self, account_id):
        c = self.conn.cursor()
        c.execute('SELECT id, name FROM accounts WHERE id = ?', (account_id,))
        row = c.fetchone()
        if row:
            return True
        return False

    def admins(self):
        c = self.conn.cursor()
        c.execute('SELECT * FROM accounts')
        return c.fetchall()

    def delete_admin(self, account_id):
        self.conn.execute('DELETE FROM accounts WHERE id = ?', (account_id,))
        self.conn.commit()