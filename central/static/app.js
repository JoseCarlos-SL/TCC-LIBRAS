// central/static/app.js
// Lógica do dashboard LibrasLink — WebSocket, fetch, voz, UI

// ============================================================
// CONFIGURAÇÃO — ajuste a chave se necessário
// ============================================================
const API_KEY  = "troque-esta-chave";
const BASE_URL = window.location.origin;
const WS_URL   = `${BASE_URL.replace(/^http/, "ws")}/ws/signs`;

// ============================================================
// Estado da aplicação
// ============================================================
let textoAtual   = "";   // texto formado pelas letras
let ws           = null; // instância do WebSocket
let wsReconTimer = null; // timer de reconexão

// ============================================================
// Referências ao DOM
// ============================================================
const elLetter     = document.getElementById("current-letter");
const elConfBar    = document.getElementById("confidence-bar");
const elConfValue  = document.getElementById("confidence-value");
const elText       = document.getElementById("current-text");
const elHistory    = document.getElementById("history-list");
const elStatus     = document.getElementById("status-indicator");
const elStatusLbl  = document.getElementById("status-label");
const elBtnSpeak   = document.getElementById("btn-speak");
const elBtnClear   = document.getElementById("btn-clear");
const elToast      = document.getElementById("toast");

// ============================================================
// Utilitários
// ============================================================

/** Formata um datetime ISO para hora local legível. */
function formatarHora(iso) {
  const d = new Date(iso);
  return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

/** Exibe um toast de feedback por `ms` milissegundos. */
function mostrarToast(msg, ms = 2500) {
  elToast.textContent = msg;
  elToast.classList.add("show");
  clearTimeout(mostrarToast._timer);
  mostrarToast._timer = setTimeout(() => elToast.classList.remove("show"), ms);
}

/** Atualiza o indicador de status de conexão. */
function setStatus(conectado) {
  elStatus.className = `status-indicator status-indicator--${conectado ? "connected" : "disconnected"}`;
  elStatusLbl.textContent = conectado ? "Conectado" : "Desconectado";
}

/** Dispara a animação de "pop" na letra grande. */
function animarLetra() {
  elLetter.classList.remove("pop");
  // forçar reflow para reiniciar a animação
  void elLetter.offsetWidth;
  elLetter.classList.add("pop");
}

// ============================================================
// Atualização do texto e da letra
// ============================================================

/** Atualiza o painel de texto com o conteúdo atual. */
function renderizarTexto() {
  if (textoAtual === "") {
    elText.innerHTML = '<span class="text-placeholder">Aguardando sinais…</span>';
    elBtnSpeak.disabled = true;
  } else {
    // exibe o texto com cursor piscante no final
    elText.innerHTML =
      `${textoAtual.replace(/&/g,"&amp;").replace(/</g,"&lt;")}` +
      `<span class="text-cursor" aria-hidden="true"></span>`;
    elBtnSpeak.disabled = false;
  }
  // scroll automático até o fim
  elText.scrollTop = elText.scrollHeight;
}

/**
 * Processa um objeto de sinal recebido (via WebSocket ou API):
 * - atualiza a letra gigante e a barra de confiança
 * - concatena ao texto atual
 * - adiciona item ao histórico
 */
function processarSinal(sinal) {
  const { label, confidence, detected_at } = sinal;

  // --- Letra grande ---
  if (label === "ESPACO") {
    elLetter.textContent = "⎵";
  } else {
    elLetter.textContent = label;
  }
  animarLetra();

  // --- Barra de confiança ---
  const pct = Math.round(confidence * 100);
  elConfBar.style.width = `${pct}%`;
  elConfValue.textContent = `${pct}% de confiança`;

  // --- Texto ---
  if (label === "ESPACO") {
    textoAtual += " ";
  } else if (label !== "NENHUM") {
    textoAtual += label;
  }
  renderizarTexto();

  // --- Histórico ---
  adicionarHistorico(sinal);
}

/** Limpa completamente o estado (texto, letra, histórico). */
function limparTudo() {
  textoAtual = "";
  renderizarTexto();

  elLetter.textContent = "—";
  elConfBar.style.width = "0%";
  elConfValue.textContent = "—";

  elHistory.innerHTML = '<li class="history-empty">Nenhum sinal recebido ainda.</li>';
  mostrarToast("Histórico limpo ✓");
}

// ============================================================
// Histórico
// ============================================================

/** Adiciona um item de sinal à lista de histórico (mais recente no topo). */
function adicionarHistorico(sinal) {
  // Remove mensagem de vazio, se existir
  const empty = elHistory.querySelector(".history-empty");
  if (empty) empty.remove();

  const li = document.createElement("li");
  li.className = "history-item";

  const badgeClass = sinal.label === "ESPACO"
    ? "history-item__badge history-item__badge--espaco"
    : "history-item__badge";

  const badgeText = sinal.label === "ESPACO" ? "SPC" : sinal.label;

  li.innerHTML = `
    <span class="${badgeClass}">${badgeText}</span>
    <span class="history-item__time">${formatarHora(sinal.detected_at)}</span>
    <span class="history-item__conf">${Math.round(sinal.confidence * 100)}%</span>
  `;

  // Insere no topo da lista
  elHistory.insertBefore(li, elHistory.firstChild);

  // Limita a 50 itens para não sobrecarregar o DOM
  const itens = elHistory.querySelectorAll(".history-item");
  if (itens.length > 50) {
    itens[itens.length - 1].remove();
  }
}

// ============================================================
// Carregamento inicial via API REST
// ============================================================

/**
 * Busca o histórico de sinais da API e monta o texto atual.
 * A API retorna mais recentes primeiro; invertemos para recriar a ordem cronológica.
 */
async function carregarHistoricoInicial() {
  try {
    const resp = await fetch(`${BASE_URL}/api/signs?limit=200`, {
      headers: { "X-API-Key": API_KEY },
    });
    if (!resp.ok) {
      console.error("Erro ao carregar histórico:", resp.status);
      return;
    }
    const sinais = await resp.json(); // mais recentes primeiro
    const cronologico = [...sinais].reverse();

    textoAtual = "";
    elHistory.innerHTML = "";

    for (const s of cronologico) {
      if (s.label === "ESPACO") {
        textoAtual += " ";
      } else if (s.label !== "NENHUM") {
        textoAtual += s.label;
      }
      adicionarHistorico(s);
    }

    if (sinais.length > 0) {
      const ultimo = sinais[0];
      elLetter.textContent = ultimo.label === "ESPACO" ? "⎵" : ultimo.label;
      const pct = Math.round(ultimo.confidence * 100);
      elConfBar.style.width = `${pct}%`;
      elConfValue.textContent = `${pct}% de confiança`;
    }

    renderizarTexto();
  } catch (err) {
    console.error("Falha ao buscar histórico:", err);
  }
}

// ============================================================
// WebSocket
// ============================================================

/** Abre o WebSocket e configura os handlers; reconexão automática a cada 2 s. */
function conectarWebSocket() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    setStatus(true);
    clearTimeout(wsReconTimer);
    console.log("[WS] Conectado.");
  };

  ws.onmessage = (evt) => {
    let msg;
    try { msg = JSON.parse(evt.data); }
    catch { return; }

    if (msg.type === "new_sign") {
      processarSinal(msg.data);
    } else if (msg.type === "cleared") {
      limparTudo();
    }
  };

  ws.onerror = (err) => {
    console.warn("[WS] Erro:", err);
  };

  ws.onclose = () => {
    setStatus(false);
    console.log("[WS] Conexão encerrada. Reconectando em 2 s…");
    wsReconTimer = setTimeout(conectarWebSocket, 2000);
  };
}

