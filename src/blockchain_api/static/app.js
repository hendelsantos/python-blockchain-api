const API = "/api/v1";

const elements = {
  blocks: document.querySelector("#stat-blocks"),
  pending: document.querySelector("#stat-pending"),
  valid: document.querySelector("#stat-valid"),
  nonce: document.querySelector("#stat-nonce"),
  heroBlock: document.querySelector("#hero-block-number"),
  chain: document.querySelector("#chain-container"),
  transactionForm: document.querySelector("#transaction-form"),
  miningForm: document.querySelector("#mining-form"),
  refreshButton: document.querySelector("#refresh-button"),
  toast: document.querySelector("#toast"),
  walletForm: document.querySelector("#wallet-form"),
  walletResult: document.querySelector("#wallet-result"),
  walletList: document.querySelector("#wallet-list"),
  walletCount: document.querySelector("#wallet-count"),
  generateWalletButton: document.querySelector("#generate-wallet"),
  activeWallet: document.querySelector("#active-wallet"),
  senderInput: document.querySelector("#sender-input"),
  minerInput: document.querySelector("#miner-input"),
  realtimeStatus: document.querySelector("#realtime-status"),
  peerForm: document.querySelector("#peer-form"),
  peerList: document.querySelector("#peer-list"),
  peerCount: document.querySelector("#peer-count"),
  nodeId: document.querySelector("#node-id"),
  discoverPeers: document.querySelector("#discover-peers"),
  resolveConsensus: document.querySelector("#resolve-consensus"),
  networkSecurity: document.querySelector("#network-security"),
  traceabilityForm: document.querySelector("#traceability-form"),
  traceabilityResult: document.querySelector("#traceability-result"),
};

const SESSION_WALLETS_KEY = "chainlab.ed25519.wallets";

function getSessionWallets() {
  try {
    return JSON.parse(sessionStorage.getItem(SESSION_WALLETS_KEY) || "{}");
  } catch {
    return {};
  }
}

function bytesToBase64(bytes) {
  let binary = "";
  bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
  return btoa(binary);
}

function base64ToBytes(value) {
  return Uint8Array.from(atob(value), (character) => character.charCodeAt(0));
}

function bytesToHex(bytes) {
  return [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function canonicalTransactionPayload({ sender, recipient, amount, nonce }) {
  return JSON.stringify({ amount: String(amount), nonce, recipient, sender });
}

async function generateBrowserWallet() {
  const keyPair = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
  const publicRaw = new Uint8Array(await crypto.subtle.exportKey("raw", keyPair.publicKey));
  const privatePkcs8 = new Uint8Array(await crypto.subtle.exportKey("pkcs8", keyPair.privateKey));
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", publicRaw));
  return {
    address: bytesToHex(digest).slice(0, 40),
    publicKey: bytesToBase64(publicRaw),
    privateKey: bytesToBase64(privatePkcs8),
  };
}

async function signBrowserTransaction(wallet, transaction) {
  const privateKey = await crypto.subtle.importKey(
    "pkcs8",
    base64ToBytes(wallet.privateKey),
    { name: "Ed25519" },
    false,
    ["sign"],
  );
  const payload = new TextEncoder().encode(canonicalTransactionPayload(transaction));
  return bytesToBase64(new Uint8Array(await crypto.subtle.sign("Ed25519", privateKey, payload)));
}

function activateWallet(wallet) {
  elements.activeWallet.textContent = `Ativa: ${wallet.address}`;
  elements.activeWallet.title = wallet.address;
  elements.senderInput.value = wallet.address;
  elements.minerInput.value = wallet.address;
  elements.walletForm.elements.address.value = wallet.address;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function request(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((item) => item.msg).join(", ")
      : data.detail;
    throw new Error(detail || "Não foi possível concluir a operação.");
  }
  return data;
}

function showToast(message, type = "success") {
  elements.toast.textContent = message;
  elements.toast.className = `toast show ${type === "error" ? "error" : ""}`;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    elements.toast.classList.remove("show");
  }, 3600);
}

function shortHash(hash) {
  if (!hash) return "—";
  return `${hash.slice(0, 16)}…${hash.slice(-10)}`;
}

function formatTimestamp(value) {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(new Date(value));
}

function formatAmount(value) {
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 8,
  }).format(Number(value));
}

function renderWalletBalance(wallet) {
  elements.walletResult.classList.remove("empty-wallet");
  elements.walletResult.innerHTML = `
    <div class="balance-item"><span>Confirmado</span><strong>${formatAmount(wallet.confirmed)}</strong></div>
    <div class="balance-item"><span>Disponível</span><strong>${formatAmount(wallet.available)}</strong></div>
    <div class="balance-item"><span>Saída pendente</span><strong>${formatAmount(wallet.pending_outgoing)}</strong></div>
    <div class="balance-item"><span>Próximo nonce</span><strong>${wallet.next_nonce}</strong></div>`;
}

