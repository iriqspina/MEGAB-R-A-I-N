(function () {
  "use strict";

  const input = document.getElementById("input");
  const btnSend = document.getElementById("btn-send");
  const messagesEl = document.getElementById("messages");
  const abaBtns = document.querySelectorAll("#aba-seletor button");
  const chatControls = document.getElementById("chat-controls");
  const modoBtns = document.querySelectorAll("#modo-seletor button");
  const modeloSelect = document.getElementById("modelo-select");
  const composerMeta = document.getElementById("composer-meta");
  const statusDot = document.getElementById("status-dot");
  const btnConfig = document.getElementById("btn-config");
  const configDialog = document.getElementById("config-dialog");
  const vaultDialog = document.getElementById("vault-dialog");
  const vaultForm = document.getElementById("vault-form");
  const vaultMsg = document.getElementById("vault-msg");
  const vaultSenha = document.getElementById("vault-senha");
  const vaultRecovery = document.getElementById("vault-recovery");
  const vaultNova = document.getElementById("vault-nova");
  const vaultRecoveryField = document.getElementById("vault-recovery-field");
  const vaultNovaField = document.getElementById("vault-nova-field");
  const btnVaultForgot = document.getElementById("btn-vault-forgot");

  let vaultMode = "unlock";

  let state = {
    aba: "chat",
    modo: "auto",
    modelo: "auto",
    historico: [],
    providers: [],
    projetos: [],
    conversaId: null,
  };

  function dataHora() {
    return new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  }

  function escapeHtml(str) {
    return str.replace(/[&<>]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c];
    });
  }

  function renderMarkdownLike(text) {
    // Não é parser completo; só quebra linha e deixa ** negrito.
    return escapeHtml(text)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, "<br>");
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function addMessage(role, text, meta, onBoost) {
    const empty = messagesEl.querySelector(".empty-state");
    if (empty) empty.remove();

    const div = document.createElement("div");
    div.className = "message " + role;
    const header = document.createElement("div");
    header.className = "message-header";
    header.innerHTML = "<span>" + (role === "user" ? "Você" : "GerenteNeuron") + " · " + dataHora() + "</span>" +
      (meta ? "<span>" + escapeHtml(meta) + "</span>" : "");
    const body = document.createElement("div");
    body.className = "message-body";
    body.innerHTML = renderMarkdownLike(text);
    div.appendChild(header);
    div.appendChild(body);

    if (role === "assistant" && state.aba === "chat") {
      const actions = document.createElement("div");
      actions.className = "msg-actions";
      if (typeof onBoost === "function") {
        const boostBtn = document.createElement("button");
        boostBtn.className = "boost-btn";
        boostBtn.type = "button";
        boostBtn.textContent = "↑ Reforçar";
        boostBtn.addEventListener("click", onBoost);
        actions.appendChild(boostBtn);
      }
      const up = document.createElement("button");
      up.className = "feedback-btn";
      up.textContent = "👍";
      up.title = "Boa resposta";
      up.addEventListener("click", function () { enviarFeedback(text, 1); });
      const down = document.createElement("button");
      down.className = "feedback-btn";
      down.textContent = "👎";
      down.title = "Resposta fraca";
      down.addEventListener("click", function () { enviarFeedback(text, -1); });
      actions.appendChild(up);
      actions.appendChild(down);
      div.appendChild(actions);
    }

    messagesEl.appendChild(div);
    scrollToBottom();
  }

  async function enviarFeedback(texto, valor) {
    try {
      await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mensagem: texto, feedback: valor }),
      });
    } catch (e) {}
  }

  function addTyping() {
    const empty = messagesEl.querySelector(".empty-state");
    if (empty) empty.remove();
    const div = document.createElement("div");
    div.className = "message assistant typing";
    div.id = "typing";
    div.innerHTML = "<span></span><span></span><span></span>";
    messagesEl.appendChild(div);
    scrollToBottom();
    return div;
  }

  function removeTyping() {
    const t = document.getElementById("typing");
    if (t) t.remove();
  }

  async function carregarModelos() {
    try {
      const res = await fetch("/api/models");
      const data = await res.json();
      state.providers = data.providers || [];
      state.modo = data.modo || "auto";
      atualizarSeletorModelo();
      statusDot.className = "status-dot online";
      statusDot.title = "Online";
    } catch (e) {
      statusDot.className = "status-dot offline";
      statusDot.title = "Offline: " + e.message;
    }
  }

  async function carregarProjetos() {
    try {
      const res = await fetch("/api/projetos");
      const data = await res.json();
      state.projetos = data.projetos || [];
    } catch (e) {
      state.projetos = [];
    }
  }

  async function verificarVault() {
    try {
      const res = await fetch("/api/vault/status");
      const data = await res.json();
      if (data.existe && !data.desbloqueado) {
        vaultDialog.showModal();
      }
    } catch (e) {}
  }

  function resetVaultForm() {
    vaultMode = "unlock";
    vaultMsg.textContent = "O cofre está protegido por senha. Digite a senha mestre para desbloquear.";
    vaultRecoveryField.classList.add("hidden");
    vaultNovaField.classList.add("hidden");
    vaultForm.querySelector("button[type='submit']").textContent = "Desbloquear";
    vaultSenha.value = "";
    vaultRecovery.value = "";
    vaultNova.value = "";
  }

  vaultForm.addEventListener("submit", async function (e) {
    e.preventDefault();
    const senha = vaultSenha.value;
    if (vaultMode === "unlock") {
      try {
        const res = await fetch("/api/vault/unlock", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ senha: senha }),
        });
        const data = await res.json();
        if (data.ok) {
          vaultDialog.close();
          resetVaultForm();
          carregarModelos();
        } else {
          vaultMsg.textContent = "Senha incorreta. Tente novamente.";
        }
      } catch (e) {
        vaultMsg.textContent = "Erro de rede.";
      }
    } else {
      const recovery = vaultRecovery.value;
      const nova = vaultNova.value;
      if (nova.length < 6) {
        vaultMsg.textContent = "Nova senha muito curta (mínimo 6 caracteres).";
        return;
      }
      try {
        const res = await fetch("/api/vault/forgot", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ recovery: recovery, nova_senha: nova }),
        });
        const data = await res.json();
        if (data.ok) {
          vaultMsg.textContent = "Senha redefinida. Nova chave de recuperação gerada em vault/recovery.key";
          vaultMode = "unlock";
          vaultRecoveryField.classList.add("hidden");
          vaultNovaField.classList.add("hidden");
          vaultForm.querySelector("button[type='submit']").textContent = "Desbloquear";
        } else {
          vaultMsg.textContent = "Erro: " + (data.erro || "falha");
        }
      } catch (e) {
        vaultMsg.textContent = "Erro de rede.";
      }
    }
  });

  btnVaultForgot.addEventListener("click", function () {
    vaultMode = "reset";
    vaultMsg.textContent = "Digite a chave de recuperação e a nova senha mestre.";
    vaultRecoveryField.classList.remove("hidden");
    vaultNovaField.classList.remove("hidden");
    vaultForm.querySelector("button[type='submit']").textContent = "Redefinir senha";
  });

  function atualizarSeletorModelo() {
    modeloSelect.innerHTML = "";
    if (state.modo === "auto") {
      const opt = document.createElement("option");
      opt.value = "auto";
      opt.textContent = "Automático";
      modeloSelect.appendChild(opt);
      modeloSelect.disabled = true;
      composerMeta.textContent = "Modo automático · escolha o modelo pelo custo/capacidade";
      return;
    }

    modeloSelect.disabled = false;
    state.providers.forEach(function (p) {
      if (!p.disponivel) return;
      p.modelos.forEach(function (m) {
        const opt = document.createElement("option");
        opt.value = p.id + "/" + m.id;
        opt.textContent = p.nome + " · " + m.nome;
        modeloSelect.appendChild(opt);
      });
    });
    if (modeloSelect.options.length === 0) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "Nenhum provedor configurado";
      modeloSelect.appendChild(opt);
      modeloSelect.disabled = true;
    }
    composerMeta.textContent = "Modo manual · você escolhe o modelo";
  }

  function atualizarAba() {
    abaBtns.forEach(function (b) { b.classList.toggle("active", b.dataset.aba === state.aba); });
    if (state.aba === "gerente") {
      chatControls.classList.add("hidden");
      modeloSelect.disabled = true;
      modeloSelect.innerHTML = "<option>Gerente de projetos</option>";
      composerMeta.textContent = "Modo Gerente · ele escolhe projeto/skill e monta o próximo passo";
    } else {
      chatControls.classList.remove("hidden");
      atualizarSeletorModelo();
    }
  }

  abaBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      state.aba = btn.dataset.aba;
      atualizarAba();
      renderEmptyState();
    });
  });

  modoBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      modoBtns.forEach(function (b) { b.classList.remove("active"); });
      btn.classList.add("active");
      state.modo = btn.dataset.modo;
      atualizarSeletorModelo();
    });
  });

  modeloSelect.addEventListener("change", function () {
    state.modelo = modeloSelect.value;
  });

  function renderEmptyState() {
    if (state.aba === "gerente") {
      messagesEl.innerHTML = "<div class=\"empty-state\"><h1>Gerente de projetos.</h1><p>Mande um pedido geral. O GerenteNeuron identifica o projeto, a intenção e diz qual skill invocar.</p></div>";
    } else {
      messagesEl.innerHTML = "<div class=\"empty-state\"><h1>Um chat para todas as IAs.</h1><p>O GerenteNeuron escolhe o modelo mais barato capaz de responder bem. Você pode trocar quando quiser.</p></div>";
    }
  }

  async function enviar(textoForcado, boost) {
    const texto = (textoForcado || input.value).trim();
    if (!texto) return;
    if (!textoForcado) input.value = "";

    addMessage("user", texto);
    btnSend.disabled = true;
    addTyping();

    try {
      const endpoint = state.aba === "gerente" ? "/api/gerente" : "/api/chat";
      const body = state.aba === "gerente"
        ? { mensagem: texto, historico: state.historico }
        : {
            mensagem: texto,
            modelo: state.modo === "auto" ? "auto" : state.modelo,
            historico: state.historico,
            boost: !!boost,
          };
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      removeTyping();
      const data = await res.json();
      if (res.ok) {
        state.historico.push({ role: "user", content: texto });
        state.historico.push({ role: "assistant", content: data.resposta });
        let meta = null;
        if (state.aba === "chat") {
          meta = data.modelo_usado + " · $" + (data.custo_estimado_usd || 0).toFixed(6) + " · " + (data.estrategia || "auto");
        } else if (data.projeto) {
          meta = data.intencao + " · " + data.projeto.skill;
        } else {
          meta = data.intencao;
        }
        addMessage("assistant", data.resposta, meta, function () {
          enviar(texto, true);
        });
      } else {
        addMessage("assistant", "Erro: " + (data.erro || "falha desconhecida"), "erro");
      }
    } catch (e) {
      removeTyping();
      addMessage("assistant", "Erro de rede: " + e.message, "erro");
    } finally {
      btnSend.disabled = false;
      input.focus();
    }
  }

  btnSend.addEventListener("click", function () { enviar(); });
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      enviar();
    }
  });

  async function carregarTestes() {
    const container = document.getElementById("testes-status");
    container.innerHTML = "<div class='teste-msg'>Testando...</div>";
    try {
      const res = await fetch("/api/testar");
      const data = await res.json();
      const resultados = data.resultados || {};
      const nomes = { openai: "OpenAI (ChatGPT)", anthropic: "Anthropic (Claude)", gemini: "Google Gemini", moonshot: "Moonshot (Kimi)", ollama: "Ollama local" };
      let html = "";
      for (const [id, r] of Object.entries(resultados)) {
        const ok = r.ok;
        const classe = ok ? "teste-ok" : "teste-erro";
        const texto = ok ? "OK" : "Falhou";
        const extra = r.modelos_disponiveis ? ` (${r.modelos_disponiveis} modelos)` : "";
        const erro = r.erro ? `<div class='teste-msg'>${escapeHtml(String(r.erro))}</div>` : "";
        html += `<div class='teste-item'><span>${nomes[id] || id}</span><span class='${classe}'>${texto}${extra}</span></div>${erro}`;
      }
      container.innerHTML = html || "Nenhum teste disponível.";
    } catch (e) {
      container.innerHTML = "<div class='teste-msg'>Erro ao testar: " + escapeHtml(e.message) + "</div>";
    }
  }

  btnConfig.addEventListener("click", function () {
    configDialog.showModal();
    carregarTestes();
  });

  document.getElementById("btn-testar").addEventListener("click", function (e) {
    e.preventDefault();
    carregarTestes();
  });

  configDialog.addEventListener("close", function () {
    if (configDialog.returnValue !== "save") return;
    const campos = configDialog.querySelectorAll("input[data-env]");
    const env = {};
    campos.forEach(function (c) { env[c.dataset.env] = c.value.trim(); });
    fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(env),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.testes) {
          const resultados = data.testes;
          const container = document.getElementById("testes-status");
          const nomes = { openai: "OpenAI (ChatGPT)", anthropic: "Anthropic (Claude)", gemini: "Google Gemini", moonshot: "Moonshot (Kimi)", ollama: "Ollama local" };
          let html = "";
          for (const [id, r] of Object.entries(resultados)) {
            const ok = r.ok;
            const classe = ok ? "teste-ok" : "teste-erro";
            const texto = ok ? "OK" : "Falhou";
            const extra = r.modelos_disponiveis ? ` (${r.modelos_disponiveis} modelos)` : "";
            const erro = r.erro ? `<div class='teste-msg'>${escapeHtml(String(r.erro))}</div>` : "";
            html += `<div class='teste-item'><span>${nomes[id] || id}</span><span class='${classe}'>${texto}${extra}</span></div>${erro}`;
          }
          container.innerHTML = html;
        }
        carregarModelos();
      })
      .catch(function () {});
  });

  document.getElementById("btn-nova").addEventListener("click", function () {
    state.historico = [];
    state.conversaId = null;
    renderEmptyState();
  });

  carregarModelos();
  carregarProjetos();
  atualizarAba();
  verificarVault();
})();
