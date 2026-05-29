from flask import Flask, request
import html
import os
import requests
import google.generativeai as genai
from config import GEMINI_API_KEY
from produtos import PRODUTOS

app = Flask(__name__)

SITE_REVITA = "https://revitamais.com.br"
WHATSAPP_REVITA = "https://wa.me/5511950547453"

EVOLUTION_API_URL = os.getenv(
    "EVOLUTION_API_URL",
    "https://evolution-api-production-9927.up.railway.app"
)
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "Revita")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

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
- Não use placeholders como [link], [site] ou [preço].
- Não prometa cura.
- Não faça diagnóstico médico.
- Se perguntarem preço, envie o site oficial.
- Se perguntarem frete ou prazo, peça o CEP.
- Se pedirem site, loja, catálogo, link ou compra, envie sempre: {SITE_REVITA}
- Sempre conduza para o próximo passo: enviar link, pedir CEP ou entender a necessidade.

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

    if "gummies" in texto or "cabelo" in texto or "unha" in texto or "unhas" in texto:
        return PRODUTOS.get("gummies")

    return None

def resposta_fixa(mensagem):
    texto = mensagem.lower()

    if any(p in texto for p in ["site", "loja", "catálogo", "catalogo", "link", "comprar", "compra"]):
        return f"""Olá! 👋

Claro, envio sim. Você pode acessar nossa loja oficial aqui:

{SITE_REVITA}

Lá você encontra todos os produtos, ofertas e novidades da Revita+. 💜

Se quiser, também posso te ajudar a escolher o produto ideal."""

    if any(p in texto for p in ["frete", "entrega", "prazo"]):
        return """Claro! 🚚

Para consultar frete e prazo de entrega, me envie seu CEP, por favor."""

    return None

def gerar_resposta_revita(mensagem):
    fixa = resposta_fixa(mensagem)
    if fixa:
        return fixa

    produto = detectar_produto(mensagem)

    contexto_produto = ""
    if produto:
        contexto_produto = f"""
Produto identificado:
Nome: {produto["nome"]}
Descrição: {produto["descricao"]}
Link: {produto["link"]}
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

        if produto and produto["link"] not in texto:
            texto += f'\n\nConfira aqui: {produto["link"]}'

        return texto

    return "Desculpe, não consegui responder agora. Pode repetir a pergunta? 😊"

def extrair_mensagem_e_numero(data):
    """
    Tenta identificar o número e a mensagem recebida pela Evolution API.
    """
    try:
        dados = data.get("data", {})

        key = dados.get("key", {})
        remote_jid = key.get("remoteJid", "")

        # Ignora mensagens enviadas por você mesmo
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
    """
    Envia resposta pelo WhatsApp usando Evolution API.
    """
    if not EVOLUTION_API_KEY:
        print("ERRO: EVOLUTION_API_KEY não configurada no Render.")
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
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Revita+ IA</title>
        <style>
            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: #f8f4fa;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }

            .chat-container {
                width: 420px;
                background: white;
                border-radius: 22px;
                box-shadow: 0 8px 30px rgba(0,0,0,0.12);
                overflow: hidden;
            }

            .chat-header {
                background: #6f3c8f;
                color: white;
                padding: 22px;
                text-align: center;
            }

            .chat-header h2 {
                margin: 0;
                font-size: 24px;
            }

            .chat-header p {
                margin: 8px 0 0;
                font-size: 14px;
            }

            .chat-body {
                padding: 24px;
            }

            input {
                width: 100%;
                padding: 14px;
                border-radius: 12px;
                border: 1px solid #ddd;
                font-size: 15px;
                box-sizing: border-box;
            }

            button {
                width: 100%;
                margin-top: 12px;
                padding: 14px;
                border: none;
                border-radius: 12px;
                background: #6f3c8f;
                color: white;
                font-size: 16px;
                cursor: pointer;
            }

            button:hover {
                background: #5d3278;
            }

            .quick-buttons {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 8px;
                margin-top: 16px;
            }

            .quick-buttons a {
                text-decoration: none;
                background: #f1e8f6;
                color: #6f3c8f;
                padding: 10px;
                border-radius: 10px;
                font-size: 13px;
                text-align: center;
            }

            .footer {
                text-align: center;
                font-size: 12px;
                color: #777;
                padding: 0 24px 20px;
            }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="chat-header">
                <h2>Revita+ IA 💜</h2>
                <p>Assistente virtual de suplementos</p>
            </div>

            <div class="chat-body">
                <form action="/perguntar" method="post">
                    <input 
                        name="mensagem" 
                        placeholder="Digite sua dúvida..."
                        required
                    >
                    <button type="submit">Enviar mensagem</button>
                </form>

                <div class="quick-buttons">
                    <a href="/rapida?msg=Quero saber sobre colágeno">Colágeno</a>
                    <a href="/rapida?msg=Quero saber sobre ômega 3">Ômega 3</a>
                    <a href="/rapida?msg=Quero saber sobre multivitamínico">Multivitamínico</a>
                    <a href="/rapida?msg=Quero saber sobre gummies">Gummies</a>
                </div>
            </div>

            <div class="footer">
                Atendimento automático Revita+
            </div>
        </div>
    </body>
    </html>
    """

