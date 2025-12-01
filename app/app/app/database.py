from sqlalchemy import create_engine,Column,Integer,String,DateTime,Text,Float,Boolean,ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker,relationship
from datetime import datetime
from .config import DATABASE_URL

engine=create_engine(DATABASE_URL)
SessionLocal=sessionmaker(autocommit=False,autoflush=False,bind=engine)
Base=declarative_base()

class User(Base):
 __tablename__='users'
 id=Column(Integer,primary_key=True,index=True)
 email=Column(String,unique=True,index=True)
 hashed_password=Column(String)
 full_name=Column(String)
 user_type=Column(String)  # 'patient' ou 'doctor'
 cpf=Column(String,unique=True)
 phone=Column(String)
 created_at=Column(DateTime,default=datetime.utcnow)
 crm=Column(String,nullable=True)
 crm_uf=Column(String,nullable=True)
 cases_as_patient=relationship('Case',back_populates='patient',foreign_keys='Case.patient_id')
 cases_as_doctor=relationship('Case',back_populates='doctor',foreign_keys='Case.doctor_id')

class Case(Base):
 __tablename__='cases'
 id=Column(Integer,primary_key=True,index=True)
 patient_id=Column(Integer,ForeignKey('users.id'))
 doctor_id=Column(Integer,ForeignKey('users.id'),nullable=True)
 case_type=Column(String)  # 'receita' ou 'relatorio'
 description=Column(Text)
 status=Column(String,default='pending')  # pending, paid, in_review, approved, rejected, completed
 payment_id=Column(String,nullable=True)
 payment_status=Column(String,default='pending')
 amount=Column(Float,default=50.0)
 created_at=Column(DateTime,default=datetime.utcnow)
 updated_at=Column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
 ai_generated_document=Column(Text,nullable=True)
 final_document_url=Column(String,nullable=True)
 rejection_reason=Column(Text,nullable=True)
 patient=relationship('User',back_populates='cases_as_patient',foreign_keys=[patient_id])
 doctor=relationship('User',back_populates='cases_as_doctor',foreign_keys=[doctor_id])

class Certificate(Base):
 __tablename__='certificates'
 id=Column(Integer,primary_key=True,index=True)
 file_path=Column(String)
 password=Column(String)
 uploaded_at=Column(DateTime,default=datetime.utcnow)
 is_active=Column(Boolean,default=True)

def get_db():
 db=SessionLocal()
 try:
  yield db
 finally:
  db.close()

def init_db():
 Base.metadata.create_all(bind=engine)
