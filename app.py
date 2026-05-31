from flask import Flask, request
import html
import os
import requests
import google.generativeai as genai
from produtos import PRODUTOS
from datetime import datetime, timedelta

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

TEMPO_PAUSA_MINUTOS = 10
CLIENTES_EM_PAUSA = {}

COMANDOS_MENU = [
    "oi", "olá", "ola", "bom dia", "boa tarde", "boa noite",
    "menu", "menu inicial", "voltar menu", "voltar ao menu",
    "começar", "comecar", "iniciar", "reiniciar"
]

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
- Respostas curtas, naturais e com cara de WhatsApp.
- Use emojis com moderação.
- Primeiro ajude o cliente. Não force venda em toda resposta.

Regras importantes:
- Não invente preços.
- Não invente promoções.
- Não invente links.
- Não use placeholders.
- Não prometa cura.
- Não faça diagnóstico médico.
- Não diga que produto trata doença.
- Se perguntarem preço, link, catálogo, loja ou compra, envie o site oficial.
- Se perguntarem frete ou prazo, peça o CEP.
- Se a dúvida for sobre produto, explique de forma simples e pergunte o objetivo do cliente.
- Só envie o site se o cliente pedir compra, preço, link, catálogo ou loja.
- Se o cliente pedir atendente, pessoa, humano ou consultora, responda que em breve uma consultora irá atender.

Produtos Revita+:
- Colágeno Verisol + Ácido Hialurônico: firmeza, elasticidade, hidratação e beleza da pele.
- Ômega 3: bem-estar geral e suporte nutricional.
- Gummies Cabelo, Pele e Unhas: cuidado prático diário com beleza.
- Revita Hair: cuidado capilar, fortalecimento dos fios e rotina para cabelos.
- Multivitamínico: vitaminas e minerais para o dia a dia.
- Multivitamínico Mulher: suporte nutricional para rotina feminina.
- Multivitamínico Homem: suporte nutricional para rotina masculina.
- Complexo B Gummies: vitaminas do complexo B para rotina, energia e disposição.
- Kids Gummies: suplemento infantil em formato gummy.
"""


def normalizar_texto(texto):
    return (texto or "").lower().strip()


def pediu_menu(mensagem):
    return normalizar_texto(mensagem) in COMANDOS_MENU


def pausar_cliente(telefone):
    if telefone:
        CLIENTES_EM_PAUSA[telefone] = datetime.now() + timedelta(minutes=TEMPO_PAUSA_MINUTOS)
        print(f"Cliente {telefone} pausado até {CLIENTES_EM_PAUSA[telefone]}")


def remover_pausa_cliente(telefone):
    if telefone in CLIENTES_EM_PAUSA:
        CLIENTES_EM_PAUSA.pop(telefone, None)
        print(f"Pausa removida para o cliente {telefone}")


def cliente_esta_em_pausa(telefone):
    if not telefone:
        return False

    pausa_ate = CLIENTES_EM_PAUSA.get(telefone)

    if not pausa_ate:
        return False

    if datetime.now() < pausa_ate:
        print(f"Cliente {telefone} ainda está em pausa até {pausa_ate}")
        return True

    CLIENTES_EM_PAUSA.pop(telefone, None)
    print(f"Pausa do cliente {telefone} finalizada.")
    return False


def cliente_pediu_atendente(mensagem):
    texto = normalizar_texto(mensagem)

    if texto in ["7", "opção 7", "opcao 7"]:
        return True

    palavras = [
        "atendente",
        "humano",
        "pessoa",
        "consultora",
        "consultor",
        "falar com alguém",
        "falar com alguem",
        "quero atendimento",
        "me chama",
        "me liga",
        "vendedora",
        "vendedor"
    ]

    return any(p in texto for p in palavras)


def menu_principal():
    return """Olá! 👋 Sou a assistente virtual da Revita+.

Como posso te ajudar hoje?

1️⃣ Cabelo, pele e unhas
2️⃣ Colágeno
3️⃣ Ômega 3
4️⃣ Multivitamínicos
5️⃣ Gummies infantil
6️⃣ Ver catálogo / comprar
7️⃣ Falar com atendente

