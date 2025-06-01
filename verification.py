import sqlite3
import time
import os

class Verification:
    def __init__(self, db_path='../verify.db'):
        os.makedirs('../verify', exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        c = self.conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS verifications (
                id TEXT UNIQUE,
                name TEXT,
                surname TEXT,
                national_id TEXT,
                id_file TEXT,
                selfie TEXT,
                verified TEXT DEFAULT 'false'
            )
        ''')

        self.conn.commit()

    def start(self, id_, name, surname, national_id, id_file, selfie):
        try:
            self.conn.execute('''
                INSERT INTO verifications (id, name, surname, national_id, id_file, selfie)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (id_, name, surname, national_id, id_file, selfie))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Pending verification already exists

    def finish(self, id_):
        self.conn.execute('UPDATE verifications SET verified="true" WHERE id = ?', (id_,))
        self.conn.commit()

    def all(self):
        c = self.conn.cursor()
        c.execute('SELECT * FROM verifications WHERE verified="false"')
        return c.fetchall()

    def delete_verification_data(self, user_id):
        c = self.conn.cursor()
        c.execute('SELECT id_file, selfie FROM verifications WHERE id = ?', (user_id,))
        row = c.fetchone()

        if row:
            id_file_path = os.path.join('../verify', row[0])
            selfie_path = os.path.join('../verify', row[1])

            # Delete the files if they exist
            if os.path.exists(id_file_path):
                os.remove(id_file_path)
            if os.path.exists(selfie_path):
                os.remove(selfie_path)

            # Delete the user from the database
            c.execute('DELETE FROM verifications WHERE id = ?', (user_id,))
            self.conn.commit()
            return {'status':'success'}
        return {'status':'User not found in verifications data'}  # No such user