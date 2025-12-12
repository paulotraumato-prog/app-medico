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

app=FastAPI(title='App Médico')
templates=Jinja2Templates(directory='app/templates')
mp=mercadopago.SDK(MERCADOPAGO_ACCESS_TOKEN) if MERCADOPAGO_ACCESS_TOKEN else None

@app.get('/',response_class=HTMLResponse)
async def home(request:Request,current_user:User=Depends(get_current_user)):
    return templates.TemplateResponse('index.html',{'request':request,'user':current_user})

@app.get('/setup-db')
async def setup_database():
    try:
        init_db()
        return {'message':'Database initialized'}
    except Exception as e:
        return {'error':str(e)}

@app.get('/login',response_class=HTMLResponse)
async def login_page(request:Request):
    return templates.TemplateResponse('login.html',{'request':request})

@app.post('/login')
async def login(email:str=Form(...),password:str=Form(...),db:Session=Depends(get_db)):
    user=db.query(User).filter(User.email==email).first()
    if not user or not verify_password(password,user.hashed_password):
        raise HTTPException(status_code=400,detail='Email ou senha incorretos')
    access_token_expires=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token=create_access_token(data={'sub':user.email},expires_delta=access_token_expires)
    response=RedirectResponse(url='/',status_code=303)
    response.set_cookie(
        key='access_token',
        value=f'Bearer {access_token}',
        httponly=True,
        samesite='lax'
    )
    return response

@app.get('/register',response_class=HTMLResponse)
async def register_page(request:Request):
    return templates.TemplateResponse('register.html',{'request':request})

@app.post('/register')
async def register(
    email:str=Form(...),
    password:str=Form(...),
    full_name:str=Form(...),
    user_type:str=Form(...),
    cpf:str=Form(...),
    phone:str=Form(...),
    crm:str=Form(None),
    crm_uf:str=Form(None),
    db:Session=Depends(get_db)
):
    existing_user=db.query(User).filter(User.email==email).first()
    if existing_user:
        raise HTTPException(status_code=400,detail='Email já cadastrado')
    user=User(
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        user_type=user_type,
        cpf=cpf,
        phone=phone,
        crm=crm if user_type=='doctor' else None,
        crm_uf=crm_uf if user_type=='doctor' else None
    )
    db.add(user)
    db.commit()
    return RedirectResponse(url='/login',status_code=303)

# -------- PIX --------

@app.post('/pagamento/pix')
async def criar_pagamento_pix(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not mp:
        raise HTTPException(status_code=500, detail='Mercado Pago não configurado (ACCESS_TOKEN ausente).')

    amount = 50.0

    preference_data = {
        "items": [
            {
                "title": "Renovação de receita / relatório médico",
                "quantity": 1,
                "unit_price": amount,
                "currency_id": "BRL"
            }
        ],
        "payer": {
            "email": current_user.email
        },
        "payment_methods": {
            "excluded_payment_types": [
                {"id": "credit_card"},
                {"id": "debit_card"}
            ],
            "default_payment_method_id": "pix"
        },
        "back_urls": {
            "success": "https://app-medico-hfb0.onrender.com/",
            "failure": "https://app-medico-hfb0.onrender.com/",
            "pending": "https://app-medico-hfb0.onrender.com/"
        },
        "auto_return": "approved"
    }

    try:
        preference_response = mp.preference().create(preference_data)
        init_point = preference_response["response"]["init_point"]
        return {"checkout_url": init_point}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar pagamento PIX: {str(e)}")

@app.get('/teste-pix', response_class=HTMLResponse)
async def teste_pix_page(request: Request,current_user:User=Depends(get_current_user)):
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Teste PIX</title>
    </head>
    <body>
        <h1>Teste de Pagamento PIX</h1>
        <p>Usuário logado: {current_user.email}</p>
        <button onclick="gerarPix()">Gerar pagamento PIX (R$ 50,00)</button>
        <p id="status"></p>
        <script>
            async function gerarPix(){{
                document.getElementById('status').innerText = 'Gerando pagamento...';
                try{{
                    const tokenCookie = document.cookie.split('access_token=')[1];
                    const token = tokenCookie ? tokenCookie.split(';')[0] : '';
                    const resp = await fetch('/pagamento/pix', {{
                        method: 'POST',
                        headers: {{
                            'Authorization': token
                        }}
                    }});
                    if(!resp.ok){{
                        const err = await resp.json();
                        document.getElementById('status').innerText = 'Erro: ' + (err.detail || resp.status);
                        return;
                    }}
                    const data = await resp.json();
                    document.getElementById('status').innerText = 'Redirecionando para o Mercado Pago...';
                    window.location.href = data.checkout_url;
                }}catch(e){{
                    document.getElementById('status').innerText = 'Erro: ' + e;
                }}
            }}
        </script>
    </body>
    </html>
    @app.get('/admin/reset')
async def reset_database(db: Session = Depends(get_db)):
    try:
        # Apaga todos os registros
        db.query(User).delete()
        db.commit()
        return {'message': 'Todos os cadastros foram apagados com sucesso'}
    except Exception as e:
        db.rollback()
        return {'error': str(e)}
    """)