É só responder com o número da opção. 💚"""


def resposta_menu(mensagem):
    texto = normalizar_texto(mensagem)

    if texto in COMANDOS_MENU:
        return menu_principal()

    if texto in ["1", "opção 1", "opcao 1"]:
        return """Temos opções para cabelo, pele e unhas. 💚

✨ Revita Hair: indicado para quem busca cuidado com os fios e rotina capilar.
✨ Gummies Cabelo, Pele e Unhas: opção prática em gummy para rotina de beleza.

Você procura algo mais para cabelo, pele ou unhas?"""

    if texto in ["2", "opção 2", "opcao 2"]:
        return """Temos o Colágeno Verisol + Ácido Hialurônico Revita+. 💚

Ele é uma opção para quem busca cuidado com a pele, firmeza, elasticidade e hidratação.

Você quer usar mais para firmeza da pele, hidratação ou prevenção?"""

    if texto in ["3", "opção 3", "opcao 3"]:
        return """Temos o Ômega 3 Revita+. 💚

Ele é muito procurado para complementar a rotina de bem-estar e suporte nutricional diário.

Você já usa ômega 3 ou está começando agora?"""

    if texto in ["4", "opção 4", "opcao 4"]:
        return """Temos opções de multivitamínicos Revita+. 💚

✨ Multivitamínico tradicional
✨ Multivitamínico Mulher
✨ Multivitamínico Homem
✨ Complexo B Gummies

Você procura para mulher, homem, disposição ou rotina geral?"""

    if texto in ["5", "opção 5", "opcao 5"]:
        return """Temos o Kids Gummies Revita+. 💚

É uma opção infantil em formato gummy para complementar a rotina das crianças.

Qual a idade da criança?"""

    if texto in ["6", "opção 6", "opcao 6"]:
        return f"""Claro! Você pode ver todos os produtos na loja oficial da Revita+:

{SITE_REVITA}

Se quiser, também posso te ajudar a escolher o produto ideal."""

    if texto in ["7", "opção 7", "opcao 7"]:
        return """Claro! Em breve uma consultora da Revita+ irá te atender. 💚"""

    return None


def detectar_produto(mensagem):
    texto = normalizar_texto(mensagem)

    if any(p in texto for p in [
        "colageno", "colágeno", "verisol", "acido hialuronico",
        "ácido hialurônico", "hialuronico", "hialurônico", "pele",
        "firmeza", "elasticidade", "hidratação", "hidratacao"
    ]):
        return PRODUTOS.get("colageno")

    if any(p in texto for p in [
        "omega", "ômega", "omega 3", "ômega 3", "oleo de peixe",
        "óleo de peixe"
    ]):
        return PRODUTOS.get("omega")

    if any(p in texto for p in [
        "revita hair", "hair", "queda", "cabelo fraco",
        "crescimento capilar", "fortalecer cabelo", "fio", "fios"
    ]):
        return PRODUTOS.get("revita_hair")

    if any(p in texto for p in [
        "gummies cabelo", "cabelo pele unhas", "cabelo pele e unhas",
        "unhas", "unha", "gummy beleza", "gummies beleza"
    ]):
        return PRODUTOS.get("gummies")

    if any(p in texto for p in [
        "mulher", "feminino", "multivitaminico mulher",
        "multivitamínico mulher", "vitamina mulher"
    ]):
        return PRODUTOS.get("multivitaminico_mulher")

    if any(p in texto for p in [
        "homem", "masculino", "multivitaminico homem",
        "multivitamínico homem", "vitamina homem"
    ]):
        return PRODUTOS.get("multivitaminico_homem")

    if any(p in texto for p in [
        "complexo b", "vitamina b", "b12", "b6", "energia",
        "disposição", "disposicao", "cansaço", "cansaco"
    ]):
        return PRODUTOS.get("complexo_b")

    if any(p in texto for p in [
        "kids", "criança", "crianca", "infantil", "gummy infantil",
        "gummies infantil", "vitamina infantil", "crianças", "criancas"
    ]):
        return PRODUTOS.get("kids")

    if any(p in texto for p in [
        "multi", "vitamina", "vitaminas", "multivitaminico",
        "multivitamínico", "minerais"
    ]):
        return PRODUTOS.get("multivitaminico")

    return None


def resposta_fixa(mensagem):
    texto = normalizar_texto(mensagem)

    menu = resposta_menu(mensagem)
    if menu:
        return menu

    if any(p in texto for p in ["site", "loja", "catálogo", "catalogo", "link", "comprar", "compra", "quero comprar", "pedido"]):
        return f"""Claro! 👋

