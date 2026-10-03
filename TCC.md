# SPEC.md — Tradutor de Libras em Tempo Real (projeto "LibrasLink")

> **Instrução para a IA que ler este documento:** este arquivo é a fonte única de verdade.
> Não troque tecnologias, não renomeie arquivos, não invente endpoints, não adicione funcionalidades fora do escopo.
> Se algo estiver ambíguo, pergunte antes de codar. Entregue **uma fase por vez** (seção 12).

---

## 1. Objetivo

Uma câmera Wi-Fi (IoT) capta as mãos de uma pessoa surda fazendo sinais do **alfabeto manual de Libras**. Um serviço de IA reconhece a letra, e uma **central de atendimento** (computador do atendente) mostra o texto sendo formado em tempo real e pode **falar o texto em voz alta** (síntese de voz do navegador).

**Contexto (vertente SmartCity):** acessibilidade e inclusão em serviços públicos, como um totem de atendimento com tradução de Libras para texto e voz.

## 2. Escopo

**Dentro:**
- Captura de vídeo por câmera Wi-Fi (ESP32-CAM; fallback: celular ou webcam)
- Detecção da mão e extração de 21 pontos de referência (landmarks) com MediaPipe
- Classificação de sinais **estáticos** (formas de mão sem movimento) com modelo treinado pela equipe
- Scripts para coletar dados e treinar o modelo
- Envio de cada letra confirmada à central via HTTP
- Central: API, banco SQLite, dashboard com texto em tempo real (WebSocket), botão "Falar" e botão "Limpar"

**Fora (NÃO implementar):**
- Sinais com movimento (J, X, Z, H e palavras/frases completas), redes recorrentes (LSTM) ou transformers
- Expressões faciais e gramática da Libras
- Duas mãos ao mesmo tempo (usar `max_num_hands=1`) e suporte a canhotos (todos sinalizam com a **mão direita**)
- Login/autenticação (apenas uma API key fixa no header)
- Docker, nuvem, MQTT, app mobile
- Tradução de texto para Libras (sentido inverso)

**Limitação a declarar na apresentação:** Libras é uma língua completa, com movimento, expressão facial e gramática própria. O projeto reconhece apenas um subconjunto de sinais estáticos do alfabeto manual, como prova de conceito.

## 3. Arquitetura

```
┌──────────────┐  MJPEG/HTTP   ┌─────────────────────┐  POST /api/signs   ┌─────────────────────┐
│  ESP32-CAM   │ ────────────► │  EDGE (IA)          │ ─────────────────► │  CENTRAL            │
│  (Wi-Fi)     │               │  OpenCV + MediaPipe │                    │  FastAPI + SQLite   │
└──────────────┘               │  + scikit-learn     │                    │  + Dashboard (WS)   │
                               └─────────────────────┘                    └─────────────────────┘
                                 modelo treinado (.joblib)                  navegador do atendente
```

