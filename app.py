from flask import Flask, request
import html
import os
import requests
import google.generativeai as genai
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import threading

app = Flask(__name__)

SITE_REVITA = "https://revitamais.com.br"
WHATSAPP_REVITA = "https://wa.me/5511950547453"

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "https://evolution-api-production-9927.up.railway.app")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "Revita")
PROMOCAO_BANNER_URL = os.getenv(
    "PROMOCAO_BANNER_URL",
    "https://res.cloudinary.com/yev40xqt/image/upload/v1782933996/WhatsApp_Image_2026-07-01_at_16.18.29_bknd0t.jpg"
)

TEMPO_PAUSA_MINUTOS = 10
TEMPO_FOLLOWUP_MINUTOS = 60

CLIENTES_EM_PAUSA = {}
ULTIMA_INTERACAO = {}
TZ_BRASIL = ZoneInfo("America/Sao_Paulo")

PROMOCAO_ATUAL = "50% OFF já aplicado no valor final, sem necessidade de cupom"
PROMOCAO_RELAMPAGO = "Na compra de 2 Ômega 3 Revita+, ganhe 1 Multivitamínico A-Z GRÁTIS"
VALOR_KIT_PROMOCAO = "R$ 109,98"
FORMAS_PAGAMENTO = "boleto, Pix ou cartão em até 3x sem juros"
FRETE_GRATIS = "Frete grátis para todo o Brasil"

COMANDOS_MENU = [
    "menu", "menu inicial", "voltar menu", "voltar ao menu",
    "opções", "opcoes", "ver opções", "ver opcoes"
]

COMANDOS_PROMOCAO_INICIAL = [
    "oi", "olá", "ola", "bom dia", "boa tarde", "boa noite",
    "começar", "comecar", "iniciar", "reiniciar",
    "tenho interesse", "queria mais informações", "quero mais informações",
    "mais informações", "mais informacoes", "informações", "informacoes",
    "interesse", "gostaria de saber", "quero saber mais"
]

GATILHOS_PROMOCAO_INICIAL = [
    "tenho interesse", "queria mais informações", "quero mais informações",
    "mais informações", "mais informacoes", "informações", "informacoes",
    "interesse", "gostaria de saber", "quero saber mais",
    "promo", "promoção", "promocao", "promoção relâmpago", "promocao relampago"
]

PRODUTOS = {
    "omega": {
        "nome": "Ômega 3 Concentrado - 60 Cápsulas",
        "preco": "R$54,95",
        "descricao": "Suporte nutricional para bem-estar geral e rotina saudável.",
        "serve": "Serve para complementar a rotina com ômega 3, ajudando no bem-estar geral e suporte nutricional diário.",
        "link": "https://revitamais.com.br/produtos/omega-3-concentrado-60-capsulas/"
    },
    "revita_hair": {
        "nome": "Revita Hair Gummies",
        "preco": "R$44,95",
        "descricao": "Gummies para cuidado com cabelo, pele e unhas.",
        "serve": "Serve para auxiliar na rotina de beleza, com foco em cabelo, pele e unhas.",
        "link": "https://revitamais.com.br/produtos/hair-30-unidades-gummys/"
    },
    "complexo_b": {
        "nome": "Complexo B Gummies",
        "preco": "R$44,95",
        "descricao": "Vitaminas do complexo B em gummies para rotina, energia e disposição.",
        "serve": "Serve para complementar a ingestão de vitaminas do complexo B, muito buscadas para rotina, energia e disposição.",
        "link": "https://revitamais.com.br/produtos/complexo-b-30-unidades-gummys/"
    },
    "multivitaminico": {
        "nome": "Multivitamínico A-Z - 30 Cápsulas",
        "preco": "R$29,95",
        "descricao": "Vitaminas e minerais para complementar a rotina diária.",
        "serve": "Serve para complementar vitaminas e minerais importantes no dia a dia.",
        "link": "https://revitamais.com.br/produtos/multivitaminico-a-z-30-capsulas/"
    },
    "multivitaminico_mulher": {
        "nome": "Multivitamínico Mulher - 30 Cápsulas",
        "preco": "R$30,38",
        "descricao": "Suporte nutricional para a rotina feminina.",
        "serve": "Serve para complementar a rotina nutricional feminina com vitaminas e minerais.",
        "link": "https://revitamais.com.br/produtos/multivitaminico-mulher-30-capsulas/"
    },
    "multivitaminico_homem": {
        "nome": "Multivitamínico Homem - 30 Cápsulas",
        "preco": "R$30,38",
        "descricao": "Suporte nutricional para a rotina masculina.",
        "serve": "Serve para complementar a rotina nutricional masculina com vitaminas e minerais.",
        "link": "https://revitamais.com.br/produtos/multivitaminico-homem-30-capsulas/"
    },
    "colageno_tipo2": {
        "nome": "Colágeno Tipo 2 - 30 Cápsulas",
        "preco": "R$29,95",
        "descricao": "Suporte para articulações, mobilidade e cuidado diário.",
        "serve": "Serve para complementar a rotina de cuidado com articulações e mobilidade.",
        "link": "https://revitamais.com.br/produtos/colageno-tipo-2-30-capsulas/"
    },
    "skin": {
        "nome": "Skin + Ácido Hialurônico + Vitamina C",
        "preco": "R$29,95",
        "descricao": "Suporte para pele, hidratação, firmeza e rotina de beleza.",
        "serve": "Serve para complementar a rotina de cuidado com a pele, hidratação, firmeza e beleza.",
        "link": SITE_REVITA
    }
}

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
else:
    model = None

