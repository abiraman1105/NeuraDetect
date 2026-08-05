"""
Run this once to create the admin account with a proper password hash.
Usage: python init_admin.py
"""
import MySQLdb
from werkzeug.security import generate_password_hash

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "passwd": "John88cena@",          # ← your MySQL password
    "db": "microbleed_db",
    "charset": "utf8mb4",
}

def create_admin():
    print("=== NeuroScan Admin Setup ===")
    username  = input("Admin username [admin]: ").strip() or "admin"
    full_name = input("Full name [System Administrator]: ").strip() or "System Administrator"
    email     = input("Email [admin@hospital.com]: ").strip() or "admin@hospital.com"
    password  = input("Password [Admin@123]: ").strip() or "Admin@123"

    conn = MySQLdb.connect(**DB_CONFIG)
    cur  = conn.cursor()
    hashed = generate_password_hash(password)
    cur.execute("""
        INSERT INTO admins (username, password_hash, full_name, email)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE password_hash=%s, full_name=%s, email=%s
    """, (username, hashed, full_name, email, hashed, full_name, email))
    conn.commit()
    cur.close()
    conn.close()
    print(f"\n✅  Admin '{username}' created/updated successfully.")
    print(f"    You can now log in at http://127.0.0.1:5000/login")

if __name__ == "__main__":
    create_admin()
