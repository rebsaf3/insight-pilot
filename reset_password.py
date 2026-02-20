from db.database import get_db
from auth.authenticator import hash_password

def reset_only_user_password(new_password):
    with get_db() as conn:
        row = conn.execute('SELECT id FROM users LIMIT 1').fetchone()
        user_id = row[0] if row else None
        if not user_id:
            print('No user found.')
            return
        new_pw_hash = hash_password(new_password)
        conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_pw_hash, user_id))
        conn.commit()
        print(f'Password updated for user: {user_id}')

if __name__ == "__main__":
    reset_only_user_password('Flowdoe00@@')