Você pode acessar nossa loja oficial aqui:

{SITE_REVITA}

Lá você encontra os produtos disponíveis da Revita+. 💚

Se quiser, me diga o que você procura que eu te ajudo a escolher."""

    if any(p in texto for p in ["frete", "entrega", "prazo"]):
        return """Claro! 🚚

Para consultar frete e prazo de entrega, me envie seu CEP, por favor."""

    if any(p in texto for p in ["preço", "preco", "valor", "quanto custa", "quanto é", "quanto e"]):
        return f"""Os valores podem variar conforme ofertas e disponibilidade. 💚

Você pode consultar os preços atualizados na loja oficial:

{SITE_REVITA}

Se quiser, me diga qual produto você quer que eu te ajudo."""

    if cliente_pediu_atendente(mensagem):
        return """Claro! Em breve uma consultora da Revita+ irá te atender. 💚"""

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
Link oficial, somente se o cliente pedir compra/preço/link: {produto.get("link", SITE_REVITA)}
"""

    prompt_completo = f"""
{PROMPT_REVITA}

{contexto_produto}

Cliente: {mensagem}

Responda primeiro a dúvida do cliente.
Não envie link de compra, site ou catálogo, a menos que o cliente tenha pedido preço, compra, link, catálogo ou loja.
Finalize com uma pergunta simples para continuar o atendimento.

Atendente Revita+:
"""

    resposta = model.generate_content(prompt_completo)

    if resposta and resposta.text:
        return resposta.text.strip()

    return "Desculpe, não consegui responder agora. Pode repetir a pergunta? 😊"


def extrair_mensagem_e_numero(data):
    try:
        if data.get("event") != "messages.upsert":
            return None, None

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
            <h2 style="text-align:center; color:#6f3c8f;">Revita+ IA 💚</h2>
            <p style="text-align:center;">Assistente virtual de suplementos</p>

            <form action="/perguntar" method="post">
                <input name="mensagem" placeholder="Digite sua dúvida..." required style="width:100%; padding:14px; border-radius:12px; border:1px solid #ddd; box-sizing:border-box;">
                <button type="submit" style="width:100%; margin-top:12px; padding:14px; border:none; border-radius:12px; background:#6f3c8f; color:white; font-size:16px;">
                    Enviar mensagem
                </button>
            </form>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:15px;">
                <a href="/rapida?msg=menu" style="text-align:center; background:#f1e8f6; padding:10px; border-radius:10px; color:#6f3c8f; text-decoration:none;">Menu</a>
                <a href="/rapida?msg=Quero saber sobre colágeno" style="text-align:center; background:#f1e8f6; padding:10px; border-radius:10px; color:#6f3c8f; text-decoration:none;">Colágeno</a>
                <a href="/rapida?msg=Quero saber sobre ômega 3" style="text-align:center; background:#f1e8f6; padding:10px; border-radius:10px; color:#6f3c8f; text-decoration:none;">Ômega 3</a>
                <a href="/rapida?msg=Quero algo para cabelo" style="text-align:center; background:#f1e8f6; padding:10px; border-radius:10px; color:#6f3c8f; text-decoration:none;">Cabelo</a>
            </div>

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
                <h2>Revita+ IA 💚</h2>
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

    if pediu_menu(mensagem):
        remover_pausa_cliente(telefone)
        resposta = menu_principal()
        enviado = enviar_whatsapp(telefone, resposta)

        return {
            "status": "ok",
            "telefone": telefone,
            "mensagem": mensagem,
            "resposta": resposta,
            "enviado": enviado,
            "motivo": "menu solicitado"
        }, 200

    if cliente_esta_em_pausa(telefone):
        return {
            "status": "pausado",
            "telefone": telefone,
            "motivo": "cliente aguardando consultora"
        }, 200

    resposta = gerar_resposta_revita(mensagem)

    if cliente_pediu_atendente(mensagem):
        pausar_cliente(telefone)

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