function renderWallets(wallets) {
  elements.walletCount.textContent = wallets.length;
  if (!wallets.length) {
    elements.walletList.innerHTML = '<div class="empty-wallet">Nenhuma carteira minerou tokens ainda.</div>';
    return;
  }
  elements.walletList.innerHTML = wallets.map((wallet) => `
    <div class="wallet-row">
      <span class="wallet-address" title="${escapeHtml(wallet.address)}">${escapeHtml(wallet.address)}</span>
      <span class="wallet-balance"><span>Confirmado</span><strong>${formatAmount(wallet.confirmed)}</strong></span>
      <span class="wallet-balance"><span>Disponível</span><strong>${formatAmount(wallet.available)}</strong></span>
    </div>`).join("");
}

function renderNetwork(network) {
  elements.nodeId.textContent = network.node_id;
  elements.nodeId.title = network.node_id;
  elements.peerCount.textContent = `${network.peer_count} peer${network.peer_count === 1 ? "" : "s"}`;
  elements.peerList.innerHTML = network.peers.length
    ? network.peers.map((peer) => `<div class="peer-row">${escapeHtml(peer)}</div>`).join("")
    : '<div class="empty-wallet">Nenhum peer registrado.</div>';
  elements.networkSecurity.textContent = network.authentication_enabled
    ? "Comunicação entre nós autenticada por HMAC"
    : "Autenticação entre nós desativada";
}

async function loadNetwork() {
  try {
    renderNetwork(await request(`${API}/nodes`));
  } catch (error) {
    showToast(error.message, "error");
  }
}

function connectRealtime() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${location.host}/ws/blocks`);
  socket.addEventListener("open", () => {
    elements.realtimeStatus.textContent = "REDE EM TEMPO REAL";
  });
  socket.addEventListener("message", () => {
    loadDashboard({ silent: true });
    loadNetwork();
  });
  socket.addEventListener("close", () => {
    elements.realtimeStatus.textContent = "RECONECTANDO À REDE";
    window.setTimeout(connectRealtime, 2000);
  });
}

function renderChain(chain) {
  if (!chain.length) {
    elements.chain.innerHTML = '<div class="empty-state">Nenhum bloco encontrado.</div>';
    return;
  }

  elements.chain.innerHTML = [...chain].reverse().map((block, position) => {
    const transactions = block.transactions.length
      ? block.transactions.map((transaction) => `
          <span class="transaction-chip">
            ${escapeHtml(transaction.sender)} → ${escapeHtml(transaction.recipient)} · ${escapeHtml(transaction.amount)}
            ${transaction.signature ? '<span class="signature-mark" title="Assinatura Ed25519 verificada">✓ assinada</span>' : ""}
          </span>`).join("")
      : '<span class="transaction-chip">Bloco gênesis</span>';

    return `
      <article class="block-card" style="animation-delay:${position * 45}ms">
        <div class="block-index"><span>BLOCO</span><strong>#${String(block.index).padStart(3, "0")}</strong></div>
        <div class="block-details">
          <div class="hash-row"><span>HASH</span><code title="${escapeHtml(block.hash)}">${shortHash(block.hash)}</code></div>
          <div class="hash-row"><span>ANTERIOR</span><code title="${escapeHtml(block.previous_hash)}">${shortHash(block.previous_hash)}</code></div>
          <div class="transaction-chips">${transactions}</div>
        </div>
        <div class="block-meta">
          <strong>nonce ${block.nonce.toLocaleString("pt-BR")}</strong>
          <span>${formatTimestamp(block.timestamp)}</span>
          <span>${block.transactions.length} transação(ões)</span>
        </div>
      </article>`;
  }).join("");
}

async function loadDashboard({ silent = false } = {}) {
  elements.refreshButton.disabled = true;
  try {
    const [chainData, pendingData, validationData, walletData] = await Promise.all([
      request(`${API}/chain`),
      request(`${API}/transactions/pending`),
      request(`${API}/chain/validate`),
      request(`${API}/wallets`),
    ]);
    const lastBlock = chainData.chain.at(-1);
    elements.blocks.textContent = chainData.length;
    elements.pending.textContent = pendingData.count;
    elements.valid.textContent = validationData.valid ? "Cadeia válida" : "Cadeia inválida";
    elements.valid.style.color = validationData.valid ? "var(--green)" : "var(--danger)";
    elements.nonce.textContent = lastBlock?.nonce?.toLocaleString("pt-BR") ?? "—";
    elements.heroBlock.textContent = `#${String(lastBlock?.index ?? 0).padStart(3, "0")}`;
    renderChain(chainData.chain);
    renderWallets(walletData.wallets);
    if (!silent) showToast("Dados da blockchain atualizados.");
  } catch (error) {
    elements.chain.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
    showToast(error.message, "error");
  } finally {
    elements.refreshButton.disabled = false;
  }
}

