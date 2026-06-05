import network
import urequests
import ujson
import time
import esp32
from machine import Pin

led = Pin(2, Pin.OUT)

# ── Configurações (idealmente num config.py separado) ──
SSID = "Glads 2.4GHZ"
PASSWORD = "GladsLello*12"

# URL da sua Lambda local — troque pelo IP do seu PC na rede
# (não funciona com localhost — ESP32 é outro dispositivo)
LAMBDA_URL = "http://192.168.0.9:3000/dev/temperatura"

DISPOSITIVO = "esp32-sala"
INTERVALO_SEGUNDOS = 0.5  


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    time.sleep(0.5)
    wlan.active(True)

    if not wlan.isconnected():
        print("Conectando ao Wi-Fi...")
        wlan.connect(SSID, PASSWORD)
        timeout = 0
        while not wlan.isconnected() and timeout < 20:
            led.on(); time.sleep(0.3); led.off(); time.sleep(0.3)
            timeout += 1

    if wlan.isconnected():
        print("Conectado! IP:", wlan.ifconfig()[0])
        return True

    print("Falha ao conectar.")
    return False


def ler_temperatura():
    temp_f = esp32.raw_temperature()
    return round((temp_f - 32) * 5 / 9, 1)


def enviar_leitura(temp_c):
    """
    Agora o ESP32 só envia dados — não decide nada.
    Quem decide se manda WhatsApp é a Lambda.
    """
    payload = ujson.dumps({
        "dispositivo": DISPOSITIVO,
        "temperatura": temp_c
    })

    try:
        response = urequests.post(
            LAMBDA_URL,
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            dados = ujson.loads(response.text)
            print("Lambda respondeu:", dados.get("nivel"), "|", dados.get("alerta"))

            # Pisca LED conforme o nível retornado pela Lambda
            nivel = dados.get("nivel", "normal")
            if nivel == "critico":
                _pisca_led(10, 0.1)   # pisca rápido — urgente
            elif nivel == "atencao":
                _pisca_led(3, 0.3)    # pisca devagar — atenção
            else:
                led.on(); time.sleep(1); led.off()  # acende 1s — ok

        response.close()

    except Exception as e:
        print("Erro ao enviar:", e)


def _pisca_led(vezes, intervalo):
    for _ in range(vezes):
        led.on(); time.sleep(intervalo)
        led.off(); time.sleep(intervalo)


# ── Execução principal ──
if connect_wifi():
    while True:
        temp = ler_temperatura()
        print(f"Temperatura: {temp}°C")
        enviar_leitura(temp)
        time.sleep(INTERVALO_SEGUNDOS)