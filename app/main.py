from fastapi import FastAPI,Depends,HTTPException,Request,Form
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import timedelta
import mercadopago
from .database import get_db,init_db,User
from .auth import get_password_hash,verify_password,create_access_token,get_current_user
from .config import *
import os

app = FastAPI(title='App Médico')
templates = Jinja2Templates(directory='app/templates')
mp = mercadopago.SDK(MERCADOPAGO_ACCESS_TOKEN) if MERCADOPAGO_ACCESS_TOKEN else None

@app.get('/', response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})

@app.get('/setup-db')
async def setup_database():
    try:
        init_db()
        return {'message': 'Database initialized'}
    except Exception as e:
        return {'error': str(e)}

@app.get('/login', response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse('login.html', {'request': request})

@app.post('/login')
async def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail='Email ou senha incorretos')
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={'sub': user.email}, expires_delta=access_token_expires)
    response = RedirectResponse(url='/', status_code=303)
    response.set_cookie(key='access_token', value=f'Bearer {access_token}', httponly=True)
    return response

@app.get('/register', response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse('register.html', {'request': request})

@app.post('/register')
async def register(
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    user_type: str = Form(...),
    cpf: str = Form(...),
    phone: str = Form(...),
    crm: str = Form(None),
    crm_uf: str = Form(None),
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail='Email já cadastrado')
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        user_type=user_type,
        cpf=cpf,
        phone=phone,
        crm=crm if user_type == 'doctor' else None,
        crm_uf=crm_uf if user_type == 'doctor' else None
    )
    db.add(user)
    db.commit()
    return RedirectResponse(url='/login', status_code=303)
