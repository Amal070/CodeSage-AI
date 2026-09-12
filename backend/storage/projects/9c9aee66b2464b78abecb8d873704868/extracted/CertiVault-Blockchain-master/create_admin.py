#!/usr/bin/env python
import os
import django
import sqlite3

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'certivault.settings')
django.setup()

from django.contrib.auth.hashers import make_password

# Connect to SQLite
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Get the next available ID
cursor.execute('SELECT MAX(id) FROM accounts_customuser')
max_id = cursor.fetchone()[0]
next_id = (max_id or 0) + 1

# Create hashed password
hashed_password = make_password('admin123')

# Insert admin user
cursor.execute('''
    INSERT INTO accounts_customuser (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined, user_type)
    VALUES (?, ?, NULL, 0, ?, '', '', ?, 0, 1, datetime('now'), ?)
''', (next_id, hashed_password, 'admin', 'admin@certivault.com', 'admin'))

conn.commit()
print(f'Admin user created successfully!')
print(f'ID: {next_id}')
print(f'Username: admin')
print(f'Password: admin123')
print(f'User Type: admin')
conn.close()

