from flask import Flask, request
import google.generativeai as genai
from config import GEMINI_API_KEY

app = Flask(__name__)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

PROMPT_REVITA = """
Você é a atendente virtual da Revita+, uma loja de suplementos.

Tom de voz:
- Português do Brasil.
- Simpática, objetiva, acolhedora e vendedora.
- Use emojis com moderação.
- Respostas curtas, como conversa de WhatsApp.

Regras importantes:
- Não invente preços.
- Não invente promoções.
- Não prometa cura ou efeito milagroso.
- Não faça diagnóstico médico.
- Se perguntarem preço, diga que pode enviar o link da oferta atual.
- Se perguntarem frete ou prazo, peça o CEP.
- Sempre tente conduzir para o próximo passo: enviar link, pedir CEP ou entender a necessidade.

Produtos principais:
1. Colágeno Verisol + Ácido Hialurônico
Indicado para quem busca firmeza, elasticidade, hidratação da pele e cuidados com beleza.

2. Ômega 3
Indicado para bem-estar geral, rotina saudável e suporte nutricional.

3. Multivitamínico
Indicado para complementar vitaminas e minerais no dia a dia.

4. Gummies cabelo, pele e unhas
Indicado para quem busca praticidade e cuidado diário com beleza.

Quando o cliente não souber o que escolher:
- Pergunte qual objetivo dele: pele, cabelo, energia, imunidade, bem-estar ou rotina saudável.
"""

def gerar_resposta_revita(mensagem):
    prompt_completo = f"""
{PROMPT_REVITA}

Cliente: {mensagem}

Atendente Revita+:
"""
    resposta = model.generate_content(prompt_completo)

    if resposta and resposta.text:
        return resposta.text.strip()

    return "Desculpe, não consegui responder agora. Pode repetir a pergunta? 😊"

@app.route("/")
def home():
    return """
    <h2>Revita+ IA Online 💜</h2>

    <form action="/perguntar" method="post">
        <input 
            name="mensagem" 
            style="width:400px; padding:10px;" 
            placeholder="Digite uma pergunta..."
            required
        >
        <button type="submit">Enviar</button>
    </form>
    """

@app.route("/perguntar", methods=["POST"])
def perguntar():
    try:
        mensagem = request.form.get("mensagem", "").strip()

        if not mensagem:
            return """
            <h2>Erro</h2>
            <p>Digite uma mensagem antes de enviar.</p>
            <br>
            <a href="/">Voltar</a>
            """

        texto_resposta = gerar_resposta_revita(mensagem)

        return f"""
        <h2>Cliente:</h2>
        <p>{mensagem}</p>

        <h2>Revita+:</h2>
        <p>{texto_resposta}</p>

        <br>
        <a href="/">Voltar</a>
        """

    except Exception as e:
        return f"""
        <h2>Erro na IA</h2>
        <p>{str(e)}</p>
        <br>
        <a href="/">Voltar</a>
        """

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Rota reservada para o WhatsApp.
    Quando a Meta liberar, vamos adaptar essa função
    para receber mensagens do WhatsApp oficial.
    """
    data = request.json
    return {"status": "webhook recebido", "dados": data}, 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)
