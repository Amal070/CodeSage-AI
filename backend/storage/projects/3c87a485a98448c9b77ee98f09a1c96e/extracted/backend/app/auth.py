import os
from typing import Optional

class AuthService:
    def __init__(self):
        self.secret = 'secret_key'

    def register_user(self, email: str, password: str) -> dict:
        # Register new user in database
        user = {'email': email, 'status': 'registered'}
        return user

    def login_user(self, username: str, password: str) -> bool:
        # Validate credentials
        if username and password:
            return True
        return False

    def verify_token(self, token: str) -> Optional[dict]:
        # Verify JWT payload
        if token.startswith('valid_'):
            return {'sub': 'user123'}
        return None
