import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="NEOTRIBUTO - Motor Oficial Receita Federal")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/logo-neotributo.png")
async def serve_logo():
    with open("frontend/logo-neotributo.png", "rb") as f:
        return Response(content=f.read(), media_type="image/png")

@app.post("/api/calcular/regime-geral")
async def calc_regular(request: Request):
    body = await request.body()
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post("http://127.0.0", content=body, headers={"Content-Type": "application/json"})
        return Response(content=r.content, status_code=r.status_code, media_type="application/json")

@app.post("/api/calcular/simples-nacional")
async def calc_simples(request: Request):
    body = await request.body()
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post("http://127.0.0", content=body, headers={"Content-Type": "application/json"})
        return Response(content=r.content, status_code=r.status_code, media_type="application/json")

@app.post("/api/gerar/danfse")
async def gerar_danfse(request: Request):
    xml_body = await request.body()
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post("http://127.0.0", content=xml_body, headers={"Content-Type": "application/xml"})
        return Response(content=r.content, status_code=r.status_code, media_type="application/pdf")
