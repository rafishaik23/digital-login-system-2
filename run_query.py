import sqlite3

conn = sqlite3.connect('database.db')  # Replace with your actual .db filename
cursor = conn.cursor()

# Check if password column exists before dropping
cursor.execute("PRAGMA table_info(users)")
columns = cursor.fetchall()
has_password = any(col[1] == 'password' for col in columns)

if has_password:
    cursor.execute("ALTER TABLE users DROP COLUMN password")
    conn.commit()
    print("Password column removed successfully!")
else:
    print("Password column does not exist.")

conn.close()