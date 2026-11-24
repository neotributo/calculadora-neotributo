import io
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

app = FastAPI(title="NEOTRIBUTO - Calculadora Reforma Tributaria")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CACHE_MUNICIPIOS = {}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/municipios/{uf}")
async def listar_municipios(uf: str):
    sigla = uf.strip().upper()[:2]
    if sigla in CACHE_MUNICIPIOS:
        return JSONResponse(CACHE_MUNICIPIOS[sigla])
        url = f"https://ibge.gov.br{sigla}/municipios?orderBy=nome"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        dados = json.loads(resp.read().decode("utf-8"))
    lista = [{"id": m["id"], "nome": m["nome"]} for m in dados]
    CACHE_MUNICIPIOS[sigla] = lista
    return JSONResponse(lista)

ALIQUOTAS_ANO = {
    2026: {"cbs": 0.009, "ibs_uf": 0.001, "ibs_mun": 0.000},
    2027: {"cbs": 0.088, "ibs_uf": 0.0005, "ibs_mun": 0.0005},
    2028: {"cbs": 0.088, "ibs_uf": 0.0005, "ibs_mun": 0.0005},
    2029: {"cbs": 0.088, "ibs_uf": 0.011, "ibs_mun": 0.0067},
    2030: {"cbs": 0.088, "ibs_uf": 0.022, "ibs_mun": 0.0134},
    2031: {"cbs": 0.088, "ibs_uf": 0.033, "ibs_mun": 0.0201},
    2032: {"cbs": 0.088, "ibs_uf": 0.044, "ibs_mun": 0.0268},
    2033: {"cbs": 0.088, "ibs_uf": 0.110, "ibs_mun": 0.0670},
}

FATOR_CST = {"000": 1.0, "200": 0.4, "210": 0.7, "400": 0.0, "410": 0.0}

# Partilha estimada LC 214/2025 no Simples Nacional (CBS substitui PIS/COFINS; IBS substitui ICMS/ISS)
SIMPLES_TABELA = {
    "I":   {"faixa1": (0.0062, 0.0136), "faixa2": (0.0115, 0.0248), "faixa3": (0.0148, 0.0318), "faixa4": (0.0172, 0.0370), "faixa5": (0.0205, 0.0442)},
    "II":  {"faixa1": (0.0068, 0.0144), "faixa2": (0.0122, 0.0256), "faixa3": (0.0155, 0.0326), "faixa4": (0.0180, 0.0380), "faixa5": (0.0215, 0.0454)},
    "III": {"faixa1": (0.0096, 0.0201), "faixa2": (0.0168, 0.0358), "faixa3": (0.0212, 0.0452), "faixa4": (0.0248, 0.0528), "faixa5": (0.0295, 0.0630)},
    "IV":  {"faixa1": (0.0085, 0.0200), "faixa2": (0.0150, 0.0360), "faixa3": (0.0192, 0.0450), "faixa4": (0.0225, 0.0525), "faixa5": (0.0270, 0.0620)},
    "V":   {"faixa1": (0.0240, 0.0217), "faixa2": (0.0285, 0.0340), "faixa3": (0.0325, 0.0435), "faixa4": (0.0360, 0.0510), "faixa5": (0.0410, 0.0615)},
}

@app.get("/health")
async def health():
    return {"status": "ok"}

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
    payload = await request.json()
    data_str = str(payload.get("dataHoraEmissao", "2027-01-15"))
    ano = int(data_str[:4]) if data_str[:4].isdigit() else 2027
    if ano < 2026:
        aliq = ALIQUOTAS_ANO
    elif ano > 2033:
        aliq = ALIQUOTAS_ANO
    else:
        aliq = ALIQUOTAS_ANO[ano]

    tot_cbs = tot_ibs_uf = tot_ibs_mun = tot_is = 0.0
    for item in payload.get("itens", []):
        bc = float(item.get("baseCalculo", 0))
        cst = str(item.get("cst", "000"))
        fator = FATOR_CST.get(cst, 1.0)
        ncm = str(item.get("ncm", ""))

        tot_cbs += round(bc * aliq["cbs"] * fator, 2)
        tot_ibs_uf += round(bc * aliq["ibs_uf"] * fator, 2)
        tot_ibs_mun += round(bc * aliq["ibs_mun"] * fator, 2)
        aliq_is = 0.15 if ncm.startswith(("2203", "2402", "8703")) else 0.0
        tot_is += round(bc * aliq_is, 2)

    return JSONResponse({
        "total": {
            "vCBS": round(tot_cbs, 2),
            "vIBSUF": round(tot_ibs_uf, 2),
            "vIBSMun": round(tot_ibs_mun, 2),
            "vIS": round(tot_is, 2),
        }
    })

@app.post("/api/calcular/simples-nacional")
async def calc_simples(request: Request):
    payload = await request.json()
    valor = sum(float(i.get("valor", 0)) for i in payload.get("itens", []))
    anexo = str(payload.get("anexo", "III"))
    faixa = str(payload.get("faixa", "faixa2"))
    aliq_cbs, aliq_ibs = SIMPLES_TABELA.get(anexo, SIMPLES_TABELA["III"]).get(faixa, (0.0168, 0.0358))

    cbs_sn = round(valor * aliq_cbs, 2)
    ibs_sn = round(valor * aliq_ibs, 2)
    return JSONResponse({
        "parcelaCBS_DAS": cbs_sn,
        "parcelaIBS_DAS": ibs_sn,
        "totalCBS_IBS": round(cbs_sn + ibs_sn, 2),
        "aliquotaEfetivaTotal": round((aliq_cbs + aliq_ibs) * 100, 2),
    })