elements.transactionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formElement = event.currentTarget;
  const button = formElement.querySelector('button[type="submit"]');
  const form = new FormData(formElement);
  button.disabled = true;
  try {
    const wallets = getSessionWallets();
    const wallet = wallets[form.get("sender")];
    if (!wallet) {
      throw new Error("Gere ou recupere a carteira do remetente nesta aba.");
    }
    const balance = await request(`${API}/wallets/${encodeURIComponent(wallet.address)}/balance`);
    const transaction = {
      sender: wallet.address,
      recipient: form.get("recipient"),
      amount: form.get("amount"),
      nonce: balance.next_nonce,
    };
    const signature = await signBrowserTransaction(wallet, transaction);
    await request(`${API}/transactions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...transaction,
        public_key: wallet.publicKey,
        signature,
      }),
    });
    formElement.reset();
    elements.senderInput.value = wallet.address;
    showToast("Transação adicionada ao próximo bloco.");
    await loadDashboard({ silent: true });
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    button.disabled = false;
  }
});

elements.miningForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formElement = event.currentTarget;
  const button = formElement.querySelector('button[type="submit"]');
  const miner = new FormData(formElement).get("miner");
  button.disabled = true;
  button.textContent = "Minerando…";
  try {
    const result = await request(`${API}/mine/${encodeURIComponent(miner)}`, { method: "POST" });
    showToast(`Bloco #${result.block.index} minerado com nonce ${result.block.nonce}.`);
    await loadDashboard({ silent: true });
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    button.disabled = false;
    button.innerHTML = '<span class="pickaxe">◆</span> Iniciar mineração';
  }
});

elements.refreshButton.addEventListener("click", () => loadDashboard());

elements.generateWalletButton.addEventListener("click", async () => {
  elements.generateWalletButton.disabled = true;
  try {
    const wallet = await generateBrowserWallet();
    const wallets = getSessionWallets();
    wallets[wallet.address] = wallet;
    sessionStorage.setItem(SESSION_WALLETS_KEY, JSON.stringify(wallets));
    activateWallet(wallet);
    showToast("Carteira Ed25519 criada. Minere um bloco para receber o primeiro token.");
  } catch (error) {
    showToast(`Não foi possível gerar a carteira: ${error.message}`, "error");
  } finally {
    elements.generateWalletButton.disabled = false;
  }
});

elements.walletForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const address = new FormData(event.currentTarget).get("address");
  try {
    const wallet = await request(`${API}/wallets/${encodeURIComponent(address)}/balance`);
    renderWalletBalance(wallet);
  } catch (error) {
    showToast(error.message, "error");
  }
});

elements.traceabilityForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const code = new FormData(event.currentTarget).get("batch_code");
  try {
    const trace = await request(`${API}/traceability/public/${encodeURIComponent(code)}`);
    const events = trace.events.map((item) => `
      <li><strong>${escapeHtml(item.event_type)}</strong> · ${escapeHtml(item.location)}
        <span>bloco #${item.block_index} · ${escapeHtml(item.event_hash.slice(0, 14))}…</span>
      </li>`).join("");
    elements.traceabilityResult.classList.remove("empty-wallet");
    elements.traceabilityResult.innerHTML = `
      <div class="trace-title"><strong>${escapeHtml(trace.product.name)}</strong><span>${escapeHtml(trace.batch.code)}</span></div>
      <p>Origem: ${escapeHtml(trace.company.name)}</p>
      <ul>${events || "<li>Nenhum evento registrado.</li>"}</ul>`;
  } catch (error) {
    elements.traceabilityResult.className = "traceability-result empty-wallet";
    elements.traceabilityResult.textContent = error.message;
  }
});

elements.peerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const url = new FormData(form).get("url");
  try {
    await request(`${API}/nodes/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ urls: [url] }),
    });
    form.reset();
    await loadNetwork();
    showToast("Peer registrado no nó atual.");
  } catch (error) {
    showToast(error.message, "error");
  }
});

elements.resolveConsensus.addEventListener("click", async () => {
  elements.resolveConsensus.disabled = true;
  try {
    const result = await request(`${API}/nodes/resolve`, { method: "POST" });
    await loadDashboard({ silent: true });
    showToast(result.replaced
      ? `Cadeia substituída pela cópia de ${result.source}.`
      : "A cadeia local já é a melhor disponível.");
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    elements.resolveConsensus.disabled = false;
  }
});

elements.discoverPeers.addEventListener("click", async () => {
  elements.discoverPeers.disabled = true;
  try {
    const result = await request(`${API}/nodes/discover`, { method: "POST" });
    await loadNetwork();
    showToast(result.discovered.length
      ? `${result.discovered.length} novo(s) peer(s) descoberto(s).`
      : "Nenhum novo peer foi encontrado.");
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    elements.discoverPeers.disabled = false;
  }
});

loadDashboard({ silent: true });
loadNetwork();
connectRealtime();

const restoredWallets = Object.values(getSessionWallets());
if (restoredWallets.length) activateWallet(restoredWallets.at(-1));
