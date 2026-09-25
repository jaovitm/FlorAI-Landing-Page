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

## Antes de publicar

- Todos os CTAs apontam para `#comecar`; o botão final (`Identificar minha primeira planta`) usa `href="#"`. Substitua pelos links reais (App Store / Google Play / web app).
- As fotografias são carregadas do Unsplash (licença Unsplash). Para produção, considere baixá-las para `assets/` e servi-las localmente.
- Os dados exibidos nos mockups (percentuais de confiança, plantas, datas) são exemplos ilustrativos.
