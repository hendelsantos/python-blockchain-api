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
};

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
    <div class="balance-item"><span>Saída pendente</span><strong>${formatAmount(wallet.pending_outgoing)}</strong></div>`;
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
    await request(`${API}/transactions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sender: form.get("sender"),
        recipient: form.get("recipient"),
        amount: form.get("amount"),
      }),
    });
    formElement.reset();
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

loadDashboard({ silent: true });
