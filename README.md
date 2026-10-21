# FlorAI — Landing page

Landing page estática (HTML + CSS + JS, sem build) do FlorAI, app de identificação e cuidado de plantas com IA.

## Rodar localmente

```bash
python -m http.server 5173
```

Abra http://localhost:5173.

## Estrutura

- `index.html` — conteúdo e mockups do app (construídos em HTML/CSS, escaláveis via container queries)
- `styles.css` — identidade visual, layout e animações
- `main.js` — navegação, animações de scroll, parallax e demo interativa de identificação
- `assets/favicon.svg`
- `guia/` — guias de cuidados de plantas (`/guia/` e `/guia/<planta>/`). **Gerados**: edite `ferramentas/plantas.json` (guias por planta) ou `ferramentas/artigos.json` (dicas, pragas e comparativos de apps; aceita `**negrito**`, `*itálico*` e links `[texto](guia:slug)` / `[texto](play)`) e rode `python ferramentas/gerar_guias.py`, que reescreve as páginas, o `sitemap.xml` e o `llms.txt`. Estilos em `guia/guia.css`.
- `robots.txt`, `sitemap.xml`, `llms.txt` — descoberta por buscadores e assistentes de IA.
- `<chave>.txt` na raiz + `ferramentas/indexnow.py` — IndexNow. Depois de publicar páginas novas, rode `python ferramentas/indexnow.py` para avisar Bing/Yandex (o Bing alimenta a busca do ChatGPT). Não apague o arquivo da chave.
- `bio/` — página de links (`/bio`) para a bio das redes sociais; redireciona Android → Google Play e iPhone/iPad → App Store. Links em `bio/bio.js` (`STORE_LINKS`); `/bio/?ficar=1` exibe a página sem redirecionar.

## Antes de publicar

- Todos os CTAs apontam para `#comecar`; o botão final (`Identificar minha primeira planta`) usa `href="#"`. Substitua pelos links reais (App Store / Google Play / web app).
- As fotografias são carregadas do Unsplash (licença Unsplash). Para produção, considere baixá-las para `assets/` e servi-las localmente.
- Os dados exibidos nos mockups (percentuais de confiança, plantas, datas) são exemplos ilustrativos.
