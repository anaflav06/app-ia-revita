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

TEMPO_PAUSA_MINUTOS = 10
TEMPO_FOLLOWUP_MINUTOS = 60

CLIENTES_EM_PAUSA = {}
ULTIMA_INTERACAO = {}
TZ_BRASIL = ZoneInfo("America/Sao_Paulo")

CUPOM_PRIMEIRA_COMPRA = "PRIMEIRACOMPRA"
FORMAS_PAGAMENTO = "boleto, Pix ou cartão em até 3x sem juros"
FRETE_GRATIS = "Frete grátis para todo o Brasil"

COMANDOS_MENU = [
    "oi", "olá", "ola", "bom dia", "boa tarde", "boa noite",
    "menu", "menu inicial", "voltar menu", "voltar ao menu",
    "começar", "comecar", "iniciar", "reiniciar",
    "tenho interesse", "queria mais informações", "quero mais informações",
    "mais informações", "mais informacoes", "informações", "informacoes"
]

GATILHOS_MENU = [
    "tenho interesse", "queria mais informações", "quero mais informações",
    "mais informações", "mais informacoes", "informações", "informacoes",
    "interesse", "gostaria de saber", "quero saber mais"
]

PRODUTOS = {
    "omega": {
        "nome": "Ômega 3 Concentrado - 60 Cápsulas",
        "preco": "R$109,90",
        "descricao": "Suporte nutricional para bem-estar geral e rotina saudável.",
        "serve": "Serve para complementar a rotina com ômega 3, ajudando no bem-estar geral e suporte nutricional diário.",
        "link": "https://revitamais.com.br/produtos/omega-3-concentrado-60-capsulas/"
    },
    "revita_hair": {
        "nome": "Revita Hair Gummies",
        "preco": "R$89,90",
        "descricao": "Gummies para cuidado com cabelo, pele e unhas.",
        "serve": "Serve para auxiliar na rotina de beleza, com foco em cabelo, pele e unhas.",
        "link": "https://revitamais.com.br/produtos/hair-30-unidades-gummys/"
    },
    "complexo_b": {
        "nome": "Complexo B Gummies",
        "preco": "R$89,90",
        "descricao": "Vitaminas do complexo B em gummies para rotina, energia e disposição.",
        "serve": "Serve para complementar a ingestão de vitaminas do complexo B, muito buscadas para rotina, energia e disposição.",
        "link": "https://revitamais.com.br/produtos/complexo-b-30-unidades-gummys/"
    },
    "multivitaminico": {
        "nome": "Multivitamínico A-Z - 30 Cápsulas",
        "preco": "R$59,90",
        "descricao": "Vitaminas e minerais para complementar a rotina diária.",
        "serve": "Serve para complementar vitaminas e minerais importantes no dia a dia.",
        "link": "https://revitamais.com.br/produtos/multivitaminico-a-z-30-capsulas/"
    },
    "multivitaminico_mulher": {
        "nome": "Multivitamínico Mulher - 30 Cápsulas",
        "preco": "R$60,75",
        "descricao": "Suporte nutricional para a rotina feminina.",
        "serve": "Serve para complementar a rotina nutricional feminina com vitaminas e minerais.",
        "link": "https://revitamais.com.br/produtos/multivitaminico-mulher-30-capsulas/"
    },
    "multivitaminico_homem": {
        "nome": "Multivitamínico Homem - 30 Cápsulas",
        "preco": "R$60,75",
        "descricao": "Suporte nutricional para a rotina masculina.",
        "serve": "Serve para complementar a rotina nutricional masculina com vitaminas e minerais.",
        "link": "https://revitamais.com.br/produtos/multivitaminico-homem-30-capsulas/"
    },
    "colageno_tipo2": {
        "nome": "Colágeno Tipo 2 - 30 Cápsulas",
        "preco": "R$59,90",
        "descricao": "Suporte para articulações, mobilidade e cuidado diário.",
        "serve": "Serve para complementar a rotina de cuidado com articulações e mobilidade.",
        "link": "https://revitamais.com.br/produtos/colageno-tipo-2-30-capsulas/"
    },
    "skin": {
        "nome": "Skin + Ácido Hialurônico + Vitamina C",
        "preco": "R$59,90",
        "descricao": "Suporte para pele, hidratação, firmeza e rotina de beleza.",
        "serve": "Serve para complementar a rotina de cuidado com a pele, hidratação, firmeza e beleza.",
        "link": SITE_REVITA
    }
}