PROMPT_REVITA = f"""
Você é a atendente virtual da Revita+, uma loja de suplementos.

Tom de voz:
- Português do Brasil.
- Simpática, objetiva, acolhedora e vendedora.
- Respostas curtas, naturais e com cara de WhatsApp.
- Use emojis com moderação.
- Primeiro ajude o cliente. Não force venda em toda resposta.

Regras obrigatórias:
- Não invente preços.
- Não invente promoções.
- Não invente links.
- Não use placeholders.
- Não prometa cura.
- Não faça diagnóstico médico.
- Não diga que produto trata doença.
- Não ofereça, não liste e não indique kits, combos ou pacotes fora da promoção-relâmpago oficial.
- Pode falar da promoção-relâmpago oficial quando o cliente chegar pelo WhatsApp ou demonstrar interesse.
- Não fale de cupom.
- Informe que os valores já estão com 50% OFF aplicado no valor final, sem necessidade de cupom.
- Se perguntarem frete, informe: {FRETE_GRATIS}.
- Se pedirem preço, link, catálogo, loja ou compra, informe o valor final cadastrado e o link direto quando houver.
- Formas de pagamento: {FORMAS_PAGAMENTO}.
- Se pedirem atendente, informe horário de atendimento e tempo médio de resposta.
- Não ofereça Gummies infantil.
- Não ofereça Colágeno em pó.

Site oficial: {SITE_REVITA}
"""


def normalizar_texto(texto):
    return (texto or "").lower().strip()


def pediu_menu(mensagem):
    texto = normalizar_texto(mensagem)
    return texto in COMANDOS_MENU


def pediu_promocao_inicial(mensagem):
    texto = normalizar_texto(mensagem)
    if texto in COMANDOS_PROMOCAO_INICIAL:
        return True
    return any(gatilho in texto for gatilho in GATILHOS_PROMOCAO_INICIAL)


def horario_atendimento_aberto():
    agora = datetime.now(TZ_BRASIL)
    return agora.weekday() <= 4 and 8 <= agora.hour < 21


def saudacao_horario():
    agora = datetime.now(TZ_BRASIL)

    if 8 <= agora.hour < 12:
        return "Bom dia"

    elif 12 <= agora.hour < 18:
        return "Boa tarde"

    else:
        return "Boa noite"