def _extrair_tag(root, nomes):
    for elem in root.iter():
        tag_limpa = elem.tag.split("}")[-1]
        if tag_limpa in nomes and elem.text and elem.text.strip():
            return elem.text.strip()
    return ""

@app.post("/api/gerar/danfse")
async def gerar_danfse(request: Request):
    content_type = request.headers.get("content-type", "")
    dados = {
        "numero": "000001",
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "prestador_nome": "EMPRESA PRESTADORA LTDA",
        "prestador_doc": "00.000.000/0001-00",
        "tomador_nome": "CLIENTE TOMADOR LTDA",
        "tomador_doc": "00.000.000/0001-91",
        "municipio": "Vitoria - ES (3205309)",
        "descricao": "Prestacao de servicos especializados",
        "valor": 0.0,
    }

    if "application/json" in content_type:
        body = await request.json()
        dados["prestador_nome"] = body.get("prestador_nome") or dados["prestador_nome"]
        dados["prestador_doc"] = body.get("prestador_doc") or dados["prestador_doc"]
        dados["tomador_nome"] = body.get("tomador_nome") or dados["tomador_nome"]
        dados["tomador_doc"] = body.get("tomador_doc") or dados["tomador_doc"]
        dados["municipio"] = body.get("municipio") or dados["municipio"]
        dados["descricao"] = body.get("descricao") or dados["descricao"]
        dados["valor"] = float(body.get("valor") or 0)
    else:
        xml_bytes = await request.body()
        xml_text = xml_bytes.decode("utf-8", errors="ignore")
        try:
            root = ET.fromstring(xml_text)
            dados["numero"] = _extrair_tag(root, ["nNFSe", "nDPS", "Numero"]) or dados["numero"]
            dados["prestador_nome"] = _extrair_tag(root, ["xNome", "RazaoSocial"]) or dados["prestador_nome"]
            dados["prestador_doc"] = _extrair_tag(root, ["CNPJ", "CPF"]) or dados["prestador_doc"]
            dados["descricao"] = _extrair_tag(root, ["xDescServ", "Discriminacao"]) or dados["descricao"]
            v_str = _extrair_tag(root, ["vServ", "ValorServicos", "vLiq"])
            if v_str:
                dados["valor"] = float(v_str.replace(",", "."))
        except Exception:
            dados["descricao"] = xml_text[:120]

    v_cbs = round(dados["valor"] * 0.088, 2)
    v_ibs = round(dados["valor"] * 0.001, 2)

    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)

    # Cabecalho institucional
    pdf.setFillColor(colors.HexColor("#0A192F"))
    pdf.rect(40, 755, 515, 55, fill=1, stroke=0)
    pdf.setFillColor(colors.HexColor("#2DD4BF"))
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(55, 788, "DANFSe — Documento Auxiliar da NFS-e (Padrao Nacional)")
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(55, 770, f"Emissao: {dados['data']}   |   Numero NFS-e: {dados['numero']}   |   Plataforma NEOTRIBUTO (LC 214/2025)")

    # Quadro Prestador e Tomador
    pdf.setStrokeColor(colors.HexColor("#CBD5E1"))
    pdf.rect(40, 655, 515, 85, fill=0, stroke=1)
    pdf.setFillColor(colors.HexColor("#0A192F"))
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(52, 722, "PRESTADOR DE SERVICOS")
    pdf.setFont("Helvetica", 9.5)
    pdf.drawString(52, 706, f"Razao Social: {dados['prestador_nome'][:65]}")
    pdf.drawString(52, 691, f"CNPJ/CPF: {dados['prestador_doc']}   |   Municipio: {dados['municipio']}")

    pdf.line(40, 680, 555, 680)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(52, 665, f"TOMADOR: {dados['tomador_nome'][:45]}   |   CNPJ/CPF: {dados['tomador_doc']}")

    # Quadro Discriminacao do Servico
    pdf.rect(40, 540, 515, 100, fill=0, stroke=1)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(52, 622, "DISCRIMINACAO DOS SERVICOS")
    pdf.setFont("Helvetica", 9.5)
    pdf.drawString(52, 602, dados["descricao"][:90])
    if len(dados["descricao"]) > 90:
        pdf.drawString(52, 586, dados["descricao"][90:180])

    # Quadro Tributacao Reforma Tributaria (CBS / IBS)
    pdf.setFillColor(colors.HexColor("#F1F5F9"))
    pdf.rect(40, 445, 515, 80, fill=1, stroke=1)
    pdf.setFillColor(colors.HexColor("#0A192F"))
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(52, 507, "DEMONSTRATIVO TRIBUTARIO — REFORMA TRIBUTARIA (LC 214/2025)")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(52, 485, f"Valor Total do Servico: R$ {dados['valor']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    pdf.drawString(52, 465, f"CBS Federal (8,80%): R$ {v_cbs:,.2f}   |   IBS Estadual/Municipal (0,10%): R$ {v_ibs:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    pdf.setFont("Helvetica-Oblique", 8.5)
    pdf.setFillColor(colors.HexColor("#475569"))
    pdf.drawString(40, 420, "Documento auxiliar gerado eletronicamente pela Calculadora NEOTRIBUTO (neotributo.com.br).")
    pdf.save()
    return Response(content=buf.getvalue(), media_type="application/pdf")
