import sys
import os

# Garante que o handler.py é encontrado
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Simula as variáveis de ambiente sem precisar do .env
os.environ["TEMP_LIMITE_ALERTA"] = "60"
os.environ["CALLMEBOT_KEY"] = "fake"
os.environ["CALLMEBOT_PHONE"] = "+5500000000000"

from handler import _avaliar_alerta_interno, _resposta, receber_leitura

# ──────────────────────────────────────────────
# Testes da função avaliar_alerta
# ──────────────────────────────────────────────

def test_temperatura_normal():
    resultado = _avaliar_alerta_interno({"temperatura": 45.0})
    assert resultado["nivel"] == "normal"
    assert resultado["deve_notificar"] == False

def test_temperatura_atencao():
    resultado = _avaliar_alerta_interno({"temperatura": 62.0})
    assert resultado["nivel"] == "atencao"
    assert resultado["deve_notificar"] == True

def test_temperatura_critica():
    resultado = _avaliar_alerta_interno({"temperatura": 75.0})
    assert resultado["nivel"] == "critico"
    assert resultado["deve_notificar"] == True

def test_limite_exato():
    resultado = _avaliar_alerta_interno({"temperatura": 60.0})
    assert resultado["nivel"] == "atencao"

# ──────────────────────────────────────────────
# Testes da função receber_leitura
# ──────────────────────────────────────────────

def test_receber_leitura_valida():
    event = {"body": '{"dispositivo": "esp32-sala", "temperatura": 45.0}'}
    resposta = receber_leitura(event, {})
    assert resposta["statusCode"] == 200

def test_receber_leitura_sem_temperatura():
    event = {"body": '{"dispositivo": "esp32-sala"}'}
    resposta = receber_leitura(event, {})
    assert resposta["statusCode"] == 400

def test_receber_leitura_temperatura_invalida():
    event = {"body": '{"dispositivo": "esp32-sala", "temperatura": "abc"}'}
    resposta = receber_leitura(event, {})
    assert resposta["statusCode"] == 400

# ──────────────────────────────────────────────
# Testes do helper _resposta
# ──────────────────────────────────────────────

def test_resposta_status_200():
    r = _resposta(200, {"ok": True})
    assert r["statusCode"] == 200

def test_resposta_tem_content_type():
    r = _resposta(200, {})
    assert r["headers"]["Content-Type"] == "application/json"
    