def ia_deve_responder():
    agora = datetime.now(TZ_BRASIL)
    hoje = agora.strftime("%Y-%m-%d")

    feriados = [
        "2026-01-01", "2026-02-16", "2026-02-17", "2026-04-03",
        "2026-04-21", "2026-05-01", "2026-06-04", "2026-09-07",
        "2026-10-12", "2026-11-02", "2026-11-15", "2026-12-25",
    ]

    if hoje in feriados:
        return True
    if agora.weekday() >= 5:
        return True
    if 8 <= agora.hour < 21:
        return False
    return True


def mensagem_atendente():
    if horario_atendimento_aberto():
        return """Claro! Em breve uma consultora da Revita+ irá te atender. 💚

⏰ Tempo médio de resposta:
até 30 minutos."""

    return """Claro! 💚

Nosso atendimento funciona de segunda a sexta, das 08h às 21h.

Recebemos sua mensagem e uma consultora retornará no próximo horário útil.

⏰ Tempo médio de resposta:
até 30 minutos."""


def mensagem_promocao_relampago():
    saudacao = saudacao_horario()

    if horario_atendimento_aberto():
        return f"""Olá! 😊 {saudacao}!

Seja bem-vindo(a) à Revita+ Suplementos.

Aproveite nossa oferta exclusiva para clientes do WhatsApp! 👇

🎁 {PROMOCAO_RELAMPAGO}.

💰 Valor do kit: {VALOR_KIT_PROMOCAO}.

💳 Formas de pagamento:
• PIX
• Boleto bancário
• Cartão de crédito em até 3x sem juros

📦 Enviamos para todo o Brasil com Nota Fiscal.

Se desejar garantir essa oferta, responda com QUERO."""

    return f"""Olá! 😊 {saudacao}!

Seja bem-vindo(a) à Revita+ Suplementos.

No momento, nosso atendimento está fora do horário comercial, mas sua mensagem é muito importante para nós. Assim que retornarmos, responderemos o mais rápido possível.

Enquanto isso, aproveite nossa oferta exclusiva para clientes do WhatsApp! 👇

🎁 {PROMOCAO_RELAMPAGO}.

💰 Valor do kit: {VALOR_KIT_PROMOCAO}.

💳 Formas de pagamento:
• PIX
• Boleto bancário
• Cartão de crédito em até 3x sem juros

📦 Enviamos para todo o Brasil com Nota Fiscal.

Se desejar garantir essa oferta, responda com QUERO. Assim que nosso atendimento retornar, daremos continuidade ao seu pedido."""

def pausar_cliente(telefone):
    if telefone:
        CLIENTES_EM_PAUSA[telefone] = datetime.now() + timedelta(minutes=TEMPO_PAUSA_MINUTOS)


def remover_pausa_cliente(telefone):
    CLIENTES_EM_PAUSA.pop(telefone, None)


def cliente_esta_em_pausa(telefone):
    if not telefone:
        return False
    pausa_ate = CLIENTES_EM_PAUSA.get(telefone)
    if not pausa_ate:
        return False
    if datetime.now() < pausa_ate:
        return True
    CLIENTES_EM_PAUSA.pop(telefone, None)
    return False


def atualizar_ultima_interacao(telefone):
    if telefone:
        ULTIMA_INTERACAO[telefone] = datetime.now()


def agendar_followup(telefone):
    if not telefone:
        return

    def enviar_followup():
        ultima = ULTIMA_INTERACAO.get(telefone)
        if not ultima:
            return
        passou_tempo = datetime.now() - ultima >= timedelta(minutes=TEMPO_FOLLOWUP_MINUTOS)
        if passou_tempo and not cliente_esta_em_pausa(telefone):
            texto = """Oi! Você ainda está aí? 💚

Posso te ajudar com alguma dúvida sobre os produtos da Revita+?"""
            enviar_whatsapp(telefone, texto)

    timer = threading.Timer(TEMPO_FOLLOWUP_MINUTOS * 60, enviar_followup)
    timer.daemon = True
    timer.start()


def cliente_pediu_atendente(mensagem):
    texto = normalizar_texto(mensagem)
    if texto in ["6", "opção 6", "opcao 6", "7", "opção 7", "opcao 7"]:
        return True
    palavras = [
        "atendente", "humano", "pessoa", "consultora", "consultor",
        "falar com alguém", "falar com alguem", "quero atendimento",
        "me chama", "me liga", "vendedora", "vendedor"
    ]
    return any(p in texto for p in palavras)


