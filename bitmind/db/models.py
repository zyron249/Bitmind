from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Float, Integer

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    reputation = Column(Float, default=0.5)
    balance = Column(Float, default=0.0)
    staked = Column(Float, default=0.0)
