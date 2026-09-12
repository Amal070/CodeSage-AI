from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.user import User
from app.schemas.auth import UserRegisterRequest, UserLoginRequest
from app.core.security import hash_password, verify_password


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Retrieve a user from the database by their normalized email address.
    """
    normalized_email = email.strip().lower()
    stmt = select(User).where(User.email == normalized_email)
    return db.scalars(stmt).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    Retrieve a user from the database by their unique ID.
    """
    stmt = select(User).where(User.id == user_id)
    return db.scalars(stmt).first()


def register_user(db: Session, user_in: UserRegisterRequest) -> User:
    """
    Creates and persists a new user with a hashed password.
    Caller must ensure email uniqueness prior to calling or handle integrity.
    """
    normalized_email = user_in.email.strip().lower()
    hashed_pwd = hash_password(user_in.password)

    new_user = User(
        name=user_in.name.strip(),
        email=normalized_email,
        password_hash=hashed_pwd
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def authenticate_user(db: Session, login_data: UserLoginRequest) -> Optional[User]:
    """
    Verifies user credentials. Returns the User model instance if valid,
    or None if the user does not exist or the password does not match.
    """
    user = get_user_by_email(db, login_data.email)
    if not user:
        return None

    if not verify_password(login_data.password, user.password_hash):
        return None

    return user
