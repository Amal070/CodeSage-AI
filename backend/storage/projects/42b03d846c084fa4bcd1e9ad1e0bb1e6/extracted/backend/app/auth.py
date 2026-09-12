import jwt
from datetime import datetime, timedelta

SECRET_KEY = 'super-secret-jwt-key'

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    '''Generates signed JWT access token for user authentication.'''
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm='HS256')

def verify_jwt_token(token: str) -> dict:
    '''Decodes and validates JWT bearer authentication token.'''
    return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
