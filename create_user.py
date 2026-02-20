from db.database import get_db
from auth.authenticator import hash_password
import uuid

def create_user(email, password, display_name):
    user_id = uuid.uuid4().hex
    pw_hash = hash_password(password)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, display_name) VALUES (?, ?, ?, ?)",
            (user_id, email, pw_hash, display_name),
        )
        conn.commit()
    print(f"User created: {email} (id: {user_id})")

if __name__ == "__main__":
    create_user("rsaffold@lebertech.com", "Flowdoe00@@", "R Saffold")
