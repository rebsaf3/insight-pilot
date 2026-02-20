"""
CLI tool for admin tasks: user management, data import/export.
Usage:
  python manage.py <command> [options]

Commands:
  list-users
  create-user <email> <password> <display_name>
  reset-password <email> <new_password>
  export-users <output_file>
  import-users <input_file>
  export-audit-log <output_file>
  review-audit-log
"""
import sys
from db.database import init_db, get_db
from auth.authenticator import hash_password
from db import queries
import csv


def list_users():
    users = []
    with get_db() as conn:
        rows = conn.execute('SELECT id, email, display_name, created_at FROM users').fetchall()
        for row in rows:
            users.append(dict(row))
    for user in users:
        print(user)

def create_user(email, password, display_name):
    pw_hash = hash_password(password)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, display_name) VALUES (?, ?, ?, ?)",
            (queries._new_id(), email.strip().lower(), pw_hash, display_name),
        )
        conn.commit()
    print(f"User created: {email}")

def reset_password(email, new_password):
    user = queries.get_user_by_email(email.strip().lower())
    if not user:
        print("User not found.")
        return
    pw_hash = hash_password(new_password)
    with get_db() as conn:
        conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (pw_hash, user.id))
        conn.commit()
    print(f"Password reset for: {email}")

def export_users(output_file):
    with get_db() as conn, open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'email', 'display_name', 'created_at'])
        for row in conn.execute('SELECT id, email, display_name, created_at FROM users'):
            writer.writerow([row['id'], row['email'], row['display_name'], row['created_at']])
    print(f"Exported users to {output_file}")

def import_users(input_file):
    with get_db() as conn, open(input_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not queries.get_user_by_email(row['email']):
                conn.execute(
                    "INSERT INTO users (id, email, password_hash, display_name, created_at) VALUES (?, ?, ?, ?, ?)",
                    (row['id'], row['email'], '', row['display_name'], row['created_at'])
                )
        conn.commit()
    print(f"Imported users from {input_file}")

def export_audit_log(output_file):
    """Export audit log to CSV file."""
    import csv
    with get_db() as conn, open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'user_id', 'workspace_id', 'action', 'entity_type', 'entity_id', 'details', 'ip_address', 'created_at'])
        for row in conn.execute('SELECT id, user_id, workspace_id, action, entity_type, entity_id, details, ip_address, created_at FROM audit_log'):
            writer.writerow([row['id'], row['user_id'], row['workspace_id'], row['action'], row['entity_type'], row['entity_id'], row['details'], row['ip_address'], row['created_at']])
    print(f"Exported audit log to {output_file}")

def review_audit_log(limit=20):
    """Print the most recent audit log entries."""
    with get_db() as conn:
        rows = conn.execute('SELECT id, user_id, action, entity_type, entity_id, details, created_at FROM audit_log ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()
        for row in rows:
            print(dict(row))

def main():
    init_db()
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == 'list-users':
        list_users()
    elif cmd == 'create-user' and len(sys.argv) == 5:
        create_user(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == 'reset-password' and len(sys.argv) == 4:
        reset_password(sys.argv[2], sys.argv[3])
    elif cmd == 'export-users' and len(sys.argv) == 3:
        export_users(sys.argv[2])
    elif cmd == 'import-users' and len(sys.argv) == 3:
        import_users(sys.argv[2])
    elif cmd == 'export-audit-log' and len(sys.argv) == 3:
        export_audit_log(sys.argv[2])
    elif cmd == 'review-audit-log':
        limit = int(sys.argv[2]) if len(sys.argv) == 3 else 20
        review_audit_log(limit)
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
