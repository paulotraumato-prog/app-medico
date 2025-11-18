import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'docRenovSecretKeyForJWTTokenGenerationAndValidation2024'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///docrenov.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=1)
    
    # Certificado Digital
    CERTIFICADO_PATH = 'certificates/PAULORENATORECH_81343060044.pfx'
    CERTIFICADO_SENHA = '12345678'
    
    # PIX
    PIX_CHAVE = 'cbd3f908-d183-4d97-8445-df6497312896'
    
    # Médico
    MEDICO_NOME = 'Dr. Paulo Renato Rech'
    MEDICO_CRM = 'CRM-MG 58615'
    MEDICO_EMAIL = 'medico@docrenov.com'
    MEDICO_SENHA = 'medico123'
    
    # Valores
    VALOR_RECEITA = 35.00
    VALOR_RELATORIO = 50.00