def pediu_preco_link_ou_compra(mensagem):
    texto = normalizar_texto(mensagem)
    palavras = [
        "preço", "preco", "valor", "quanto custa", "quanto é", "quanto e",
        "link", "comprar", "compra", "quero comprar", "pedido", "catálogo",
        "catalogo", "loja", "site"
    ]
    return any(p in texto for p in palavras)


def pediu_compra_fora_site(mensagem):
    texto = normalizar_texto(mensagem)
    palavras = [
        "não quero comprar pelo site", "nao quero comprar pelo site",
        "não consigo comprar no site", "nao consigo comprar no site",
        "comprar por aqui", "quero comprar por aqui",
        "prefiro passar os dados", "posso passar os dados",
        "fazer pedido por aqui", "fechar por aqui",
        "não quero pelo site", "nao quero pelo site"
    ]
    return any(p in texto for p in palavras)


def mensagem_compra_fora_site():
    return f"""Claro! Podemos seguir por aqui. 💚

Por favor, me envie:

1️⃣ CPF
2️⃣ Nome completo
3️⃣ E-mail
4️⃣ Produto desejado
5️⃣ Forma de pagamento: boleto, Pix ou cartão em até 3x sem juros

🚚 {FRETE_GRATIS}
🏷️ {PROMOCAO_ATUAL}"""


def pediu_formas_pagamento(mensagem):
    texto = normalizar_texto(mensagem)
    palavras = [
        "forma de pagamento", "formas de pagamento", "pagamento",
        "boleto", "pix", "cartão", "cartao", "parcelar",
        "parcelamento", "3x", "juros"
    ]
    return any(p in texto for p in palavras)


def mensagem_pagamento():
    return f"""As formas de pagamento são:

💳 Cartão em até 3x sem juros
💚 Pix
🧾 Boleto

🚚 {FRETE_GRATIS}
🏷️ {PROMOCAO_ATUAL}"""


def pediu_frete(mensagem):
    texto = normalizar_texto(mensagem)
    return any(p in texto for p in ["frete", "entrega", "prazo", "envio"])


def mensagem_frete():
    return f"""🚚 {FRETE_GRATIS}

Os valores dos produtos já estão com 50% OFF aplicado no valor final, sem cupom.

Se quiser comprar pelo site, acesse:
{SITE_REVITA}"""


def pediu_pra_que_serve(mensagem):
    texto = normalizar_texto(mensagem)
    palavras = [
        "pra que serve", "para que serve", "serve pra que", "serve para que",
        "benefício", "beneficio", "benefícios", "beneficios",
        "me fala mais", "falar mais", "me explique", "explica",
        "como funciona", "detalhes", "mais sobre"
    ]
    return any(p in texto for p in palavras)


def pediu_produto_removido(mensagem):
    texto = normalizar_texto(mensagem)
    if any(p in texto for p in ["gummies infantil", "gummy infantil", "kids", "criança", "crianca", "infantil"]):
        return True
    if any(p in texto for p in ["colágeno em pó", "colageno em po", "colageno pó", "colágeno pó", "colageno 108g"]):
        return True
    if any(p in texto for p in ["kit", "kits", "combo", "combos", "pacote", "pacotes"]):
        return True
    return False


def mensagem_produto_removido():
    return """No momento esse item não está disponível no atendimento automático. 💚

Posso te apresentar as opções disponíveis da Revita+:

1️⃣ Cabelo, pele e unhas
2️⃣ Colágeno Tipo 2
3️⃣ Ômega 3
4️⃣ Multivitamínicos
5️⃣ Ver catálogo / comprar
6️⃣ Falar com atendente

💡 Digite MENU INICIAL para voltar ao menu principal."""


