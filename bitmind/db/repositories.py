# Placeholder repository functions for future DB-backed operations
from . import models as dbmodels


def create_user(db, id: str, username: str):
    user = dbmodels.User(id=id, username=username)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user(db, user_id: str):
    return db.query(dbmodels.User).filter(dbmodels.User.id == user_id).first()
