(function () {
  "use strict";

  const input = document.getElementById("input");
  const btnSend = document.getElementById("btn-send");
  const messagesEl = document.getElementById("messages");
  const modoBtns = document.querySelectorAll("#modo-seletor button");
  const modeloSelect = document.getElementById("modelo-select");
  const composerMeta = document.getElementById("composer-meta");
  const statusDot = document.getElementById("status-dot");
  const btnConfig = document.getElementById("btn-config");
  const configDialog = document.getElementById("config-dialog");

  let state = {
    modo: "auto",
    modelo: "auto",
    historico: [],
    providers: [],
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

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function addMessage(role, text, meta) {
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
    body.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
    div.appendChild(header);
    div.appendChild(body);
    messagesEl.appendChild(div);
    scrollToBottom();
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

  async function enviar() {
    const texto = input.value.trim();
    if (!texto) return;

    addMessage("user", texto);
    input.value = "";
    btnSend.disabled = true;
    addTyping();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mensagem: texto,
          modelo: state.modo === "auto" ? "auto" : state.modelo,
          historico: state.historico,
        }),
      });
      removeTyping();
      const data = await res.json();
      if (res.ok) {
        state.historico.push({ role: "user", content: texto });
        state.historico.push({ role: "assistant", content: data.resposta });
        const meta = data.modelo_usado + " · $" + (data.custo_estimado_usd || 0).toFixed(6);
        addMessage("assistant", data.resposta, meta);
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

  btnSend.addEventListener("click", enviar);
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      enviar();
    }
  });

  btnConfig.addEventListener("click", function () {
    configDialog.showModal();
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
    }).catch(function () {});
  });

  document.getElementById("btn-nova").addEventListener("click", function () {
    state.historico = [];
    state.conversaId = null;
    messagesEl.innerHTML = "<div class=\"empty-state\"><h1>Um chat para todas as IAs.</h1><p>O GerenteNeuron escolhe o modelo mais barato capaz de responder bem. Você pode trocar quando quiser.</p></div>";
  });

  carregarModelos();
})();