def menu_principal():
    saudacao = saudacao_horario()
    return f"""Olá! 👋 {saudacao}!

Sou a assistente virtual da Revita+.

Como posso te ajudar hoje?

1️⃣ Cabelo, pele e unhas
2️⃣ Colágeno Tipo 2
3️⃣ Ômega 3
4️⃣ Multivitamínicos
5️⃣ Ver catálogo / comprar
6️⃣ Falar com atendente

🚚 {FRETE_GRATIS}
🏷️ Valores já com 50% OFF aplicado, sem cupom

💡 Digite MENU INICIAL para voltar a este menu quando quiser.

É só responder com o número da opção. 💚"""


def detectar_produto(mensagem):
    texto = normalizar_texto(mensagem)

    if any(p in texto for p in ["colageno em po", "colágeno em pó", "colageno 108g", "colágeno 108g"]):
        return None
    if any(p in texto for p in [
        "colageno tipo 2", "colágeno tipo 2", "articulação", "articulacao",
        "articulações", "articulacoes", "mobilidade", "ossos", "joelho", "colageno", "colágeno"
    ]):
        return PRODUTOS.get("colageno_tipo2")
    if any(p in texto for p in ["omega", "ômega", "omega 3", "ômega 3", "oleo de peixe", "óleo de peixe"]):
        return PRODUTOS.get("omega")
    if any(p in texto for p in [
        "revita hair", "hair", "queda", "cabelo fraco", "crescimento capilar",
        "fortalecer cabelo", "fio", "fios", "cabelo", "unha", "unhas"
    ]):
        return PRODUTOS.get("revita_hair")
    if any(p in texto for p in [
        "skin", "pele", "acido hialuronico", "ácido hialurônico",
        "hialuronico", "hialurônico", "firmeza", "elasticidade",
        "hidratação", "hidratacao", "vitamina c"
    ]):
        return PRODUTOS.get("skin")
    if any(p in texto for p in ["mulher", "feminino", "multivitaminico mulher", "multivitamínico mulher", "vitamina mulher"]):
        return PRODUTOS.get("multivitaminico_mulher")
    if any(p in texto for p in ["homem", "masculino", "multivitaminico homem", "multivitamínico homem", "vitamina homem"]):
        return PRODUTOS.get("multivitaminico_homem")
    if any(p in texto for p in ["complexo b", "vitamina b", "b12", "b6", "energia", "disposição", "disposicao", "cansaço", "cansaco"]):
        return PRODUTOS.get("complexo_b")
    if any(p in texto for p in ["multi", "vitamina", "vitaminas", "multivitaminico", "multivitamínico", "minerais"]):
        return PRODUTOS.get("multivitaminico")
    return None


def resposta_produto_com_preco(produto):
    return f"""{produto["nome"]} 💚

{produto["descricao"]}

✨ Pra que serve:
{produto["serve"]}

💰 Valor final com 50% OFF: {produto["preco"]}
🏷️ Sem necessidade de cupom

🚚 {FRETE_GRATIS}
💳 Pagamento: {FORMAS_PAGAMENTO}

🔗 Link direto:
{produto["link"]}

Se preferir comprar por aqui, me envie:
CPF, nome completo, e-mail, forma de pagamento e o produto desejado."""


