from sqlalchemy import create_engine,Column,Integer,String,Boolean,DateTime,ForeignKey,Text,Float
from sqlalchemy.orm import sessionmaker,relationship,DeclarativeBase
from datetime import datetime
from .config import DATABASE_URL

class Base(DeclarativeBase):
    pass

engine=create_engine(DATABASE_URL,echo=False,future=True)
SessionLocal=sessionmaker(autocommit=False,autoflush=False,bind=engine)

def get_db():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()

class User(Base):
    __tablename__='users'
    id=Column(Integer,primary_key=True,index=True)
    email=Column(String,unique=True,index=True,nullable=False)
    hashed_password=Column(String,nullable=False)
    full_name=Column(String,nullable=False)
    user_type=Column(String,nullable=False)  # 'patient' ou 'doctor'
    cpf=Column(String,nullable=False)
    phone=Column(String,nullable=False)
    crm=Column(String,nullable=True)
    crm_uf=Column(String,nullable=True)
    created_at=Column(DateTime,default=datetime.utcnow)

class Case(Base):
    __tablename__='cases'
    id=Column(Integer,primary_key=True,index=True)
    patient_id=Column(Integer,ForeignKey('users.id'))
    doctor_id=Column(Integer,ForeignKey('users.id'),nullable=True)
    description=Column(Text,nullable=False)
    status=Column(String,default='pending_payment')  # pending_payment, in_review, approved, rejected
    amount=Column(Float,default=50.0)
    payment_preference_id=Column(String,nullable=True)
    created_at=Column(DateTime,default=datetime.utcnow)

class Certificate(Base):
    __tablename__='certificates'
    id=Column(Integer,primary_key=True,index=True)
    doctor_id=Column(Integer,ForeignKey('users.id'))
    filename=Column(String,nullable=False)
    created_at=Column(DateTime,default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