KITS = {
    "energia_total": {
        "nome": "KIT – Energia Total",
        "preco": "R$229,90",
        "descricao": "Kit para quem busca mais energia, disposição e suporte nutricional na rotina.",
        "serve": "Serve para quem busca uma rotina com mais energia, disposição e suporte nutricional.",
        "link": "https://revitamais.com.br/kits/"
    },
    "articulacoes_mobilidade": {
        "nome": "KIT – Articulações & Mobilidade",
        "preco": "R$149,90",
        "descricao": "Kit voltado para suporte às articulações, mobilidade e cuidado diário.",
        "serve": "Serve para quem busca suporte para articulações, mobilidade e cuidado diário.",
        "link": "https://revitamais.com.br/kits/"
    },
    "saude_masculina": {
        "nome": "KIT – Saúde Masculina",
        "preco": "R$149,90",
        "descricao": "Kit pensado para complementar a rotina nutricional masculina.",
        "serve": "Serve para complementar a rotina nutricional masculina.",
        "link": "https://revitamais.com.br/kits/"
    },
    "saude_feminina": {
        "nome": "KIT – Saúde Feminina",
        "preco": "R$219,99",
        "descricao": "Kit pensado para complementar a rotina nutricional feminina.",
        "serve": "Serve para complementar a rotina nutricional feminina.",
        "link": "https://revitamais.com.br/kits/"
    },
    "foco_energia": {
        "nome": "KIT – Foco & Energia",
        "preco": "R$129,99",
        "descricao": "Kit para rotina, foco, energia e disposição.",
        "serve": "Serve para quem busca suporte para foco, energia e disposição.",
        "link": "https://revitamais.com.br/kits/"
    },
    "beleza_completa": {
        "nome": "KIT – Beleza Completa",
        "preco": "R$169,99",
        "descricao": "Kit para rotina de beleza, pele, cabelo e unhas.",
        "serve": "Serve para uma rotina de beleza mais completa, com foco em pele, cabelo e unhas.",
        "link": "https://revitamais.com.br/kits/"
    },
    "beleza_essencial": {
        "nome": "KIT – Beleza Essencial",
        "preco": "R$119,99",
        "descricao": "Kit essencial para cuidado diário com beleza.",
        "serve": "Serve para quem quer começar uma rotina de beleza de forma prática.",
        "link": "https://revitamais.com.br/kits/"
    },
    "imunidade_energia": {
        "nome": "KIT – Imunidade & Energia",
        "preco": "R$149,99",
        "descricao": "Kit para suporte nutricional, imunidade e energia.",
        "serve": "Serve para complementar a rotina com foco em imunidade, energia e suporte nutricional.",
        "link": "https://revitamais.com.br/kits/"
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

Regras:
- Não invente preços.
- Não invente promoções.
- Não invente links.
- Não use placeholders.
- Não prometa cura.
- Não faça diagnóstico médico.
- Não diga que produto trata doença.
- Se perguntarem frete, informe: {FRETE_GRATIS}.
- Se pedirem preço, link, catálogo, loja ou compra, informe o valor cadastrado e o link direto quando houver.
- Se for primeira compra, informe o cupom: {CUPOM_PRIMEIRA_COMPRA}.
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
    if texto in COMANDOS_MENU:
        return True
    return any(gatilho in texto for gatilho in GATILHOS_MENU)


def horario_atendimento_aberto():
    agora = datetime.now(TZ_BRASIL)
    return agora.weekday() <= 4 and 8 <= agora.hour < 18


def mensagem_atendente():
    if horario_atendimento_aberto():
        return """Claro! Em breve uma consultora da Revita+ irá te atender. 💚

⏰ Tempo médio de resposta:
até 30 minutos."""

    return """Claro! 💚

Nosso atendimento funciona de segunda a sexta, das 08h às 18h.

Recebemos sua mensagem e uma consultora retornará no próximo horário útil.

⏰ Tempo médio de resposta:
até 30 minutos."""


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

Posso te ajudar com alguma dúvida sobre os produtos ou kits da Revita+?"""
            enviar_whatsapp(telefone, texto)

    timer = threading.Timer(TEMPO_FOLLOWUP_MINUTOS * 60, enviar_followup)
    timer.daemon = True
    timer.start()


def cliente_pediu_atendente(mensagem):
    texto = normalizar_texto(mensagem)

    if texto in ["7", "opção 7", "opcao 7"]:
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
4️⃣ Produto ou kit desejado
5️⃣ Forma de pagamento: boleto, Pix ou cartão em até 3x sem juros

🚚 {FRETE_GRATIS}
🎁 Primeira compra? Use o cupom: {CUPOM_PRIMEIRA_COMPRA}"""


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
🎁 Primeira compra? Use o cupom: {CUPOM_PRIMEIRA_COMPRA}"""


def pediu_frete(mensagem):
    texto = normalizar_texto(mensagem)
    return any(p in texto for p in ["frete", "entrega", "prazo", "envio"])


def mensagem_frete():
    return f"""🚚 {FRETE_GRATIS}

Se quiser comprar pelo site, acesse:
{SITE_REVITA}

🎁 Primeira compra? Use o cupom: {CUPOM_PRIMEIRA_COMPRA}"""


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

    return False


def mensagem_produto_removido():
    return """No momento não estamos trabalhando com esse produto no atendimento automático. 💚

Posso te apresentar as opções disponíveis da Revita+:

1️⃣ Cabelo, pele e unhas
2️⃣ Colágeno Tipo 2
3️⃣ Ômega 3
4️⃣ Multivitamínicos
5️⃣ Kits promocionais
6️⃣ Ver catálogo / comprar
7️⃣ Falar com atendente

💡 Digite MENU INICIAL para voltar ao menu principal."""


def menu_principal():
    return """Olá! 👋 Sou a assistente virtual da Revita+.

Como posso te ajudar hoje?

1️⃣ Cabelo, pele e unhas
2️⃣ Colágeno Tipo 2
3️⃣ Ômega 3
4️⃣ Multivitamínicos
5️⃣ Kits promocionais
6️⃣ Ver catálogo / comprar
7️⃣ Falar com atendente

🚚 Frete grátis para todo o Brasil
🎁 Primeira compra? Use o cupom: PRIMEIRACOMPRA

💡 Digite MENU INICIAL para voltar a este menu quando quiser.

É só responder com o número da opção. 💚"""


def lista_kits():
    return f"""Temos kits promocionais Revita+ 💚

✨ {KITS["beleza_essencial"]["nome"]}
💰 {KITS["beleza_essencial"]["preco"]}

✨ {KITS["beleza_completa"]["nome"]}
💰 {KITS["beleza_completa"]["preco"]}

✨ {KITS["energia_total"]["nome"]}
💰 {KITS["energia_total"]["preco"]}

✨ {KITS["saude_feminina"]["nome"]}
💰 {KITS["saude_feminina"]["preco"]}

✨ {KITS["saude_masculina"]["nome"]}
💰 {KITS["saude_masculina"]["preco"]}

✨ {KITS["articulacoes_mobilidade"]["nome"]}
💰 {KITS["articulacoes_mobilidade"]["preco"]}

✨ {KITS["foco_energia"]["nome"]}
💰 {KITS["foco_energia"]["preco"]}

✨ {KITS["imunidade_energia"]["nome"]}
💰 {KITS["imunidade_energia"]["preco"]}

🚚 {FRETE_GRATIS}
🎁 Primeira compra? Use o cupom: {CUPOM_PRIMEIRA_COMPRA}

🔗 Ver todos os kits:
https://revitamais.com.br/kits/

Qual deles você quer conhecer melhor?"""


def detectar_kit(mensagem):
    texto = normalizar_texto(mensagem)

    if any(p in texto for p in ["beleza essencial", "kit beleza essencial"]):
        return KITS["beleza_essencial"]

    if any(p in texto for p in ["beleza completa", "kit beleza completa"]):
        return KITS["beleza_completa"]

    if any(p in texto for p in ["energia total", "kit energia total"]):
        return KITS["energia_total"]

    if any(p in texto for p in ["saúde feminina", "saude feminina", "kit feminino", "kit mulher"]):
        return KITS["saude_feminina"]

    if any(p in texto for p in ["saúde masculina", "saude masculina", "kit masculino", "kit homem"]):
        return KITS["saude_masculina"]

    if any(p in texto for p in ["articulações", "articulacoes", "mobilidade", "kit articulações", "kit articulacoes"]):
        return KITS["articulacoes_mobilidade"]

    if any(p in texto for p in ["foco", "foco e energia", "kit foco"]):
        return KITS["foco_energia"]

    if any(p in texto for p in ["imunidade", "imunidade e energia", "kit imunidade"]):
        return KITS["imunidade_energia"]

    return None


def pediu_kits(mensagem):
    texto = normalizar_texto(mensagem)

    palavras = [
        "kit", "kits", "combo", "combos", "promoção", "promocao",
        "promoções", "promocoes", "mais vendido", "mais vendidos",
        "pacote", "pacotes", "economizar"
    ]

    return any(p in texto for p in palavras)


def resposta_kit_com_preco(kit):
    return f"""{kit["nome"]} 💚

{kit["descricao"]}

✨ Pra que serve:
{kit["serve"]}

💰 Valor: {kit["preco"]}

🚚 {FRETE_GRATIS}
🎁 Primeira compra? Use o cupom: {CUPOM_PRIMEIRA_COMPRA}
💳 Pagamento: {FORMAS_PAGAMENTO}

🔗 Link direto:
{kit["link"]}

Se preferir comprar por aqui, me envie:
CPF, nome completo, e-mail, forma de pagamento e o produto/kit desejado."""


def resposta_menu(mensagem):
    texto = normalizar_texto(mensagem)

    if pediu_menu(mensagem):
        return menu_principal()

    if texto in ["1", "opção 1", "opcao 1"]:
        return f"""Temos opções para cabelo, pele e unhas. 💚

✨ {PRODUTOS["revita_hair"]["nome"]}
💰 Valor: {PRODUTOS["revita_hair"]["preco"]}

✨ {PRODUTOS["skin"]["nome"]}
💰 Valor: {PRODUTOS["skin"]["preco"]}

Também temos kits de beleza na opção 5.

🚚 {FRETE_GRATIS}
🎁 Primeira compra? Use o cupom: {CUPOM_PRIMEIRA_COMPRA}

Você procura algo mais para cabelo, pele ou unhas?"""

    if texto in ["2", "opção 2", "opcao 2"]:
        p = PRODUTOS["colageno_tipo2"]

        return f"""Temos o {p["nome"]}. 💚

✨ Pra que serve:
{p["serve"]}

💰 Valor: {p["preco"]}

🚚 {FRETE_GRATIS}
🎁 Primeira compra? Use o cupom: {CUPOM_PRIMEIRA_COMPRA}

Você quer usar mais para mobilidade, articulações ou rotina preventiva?"""

    if texto in ["3", "opção 3", "opcao 3"]:
        p = PRODUTOS["omega"]

        return f"""Temos o {p["nome"]}. 💚

✨ Pra que serve:
{p["serve"]}

💰 Valor: {p["preco"]}

🚚 {FRETE_GRATIS}
🎁 Primeira compra? Use o cupom: {CUPOM_PRIMEIRA_COMPRA}

Você já usa ômega 3 ou está começando agora?"""

    if texto in ["4", "opção 4", "opcao 4"]:
        return f"""Temos opções de multivitamínicos Revita+. 💚

✨ {PRODUTOS["multivitaminico"]["nome"]}
💰 {PRODUTOS["multivitaminico"]["preco"]}

✨ {PRODUTOS["multivitaminico_mulher"]["nome"]}
💰 {PRODUTOS["multivitaminico_mulher"]["preco"]}

✨ {PRODUTOS["multivitaminico_homem"]["nome"]}
💰 {PRODUTOS["multivitaminico_homem"]["preco"]}

✨ {PRODUTOS["complexo_b"]["nome"]}
💰 {PRODUTOS["complexo_b"]["preco"]}

🚚 {FRETE_GRATIS}
🎁 Primeira compra? Use o cupom: {CUPOM_PRIMEIRA_COMPRA}

Você procura para mulher, homem, disposição ou rotina geral?"""

    if texto in ["5", "opção 5", "opcao 5"]:
        return lista_kits()

    if texto in ["6", "opção 6", "opcao 6"]:
        return f"""Claro! Você pode ver todos os produtos e kits na loja oficial da Revita+:

{SITE_REVITA}

🚚 {FRETE_GRATIS}
🎁 Primeira compra? Use o cupom: {CUPOM_PRIMEIRA_COMPRA}
💳 Pagamento: {FORMAS_PAGAMENTO}

Se preferir comprar por aqui, me envie:
CPF, nome completo, e-mail, forma de pagamento e o produto/kit desejado."""

    if texto in ["7", "opção 7", "opcao 7"]:
        return mensagem_atendente()

    return None


def detectar_produto(mensagem):
    texto = normalizar_texto(mensagem)

    if any(p in texto for p in ["colageno em po", "colágeno em pó", "colageno 108g", "colágeno 108g"]):
        return None

    if any(p in texto for p in [
        "colageno tipo 2", "colágeno tipo 2", "articulação", "articulacao",
        "articulações", "articulacoes", "mobilidade", "ossos", "joelho"
    ]):
        return PRODUTOS.get("colageno_tipo2")

    if any(p in texto for p in ["colageno", "colágeno"]):
        return PRODUTOS.get("colageno_tipo2")

    if any(p in texto for p in ["omega", "ômega", "omega 3", "ômega 3", "oleo de peixe", "óleo de peixe"]):
        return PRODUTOS.get("omega")

    if any(p in texto for p in [
        "revita hair", "hair", "queda", "cabelo fraco",
        "crescimento capilar", "fortalecer cabelo", "fio", "fios",
        "cabelo", "unha", "unhas"
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

💰 Valor: {produto["preco"]}

🚚 {FRETE_GRATIS}
🎁 Primeira compra? Use o cupom: {CUPOM_PRIMEIRA_COMPRA}
💳 Pagamento: {FORMAS_PAGAMENTO}

🔗 Link direto:
{produto["link"]}

Se preferir comprar por aqui, me envie:
CPF, nome completo, e-mail, forma de pagamento e o produto desejado."""


def resposta_pra_que_serve(produto=None, kit=None):
    if produto:
        return f"""{produto["nome"]} 💚

✨ Pra que serve:
{produto["serve"]}

💰 Valor: {produto["preco"]}
🚚 {FRETE_GRATIS}

Quer que eu te envie o link direto para compra?"""

    if kit:
        return f"""{kit["nome"]} 💚

✨ Pra que serve:
{kit["serve"]}

💰 Valor: {kit["preco"]}
🚚 {FRETE_GRATIS}

Quer que eu te envie o link direto para compra?"""

    return """Claro! 💚

Me diga qual produto ou kit você quer conhecer melhor que eu te explico para que serve.

Você pode escolher pelo menu:

1️⃣ Cabelo, pele e unhas
2️⃣ Colágeno Tipo 2
3️⃣ Ômega 3
4️⃣ Multivitamínicos
5️⃣ Kits promocionais"""


def resposta_fixa(mensagem):
    texto = normalizar_texto(mensagem)

    if pediu_produto_removido(mensagem):
        return mensagem_produto_removido()

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

    kit = detectar_kit(mensagem)
    produto = detectar_produto(mensagem)

    if pediu_pra_que_serve(mensagem):
        return resposta_pra_que_serve(produto=produto, kit=kit)

    if kit:
        return resposta_kit_com_preco(kit)

    if pediu_kits(mensagem):
        return lista_kits()

    if pediu_preco_link_ou_compra(mensagem):
        if produto:
            return resposta_produto_com_preco(produto)

        return f"""Claro! 👋

Você pode acessar nossa loja oficial aqui:

{SITE_REVITA}

Lá você encontra os produtos e kits disponíveis da Revita+. 💚

🚚 {FRETE_GRATIS}
🎁 Primeira compra? Use o cupom: {CUPOM_PRIMEIRA_COMPRA}
💳 Pagamento: {FORMAS_PAGAMENTO}

Se preferir comprar por aqui, me envie:
CPF, nome completo, e-mail, forma de pagamento e o produto/kit desejado."""

    return None


def resposta_seguranca():
    return """Claro, posso te ajudar. 💚

Não consegui entender 100% sua mensagem, mas posso te orientar por aqui.

Digite uma opção:

1️⃣ Cabelo, pele e unhas
2️⃣ Colágeno Tipo 2
3️⃣ Ômega 3
4️⃣ Multivitamínicos
5️⃣ Kits promocionais
6️⃣ Ver catálogo / comprar
7️⃣ Falar com atendente

Ou digite MENU INICIAL para voltar ao menu."""


def gerar_resposta_revita(mensagem):
    try:
        if not model:
            return resposta_seguranca()

        fixa = resposta_fixa(mensagem)
        if fixa:
            return fixa

        produto = detectar_produto(mensagem)
        kit = detectar_kit(mensagem)

        contexto = ""

        if produto:
            contexto += f"""
Produto identificado:
Nome: {produto.get("nome", "")}
Descrição: {produto.get("descricao", "")}
Pra que serve: {produto.get("serve", "")}
Preço: {produto.get("preco", "")}
Link direto: {produto.get("link", SITE_REVITA)}
"""

        if kit:
            contexto += f"""
Kit identificado:
Nome: {kit.get("nome", "")}
Descrição: {kit.get("descricao", "")}
Pra que serve: {kit.get("serve", "")}
Preço: {kit.get("preco", "")}
Link direto: {kit.get("link", SITE_REVITA)}
"""

        prompt_completo = f"""
{PROMPT_REVITA}

{contexto}

Cliente: {mensagem}

Responda primeiro a dúvida do cliente.
Se houver produto ou kit identificado, pode informar o valor.
Só envie link direto se o cliente pedir preço, compra, link, catálogo ou loja.
Sempre que falar de compra, mencione:
- {FRETE_GRATIS}
- Cupom de primeira compra: {CUPOM_PRIMEIRA_COMPRA}
- Pagamento: {FORMAS_PAGAMENTO}

Se não entender a pergunta, responda de forma útil e ofereça o MENU INICIAL.

Finalize com uma pergunta simples para continuar o atendimento.

Atendente Revita+:
"""

        resposta = model.generate_content(prompt_completo)

        if resposta and getattr(resposta, "text", None) and resposta.text.strip():
            return resposta.text.strip()

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
                <a href="/rapida?msg=Quero saber sobre kits" style="text-align:center; background:#f1e8f6; padding:10px; border-radius:10px; color:#6f3c8f; text-decoration:none;">Kits</a>
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

    atualizar_ultima_interacao(telefone)

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
        return {
            "status": "pausado",
            "telefone": telefone,
            "motivo": "cliente aguardando consultora"
        }, 200

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
