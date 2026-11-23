import os, httpx
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title='NEOTRIBUTO - Calculadora Reforma Tributaria')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

URL_REGULAR = 'http://127.0.0'
URL_SIMPLES = 'http://127.0.0'
URL_DANFSE = 'http://127.0.0'

@app.get('/', response_class=HTMLResponse)
async def serve_frontend():
    with open('frontend/index.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.get('/logo-neotributo.png')
async def serve_logo():
    return FileResponse('frontend/logo-neotributo.png')

@app.get('/health')
async def health():
    return {'status': 'online'}

@app.post('/api/calcular/regime-geral')
async def calc_regular(request: Request):
    payload = await request.json()
    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            r = await client.post(f'{URL_REGULAR}/observabilidade/regime-geral', json=payload)
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception as e:
            raise HTTPException(status_code=502, detail=f'Motor iniciando, tente em 15s: {str(e)}')

@app.post('/api/calcular/simples-nacional')
async def calc_simples(request: Request):
    payload = await request.json()
    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            r = await client.post(f'{URL_SIMPLES}/calculadora/observabilidade/simples-nacional', json=payload)
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception as e:
            raise HTTPException(status_code=502, detail=f'Motor iniciando, tente em 15s: {str(e)}')

@app.post('/api/gerar/danfse')
async def gerar_danfse(request: Request):
    xml_body = await request.body()
    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            r = await client.post(URL_DANFSE, content=xml_body, headers={'Content-Type': 'application/xml'})
            if r.status_code != 200:
                return JSONResponse(status_code=r.status_code, content={'erro': r.text})
            return Response(content=r.content, media_type='application/pdf')
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))