def resposta_menu(mensagem):
    texto = normalizar_texto(mensagem)

    if pediu_menu(mensagem):
        return menu_principal()

    if texto in ["1", "opção 1", "opcao 1"]:
        return f"""Temos opções para cabelo, pele e unhas. 💚

✨ {PRODUTOS["revita_hair"]["nome"]}
💰 Valor final com 50% OFF: {PRODUTOS["revita_hair"]["preco"]}

✨ {PRODUTOS["skin"]["nome"]}
💰 Valor final com 50% OFF: {PRODUTOS["skin"]["preco"]}

🚚 {FRETE_GRATIS}
🏷️ Sem necessidade de cupom

Você procura algo mais para cabelo, pele ou unhas?"""

    if texto in ["2", "opção 2", "opcao 2"]:
        return resposta_produto_com_preco(PRODUTOS["colageno_tipo2"])

    if texto in ["3", "opção 3", "opcao 3"]:
        return resposta_produto_com_preco(PRODUTOS["omega"])

    if texto in ["4", "opção 4", "opcao 4"]:
        return f"""Temos opções de multivitamínicos Revita+. 💚

✨ {PRODUTOS["multivitaminico"]["nome"]}
💰 Valor final com 50% OFF: {PRODUTOS["multivitaminico"]["preco"]}

✨ {PRODUTOS["multivitaminico_mulher"]["nome"]}
💰 Valor final com 50% OFF: {PRODUTOS["multivitaminico_mulher"]["preco"]}

✨ {PRODUTOS["multivitaminico_homem"]["nome"]}
💰 Valor final com 50% OFF: {PRODUTOS["multivitaminico_homem"]["preco"]}

✨ {PRODUTOS["complexo_b"]["nome"]}
💰 Valor final com 50% OFF: {PRODUTOS["complexo_b"]["preco"]}

🚚 {FRETE_GRATIS}
🏷️ Sem necessidade de cupom

Você procura para mulher, homem, disposição ou rotina geral?"""

    if texto in ["5", "opção 5", "opcao 5"]:
        return f"""Claro! Você pode ver os produtos disponíveis na loja oficial da Revita+:

{SITE_REVITA}

🚚 {FRETE_GRATIS}
🏷️ Valores já com 50% OFF aplicado, sem cupom
💳 Pagamento: {FORMAS_PAGAMENTO}

Se preferir comprar por aqui, me envie:
CPF, nome completo, e-mail, forma de pagamento e o produto desejado."""

    if texto in ["6", "opção 6", "opcao 6", "7", "opção 7", "opcao 7"]:
        return mensagem_atendente()

    return None


def resposta_pra_que_serve(produto=None):
    if produto:
        return f"""{produto["nome"]} 💚

✨ Pra que serve:
{produto["serve"]}

💰 Valor final com 50% OFF: {produto["preco"]}
🏷️ Sem necessidade de cupom
🚚 {FRETE_GRATIS}

Quer que eu te envie o link direto para compra?"""

    return """Claro! 💚

Me diga qual produto você quer conhecer melhor que eu te explico para que serve.

Você pode escolher pelo menu:

1️⃣ Cabelo, pele e unhas
2️⃣ Colágeno Tipo 2
3️⃣ Ômega 3
4️⃣ Multivitamínicos
5️⃣ Ver catálogo / comprar
6️⃣ Falar com atendente"""


def resposta_fixa(mensagem):
    if cliente_respondeu_quero(mensagem):
        return mensagem_quero_promocao()

    if pediu_produto_removido(mensagem):
        return mensagem_produto_removido()

    if pediu_promocao_inicial(mensagem):
        return mensagem_promocao_relampago()

    menu = resposta_menu(mensagem)
    if menu:
        return menu

    if pediu_compra_fora_site(mensagem):
        return mensagem_compra_fora_site()

    if pediu_formas_pagamento(mensagem):
        return mensagem_pagamento()

    if pediu_frete(mensagem):
        return mensagem_frete()

    if cliente_pediu_atendente(mensagem):
        return mensagem_atendente()

    produto = detectar_produto(mensagem)

    if pediu_pra_que_serve(mensagem):
        return resposta_pra_que_serve(produto=produto)

    if pediu_preco_link_ou_compra(mensagem):
        if produto:
            return resposta_produto_com_preco(produto)
        return f"""Claro! 👋

Você pode acessar nossa loja oficial aqui:

{SITE_REVITA}

Lá você encontra os produtos disponíveis da Revita+. 💚

🚚 {FRETE_GRATIS}
🏷️ Valores já com 50% OFF aplicado, sem cupom
💳 Pagamento: {FORMAS_PAGAMENTO}

Se preferir comprar por aqui, me envie:
CPF, nome completo, e-mail, forma de pagamento e o produto desejado."""

    return None


def resposta_seguranca():
    saudacao = saudacao_horario()
    return f"""{saudacao}! Claro, posso te ajudar. 💚

Não consegui entender 100% sua mensagem, mas posso te orientar por aqui.

Digite uma opção:

1️⃣ Cabelo, pele e unhas
2️⃣ Colágeno Tipo 2
3️⃣ Ômega 3
4️⃣ Multivitamínicos
5️⃣ Ver catálogo / comprar
6️⃣ Falar com atendente

Ou digite MENU INICIAL para voltar ao menu."""


