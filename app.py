from flask import Flask, request
import html
import os
import requests
import google.generativeai as genai
from produtos import PRODUTOS

app = Flask(__name__)

SITE_REVITA = "https://revitamais.com.br"
WHATSAPP_REVITA = "https://wa.me/5511950547453"

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

EVOLUTION_API_URL = os.getenv(
    "EVOLUTION_API_URL",
    "https://evolution-api-production-9927.up.railway.app"
)

EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "Revita")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
else:
    model = None

PROMPT_REVITA = f"""
Você é a atendente virtual da Revita+, uma loja de suplementos.

Informações oficiais:
Site oficial: {SITE_REVITA}
WhatsApp oficial: {WHATSAPP_REVITA}

Tom de voz:
- Português do Brasil.
- Simpática, objetiva, acolhedora e vendedora.
- Respostas curtas, como conversa de WhatsApp.
- Use emojis com moderação.

Regras:
- Não invente preços.
- Não invente promoções.
- Não invente links.
- Não use placeholders.
- Não prometa cura.
- Não faça diagnóstico médico.
- Se perguntarem preço, envie o site oficial.
- Se perguntarem frete ou prazo, peça o CEP.
- Se pedirem site, loja, catálogo, link ou compra, envie sempre: {SITE_REVITA}
- Sempre conduza para o próximo passo.

Produtos:
- Colágeno Verisol + Ácido Hialurônico: firmeza, elasticidade, hidratação e beleza da pele.
- Ômega 3: bem-estar geral e suporte nutricional.
- Multivitamínico: vitaminas e minerais para o dia a dia.
- Gummies Cabelo, Pele e Unhas: cuidado prático diário com beleza.
"""

def detectar_produto(mensagem):
    texto = mensagem.lower()

    if "colageno" in texto or "colágeno" in texto or "pele" in texto or "firmeza" in texto:
        return PRODUTOS.get("colageno")

    if "omega" in texto or "ômega" in texto or "omega 3" in texto or "ômega 3" in texto:
        return PRODUTOS.get("omega")

    if "multi" in texto or "vitamina" in texto or "multivitaminico" in texto or "multivitamínico" in texto:
        return PRODUTOS.get("multivitaminico")

    if "gummies" in texto or "cabelo" in texto or "unha" in texto or "unhas":
        return PRODUTOS.get("gummies")

    return None

def resposta_fixa(mensagem):
    texto = mensagem.lower()

    if any(p in texto for p in ["site", "loja", "catálogo", "catalogo", "link", "comprar", "compra"]):
        return f"""Olá! 👋

Claro, envio sim. Você pode acessar nossa loja oficial aqui:

{SITE_REVITA}

Lá você encontra todos os produtos, ofertas e novidades da Revita+. 💜"""

    if any(p in texto for p in ["frete", "entrega", "prazo"]):
        return """Claro! 🚚

Para consultar frete e prazo de entrega, me envie seu CEP, por favor."""

    return None

def gerar_resposta_revita(mensagem):
    if not model:
        return "A IA ainda não está configurada. Verifique a variável GOOGLE_API_KEY no Render."

    fixa = resposta_fixa(mensagem)
    if fixa:
        return fixa

    produto = detectar_produto(mensagem)

    contexto_produto = ""
    if produto:
        contexto_produto = f"""
Produto identificado:
Nome: {produto.get("nome", "")}
Descrição: {produto.get("descricao", "")}
Link: {produto.get("link", SITE_REVITA)}
"""

    prompt_completo = f"""
{PROMPT_REVITA}

{contexto_produto}

Cliente: {mensagem}

Atendente Revita+:
"""

    resposta = model.generate_content(prompt_completo)

    if resposta and resposta.text:
        texto = resposta.text.strip()

        if produto:
            link = produto.get("link")
            if link and link not in texto:
                texto += f"\n\nConfira aqui: {link}"

        return texto

    return "Desculpe, não consegui responder agora. Pode repetir a pergunta? 😊"

