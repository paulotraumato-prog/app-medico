from fastapi import FastAPI,Depends,HTTPException,Request,Form
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import timedelta
import mercadopago
from .database import get_db,init_db,User,Case,Document
from .auth import get_password_hash,verify_password,create_access_token,get_current_user
from .config import *
import os
import requests, json # Importar requests e json aqui

app = FastAPI(title='App Médico')
templates = Jinja2Templates(directory='app/templates')

# ---------- PÁGINA INICIAL (protegida por login) ----------

@app.get('/', response_class=HTMLResponse)
async def home(request: Request, current_user: User = Depends(get_current_user)):
    # Se o usuário estiver autenticado, mostra uma home simples
    return templates.TemplateResponse(
        'index.html',
        {
            'request': request,
            'user': current_user,
            'is_doctor': current_user.user_type == 'doctor'
        }
    )


# ---------- SETUP DB ----------

@app.get('/setup-db')
async def setup_database():
    try:
        init_db()
        return {'message': 'Database initialized'}
    except Exception as e:
        return {'error': str(e)}


# ---------- LOGIN / LOGOUT / REGISTRO ----------

@app.get('/login', response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse('login.html', {'request': request})


@app.post('/login')
async def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return RedirectResponse(url='/login?error=1', status_code=303)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={'sub': user.email},
        expires_delta=access_token_expires
    )

    response = RedirectResponse(url='/', status_code=303)
    response.set_cookie(
        key='access_token',
        value=f'Bearer {access_token}',
        httponly=True,
        samesite='lax'
    )
    return response


@app.get('/logout')
async def logout():
    response = RedirectResponse(url='/login', status_code=303)
    response.delete_cookie('access_token')
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


# ---------- RESET CADASTROS (temporário, SEM proteção) ----------

@app.get('/admin/reset')
async def reset_database(db: Session = Depends(get_db)):
    try:
        db.query(Document).delete() # Apaga documentos primeiro
        db.query(Case).delete()     # Apaga casos
        db.query(User).delete()     # Apaga usuários
        db.commit()
        return {'message': 'Todos os cadastros foram apagados com sucesso'}
    except Exception as e:
        db.rollback()
        return {'error': str(e)}


# ---------- PIX (TESTE) ----------

@app.post('/pagamento/pix')
async def criar_pagamento_pix(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not MERCADOPAGO_ACCESS_TOKEN:
        raise HTTPException(
            status_code=500,
            detail='Mercado Pago não configurado (ACCESS_TOKEN ausente).'
        )

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
            ]
        },
        "back_urls": {
            "success": "https://app-medico-hfb0.onrender.com/",
            "failure": "https://app-medico-hfb0.onrender.com/",
            "pending": "https://app-medico-hfb0.onrender.com/"
        },
        "auto_return": "approved"
    }

    headers = {
        "Authorization": f"Bearer {MERCADOPAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            "https://api.mercadopago.com/checkout/preferences",
            json=preference_data,
            headers=headers,
            timeout=15
        )

        if response.status_code != 201:
            raise HTTPException(
                status_code=500,
                detail=f"Erro do Mercado Pago: {response.status_code} - {response.text}"
            )

        data = response.json()

        init_point = data.get("init_point")
        if not init_point:
            raise HTTPException(
                status_code=500,
                detail=f"init_point não encontrado. Resposta: {data}"
            )

        return {"checkout_url": init_point}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar pagamento PIX (exceção): {repr(e)}"
        )


