# ============================================================
# app.py — servidor Flask com a Flora
# ============================================================

import os
from flask import Flask, request, jsonify, render_template
import anthropic

# inicializa o app Flask e o cliente da Anthropic
app = Flask(__name__, template_folder="templates")
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# banco de dados de plantas
plantas = {
    "jiboia": {
        "rega": "a cada 7 dias",
        "luz": "indireta baixa a média",
        "temperatura": "18-27°C",
        "umidade": "média",
        "substrato": "leve e drenante, com perlita e casca de pinus",
        "propagação": "estacas em água ou diretamente no solo"
    },
    "monstera": {
        "rega": "a cada 10 dias",
        "luz": "indireta brilhante",
        "temperatura": "18-30°C",
        "umidade": "alta",
        "substrato": "aerado, com perlita, argila expandida e casca de pinus",
        "propagação": "estacas com nó, em água ou solo úmido"
    },
    "zamioculca": {
        "rega": "a cada 15 dias",
        "luz": "baixa a indireta",
        "temperatura": "15-26°C",
        "umidade": "baixa",
        "substrato": "drenante, com areia grossa ou perlita",
        "propagação": "divisão de rizoma ou folha em solo úmido"
    }
}

# função de busca de plantas
def buscar_planta(nome):
    nome = nome.lower()
    if nome in plantas:
        dados = plantas[nome]
        return (
            f"{nome.capitalize()}: "
            f"rega {dados['rega']}, "
            f"luz {dados['luz']}, "
            f"temperatura {dados['temperatura']}, "
            f"umidade {dados['umidade']}, "
            f"substrato {dados['substrato']}, "
            f"propagação: {dados['propagação']}"
        )
    else:
        return f"Planta '{nome}' não encontrada no banco de dados."

# definição da ferramenta para o Claude
ferramenta = [
    {
        "name": "buscar_planta",
        "description": "Busca informações de cuidado de uma planta específica, como rega, luz, temperatura e umidade.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nome": {
                    "type": "string",
                    "description": "Nome da planta a ser buscada"
                }
            },
            "required": ["nome"]
        }
    }
]

# rota principal — carrega a interface de chat
@app.route("/")
def index():
    return render_template("index.html")

# rota que recebe a mensagem do usuário e retorna a resposta da Flora
@app.route("/chat", methods=["POST"])
def chat():
    # pega o histórico e a nova mensagem enviados pelo navegador
    dados = request.json
    historico = dados.get("historico", [])
    pergunta = dados.get("mensagem", "")

    # adiciona a pergunta ao histórico
    historico.append({"role": "user", "content": pergunta})

    # primeira chamada à API
    resposta = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system="Você é Flora, uma assistente especialista em cuidado de plantas domésticas. \
Responda sempre em português, de forma simpática e prática.",
        tools=ferramenta,
        messages=historico
    )

    # verifica se o Claude quer usar uma ferramenta
    if resposta.stop_reason == "tool_use":
        tool_block = next(b for b in resposta.content if b.type == "tool_use")
        nome_planta = tool_block.input["nome"]
        resultado = buscar_planta(nome_planta)

        # segunda chamada com o resultado da ferramenta
        resposta_final = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system="Você é Flora, uma assistente especialista em cuidado de plantas domésticas. \
                    Responda sempre em português, de forma simpática e prática.\
                    Primeiro, um explicação breve (um parágrafo). \
                    Depois, uma lista de passo a passo sobre o tema ou explicação.\
                    Peça para o usuário dizer se pode avançar.\
                    Vá passo por passo, sempre perguntando ao usuário.\
                    Foque apenas em assuntos relacionados a plantas. \
                    Se perguntarem sobre outro assunto, redirecione gentilmente para plantas.",
            tools=ferramenta,
            messages=historico + [
                {"role": "assistant", "content": resposta.content},
                {"role": "user", "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_block.id,
                        "content": resultado
                    }
                ]}
            ]
        )
        texto = resposta_final.content[0].text
    else:
        texto = resposta.content[0].text

    # adiciona a resposta da Flora ao histórico
    historico.append({"role": "assistant", "content": texto})

    # retorna a resposta e o histórico atualizado para o navegador
    return jsonify({"resposta": texto, "historico": historico})

# necessário para o Vercel — expõe o app como função serverless
app = app