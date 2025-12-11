import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL=os.getenv('DATABASE_URL')

SECRET_KEY=os.getenv('SECRET_KEY','super-secret-key-change-me')
ALGORITHM='HS256'
ACCESS_TOKEN_EXPIRE_MINUTES=60

MERCADOPAGO_PUBLIC_KEY=os.getenv('MERCADOPAGO_PUBLIC_KEY','')
MERCADOPAGO_ACCESS_TOKEN=os.getenv('MERCADOPAGO_ACCESS_TOKEN','')
