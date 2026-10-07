/* Almoxarifado Hospitalar — comportamentos da interface */
(function () {
  "use strict";

  // Notificações: exibe os toasts gerados pelo servidor (flash)
  document.querySelectorAll(".toast").forEach(function (el) {
    if (window.bootstrap) bootstrap.Toast.getOrCreateInstance(el).show();
  });

  // Confirmação: <form data-confirmar="Texto" data-confirmar-titulo="..." data-confirmar-botao="...">
  var modalEl = document.getElementById("modalConfirmar");
  var formPendente = null;
  if (modalEl && window.bootstrap) {
    var modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    document.addEventListener("submit", function (ev) {
      var form = ev.target;
      if (!form.dataset || !form.dataset.confirmar || form.dataset.confirmado === "1") return;
      ev.preventDefault();
      formPendente = form;
      modalEl.querySelector("#modalConfirmarTitulo").textContent = form.dataset.confirmarTitulo || "Confirmar ação";
      modalEl.querySelector("[data-confirmar-texto]").textContent = form.dataset.confirmar;
      var ok = modalEl.querySelector("[data-confirmar-ok]");
      ok.textContent = form.dataset.confirmarBotao || "Confirmar";
      ok.className = "btn " + (form.dataset.confirmarEstilo || "btn-perigo");
      modal.show();
    }, true);
    modalEl.querySelector("[data-confirmar-ok]").addEventListener("click", function () {
      if (!formPendente) return;
      formPendente.dataset.confirmado = "1";
      modal.hide();
      formPendente.requestSubmit ? formPendente.requestSubmit() : formPendente.submit();
    });
  }

  // Evita envio duplo (clique repetido no botão salvar)
  document.addEventListener("submit", function (ev) {
    var form = ev.target;
    if (ev.defaultPrevented || form.method.toLowerCase() !== "post") return;
    setTimeout(function () {
      form.querySelectorAll("button[type=submit]").forEach(function (b) { b.disabled = true; });
    }, 0);
  });

  // Mostrar / ocultar senha
  document.querySelectorAll("[data-mostrar-senha]").forEach(function (botao) {
    botao.addEventListener("click", function () {
      var campo = document.getElementById(botao.dataset.mostrarSenha);
      var mostrar = campo.type === "password";
      campo.type = mostrar ? "text" : "password";
      botao.setAttribute("aria-label", mostrar ? "Ocultar senha" : "Mostrar senha");
      botao.querySelector("i").className = mostrar ? "bi bi-eye-slash" : "bi bi-eye";
    });
  });

  // Força da senha (mesmas regras do servidor: 8+ caracteres, letras e números)
  document.querySelectorAll("[data-forca]").forEach(function (campo) {
    var medidor = document.getElementById(campo.dataset.forca);
    campo.addEventListener("input", function () {
      var s = campo.value, nivel = 0;
      if (s.length) nivel = 1;
      if (s.length >= 8 && /[a-zA-Z]/.test(s) && /\d/.test(s)) nivel = 2;
      if (nivel === 2 && s.length >= 10 && /[A-Z]/.test(s) && /[a-z]/.test(s)) nivel = 3;
      if (nivel === 3 && /[^a-zA-Z0-9]/.test(s) && s.length >= 12) nivel = 4;
      medidor.dataset.nivel = nivel;
    });
  });

  // Filtros que se aplicam sozinhos ao mudar (selects e datas)
  document.querySelectorAll("form[data-auto-enviar] select, form[data-auto-enviar] input[type=date]").forEach(function (el) {
    el.addEventListener("change", function () { el.form.submit(); });
  });
})();