// ============================================================
// Síntese de voz
// ============================================================

/** Lê o texto atual em pt-BR usando a Web Speech API. */
function falar() {
  if (!textoAtual.trim()) return;
  if (!window.speechSynthesis) {
    mostrarToast("Síntese de voz não suportada neste navegador.");
    return;
  }
  window.speechSynthesis.cancel(); // cancela fala anterior
  const utt = new SpeechSynthesisUtterance(textoAtual.trim());
  utt.lang = "pt-BR";
  utt.rate = 0.95;
  window.speechSynthesis.speak(utt);
  mostrarToast("🔊 Lendo o texto…");
}

// ============================================================
// Limpar via API
// ============================================================

/** Envia DELETE /api/signs; a limpeza real ocorre via WS ("cleared"). */
async function limparViaAPI() {
  try {
    const resp = await fetch(`${BASE_URL}/api/signs`, {
      method: "DELETE",
      headers: { "X-API-Key": API_KEY },
    });
    if (resp.status !== 204) {
      mostrarToast("Erro ao limpar. Verifique a API key.");
    }
    // o evento "cleared" via WebSocket vai disparar limparTudo()
  } catch (err) {
    console.error("Erro ao limpar:", err);
    mostrarToast("Sem conexão com a central.");
  }
}

// ============================================================
// Event listeners
// ============================================================

elBtnSpeak.addEventListener("click", falar);
elBtnClear.addEventListener("click", limparViaAPI);

// atalho de teclado: Espaço = Falar, Delete = Limpar
document.addEventListener("keydown", (e) => {
  if (e.target.tagName === "BUTTON") return;
  if (e.key === "F5" || e.key === " ") { e.preventDefault(); falar(); }
  if (e.key === "Delete") { e.preventDefault(); limparViaAPI(); }
});

// ============================================================
// Inicialização
// ============================================================
(async () => {
  setStatus(false);
  await carregarHistoricoInicial();
  conectarWebSocket();
})();
