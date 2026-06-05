import json
import os
import requests
from datetime import datetime

# ──────────────────────────────────────────────
# Função 1: Recebe e valida a leitura do ESP32
# ──────────────────────────────────────────────
def receber_leitura(event, context):
    """
    Ponto de entrada. O ESP32 faz POST aqui com JSON:
    { "dispositivo": "esp32-sala", "temperatura": 45.2 }
    """
    try:
        body = json.loads(event.get("body", "{}"))

        if "temperatura" not in body:
            return _resposta(400, {"erro": "Campo 'temperatura' obrigatório"})

        temp = float(body["temperatura"])
        dispositivo = body.get("dispositivo", "esp32-desconhecido")

        leitura = {
            "dispositivo": dispositivo,
            "temperatura": temp,
            "timestamp": datetime.now().isoformat(),
            "unidade": "celsius"
        }

        print(f"[LEITURA] {dispositivo}: {temp}°C às {leitura['timestamp']}")

        # Encadeia para a função de avaliação
        avaliacao = _avaliar_alerta_interno(leitura)
        leitura["alerta"] = avaliacao["alerta"]
        leitura["nivel"] = avaliacao["nivel"]

        # Se precisar notificar, encadeia para a função de notificação
        if avaliacao["deve_notificar"]:
            _notificar_interno(leitura)

        return _resposta(200, leitura)

    except ValueError:
        return _resposta(400, {"erro": "Temperatura inválida"})
    except Exception as e:
        return _resposta(500, {"erro": str(e)})


# ──────────────────────────────────────────────
# Função 2: Avalia se a temperatura é crítica
# ──────────────────────────────────────────────
def avaliar_alerta(event, context):
    """Endpoint HTTP independente — útil para testes."""
    body = json.loads(event.get("body", "{}"))
    resultado = _avaliar_alerta_interno(body)
    return _resposta(200, resultado)


def _avaliar_alerta_interno(leitura: dict) -> dict:
    """
    Regras de negócio isoladas aqui.
    Fácil de testar unitariamente e de evoluir.
    """
    temp = leitura.get("temperatura", 0)
    limite = float(os.environ.get("TEMP_LIMITE_ALERTA", 60))

    if temp >= limite + 20:       # ex: >= 70°C
        nivel = "critico"
        deve_notificar = True
        mensagem = f"🔴 CRÍTICO: {temp:.1f}°C — acima de {limite + 10}°C!"

    elif temp >= limite:          # ex: >= 60°C
        nivel = "atencao"
        deve_notificar = True
        mensagem = f"🟡 ATENÇÃO: {temp:.1f}°C — acima do limite de {limite}°C"

    else:
        nivel = "normal"
        deve_notificar = False
        mensagem = f"✅ Normal: {temp:.1f}°C"

    return {
        "temperatura": temp,
        "nivel": nivel,
        "alerta": mensagem,
        "deve_notificar": deve_notificar,
        "limite_configurado": limite
    }


# ──────────────────────────────────────────────
# Função 3: Envia WhatsApp via CallMeBot
# ──────────────────────────────────────────────
def notificar(event, context):
    """Endpoint HTTP independente — útil para testes manuais."""
    body = json.loads(event.get("body", "{}"))
    resultado = _notificar_interno(body)
    return _resposta(200, resultado)


def _notificar_interno(leitura: dict) -> dict:
    """
    Responsabilidade única: enviar a notificação.
    Não sabe nada sobre temperatura ou regras de negócio.
    """
    api_key = os.environ.get("CALLMEBOT_KEY", "")
    phone = os.environ.get("CALLMEBOT_PHONE", "")

    if not api_key or not phone:
        print("[NOTIFICAR] Credenciais não configuradas no .env")
        return {"enviado": False, "motivo": "credenciais ausentes"}

    dispositivo = leitura.get("dispositivo", "ESP32")
    alerta = leitura.get("alerta", "Alerta de temperatura")
    timestamp = leitura.get("timestamp", "")

    mensagem = f"{alerta} | {dispositivo} | {timestamp[:16]}"
    msg_encoded = mensagem.replace(" ", "+")

    url = (
        f"https://api.callmebot.com/whatsapp.php"
        f"?phone={phone}&apikey={api_key}&text={msg_encoded}"
    )

    try:
        response = requests.get(url, timeout=10)
        sucesso = response.status_code == 200
        print(f"[NOTIFICAR] {'Enviado' if sucesso else 'Falhou'}: {mensagem}")
        return {"enviado": sucesso, "mensagem": mensagem}
    except Exception as e:
        print(f"[NOTIFICAR] Erro: {e}")
        return {"enviado": False, "erro": str(e)}


# ──────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────
def _resposta(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False)
    }