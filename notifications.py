import sqlite3
import time
import uuid
import os

class Notifications:
    def __init__(self, db_path='../notifications.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        c = self.conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT,
                stamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                content TEXT,
                account_id TEXT,
                publisher TEXT,
                viewed TEXT DEFAULT 'false'
            )
        ''')

        self.conn.commit()

    def add(self, id_, account_id, content, publisher):
        try:
            self.conn.execute('''
                INSERT INTO notifications (id, content, account_id, publisher)
                VALUES (?, ?, ?, ?)
            ''', (id_, content, account_id, publisher))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Existing notification with same ID

    def delete_noti(self, id_):
        self.conn.execute('DELETE FROM notifications WHERE id = ?', (id_,))
        self.conn.commit()

    def admin_noti(self):
        c = self.conn.cursor()
        c.execute('SELECT id,stamp,content,viewed FROM notifications WHERE publisher="admin"')
        return c.fetchall()

    def user_noti(self, account_id):
        c = self.conn.cursor()
        c.execute('SELECT stamp,content FROM notifications WHERE viewed="false" AND account_id=?', (account_id,))
        noti=c.fetchall()
        #now show them as viewed
        self.conn.execute('UPDATE notifications SET viewed="true" WHERE viewed="false" AND account_id=?', (account_id,))
        self.conn.commit()
        return noti