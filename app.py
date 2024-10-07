from flask import Flask, request
import requests, ast, os
from flask_cors import CORS
from dotenv import load_dotenv

app = Flask(__name__)
CORS (app)
aluno = None
load_dotenv()
openai_api_key = os.getenv('OPENAI_API_KEY')

class Aluno:
  def __init__(self, nome: str, idade: str, interesses: str, habilidade: str, habilidades_atuais: list) -> None:
    self.nome: str = nome
    self.idade: str = idade
    self.interesses: str = interesses
    self.habilidade: str = habilidade
    self.habilidades_atuais: list = habilidades_atuais
    self.gpt: dict = {
      'introdução': '',
      'exercício': '',
      'resposta': ''
    }

@app.route('/')
def index():
    return "Backend is running!"

@app.route('/enviar-questionario', methods=['POST'])
def post_questionario():
    global aluno

    # Recebendo os dados da requisição
    data = request.json
    res = data.get('respostas', [])
    
    # Instanciando o aluno com os dados fornecidos
    aluno = Aluno(res['name'], res['age'], res['interests'], res['ability'], res['currentAbilities'])

    # Criando o prompt a ser enviado para o GPT
    aluno.gpt['introdução'] = f'Imagine que você é um professor de inglês e escreverá uma questão para um alunx que se chama {aluno.nome}, de {aluno.idade} anos, que se interessa por {aluno.interesses}, deseja focar em aprender {aluno.habilidade} e já domina {aluno.habilidades_atuais}. '
    
    prompt = '''Com base nesse aluno, escreva uma história em inglês referente ao perfil do usuário para ensino de inglês e formule uma questão sobre esse texto de forma que o aluno possa responder com suas palavras. a saída deve ser analisável com ast.literal_eval() do Python e nada mais, com os campos: "titleText", "text", and "question" (o conteúdo é apenas um exemplo):
    {
        "titleText": "Exploring the World Through Travel and Conversation.",
        "text": "Traveling is one of the most enriching experiences you can have. At 25, you’ve likely already seen a few places, but the world is vast and full of wonders waiting to be explored...",
        "question": "Why is enhancing conversation skills important for someone who enjoys traveling?"
    }'''
    
    # Concatenando o conteúdo do prompt
    content = aluno.gpt['introdução'] + prompt
    
    # Enviando a requisição para o GPT
    response = gpt_request(content)
    
    # Limpando a resposta recebida para remover blocos de código ou caracteres indesejados
    texto_recebido = response.replace('```json', '').replace('```', '').strip()

    # Remover o prefixo "python" caso exista
    if texto_recebido.startswith("python"):
        texto_recebido = texto_recebido.replace("python", "").strip()
    
    # Removendo quebras de linha e espaços extras
    texto_recebido_tratado = texto_recebido.replace("\n", "").replace("  ", " ")
    
    # Tentando converter o texto recebido em um dicionário Python
    try:
        resposta_em_json = ast.literal_eval(texto_recebido_tratado)
        print("Resposta convertida em JSON:", resposta_em_json)
    except (SyntaxError, ValueError) as e:
        # Em caso de erro, exibe o erro e o conteúdo original tratado
        print(f"Erro ao converter resposta para JSON: {e}")
        print("Texto não formatado corretamente:", texto_recebido_tratado)
        return {"error": "Formato da resposta inválido", "conteudo_original": texto_recebido_tratado}, 400
    
    # Retornando o JSON corretamente convertido
    return resposta_em_json

@app.route('/enviar-resposta', methods=['POST'])
def post_resposta():
        # Recebendo os dados da requisição
    data = request.json
    res = data.get('response', [])
    
    aluno.gpt['resposta'] = res

    # Criando o prompt para o GPT
    prompt = '''Em formato de texto contendo a porcentagem de acertos e os pontos onde esse aluno poderia melhorar. a saída deve ser analisável com ast.literal_eval() do Python e nada mais, com os campos: "titleText", "text", "question" (próxima questão), "return" (resultado). Assim como no *exemplo* abaixo:
    {
        "titleText": "Milton's Football Journey",
        "text": "Milton, a 25-year-old football enthusiast, had always loved the beautiful game. Every weekend, he would gather with friends at the local pub (...)",
        "question": "What does football mean to you, and how does it impact your life today?",
        "return": "80%\ correct Milton, your response about football emphasizes its enjoyable and active aspects, which is great! You correctly identified the sport's positive qualities."
    }
    A questão dada para o aluno foi: '''

    # Montando o conteúdo para enviar à API
    content = aluno.gpt['introdução'] + prompt + aluno.gpt['exercício'] + ' A resposta do aluno foi: ' + aluno.gpt['resposta']
    
    # Fazendo a requisição ao GPT (função gpt_request)
    response = gpt_request(content)
    print("Resposta recebida do GPT:", response)
    
    # Remover blocos de código (ex: ```json) e fazer a limpeza básica
    texto_recebido = response.replace('```json', '').replace('```', '').strip()

    # Remover o prefixo "python" caso exista
    if texto_recebido.startswith("python"):
        texto_recebido = texto_recebido.replace("python", "").strip()
    
    # Remover quebras de linha desnecessárias e espaços extras
    texto_recebido_tratado = texto_recebido.replace("\n", "").replace("  ", " ")
    
    # Tentar converter a string em um dicionário usando ast.literal_eval
    try:
        resposta_em_json = ast.literal_eval(texto_recebido_tratado)
        print("Resposta convertida em JSON:", resposta_em_json)
    except (SyntaxError, ValueError) as e:
        # Caso ocorra um erro de sintaxe ou valor, exibe o erro e o conteúdo original
        print(f"Erro ao converter resposta para JSON: {e}")
        print("Texto não formatado corretamente:", texto_recebido_tratado)
        return {"error": "Formato da resposta inválido", "conteudo_original": texto_recebido_tratado}, 400

    # Retornando o JSON tratado
    return resposta_em_json

def gpt_request(prompt: str):
    # Content
    link = "https://api.openai.com/v1/chat/completions"
    modelId = "gpt-4o-mini"
    maxTokens = 220
    messages= [
        {"role": "user", "content": prompt}
    ]
    TOKEN = openai_api_key

    # Requisition
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "model": modelId,
        "messages": messages,
        "max_tokens": maxTokens,
    }

    response = requests.post(link, headers=headers, json=body)

    json_response = response.json()

    # Verificando se 'choices' existe na resposta
    if 'choices' in json_response and len(json_response['choices']) > 0:
        # Retornando o conteúdo correto
        return json_response['choices'][0]['message']['content']

    else:
        print("A resposta não contém o formato esperado.")
        return None

if __name__ == '__main__':
    app.run(debug=True)
