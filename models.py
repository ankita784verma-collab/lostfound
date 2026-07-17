from flask_login import UserMixin
import db


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.full_name = row["full_name"]
        self.email = row["email"]
        self.phone = row.get("phone")
        self.is_admin = bool(row["is_admin"])

    @staticmethod
    def get_by_id(user_id):
        row = db.query(
            "SELECT * FROM users WHERE id = %s",
            (user_id,),
            fetchone=True
        )
        return User(row) if row else None

    @staticmethod
    def get_by_email(email):
        row = db.query(
            "SELECT * FROM users WHERE email = %s",
            (email,),
            fetchone=True
        )
        return User(row) if row else None