Dois processos Python independentes (podem rodar na mesma máquina na demo):
1. **edge/** — lê o stream, reconhece a letra, envia à central.
2. **central/** — recebe, salva, transmite ao dashboard.

## 4. Stack (FECHADA)

| Item | Escolha | Observação |
|---|---|---|
| Linguagem | Python 3.11 | edge e central |
| Vídeo | `opencv-python` >= 4.10 | |
| Mãos | `mediapipe==0.10.14` | usar `mp.solutions.hands` (API clássica). **Não usar** YOLO, TensorFlow, PyTorch ou Keras |
| Classificador | `scikit-learn` (`RandomForestClassifier`) | salvo com `joblib` |
| Números | `numpy` (versão < 2) | |
| HTTP cliente | `requests` | edge → central |
| API central | `fastapi` + `uvicorn[standard]` | |
| Banco | SQLite via `sqlalchemy` 2.x | `central/data/signs.db` |
| Config | `python-dotenv` | `.env` em cada módulo |
| Dashboard | HTML + CSS + JavaScript puro (sem framework, sem npm) | servido pelo FastAPI |
| Voz | `window.speechSynthesis` com `lang = "pt-BR"` | no navegador, sem API externa |
| Câmera | ESP32-CAM (AI-Thinker), firmware Arduino `CameraWebServer` | stream em `http://<IP>:81/stream` |
| Fallback câmera | App "IP Webcam" (`http://<IP>:8080/video`) ou webcam USB (`0`) | só muda `CAMERA_SOURCE` |

## 5. Estrutura de pastas (não alterar)

```
libraslink/
├── SPEC.md
├── README.md
├── edge/
│   ├── .env.example
│   ├── requirements.txt
│   ├── config.py
│   ├── camera.py             # abre o stream e devolve frames
│   ├── hand_features.py      # MediaPipe + normalização dos landmarks
│   ├── classifier.py         # carrega o modelo e prediz
│   ├── sign_client.py        # envia letra à central
│   ├── collect.py            # coleta de dados (tecla = rótulo)
│   ├── train.py              # treina e avalia o modelo
│   ├── main.py               # loop de reconhecimento
│   ├── data/
│   │   └── dataset.csv       # gerado por collect.py
│   └── models/
│       └── libras_model.joblib
├── central/
│   ├── .env.example
│   ├── requirements.txt
│   ├── config.py
│   ├── main.py               # app FastAPI
│   ├── database.py
│   ├── models.py             # tabela Sign
│   ├── schemas.py
│   ├── ws_manager.py
│   ├── data/                 # signs.db
│   └── static/
│       ├── index.html
│       ├── style.css
│       └── app.js
└── firmware/
    └── README.md             # passo a passo do ESP32-CAM
```

## 6. Classes reconhecidas

- Definir em `edge/config.py` a constante `CLASSES`, com **10 a 12 letras estáticas** do alfabeto manual de Libras, mais a classe especial `ESPACO`.
- A equipe escolhe as letras conferindo uma fonte oficial de Libras (ex.: material do INES). Preferir formas de mão bem distintas entre si.
- Gesto de `ESPACO` (padrão: polegar para cima) e gesto de `NENHUM` (mão relaxada/aberta qualquer, usada como classe "ruído") também são coletados e treinados.
- Exemplo de valor inicial (ajustável pela equipe): `["A","B","C","E","I","L","O","U","V","ESPACO","NENHUM"]`.

## 7. Configuração (.env)

**edge/.env**
```
CAMERA_ID=cam-01
CAMERA_SOURCE=http://192.168.0.50:81/stream   # ou 0 para webcam USB
CENTRAL_URL=http://192.168.0.10:8000
API_KEY=troque-esta-chave
MIN_CONFIDENCE=0.80
CONSECUTIVE_FRAMES=8
RELEASE_FRAMES=5
PROCESS_EVERY_N_FRAMES=2
FRAME_WIDTH=640
SHOW_PREVIEW=true
```

**central/.env**
```
API_KEY=troque-esta-chave
HOST=0.0.0.0
PORT=8000
```

## 8. Modelo de dados (central)

Tabela `signs`:

| Campo | Tipo | Nota |
|---|---|---|
| id | integer PK autoincrement | |
| camera_id | string | |
| label | string | letra ou `ESPACO` |
| confidence | float | 0 a 1 |
| detected_at | datetime (UTC) | enviado pelo edge |

## 9. Pipeline de IA (edge) — regras exatas

### 9.1 Features (`hand_features.py`)
1. Converter o frame BGR → RGB e rodar `mp.solutions.hands.Hands(max_num_hands=1, min_detection_confidence=0.6, min_tracking_confidence=0.5)`.
2. Sem mão detectada → retornar `None`.
3. Com mão: pegar os 21 landmarks `(x, y, z)` → array `(21, 3)`.
4. **Normalizar:** subtrair o landmark 0 (pulso) de todos os pontos; dividir tudo pela maior distância euclidiana entre o pulso e qualquer ponto (evita dependência de posição e distância da câmera).
5. Achatar para vetor de **63 valores**. Esse é o vetor de entrada do modelo, tanto no treino quanto na inferência (mesma função nos dois).

### 9.2 Coleta (`collect.py`)
- Abre a câmera (`CAMERA_SOURCE`), mostra a mão com landmarks desenhados.
- Cada tecla do teclado associada a uma classe (mostrar legenda na tela). Enquanto a tecla estiver pressionada, grava uma linha em `data/dataset.csv`: `label,f0,f1,...,f62`.
- Mostrar contador de amostras por classe na janela. Tecla `ESC` encerra.
- **Meta:** ≥ 300 amostras por classe, de **pelo menos 2 pessoas**, variando distância, ângulo leve e iluminação.

### 9.3 Treino (`train.py`)
- Ler o CSV, separar 80% treino / 20% teste (`stratify`, `random_state=42`).
- `RandomForestClassifier(n_estimators=200, random_state=42)`.
- Imprimir acurácia e matriz de confusão; salvar o modelo em `models/libras_model.joblib` (guardar junto a lista de classes).
- Meta de acurácia no teste: ≥ 90%. Se ficar abaixo, a solução é coletar mais dados, não trocar de algoritmo.

### 9.4 Inferência (`main.py`)
1. Abrir `CAMERA_SOURCE`. Se cair, tentar reconectar a cada 3 s, indefinidamente.
2. Processar 1 a cada `PROCESS_EVERY_N_FRAMES` frames; redimensionar para `FRAME_WIDTH`. **Não espelhar o frame** (igual ao da coleta).
3. Extrair features; sem mão → contar como frame "vazio".
4. Predizer com `predict_proba`; pegar a classe de maior probabilidade.
5. Ignorar se a classe for `NENHUM` ou se a probabilidade < `MIN_CONFIDENCE`.
6. **Estabilidade:** só confirmar uma letra após `CONSECUTIVE_FRAMES` frames processados consecutivos com a **mesma** classe.
7. **Anti-repetição:** depois de enviar uma letra, a mesma letra só pode ser enviada de novo após a mão sumir ou o modelo prever outra classe (ou `NENHUM`) por `RELEASE_FRAMES` frames processados. Isso permite letras repetidas (ex.: "LL") sem enviar dezenas de vezes.
8. Envio: `POST {CENTRAL_URL}/api/signs`, timeout de 3 s. Se falhar, logar e **não travar o loop** (sem fila).
9. Se `SHOW_PREVIEW=true`, mostrar janela com landmarks, letra prevista e confiança; `q` encerra.
10. Logs em português com `logging` (INFO), sem `print` solto.

## 10. Contratos da API (central)

Endpoints `/api/*` exigem o header `X-API-Key: <API_KEY>`. WebSocket, `/health` e a página estática não exigem.

**POST `/api/signs`** — usado pelo edge
```json
{ "camera_id": "cam-01", "label": "A", "confidence": 0.93, "detected_at": "2026-05-10T14:32:10Z" }
```
Resposta `201`: `{ "id": 41 }`. Efeito: grava no banco e transmite por WebSocket.

**GET `/api/signs?limit=100`** → lista, mais recentes primeiro:
```json
[{ "id": 41, "camera_id": "cam-01", "label": "A", "confidence": 0.93, "detected_at": "2026-05-10T14:32:10Z" }]
```

**GET `/api/signs/latest`** → último registro (ou `404` se vazio). Usado pelo display opcional da fase 9.

**DELETE `/api/signs`** → apaga todos os registros, responde `204` e transmite `{ "type": "cleared" }` por WebSocket.

**GET `/health`** → `{ "status": "ok" }`.

**WebSocket `/ws/signs`** — mensagens do servidor:
```json
{ "type": "new_sign", "data": { ...mesmo formato do item da lista... } }
{ "type": "cleared" }
```

**Estáticos:** `/` serve `static/index.html`.

## 11. Dashboard (central/static)

- Página única, tema escuro, fonte grande (legível a distância), responsiva.
- Ao carregar: `GET /api/signs` (reverter a ordem para montar o texto) e abrir o WebSocket (reconexão automática a cada 2 s).
- **Texto atual** em destaque: cada `new_sign` com letra concatena a letra; `ESPACO` adiciona um espaço.
- **Última letra reconhecida** em tamanho gigante, com a confiança em %.
- Botão **"Falar"**: `speechSynthesis` em `pt-BR` lendo o texto atual.
- Botão **"Limpar"**: chama `DELETE /api/signs`; também limpa ao receber `cleared`.
- Indicador de conexão (verde/vermelho). A chave da API fica em uma constante no topo do `app.js`.

## 12. Fases de desenvolvimento (uma por vez, cada uma testável)

| Fase | Entrega | Critério de aceite |
|---|---|---|
| 1 | Central: banco + endpoints + WebSocket | `curl` cria, lista, apaga; WS recebe eventos |
| 2 | Dashboard | POST manual aparece em tempo real, "Falar" lê o texto |
| 3 | Edge: `camera.py` + `hand_features.py` com webcam | Janela mostra landmarks; vetor de 63 valores impresso |
| 4 | `collect.py` | `dataset.csv` com ≥ 300 amostras por classe |
| 5 | `train.py` | Acurácia ≥ 90% e modelo salvo |
| 6 | `main.py` com preview local (sem envio) | Letra correta na tela, estável, sem repetir |
| 7 | Edge → Central integrados | Sinalizar "OI" ou outra sequência e ver o texto no dashboard |
| 8 | Trocar `CAMERA_SOURCE` para ESP32-CAM | Mesmo fluxo via Wi-Fi (pode ser necessário recoletar alguns dados com a câmera da ESP32) |
| 9 | (Opcional) Display no ESP32 | Ver seção 15 |
| 10 | README + roteiro de demo | Outra pessoa roda seguindo só o README |

**Se o tempo apertar:** pule as fases 8 e 9; demonstre com celular ou webcam.

## 13. Regras para a IA (leia antes de cada resposta)

1. Entregue **apenas a fase pedida**.
2. Cada arquivo completo, pronto para copiar, com o caminho no topo (ex.: `# edge/hand_features.py`).
3. Type hints e docstrings curtas em português.
4. Não adicionar dependências além das listadas. Se precisar, pergunte.
5. Não criar arquivos fora da estrutura da seção 5.
6. Não mudar nomes de campos, rotas ou variáveis de ambiente.
7. A normalização de features deve existir em **um único lugar** (`hand_features.py`) e ser usada por `collect.py`, `train.py` e `main.py`.
8. Sem `async` no edge. No central, `async` apenas onde o FastAPI/WebSocket exigir.
9. Tratar erros de rede e de câmera sem derrubar o programa.
10. Ao final de cada fase, listar: comandos de instalação, comando para rodar e como testar.
11. Se houver conflito entre o pedido do usuário e este SPEC, avise antes de agir.

## 14. Requirements

**edge/requirements.txt**
```
opencv-python>=4.10
mediapipe==0.10.14
numpy<2
scikit-learn
joblib
requests
python-dotenv
```

**central/requirements.txt**
```
fastapi
uvicorn[standard]
sqlalchemy>=2.0
python-dotenv
pydantic>=2
```

## 15. Parte IoT

### 15.1 ESP32-CAM (`firmware/README.md`)
1. Arduino IDE → instalar pacote de placas **esp32** (Espressif).
2. Placa: **AI Thinker ESP32-CAM**. Exemplo: *Arquivo → Exemplos → ESP32 → Camera → CameraWebServer*.
3. Ativar `#define CAMERA_MODEL_AI_THINKER`, preencher SSID e senha do Wi-Fi (2.4 GHz).
4. Gravar com adaptador FTDI (GPIO0 no GND durante o upload; depois remover e resetar).
5. IP no Serial Monitor (115200). Stream em `http://<IP>:81/stream`.
6. Resolução **VGA (640x480)**, qualidade JPEG ~12. Boa iluminação e fundo simples melhoram muito o resultado.

### 15.2 (Opcional, fase 9) Display no ESP32
- Segundo ESP32 (comum) com display OLED SSD1306 (I2C) mostrando a última letra.
- A cada 1 s faz `GET {CENTRAL_URL}/api/signs/latest` e exibe o campo `label`.
- Código Arduino em `firmware/display/display.ino`. Bibliotecas: `Adafruit_SSD1306`, `Adafruit_GFX`, `ArduinoJson`.
- Sem OLED: usar LED que pisca a cada letra recebida (mesmo endpoint).

## 16. Roteiro de demo

1. Dashboard vazio na tela do "atendente".
2. Pessoa faz as letras uma a uma; elas aparecem no texto com confiança.
3. Fazer uma palavra curta usando as letras treinadas, com o gesto de `ESPACO` entre palavras.
4. Clicar em "Falar" e mostrar a voz lendo o texto; clicar em "Limpar".
5. Apresentar as limitações (seção 2), a acessibilidade como objetivo e o próximo passo: sinais com movimento (LSTM) e vocabulário maior, validados com a comunidade surda.

## 17. Riscos e plano B

| Risco | Plano B |
|---|---|
| Acurácia baixa | Mais amostras, de mais pessoas, e menos classes parecidas entre si |
| Modelo funciona na webcam mas não na ESP32-CAM | Recoletar parte do dataset usando a própria ESP32-CAM |
| Letras confundidas entre si | Remover uma das duas letras mais parecidas da lista `CLASSES` |
| Instabilidade (letras piscando) | Subir `CONSECUTIVE_FRAMES` (ex.: 10) e `MIN_CONFIDENCE` (ex.: 0.85) |
| ESP32-CAM instável | Celular com "IP Webcam" ou webcam USB |
| Wi-Fi da faculdade bloqueia dispositivos | Hotspot do celular para tudo |
| Mediapipe não instala | Confirmar Python 3.11 (64 bits) e `pip install --upgrade pip` |
