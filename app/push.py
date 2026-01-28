"""Manages push notification subscriptions.

For progressive web apps, all push notifications are represented
through subscription info objects. When subscribing to push notifications,
we receive such an object, and store it an sqlite database.
"""
import json
import os
import sqlite3

import pywebpush

DB_PATH = '/data/subs.db'


def _execute_sql(sql, args):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(sql, args)
        conn.commit()
    finally:
        if conn:
            conn.close()


def _ensure_db_exists():
    db_exists = os.path.exists(DB_PATH)
    if not db_exists:
        _execute_sql('CREATE TABLE subs (sub text)', [])


def save_subscription(data):
    _ensure_db_exists()
    _validate_subscription_info(data)
    _execute_sql('INSERT INTO subs (sub) VALUES (?)', (data,))


def remove_subscription(data):
    _ensure_db_exists()
    _validate_subscription_info(data)
    _execute_sql('DELETE FROM subs WHERE sub = ?', (data,))


def _validate_subscription_info(data):
    """Checks whether or not a string representing subscription info is valid"""
    subscription_info = json.loads(data)
    # We exploit the fact that pywebpush.WebPusher validates the data on initialization; we don't actually use
    # pywebpush for any of its real functionality here.
    pywebpush.WebPusher(subscription_info)
