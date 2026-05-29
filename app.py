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

EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "https://evolution-api-production-9927.up.railway.app")
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
- Sempre conduza para o próximo passo: enviar link, pedir CEP ou