@app.get('/teste-pix', response_class=HTMLResponse)
async def teste_pix_page(request: Request, current_user: User = Depends(get_current_user)):
    html = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Teste PIX</title>
    </head>
    <body>
        <h1>Teste de Pagamento PIX</h1>
        <p>Usuário logado: %s</p>
        <button onclick="gerarPix()">Gerar pagamento PIX (R$ 50,00)</button>
        <p id="status"></p>
        <script>
            async function gerarPix(){
                document.getElementById('status').innerText = 'Gerando pagamento...';
                try{
                    const tokenCookie = document.cookie.split('access_token=')[1];
                    const token = tokenCookie ? tokenCookie.split(';')[0] : '';
                    const resp = await fetch('/pagamento/pix', {
                        method: 'POST',
                        headers: {
                            'Authorization': token
                        }
                    });
                    if(!resp.ok){
                        const err = await resp.json();
                        document.getElementById('status').innerText = 'Erro: ' + (err.detail || resp.status);
                        return;
                    }
                    const data = await resp.json();
                    document.getElementById('status').innerText = 'Redirecionando para o Mercado Pago...';
                    window.location.href = data.checkout_url;
                }catch(e){
                    document.getElementById('status').innerText = 'Erro: ' + e;
                }
            }
        </script>
    </body>
    </html>
    """ % (current_user.email)
    return HTMLResponse(html)


# ---------- ROTAS DE PACIENTE ----------

@app.get('/patient/dashboard', response_class=HTMLResponse)
async def patient_dashboard(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.user_type != 'patient':
        raise HTTPException(status_code=403, detail='Acesso negado')
    
    cases = db.query(Case).filter(Case.patient_id == current_user.id).order_by(Case.created_at.desc()).all()
    
    return templates.TemplateResponse(
        'patient_dashboard.html',
        {
            'request': request,
            'user': current_user,
            'cases': cases
        }
    )

@app.get('/patient/new-case', response_class=HTMLResponse)
async def new_case_page(request: Request, current_user: User = Depends(get_current_user)):
    if current_user.user_type != 'patient':
        raise HTTPException(status_code=403, detail='Acesso negado')
    return templates.TemplateResponse('new_case.html', {'request': request, 'user': current_user})

@app.post('/patient/new-case')
async def create_new_case(
    request_type: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.user_type != 'patient':
        raise HTTPException(status_code=403, detail='Acesso negado')
    
    new_case = Case(patient_id=current_user.id, request_type=request_type, status='pending_payment')
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    
    # Redireciona para a página de pagamento do caso
    return RedirectResponse(url=f'/patient/pay-case/{new_case.id}', status_code=303)


@app.get('/patient/pay-case/{case_id}', response_class=HTMLResponse)
async def pay_case_page(request: Request, case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.user_type != 'patient':
        raise HTTPException(status_code=403, detail='Acesso negado')
    
    case = db.query(Case).filter(Case.id == case_id, Case.patient_id == current_user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail='Caso não encontrado')
    if case.status != 'pending_payment':
        return RedirectResponse(url='/patient/dashboard', status_code=303) # Já pago ou em revisão
    
    return templates.TemplateResponse(
        'pay_case.html',
        {
            'request': request,
            'user': current_user,
            'case': case
        }
    )

@app.post('/patient/pay-case/{case_id}/generate-pix')
async def generate_pix_for_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.user_type != 'patient':
        raise HTTPException(status_code=403, detail='Acesso negado')
    
    case = db.query(Case).filter(Case.id == case_id, Case.patient_id == current_user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail='Caso não encontrado')
    if case.status != 'pending_payment':
        raise HTTPException(status_code=400, detail='Caso já pago ou em revisão')

    if not MERCADOPAGO_ACCESS_TOKEN:
        raise HTTPException(
            status_code=500,
            detail='Mercado Pago não configurado (ACCESS_TOKEN ausente).'
        )

    amount = 50.0 # Valor fixo por enquanto

    preference_data = {
        "items": [
            {
                "title": f"Pagamento Caso #{case.id} - {case.request_type}",
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
            ]
        },
        "back_urls": {
            "success": f"https://app-medico-hfb0.onrender.com/patient/case/{case.id}/status?payment_status=success",
            "failure": f"https://app-medico-hfb0.onrender.com/patient/case/{case.id}/status?payment_status=failure",
            "pending": f"https://app-medico-hfb0.onrender.com/patient/case/{case.id}/status?payment_status=pending"
        },
        "auto_return": "approved",
        "external_reference": str(case.id) # Usar o ID do caso como referência externa
    }

    headers = {
        "Authorization": f"Bearer {MERCADOPAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            "https://api.mercadopago.com/checkout/preferences",
            json=preference_data,
            headers=headers,
            timeout=15
        )

        if response.status_code != 201:
            raise HTTPException(
                status_code=500,
                detail=f"Erro do Mercado Pago: {response.status_code} - {response.text}"
            )

        data = response.json()
        init_point = data.get("init_point")
        if not init_point:
            raise HTTPException(
                status_code=500,
                detail=f"init_point não encontrado. Resposta: {data}"
            )
        
        # Atualiza o payment_id no caso
        case.payment_id = data.get('id') # ID da preferência do MP
        db.add(case)
        db.commit()
        db.refresh(case)

        return {"checkout_url": init_point}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar pagamento PIX: {repr(e)}"
        )

@app.get('/patient/case/{case_id}/status', response_class=HTMLResponse)
async def case_payment_status(
    request: Request,
    case_id: int,
    payment_status: str, # success, failure, pending
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.user_type != 'patient':
        raise HTTPException(status_code=403, detail='Acesso negado')
    
    case = db.query(Case).filter(Case.id == case_id, Case.patient_id == current_user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail='Caso não encontrado')
    
    # Atualiza o status do pagamento no caso
    case.payment_status = payment_status
    if payment_status == 'success':
        case.status = 'pending_review' # Se pagou, vai para revisão
    db.add(case)
    db.commit()
    db.refresh(case)

    return templates.TemplateResponse(
        'case_status.html',
        {
            'request': request,
            'user': current_user,
            'case': case,
            'payment_status': payment_status
        }
    )


# ---------- ROTAS DE MÉDICO ----------

@app.get('/doctor/dashboard', response_class=HTMLResponse)
async def doctor_dashboard(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.user_type != 'doctor':
        raise HTTPException(status_code=403, detail='Acesso negado')
    
    # Casos pendentes de revisão (já pagos)
    pending_cases = db.query(Case).filter(Case.status == 'pending_review').order_by(Case.created_at.asc()).all()
    
    # Casos que o médico já revisou
    my_reviewed_cases = db.query(Case).filter(Case.doctor_id == current_user.id).order_by(Case.updated_at.desc()).all()

    return templates.TemplateResponse(
        'doctor_dashboard.html',
        {
            'request': request,
            'user': current_user,
            'pending_cases': pending_cases,
            'my_reviewed_cases': my_reviewed_cases
        }
    )

@app.get('/doctor/review-case/{case_id}', response_class=HTMLResponse)
async def review_case_page(request: Request, case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.user_type != 'doctor':
        raise HTTPException(status_code=403, detail='Acesso negado')
    
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail='Caso não encontrado')
    if case.status != 'pending_review':
        return RedirectResponse(url='/doctor/dashboard', status_code=303) # Já revisado ou não pago
    
    return templates.TemplateResponse(
        'review_case.html',
        {
            'request': request,
            'user': current_user,
            'case': case,
            'patient': case.patient # Acesso aos dados do paciente
        }
    )

@app.post('/doctor/review-case/{case_id}')
async def submit_review_case(
    case_id: int,
    action: str = Form(...), # 'approve' ou 'reject'
    rejection_reason: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.user_type != 'doctor':
        raise HTTPException(status_code=403, detail='Acesso negado')
    
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail='Caso não encontrado')
    if case.status != 'pending_review':
        raise HTTPException(status_code=400, detail='Caso já revisado ou não pago')
    
    case.doctor_id = current_user.id
    case.updated_at = datetime.utcnow()

    if action == 'approve':
        case.status = 'approved'
        # TODO: Gerar e assinar o documento aqui na Etapa 2
    elif action == 'reject':
        case.status = 'rejected'
        case.rejection_reason = rejection_reason
    else:
        raise HTTPException(status_code=400, detail='Ação inválida')
    
    db.add(case)
    db.commit()
    db.refresh(case)
    
    return RedirectResponse(url='/doctor/dashboard', status_code=303)
