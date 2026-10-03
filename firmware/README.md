# firmware/README.md — ESP32-CAM (AI Thinker)

Guia de configuracao da camera Wi-Fi para o projeto LibrasLink.

---

## 1. Materiais necessarios

| Item | Observacao |
|------|-----------|
| ESP32-CAM AI Thinker | Modulo com camera OV2640 |
| Adaptador FTDI (USB-Serial) | Conversor 3.3 V, ex.: CH340 ou FT232 |
| Jumper para GPIO0 → GND | Necessario apenas durante o upload |
| Fonte 5 V / 2 A | O modulo consome bastante no peak |

---

## 2. Instalacao do ambiente

1. Abra o **Arduino IDE** (versao 2.x recomendada).
2. Em _Arquivo → Preferencias → URLs adicionais de gerenciadores de placas_, adicione:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. Em _Ferramentas → Gerenciador de placas_, pesquise **esp32** e instale o pacote **Espressif Systems**.

---

## 3. Abrindo o exemplo CameraWebServer

1. _Arquivo → Exemplos → ESP32 → Camera → **CameraWebServer**_.
2. No inicio do arquivo `CameraWebServer.ino`, descomente a linha correta:
   ```cpp
   #define CAMERA_MODEL_AI_THINKER   // ← ativar esta
   // #define CAMERA_MODEL_WROVER_KIT  // comentar as outras
   ```
3. Preencha suas credenciais Wi-Fi (rede 2.4 GHz):
   ```cpp
   const char* ssid     = "NOME_DA_SUA_REDE";
   const char* password = "SENHA_DA_SUA_REDE";
   ```

---

## 4. Configuracoes de placa e upload

| Parametro | Valor |
|-----------|-------|
| Placa | AI Thinker ESP32-CAM |
| Upload Speed | 115200 |
| Flash Mode | QIO |
| Partition Scheme | Huge APP (3MB No OTA) |
| Porta | COM* (porta do adaptador FTDI) |

**Conexoes FTDI → ESP32-CAM para upload:**

| FTDI | ESP32-CAM |
|------|-----------|
| GND | GND |
| 5V ou 3.3V | 5V (prefira alimentacao externa 5V) |
| TX | UOR (GPIO3) |
| RX | UOT (GPIO1) |
| GND | **GPIO0** (coloque jumper ANTES de ligar) |

> **ATENCAO:** o jumper GPIO0 → GND deve estar conectado **somente durante o upload**.
> Apos gravar, remova o jumper e pressione o botao de RESET.

---

## 5. Gravando o firmware

1. Conecte o FTDI com o jumper GPIO0 → GND.
2. No Arduino IDE, clique em **Carregar** (seta →).
3. Aguarde a mensagem `Connecting...` e o progresso de upload.
4. Quando terminar: **remova o jumper** e pressione **RESET** no modulo.

---

## 6. Descobrindo o IP e testando o stream

1. Abra o **Monitor Serial** (115200 baud).
2. Pressione RESET; aguarde a mensagem:
   ```
   Camera Ready! Use 'http://192.168.x.x' to connect
   ```
3. Acesse `http://<IP>` no navegador para ver a interface da camera.
4. O stream MJPEG estara disponivel em:
   ```
   http://<IP>:81/stream
   ```

---

## 7. Configuracao recomendada

Na interface web da ESP32-CAM, antes de usar com o LibrasLink:

| Parametro | Valor recomendado |
|-----------|------------------|
| Resolution | VGA (640×480) |
| Quality | 12 |
| Brightness | 0 a 1 |
| Flip | Off |
| Mirror | Off |

> **Dica:** Boa iluminacao frontal e fundo simples (parede branca/escura) melhoram muito a deteccao do MediaPipe.

---

## 8. Configurando o edge para usar a ESP32-CAM

Edite `edge/.env`:

```env
CAMERA_SOURCE=http://192.168.x.x:81/stream
```

Substitua `192.168.x.x` pelo IP mostrado no Serial Monitor.

Teste a conexao:
```bash
cd edge
python camera.py
```

---

## 9. Planos B (se a ESP32-CAM nao funcionar)

| Alternativa | Configuracao |
|-------------|-------------|
| App **IP Webcam** (Android) | `CAMERA_SOURCE=http://<IP>:8080/video` |
| Webcam USB / camera do notebook | `CAMERA_SOURCE=0` |

---

## 10. Problemas comuns

| Sintoma | Solucao |
|---------|---------|
| `Connecting...` trava | Verifique jumper GPIO0 → GND e porta COM correta |
| Imagem muito escura | Aumentar brilho na interface web |
| Stream trava / lento | Reduzir resolucao para CIF (400×296) |
| MediaPipe nao detecta mao | Melhorar iluminacao; verificar se nao esta espelhando |
| Wi-Fi da faculdade bloqueia | Usar hotspot do celular para tudo |