def extrair_mensagem_e_numero(data):
    try:
        dados = data.get("data", {})
        key = dados.get("key", {})
        remote_jid = key.get("remoteJid", "")

        if key.get("fromMe") is True:
            return None, None

        telefone = remote_jid.replace("@s.whatsapp.net", "").replace("@c.us", "")

        message = dados.get("message", {})

        texto = (
            message.get("conversation")
            or message.get("extendedTextMessage", {}).get("text")
            or message.get("imageMessage", {}).get("caption")
            or message.get("videoMessage", {}).get("caption")
        )

        return telefone, texto

    except Exception as e:
        print("Erro ao extrair mensagem:", str(e))
        return None, None

def enviar_whatsapp(numero, texto):
    if not EVOLUTION_API_KEY:
        print("ERRO: EVOLUTION_API_KEY não configurada.")
        return False

    url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"

    payload = {
        "number": numero,
        "text": texto
    }

    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print("Status envio WhatsApp:", response.status_code)
        print("Resposta Evolution:", response.text)
        return response.status_code in [200, 201]
    except Exception as e:
        print("Erro ao enviar WhatsApp:", str(e))
        return False

@app.route("/")
def home():
    return """
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Revita+ IA</title>
    </head>
    <body style="font-family: Arial; background:#f8f4fa; display:flex; justify-content:center; align-items:center; min-height:100vh;">
        <div style="background:white; padding:30px; border-radius:20px; width:420px; box-shadow:0 8px 30px rgba(0,0,0,0.12);">
            <h2 style="text-align:center; color:#6f3c8f;">Revita+ IA 💜</h2>
            <p style="text-align:center;">Assistente virtual de suplementos</p>

            <form action="/perguntar" method="post">
                <input name="mensagem" placeholder="Digite sua dúvida..." required style="width:100%; padding:14px; border-radius:12px; border:1px solid #ddd; box-sizing:border-box;">
                <button type="submit" style="width:100%; margin-top:12px; padding:14px; border:none; border-radius:12px; background:#6f3c8f; color:white; font-size:16px;">
                    Enviar mensagem
                </button>
            </form>

            <p style="text-align:center; font-size:12px; color:#777; margin-top:20px;">
                Atendimento automático Revita+
            </p>
        </div>
    </body>
    </html>
    """

@app.route("/perguntar", methods=["POST"])
def perguntar():
    mensagem = request.form.get("mensagem", "").strip()
    return mostrar_resposta(mensagem)

@app.route("/rapida", methods=["GET"])
def rapida():
    mensagem = request.args.get("msg", "")
    return mostrar_resposta(mensagem)

def mostrar_resposta(mensagem):
    try:
        if not mensagem:
            return '<h2>Erro</h2><p>Digite uma mensagem.</p><a href="/">Voltar</a>'

        texto_resposta = gerar_resposta_revita(mensagem)

        return f"""
        <html lang="pt-BR">
        <head><meta charset="UTF-8"><title>Resposta Revita+</title></head>
        <body style="font-family:Arial; background:#f8f4fa; padding:40px;">
            <div style="background:white; padding:25px; border-radius:20px; max-width:500px; margin:auto;">
                <h2>Revita+ IA 💜</h2>
                <p><strong>Cliente:</strong><br>{html.escape(mensagem)}</p>
                <p style="background:#f1e8f6; padding:15px; border-radius:12px; white-space:pre-line;">
                    <strong>Revita+:</strong><br>{html.escape(texto_resposta)}
                </p>
                <a href="/" style="display:block; text-align:center; margin-top:15px;">Voltar</a>
            </div>
        </body>
        </html>
        """

    except Exception as e:
        return f"""
        <h2>Erro na IA</h2>
        <p>{html.escape(str(e))}</p>
        <br>
        <a href="/">Voltar</a>
        """

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    print("=" * 60)
    print("WEBHOOK RECEBIDO:")
    print(data)
    print("=" * 60)

    telefone, mensagem = extrair_mensagem_e_numero(data)

    if not telefone or not mensagem:
        return {"status": "ignorado", "motivo": "sem mensagem válida"}, 200

    resposta = gerar_resposta_revita(mensagem)
    enviado = enviar_whatsapp(telefone, resposta)

    return {
        "status": "ok",
        "telefone": telefone,
        "mensagem": mensagem,
        "resposta": resposta,
        "enviado": enviado
    }, 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
