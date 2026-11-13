import logging

import bcrypt

logger = logging.getLogger(__name__)


class UserRepository:
    """All Supabase calls related to users (login, signup)."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    def get_user_by_username(self, username: str):
        """Return a user record dict or None."""
        result = self.db.table("users").select("*").eq("username", username).execute()
        return result.data[0] if result.data else None

    def verify_login(self, username: str, password_plain: str):
        """
        Return the user dict if the password matches, else None.
        bcrypt.checkpw compares plain text against the stored hash safely.
        """
        user = self.get_user_by_username(username)
        if not user:
            return None
        stored_hash = user.get("password", "")
        if bcrypt.checkpw(password_plain.encode(), stored_hash.encode()):
            return user
        return None

    def create_user(self, user_data: dict, password_plain: str):
        """
        Hash the password with bcrypt before storing.
        bcrypt.gensalt() adds a random salt so identical passwords
        produce different hashes — secure against rainbow-table attacks.
        """
        hashed = bcrypt.hashpw(password_plain.encode(), bcrypt.gensalt()).decode()
        user_data["password"] = hashed  # only the hash goes to the database
        result = self.db.table("users").insert(user_data).execute()
        return result.data
