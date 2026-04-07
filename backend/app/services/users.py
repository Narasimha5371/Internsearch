from sqlalchemy.orm import Session

from app.db.models import User


def get_or_create_user(db: Session, clerk_user_id: str, email: str | None) -> User:
    user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
    if user:
        if email and not user.email:
            user.email = email
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    user = User(clerk_user_id=clerk_user_id, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
