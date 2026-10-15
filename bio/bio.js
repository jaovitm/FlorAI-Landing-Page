/* =========================================================
   FlorAI — /bio
   Detecta o sistema do visitante e redireciona para a loja.
   Sem detecção (desktop etc.) ou sem link configurado, mostra a página.
   ========================================================= */

// Preencha quando o app for publicado. Link vazio = botão "Em breve" e sem redirecionamento.
var STORE_LINKS = {
  android: "https://play.google.com/store/apps/details?id=com.florai",
  ios: ""      // ex.: https://apps.apple.com/app/id0000000000
};

(function () {
  var ua = navigator.userAgent || "";

  function detect() {
    if (/android/i.test(ua)) return "android";
    if (/iphone|ipad|ipod/i.test(ua)) return "ios";
    // iPadOS 13+ se identifica como Mac; o toque denuncia
    if (/macintosh/i.test(ua) && navigator.maxTouchPoints > 1) return "ios";
    return null;
  }

  var params = new URLSearchParams(location.search);
  var stay = params.has("ficar");
  var os = detect();
  var target = os && STORE_LINKS[os];

  if (target && !stay) {
    location.replace(target);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var links = document.querySelectorAll("[data-store]");
    for (var i = 0; i < links.length; i++) {
      var a = links[i];
      var url = STORE_LINKS[a.getAttribute("data-store")];
      if (url) {
        a.href = url;
      } else {
        a.removeAttribute("href");
        a.setAttribute("aria-disabled", "true");
        a.classList.add("is-soon");
        a.querySelector("small").textContent = "Em breve no";
      }
      // Destaca a loja do aparelho quando a página é exibida (ex.: ?ficar=1)
      if (a.getAttribute("data-store") === os) a.classList.add("is-primary");
    }

    if (target && !stay) {
      document.getElementById("bioRedirect").hidden = false;
    }
  });
})();
