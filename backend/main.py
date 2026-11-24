import io
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = FastAPI(title="NEOTRIBUTO - Calculadora Reforma Tributaria")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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
    aliq = ALIQUOTAS_ANO.get(ano, ALIQUOTAS_ANO[2033])

    tot_cbs = tot_ibs_uf = tot_ibs_mun = tot_is = 0.0
    itens_calc = []
    for item in payload.get("itens", []):
        bc = float(item.get("baseCalculo", 0))
        cst = str(item.get("cst", "000"))
        fator = FATOR_CST.get(cst, 1.0)
        ncm = str(item.get("ncm", ""))

        v_cbs = round(bc * aliq["cbs"] * fator, 2)
        v_ibs_uf = round(bc * aliq["ibs_uf"] * fator, 2)
        v_ibs_mun = round(bc * aliq["ibs_mun"] * fator, 2)
        aliq_is = 0.15 if ncm.startswith(("2203", "2402", "8703")) else 0.0
        v_is = round(bc * aliq_is, 2)

        tot_cbs += v_cbs
        tot_ibs_uf += v_ibs_uf
        tot_ibs_mun += v_ibs_mun
        tot_is += v_is

        itens_calc.append({
            "numero": item.get("numero", 1),
            "ncm": ncm,
            "cst": cst,
            "baseCalculo": bc,
            "CBS": {"aliquota": round(aliq["cbs"] * fator * 100, 4), "valor": v_cbs},
            "IBSUF": {"aliquota": round(aliq["ibs_uf"] * fator * 100, 4), "valor": v_ibs_uf},
            "IBSMun": {"aliquota": round(aliq["ibs_mun"] * fator * 100, 4), "valor": v_ibs_mun},
            "IS": {"aliquota": round(aliq_is * 100, 2), "valor": v_is},
        })

    return JSONResponse({
        "fundamentacao": "Lei Complementar 214/2025 (Reforma Tributaria)",
        "anoApuracao": ano,
        "uf": payload.get("uf", "ES"),
        "municipio": payload.get("municipio", 3205309),
        "total": {
            "vCBS": round(tot_cbs, 2),
            "vIBSUF": round(tot_ibs_uf, 2),
            "vIBSMun": round(tot_ibs_mun, 2),
            "vIS": round(tot_is, 2),
            "vTotalTributos": round(tot_cbs + tot_ibs_uf + tot_ibs_mun + tot_is, 2),
        },
        "itens": itens_calc,
    })

@app.post("/api/calcular/simples-nacional")
async def calc_simples(request: Request):
    payload = await request.json()
    valor = sum(float(i.get("valor", 0)) for i in payload.get("itens", []))
    cbs_sn = round(valor * 0.0185, 2)
    ibs_sn = round(valor * 0.0235, 2)
    return JSONResponse({
        "regime": "Simples Nacional - Recolhimento Unificado DAS (LC 214/2025)",
        "uf": payload.get("uf", "ES"),
        "valorOperacao": valor,
        "parcelaCBS_DAS": cbs_sn,
        "parcelaIBS_DAS": ibs_sn,
        "totalCBS_IBS": round(cbs_sn + ibs_sn, 2),
    })

@app.post("/api/gerar/danfse")
async def gerar_danfse(request: Request):
    xml_bytes = await request.body()
    xml_text = xml_bytes.decode("utf-8", errors="ignore")
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, 790, "DANFSe - Documento Auxiliar da NFS-e (Padrao Nacional)")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, 770, "Gerado via Plataforma NEOTRIBUTO - Reforma Tributaria (LC 214/2025)")
    pdf.line(50, 760, 545, 760)
    y = 735
    for line in xml_text.splitlines()[:35]:
        pdf.drawString(50, y, line.strip()[:95])
        y -= 16
    pdf.save()
    return Response(content=buf.getvalue(), media_type="application/pdf")