@app.route("/rapida", methods=["GET"])
def rapida():
    mensagem = request.args.get("msg", "")
    return mostrar_resposta(mensagem)

@app.route("/perguntar", methods=["POST"])
def perguntar():
    mensagem = request.form.get("mensagem", "").strip()
    return mostrar_resposta(mensagem)

def mostrar_resposta(mensagem):
    try:
        if not mensagem:
            return """
            <h2>Erro</h2>
            <p>Digite uma mensagem antes de enviar.</p>
            <br>
            <a href="/">Voltar</a>
            """

        texto_resposta = gerar_resposta_revita(mensagem)

        mensagem_segura = html.escape(mensagem)
        resposta_segura = html.escape(texto_resposta)

        return f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <title>Resposta Revita+</title>
            <style>
                body {{
                    margin: 0;
                    font-family: Arial, sans-serif;
                    background: #f8f4fa;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }}

                .chat {{
                    width: 460px;
                    background: white;
                    border-radius: 22px;
                    box-shadow: 0 8px 30px rgba(0,0,0,0.12);
                    padding: 24px;
                }}

                .cliente {{
                    background: #e9e9e9;
                    padding: 14px;
                    border-radius: 14px;
                    margin-bottom: 16px;
                }}

                .bot {{
                    background: #f1e8f6;
                    padding: 14px;
                    border-radius: 14px;
                    white-space: pre-line;
                }}

                a.botao {{
                    display: block;
                    text-align: center;
                    margin-top: 16px;
                    background: #6f3c8f;
                    color: white;
                    padding: 14px;
                    border-radius: 12px;
                    text-decoration: none;
                }}

                a.botao.whats {{
                    background: #25D366;
                }}

                a.voltar {{
                    display: block;
                    text-align: center;
                    margin-top: 12px;
                    color: #6f3c8f;
                    text-decoration: none;
                }}
            </style>
        </head>
        <body>
            <div class="chat">
                <h2>Revita+ IA 💜</h2>

                <div class="cliente">
                    <strong>Cliente:</strong><br>
                    {mensagem_segura}
                </div>

                <div class="bot">
                    <strong>Revita+:</strong><br>
                    {resposta_segura}
                </div>

                <a class="botao" href="{SITE_REVITA}" target="_blank">
                    Comprar agora
                </a>

                <a class="botao whats" href="{WHATSAPP_REVITA}" target="_blank">
                    Falar com especialista
                </a>

                <a class="voltar" href="/">
                    Voltar
                </a>
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
    app.run(port=5000, debug=True)