def gerar_resposta_revita(mensagem):
    try:
        fixa = resposta_fixa(mensagem)
        if fixa:
            return fixa

        if not model:
            return resposta_seguranca()

        produto = detectar_produto(mensagem)
        contexto = ""

        if produto:
            contexto += f"""
Produto identificado:
Nome: {produto.get("nome", "")}
Descrição: {produto.get("descricao", "")}
Pra que serve: {produto.get("serve", "")}
Preço final com 50% OFF: {produto.get("preco", "")}
Link direto: {produto.get("link", SITE_REVITA)}
"""

        saudacao = saudacao_horario()

        prompt_completo = f"""
{PROMPT_REVITA}

Saudação obrigatória para este atendimento: {saudacao}.
Nunca use uma saudação diferente dessa.
Regras de saudação:
- Das 08:00 às 11:59 use Bom dia.
- Das 12:00 às 17:59 use Boa tarde.
- Das 18:00 às 07:59 use Boa noite.

{contexto}

Cliente: {mensagem}

Responda primeiro a dúvida do cliente.
Se houver produto identificado, pode informar o valor final com 50% OFF.
Não fale de cupom.
Não fale de kits, combos ou pacotes.
Só envie link direto se o cliente pedir preço, compra, link, catálogo ou loja.
Sempre que falar de compra, mencione:
- {FRETE_GRATIS}
- 50% OFF já aplicado no valor final, sem cupom
- Pagamento: {FORMAS_PAGAMENTO}

Se não entender a pergunta, responda de forma útil e ofereça o MENU INICIAL.

Finalize com uma pergunta simples para continuar o atendimento.

Atendente Revita+:
"""

        resposta = model.generate_content(prompt_completo)
        if resposta and getattr(resposta, "text", None) and resposta.text.strip():
            texto_resposta = resposta.text.strip()
            termos_bloqueados = ["kit", "kits", "combo", "combos", "cupom"]
            if any(t in normalizar_texto(texto_resposta) for t in termos_bloqueados):
                return resposta_seguranca()
            return texto_resposta

        return resposta_seguranca()

    except Exception as e:
        print("ERRO DENTRO DA IA:", str(e))
        return resposta_seguranca()


def extrair_mensagem_e_numero(data):
    try:
        if data.get("event") != "messages.upsert":
            return None, None

        dados = data.get("data", {})
        key = dados.get("key", {})
        remote_jid = key.get("remoteJid", "")

        # Segurança extra: nunca responder grupos, listas, broadcast ou status.
        if (
            remote_jid.endswith("@g.us")
            or remote_jid.endswith("@broadcast")
            or remote_jid == "status@broadcast"
            or "@g.us" in remote_jid
        ):
            print("Mensagem de grupo/lista/status ignorada:", remote_jid)
            return None, None

        if key.get("fromMe") is True:
            telefone = remote_jid.replace("@s.whatsapp.net", "").replace("@c.us", "")
            pausar_cliente(telefone)
            print("Mensagem enviada por atendente humano. IA pausada para:", telefone)
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
    payload = {"number": numero, "text": texto}
    headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print("Status envio WhatsApp:", response.status_code)
        print("Resposta Evolution:", response.text)
        return response.status_code in [200, 201]
    except Exception as e:
        print("Erro ao enviar WhatsApp:", str(e))
        return False


def enviar_imagem_whatsapp(numero, legenda=""):
    if not EVOLUTION_API_KEY:
        print("ERRO: EVOLUTION_API_KEY não configurada.")
        return False

    if not PROMOCAO_BANNER_URL:
        print("ERRO: PROMOCAO_BANNER_URL não configurada.")
        return False

    url = f"{EVOLUTION_API_URL}/message/sendMedia/{EVOLUTION_INSTANCE}"
    payload = {
        "number": numero,
        "mediatype": "image",
        "mimetype": "image/jpeg",
        "media": PROMOCAO_BANNER_URL,
        "caption": legenda,
        "fileName": "promocao-revita-whatsapp.jpg"
    }
    headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print("Status envio imagem WhatsApp:", response.status_code)
        print("Resposta Evolution imagem:", response.text)
        return response.status_code in [200, 201]
    except Exception as e:
        print("Erro ao enviar imagem WhatsApp:", str(e))
        return False


