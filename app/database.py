from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from datetime import datetime
from .config import DATABASE_URL

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    user_type = Column(String) # 'patient' ou 'doctor'
    cpf = Column(String, unique=True, nullable=True)
    phone = Column(String, nullable=True)
    crm = Column(String, nullable=True) # Apenas para doctors
    crm_uf = Column(String, nullable=True) # Apenas para doctors

    cases_as_patient = relationship('Case', back_populates='patient', foreign_keys='Case.patient_id')
    cases_as_doctor = relationship('Case', back_populates='doctor', foreign_keys='Case.doctor_id')
    documents = relationship('Document', back_populates='case')

class Case(Base):
    __tablename__ = 'cases'
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey('users.id'))
    doctor_id = Column(Integer, ForeignKey('users.id'), nullable=True) # Médico que revisou/assinou
    request_type = Column(String) # Ex: 'receita', 'relatorio'
    status = Column(String, default='pending_payment') # pending_payment, pending_review, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    payment_status = Column(String, default='pending') # pending, paid, failed
    payment_id = Column(String, nullable=True) # ID do pagamento no MP
    rejection_reason = Column(Text, nullable=True) # Motivo da rejeição pelo médico

    patient = relationship('User', back_populates='cases_as_patient', foreign_keys=[patient_id])
    doctor = relationship('User', back_populates='cases_as_doctor', foreign_keys=[doctor_id])
    document = relationship('Document', back_populates='case', uselist=False) # Um caso tem um documento

class Document(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey('cases.id'))
    file_path = Column(String, nullable=True) # Caminho para o PDF gerado
    signed_by_doctor = Column(Boolean, default=False)
    signed_at = Column(DateTime, nullable=True)
    generated_text = Column(Text, nullable=True) # Texto base gerado pela IA (se for o caso)

    case = relationship('Case', back_populates='document')

# Configuração do banco de dados
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
def init_db():
    Base.metadata.create_all(bind=engine)