def cliente_respondeu_quero(mensagem):
    texto = normalizar_texto(mensagem)
    return texto in [
        "quero", "eu quero", "quero a promoção", "quero a promocao",
        "quero promoção", "quero promocao", "quero o kit", "tenho interesse na promoção",
        "tenho interesse na promocao"
    ]


def mensagem_quero_promocao():
    return f"""Perfeito! 💚

Vamos dar continuidade ao seu pedido da promoção exclusiva do WhatsApp:

🎁 {PROMOCAO_RELAMPAGO}
💰 Valor do kit: {VALOR_KIT_PROMOCAO}

Para reservar sua oferta, me envie por favor:

1️⃣ Nome completo
2️⃣ CPF
3️⃣ E-mail
4️⃣ CEP e endereço completo
5️⃣ Forma de pagamento: PIX, boleto ou cartão em até 3x sem juros

📦 Enviamos para todo o Brasil com Nota Fiscal."""


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
                <a href="/rapida?msg=oi" style="text-align:center; background:#f1e8f6; padding:10px; border-radius:10px; color:#6f3c8f; text-decoration:none;">Promoção</a>
                <a href="/rapida?msg=Quero saber sobre ômega 3" style="text-align:center; background:#f1e8f6; padding:10px; border-radius:10px; color:#6f3c8f; text-decoration:none;">Ômega 3</a>
                <a href="/rapida?msg=Quero algo para cabelo" style="text-align:center; background:#f1e8f6; padding:10px; border-radius:10px; color:#6f3c8f; text-decoration:none;">Cabelo</a>
                <a href="/rapida?msg=Quero ver os produtos" style="text-align:center; background:#f1e8f6; padding:10px; border-radius:10px; color:#6f3c8f; text-decoration:none;">Produtos</a>
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
    data = request.json or {}

    print("=" * 60)
    print("WEBHOOK RECEBIDO:")
    print(data)
    print("=" * 60)

    telefone, mensagem = extrair_mensagem_e_numero(data)

    if not telefone or not mensagem:
        return {"status": "ignorado", "motivo": "sem mensagem válida ou grupo/lista/status"}, 200

    atualizar_ultima_interacao(telefone)

    if pediu_promocao_inicial(mensagem):
        remover_pausa_cliente(telefone)
        resposta = mensagem_promocao_relampago()
        imagem_enviada = enviar_imagem_whatsapp(telefone)
        enviado = enviar_whatsapp(telefone, resposta)
        agendar_followup(telefone)
        return {
            "status": "ok",
            "telefone": telefone,
            "mensagem": mensagem,
            "resposta": resposta,
            "imagem_enviada": imagem_enviada,
            "enviado": enviado,
            "motivo": "promocao_relampago_inicial"
        }, 200

    if not ia_deve_responder():
        return {"status": "ignorado", "motivo": "horario comercial com atendimento humano ativo"}, 200

    if pediu_menu(mensagem):
        remover_pausa_cliente(telefone)
        resposta = menu_principal()
        enviado = enviar_whatsapp(telefone, resposta)
        agendar_followup(telefone)
        return {
            "status": "ok",
            "telefone": telefone,
            "mensagem": mensagem,
            "resposta": resposta,
            "enviado": enviado,
            "motivo": "menu solicitado"
        }, 200

    if cliente_esta_em_pausa(telefone):
        return {"status": "pausado", "telefone": telefone, "motivo": "cliente aguardando consultora"}, 200

    try:
        resposta = gerar_resposta_revita(mensagem)
    except Exception as e:
        print("ERRO AO GERAR RESPOSTA:", str(e))
        resposta = resposta_seguranca()

    if cliente_pediu_atendente(mensagem):
        pausar_cliente(telefone)

    enviado = enviar_whatsapp(telefone, resposta)
    agendar_followup(telefone)

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
