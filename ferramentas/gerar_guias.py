"""
FlorAI — gerador dos guias de cuidados.

Lê ferramentas/plantas.json e escreve páginas estáticas:
  guia/index.html, guia/<slug>/index.html, sitemap.xml e llms.txt

Uso (na raiz do repositório):
  python ferramentas/gerar_guias.py
"""

import json
import re
import unicodedata
from html import escape
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SITE = "https://florai.cc"
PLAY = "https://play.google.com/store/apps/details?id=com.florai"
ASPCA = "https://www.aspca.org/pet-care/animal-poison-control/toxic-and-non-toxic-plants"

# Frase de entidade: repetida de forma idêntica nas páginas para que buscadores
# e modelos de IA associem o FlorAI sempre aos mesmos fatos.
ENTIDADE = (
    "O FlorAI é um aplicativo brasileiro para Android que identifica plantas por foto "
    "com inteligência artificial e mostra como cuidar de cada uma: luz, rega, temperatura e solo. "
    "O plano gratuito inclui 3 identificações por dia; os planos pagos adicionam mais identificações, "
    "mais plantas salvas e lembretes de rega."
)

SLUGS = set()  # todos os slugs publicados em /guia/, preenchido em main()

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]

REGIOES = [
    ("sul", "Sul", "Porto Alegre, Curitiba, Florianópolis"),
    ("sudeste", "Sudeste", "São Paulo, Rio de Janeiro, Belo Horizonte"),
    ("nordeste_norte", "Nordeste e Norte", "Salvador, Recife, Fortaleza, Belém, Manaus"),
    ("centro_oeste", "Centro-Oeste", "Brasília, Goiânia, Cuiabá"),
]

ICONES = """<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <defs>
    <symbol id="i-leaf" viewBox="0 0 24 24"><path d="M5 19c0-8 5-14 15-14 0 10-6 15-14 15"/><path d="M5 19c3-4 6-7 10-9"/></symbol>
    <symbol id="i-camera" viewBox="0 0 24 24"><path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/></symbol>
    <symbol id="i-drop" viewBox="0 0 24 24"><path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/></symbol>
    <symbol id="i-sun" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></symbol>
    <symbol id="i-pot" viewBox="0 0 24 24"><path d="M5 11h14l-2 9H7z"/><path d="M12 11V7m0 0c0-2 2-3.5 4.5-3.5 0 2-2 3.5-4.5 3.5zm0 0c0-2-2-3.5-4.5-3.5 0 2 2 3.5 4.5 3.5z"/></symbol>
    <symbol id="i-bell" viewBox="0 0 24 24"><path d="M6 16v-5a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0"/></symbol>
    <symbol id="i-chev" viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></symbol>
  </defs>
</svg>"""


# ---------------------------------------------------------------- texto

def data_extenso(iso):
    a, m, d = iso.split("-")
    return f"{int(d)} de {MESES[int(m) - 1]} de {a}"


def cap(s):
    return s[0].upper() + s[1:]


class Gram:
    """Concordância de artigo, preposição e verbo com o nome da planta."""

    def __init__(self, p):
        f, pl = p["genero"] == "f", p["plural"]
        s = "s" if pl else ""
        self.art = ("a" if f else "o") + s
        self.de = "d" + self.art
        self.e = "são" if pl else "é"
        self.precisa = "precisam" if pl else "precisa"
        self.toxica = "tóxic" + ("a" if f else "o") + s
        self.nome = p["nome"]
        self.o_nome = f"{self.art} {self.nome}"
        self.do_nome = f"{self.de} {self.nome}"


def perguntas(p):
    g = Gram(p)
    return {
        "rega": f"Quando regar {g.o_nome}?",
        "luz": f"Quanta luz {g.o_nome} {g.precisa}?",
        "adubo": f"Como adubar {g.o_nome}?",
        "substrato": f"Qual o melhor substrato e vaso para {g.o_nome}?",
        "regioes": f"Cuidados {g.do_nome} por região do Brasil",
        "problemas": f"Problemas comuns {g.do_nome} e como resolver",
        "pets": f"{cap(g.o_nome)} {g.e} {g.toxica} para gatos e cachorros?",
        "muda": f"Como fazer muda {g.do_nome}",
        "faq": "Outras perguntas frequentes",
    }


def sci_curto(p):
    return p["cientifico"].split(" (")[0]


LINK = re.compile(r"\[([^\]]+)\]\(([^)]*)\)")
NEGRITO = re.compile(r"\*\*(.+?)\*\*")
ITALICO = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")


def destino(alvo, raiz_guia):
    """guia:slug → página do guia; guia: → índice; play → Google Play."""
    if alvo == "play":
        return PLAY
    if alvo.startswith("guia:"):
        slug = alvo[5:]
        if slug and slug not in SLUGS:
            raise SystemExit(f"link para guia inexistente: {slug}")
        return f"{raiz_guia}{slug}/" if slug else raiz_guia
    return alvo


def inline(texto, raiz_guia="../"):
    """Texto dos JSONs → HTML: **negrito**, *itálico* e [texto](guia:slug)."""
    s = escape(texto, quote=False)
    s = LINK.sub(lambda m: f'<a href="{escape(destino(m.group(2), raiz_guia))}">{m.group(1)}</a>', s)
    s = NEGRITO.sub(r"<strong>\1</strong>", s)
    return ITALICO.sub(r"<em>\1</em>", s)


def texto_puro(texto):
    s = LINK.sub(r"\1", texto)
    return NEGRITO.sub(r"\1", ITALICO.sub(r"\1", s))


def jsonld(obj):
    txt = json.dumps(obj, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return f'<script type="application/ld+json">\n{txt}\n</script>'


# ---------------------------------------------------------------- moldura

def cabecalho(titulo, descricao, url, raiz, extra=""):
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(titulo)}</title>
  <meta name="description" content="{escape(descricao)}" />
  <meta name="theme-color" content="#070b09" />
  <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large" />
  <link rel="canonical" href="{url}" />
  <meta property="og:type" content="article" />
  <meta property="og:locale" content="pt_BR" />
  <meta property="og:site_name" content="FlorAI" />
  <meta property="og:title" content="{escape(titulo)}" />
  <meta property="og:description" content="{escape(descricao)}" />
  <meta property="og:url" content="{url}" />
  <link rel="icon" href="{raiz}assets/favicon.svg" type="image/svg+xml" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Inter+Tight:wght@500;600;700&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="{raiz}styles.css" />
  <link rel="stylesheet" href="{raiz}guia/guia.css" />
{extra}
</head>
<body>

{ICONES}

<header class="nav page-nav">
  <div class="nav__inner container">
    <a class="brand" href="{raiz}" aria-label="FlorAI — início">
      <span class="brand__mark"><svg class="i"><use href="#i-leaf"/></svg></span>
      <span class="brand__name">Flor<span>AI</span></span>
    </a>
    <nav class="page-nav__right" aria-label="Principal">
      <a class="page-nav__link" href="{raiz}guia/">Guias de plantas</a>
      <a class="btn btn--primary btn--sm" href="{PLAY}">Baixar o app</a>
    </nav>
  </div>
</header>
"""


def rodape(raiz):
    return f"""
<footer class="footer">
  <div class="container footer__inner">
    <a class="brand" href="{raiz}" aria-label="FlorAI — início">
      <span class="brand__mark"><svg class="i"><use href="#i-leaf"/></svg></span>
      <span class="brand__name">Flor<span>AI</span></span>
    </a>
    <nav class="footer__links" aria-label="Rodapé">
      <a href="{raiz}">Início</a>
      <a href="{raiz}guia/">Guias de plantas</a>
      <a href="{PLAY}">Google Play</a>
      <a href="{raiz}termos.html">Termos de Uso</a>
      <a href="{raiz}privacidade.html">Privacidade</a>
    </nav>
    <p class="footer__copy">© 2026 FlorAI.</p>
  </div>
</footer>

</body>
</html>
"""


def cta_final(titulo, raiz):
    return f"""
    <aside class="cta-card" aria-label="Aplicativo FlorAI">
      <span class="cta-card__icon"><svg class="i"><use href="#i-camera"/></svg></span>
      <h2>{escape(titulo)}</h2>
      <p>{escape(ENTIDADE)}</p>
      <div class="cta-card__actions">
        <a class="btn btn--primary" href="{PLAY}">Baixar grátis no Google Play</a>
        <a class="btn btn--ghost" href="{raiz}#como-funciona">Ver como funciona</a>
      </div>
    </aside>"""


# ---------------------------------------------------------------- guia de uma planta

def pagina_planta(p, por_slug, atualizado):
    g = Gram(p)
    q = perguntas(p)
    raiz = "../../"
    url = f"{SITE}/guia/{p['slug']}/"
    nome_cap = cap(p["nome"])
    titulo = f"{nome_cap}: como cuidar, quando regar e adubar | FlorAI"
    descricao = (f"Quando regar, quanta luz e como adubar {g.o_nome} ({sci_curto(p)}). "
                 f"Resposta rápida, problemas comuns e cuidados por região do Brasil.")
    r = p["resumo"]

    faq_schema = [
        (q["rega"], p["rega"]["resposta"]),
        (q["luz"], p["luz"]["resposta"]),
        (q["adubo"], p["adubo"]["resposta"]),
        (q["substrato"], p["substrato"]),
        (q["pets"], p["pets"]),
        (q["muda"] + "?", p["muda"]),
    ] + [tuple(f) for f in p["faqs"]]

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "@id": url + "#artigo",
                "headline": f"Como cuidar {g.do_nome}: quando regar, luz e adubo",
                "description": descricao,
                "inLanguage": "pt-BR",
                "datePublished": atualizado,
                "dateModified": atualizado,
                "mainEntityOfPage": url,
                "author": {"@id": SITE + "/#organizacao"},
                "publisher": {"@id": SITE + "/#organizacao"},
                "about": {
                    "@type": "Thing",
                    "name": nome_cap,
                    "alternateName": [sci_curto(p)] + p["outros_nomes"],
                },
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Início", "item": SITE + "/"},
                    {"@type": "ListItem", "position": 2, "name": "Guias de plantas", "item": SITE + "/guia/"},
                    {"@type": "ListItem", "position": 3, "name": nome_cap, "item": url},
                ],
            },
            {
                "@type": "FAQPage",
                "@id": url + "#faq",
                "mainEntity": [
                    {"@type": "Question", "name": pq,
                     "acceptedAnswer": {"@type": "Answer", "text": rs}}
                    for pq, rs in faq_schema
                ],
            },
            {
                "@type": "Organization",
                "@id": SITE + "/#organizacao",
                "name": "FlorAI",
                "url": SITE + "/",
            },
        ],
    }

    apelidos = ""
    if p["outros_nomes"]:
        chamada = "chamad" + ("a" if p["genero"] == "f" else "o") + ("s" if p["plural"] else "")
        apelidos = f" · também {chamada} de {escape(', '.join(p['outros_nomes']))}"
    resumo_itens = [
        ("i-drop", "Rega", r["rega"]),
        ("i-sun", "Luz", r["luz"]),
        ("i-pot", "Adubo", r["adubo"]),
        ("i-leaf", "Dificuldade", r["dificuldade"]),
        ("i-leaf", "Pets", r["pets"]),
    ]
    resumo_html = "\n".join(
        f'        <div><dt><svg class="i"><use href="#{ic}"/></svg> {rot}</dt><dd>{escape(v)}</dd></div>'
        for ic, rot, v in resumo_itens
    )

    problemas_html = "\n".join(
        f"""        <li>
          <h3>{escape(s)}</h3>
          <p><span>Causa provável:</span> {escape(c)}</p>
          <p><span>O que fazer:</span> {escape(f)}</p>
        </li>"""
        for s, c, f in p["problemas"]
    )

    regioes_html = "\n".join(
        f"""        <div>
          <dt>{rot} <small>{cidades}</small></dt>
          <dd>{escape(p['clima'][chave])}</dd>
        </div>"""
        for chave, rot, cidades in REGIOES
    )

    faqs_html = "\n".join(
        f"      <h3>{escape(pq)}</h3>\n      <p>{escape(rs)}</p>" for pq, rs in p["faqs"]
    )

    relacionadas_html = "\n".join(
        f"""      <li><a href="../{s}/"><b>{escape(cap(por_slug[s]['nome']))}</b><span>{escape(sci_curto(por_slug[s]))}</span><svg class="i"><use href="#i-chev"/></svg></a></li>"""
        for s in p["relacionadas"]
    )

    corpo = f"""
<main class="guide">
  <article class="container guide__wrap">
    <nav class="crumbs" aria-label="Você está em">
      <a href="{raiz}">Início</a><span aria-hidden="true">›</span><a href="../">Guias de plantas</a><span aria-hidden="true">›</span><span aria-current="page">{escape(nome_cap)}</span>
    </nav>

    <header class="guide__head">
      <p class="eyebrow">Guia de cuidados</p>
      <h1 class="h2">Como cuidar {escape(g.do_nome)}</h1>
      <p class="guide__sci"><em>{escape(p['cientifico'])}</em> · {escape(p['familia'])} · origem: {escape(p['origem'])}{apelidos}</p>
      <p class="guide__meta">Atualizado em {data_extenso(atualizado)} · Equipe FlorAI</p>
      <p class="guide__intro">{escape(p['intro'])}</p>
    </header>

    <section class="quick" aria-labelledby="resumo">
      <h2 id="resumo">Resposta rápida</h2>
      <dl>
{resumo_html}
      </dl>
    </section>

    <aside class="id-callout">
      <svg class="i"><use href="#i-camera"/></svg>
      <p><b>Não tem certeza da espécie?</b> Cuidados que funcionam para {escape(g.o_nome)} podem prejudicar uma planta parecida. Tire uma foto no FlorAI: a IA identifica a planta em segundos e mostra os cuidados certos para ela.</p>
      <a class="btn btn--ghost btn--sm" href="{PLAY}">Identificar pela foto</a>
    </aside>

    <div class="guide__body">
    <section id="rega">
      <h2>{escape(q['rega'])}</h2>
      <p class="answer">{escape(p['rega']['resposta'])}</p>
      <h3>Como saber se precisa de água</h3>
      <p>{escape(p['rega']['como_saber'])}</p>
      <h3>Sinais de rega errada</h3>
      <ul>
        <li><strong>Água demais:</strong> {escape(p['rega']['excesso'])}</li>
        <li><strong>Água de menos:</strong> {escape(p['rega']['falta'])}</li>
      </ul>
      <p class="tip"><svg class="i"><use href="#i-bell"/></svg> <span>Para não depender da memória, salve {escape(g.o_nome)} na sua coleção do FlorAI: o app mostra os cuidados da espécie e, nos planos pagos, avisa quando chegar a hora de regar.</span></p>
    </section>

    <section id="luz">
      <h2>{escape(q['luz'])}</h2>
      <p class="answer">{escape(p['luz']['resposta'])}</p>
      <p>{escape(p['luz']['detalhes'])}</p>
    </section>

    <section id="adubo">
      <h2>{escape(q['adubo'])}</h2>
      <p class="answer">{escape(p['adubo']['resposta'])}</p>
      <p>{escape(p['adubo']['detalhes'])}</p>
    </section>

    <section id="substrato">
      <h2>{escape(q['substrato'])}</h2>
      <p class="answer">{escape(p['substrato'])}</p>
      <p>{escape(p['vaso'])}</p>
    </section>

    <section id="regioes">
      <h2>{escape(q['regioes'])}</h2>
      <p>{escape(p['temperatura'])}</p>
      <dl class="regions">
{regioes_html}
      </dl>
    </section>

    <section id="problemas">
      <h2>{escape(q['problemas'])}</h2>
      <ul class="problems">
{problemas_html}
      </ul>
    </section>

    <section id="pets">
      <h2>{escape(q['pets'])}</h2>
      <p class="answer">{escape(p['pets'])}</p>
      <p class="fine">Em caso de ingestão, procure um veterinário. Para pessoas, ligue para o Disque-Intoxicação: 0800 722 6001.</p>
    </section>

    <section id="muda">
      <h2>{escape(q['muda'])}</h2>
      <p>{escape(p['muda'])}</p>
    </section>

    <section id="faq">
      <h2>{escape(q['faq'])}</h2>
{faqs_html}
    </section>

    <section id="referencias" class="refs">
      <h2>Referências</h2>
      <p>Toxicidade para animais conforme a lista de plantas tóxicas e não tóxicas da <a href="{ASPCA}" rel="noopener">ASPCA</a>. Frequências de rega são médias para vasos em ambiente interno e mudam com o tamanho do vaso, o substrato, a luz e o clima da sua cidade.</p>
    </section>
    </div>
{cta_final(f"Cuide {g.do_nome} com o FlorAI", raiz)}

    <nav class="related" aria-labelledby="relacionadas">
      <h2 id="relacionadas">Outros guias</h2>
      <ul>
{relacionadas_html}
      </ul>
    </nav>
  </article>
</main>
"""
    return cabecalho(titulo, descricao, url, raiz, jsonld(schema)) + corpo + rodape(raiz)


# ---------------------------------------------------------------- artigo (tópicos e comparativos)

def bloco(b):
    if "p" in b:
        return f"      <p>{inline(b['p'])}</p>"
    if "h3" in b:
        return f"      <h3>{inline(b['h3'])}</h3>"
    if "ul" in b or "ol" in b:
        tag = "ul" if "ul" in b else "ol"
        cls = "" if tag == "ul" else ' class="steps"'
        itens = "\n".join(f"        <li>{inline(i)}</li>" for i in b[tag])
        return f"      <{tag}{cls}>\n{itens}\n      </{tag}>"
    if "tabela" in b:
        t = b["tabela"]
        cab = "".join(f"<th scope=\"col\">{inline(c)}</th>" for c in t["cab"])
        linhas = "\n".join(
            "          <tr>" + "".join(
                (f"<th scope=\"row\">{inline(c)}</th>" if i == 0 else f"<td>{inline(c)}</td>")
                for i, c in enumerate(l)
            ) + "</tr>"
            for l in t["linhas"]
        )
        return f"""      <div class="table-wrap">
        <table class="data-table">
          <thead><tr>{cab}</tr></thead>
          <tbody>
{linhas}
          </tbody>
        </table>
      </div>"""
    raise SystemExit(f"bloco desconhecido: {list(b)}")


def lista_relacionadas(slugs, rotulos):
    return "\n".join(
        f"""      <li><a href="../{s}/"><b>{escape(rotulos[s][0])}</b><span>{escape(rotulos[s][1])}</span><svg class="i"><use href="#i-chev"/></svg></a></li>"""
        for s in slugs
    )


def pagina_artigo(a, rotulos, atualizado):
    raiz = "../../"
    url = f"{SITE}/guia/{a['slug']}/"
    titulo = f"{a['titulo']} | FlorAI"

    faq_schema = [(a["pergunta"], texto_puro(a["resposta"]))] + [
        (pq, texto_puro(rs)) for pq, rs in a["faqs"]
    ]
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "@id": url + "#artigo",
                "headline": a["h1"],
                "description": a["descricao"],
                "inLanguage": "pt-BR",
                "datePublished": atualizado,
                "dateModified": atualizado,
                "mainEntityOfPage": url,
                "author": {"@id": SITE + "/#organizacao"},
                "publisher": {"@id": SITE + "/#organizacao"},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Início", "item": SITE + "/"},
                    {"@type": "ListItem", "position": 2, "name": "Guias de plantas", "item": SITE + "/guia/"},
                    {"@type": "ListItem", "position": 3, "name": a["curto"], "item": url},
                ],
            },
            {
                "@type": "FAQPage",
                "@id": url + "#faq",
                "mainEntity": [
                    {"@type": "Question", "name": pq,
                     "acceptedAnswer": {"@type": "Answer", "text": rs}}
                    for pq, rs in faq_schema
                ],
            },
            {"@type": "Organization", "@id": SITE + "/#organizacao", "name": "FlorAI", "url": SITE + "/"},
        ],
    }

    aviso = f'\n      <p class="guide__notice">{inline(a["aviso"])}</p>' if a.get("aviso") else ""
    secoes = "\n\n".join(
        f"""    <section id="{s['id']}">
      <h2>{inline(s['h2'])}</h2>
{chr(10).join(bloco(b) for b in s['blocos'])}
    </section>"""
        for s in a["secoes"]
    )
    faqs = "\n".join(f"      <h3>{escape(pq)}</h3>\n      <p>{inline(rs)}</p>" for pq, rs in a["faqs"])
    refs = ""
    if a.get("referencias"):
        itens = "\n".join(
            f'        <li><a href="{escape(u)}" rel="noopener">{escape(t)}</a></li>' for t, u in a["referencias"]
        )
        refs = f"""

    <section id="referencias" class="refs">
      <h2>Referências</h2>
      <ul>
{itens}
      </ul>
    </section>"""

    corpo = f"""
<main class="guide">
  <article class="container guide__wrap">
    <nav class="crumbs" aria-label="Você está em">
      <a href="{raiz}">Início</a><span aria-hidden="true">›</span><a href="../">Guias de plantas</a><span aria-hidden="true">›</span><span aria-current="page">{escape(a['curto'])}</span>
    </nav>

    <header class="guide__head">
      <p class="eyebrow">{escape(a['eyebrow'])}</p>
      <h1 class="h2">{escape(a['h1'])}</h1>
      <p class="guide__meta">Atualizado em {data_extenso(atualizado)} · Equipe FlorAI</p>
      <p class="guide__intro">{inline(a['intro'])}</p>{aviso}
    </header>

    <section class="quick quick--text" aria-labelledby="resumo">
      <h2 id="resumo">Resposta rápida</h2>
      <p>{inline(a['resposta'])}</p>
    </section>

    <div class="guide__body">
{secoes}

    <section id="faq">
      <h2>Perguntas frequentes</h2>
{faqs}
    </section>{refs}
    </div>
{cta_final("Identifique e cuide das suas plantas com o FlorAI", raiz)}

    <nav class="related" aria-labelledby="relacionadas">
      <h2 id="relacionadas">Leia também</h2>
      <ul>
{lista_relacionadas(a['relacionadas'], rotulos)}
      </ul>
    </nav>
  </article>
</main>
"""
    return cabecalho(titulo, a["descricao"], url, raiz, jsonld(schema)) + corpo + rodape(raiz)


# ---------------------------------------------------------------- índice dos guias

FAQ_GERAL = [
    ("Como saber quando regar uma planta?",
     "Na maioria das plantas de casa, a regra mais segura é o teste do dedo: enfie o dedo de 3 a 5 cm no substrato. "
     "Se estiver seco, regue até a água escorrer pelo furo do vaso; se estiver úmido, espere. Suculentas, cactos, "
     "zamioculca e espada-de-são-jorge preferem secar totalmente; samambaia e lírio-da-paz preferem ficar levemente úmidos."),
    ("Qual o melhor horário para regar as plantas?",
     "De manhã cedo ou no fim da tarde, quando o sol está fraco. Regar de manhã dá tempo para as folhas secarem e "
     "reduz o risco de fungos."),
    ("Com que frequência devo adubar plantas de vaso?",
     "Para a maioria das plantas de casa, a cada 30 dias na primavera e no verão (de setembro a março no Brasil), "
     "com a dose da embalagem ou menos. No outono e no inverno o crescimento diminui, e o adubo pode ser espaçado ou suspenso."),
    ("Por que as folhas da minha planta estão amarelas?",
     "Em plantas de vaso, a causa mais comum é excesso de água. Outras causas são pouca luz, falta de nutrientes e o "
     "envelhecimento natural das folhas mais baixas. Confira primeiro se o substrato está encharcado e se o vaso tem furos."),
    ("Como descobrir o nome de uma planta?",
     "Tire uma foto nítida, com boa luz, de uma folha inteira e, se houver, da flor. Aplicativos de identificação por "
     "inteligência artificial, como o FlorAI, comparam formato, cor e textura e mostram a espécie mais provável em "
     "segundos, junto com os cuidados de luz, rega, temperatura e solo."),
]


def pagina_indice(plantas, artigos, atualizado):
    raiz = "../"
    url = f"{SITE}/guia/"
    titulo = "Guias de cuidados de plantas: rega, luz e adubo | FlorAI"
    descricao = ("Guias práticos para cuidar de plantas de casa no Brasil: quando regar, quanta luz, como adubar, "
                 "pragas, folhas amarelas e os melhores apps para identificar plantas e lembrar de regar.")
    itens = [(a["curto"], a["slug"]) for a in artigos] + [(cap(p["nome"]), p["slug"]) for p in plantas]

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": url,
                "name": "Guias de cuidados de plantas",
                "description": descricao,
                "inLanguage": "pt-BR",
                "dateModified": atualizado,
                "publisher": {"@id": SITE + "/#organizacao"},
                "mainEntity": {
                    "@type": "ItemList",
                    "itemListElement": [
                        {"@type": "ListItem", "position": i + 1, "name": nome, "url": f"{SITE}/guia/{slug}/"}
                        for i, (nome, slug) in enumerate(itens)
                    ],
                },
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {"@type": "Question", "name": pq,
                     "acceptedAnswer": {"@type": "Answer", "text": rs}}
                    for pq, rs in FAQ_GERAL
                ],
            },
            {"@type": "Organization", "@id": SITE + "/#organizacao", "name": "FlorAI", "url": SITE + "/"},
        ],
    }

    cards = "\n".join(
        f"""      <li><a class="plant-card" href="{p['slug']}/">
        <b>{escape(cap(p['nome']))}</b>
        <em>{escape(sci_curto(p))}</em>
        <span><svg class="i"><use href="#i-drop"/></svg> {escape(p['resumo']['rega'])}</span>
        <span><svg class="i"><use href="#i-sun"/></svg> {escape(p['resumo']['luz'])}</span>
      </a></li>"""
        for p in plantas
    )

    dicas = "\n".join(
        f"""      <li><a class="topic-card" href="{a['slug']}/">
        <small>{escape(a['eyebrow'])}</small>
        <b>{escape(a['curto'])}</b>
      </a></li>"""
        for a in artigos
    )

    faqs = "\n".join(f"      <h3>{escape(pq)}</h3>\n      <p>{escape(rs)}</p>" for pq, rs in FAQ_GERAL)

    corpo = f"""
<main class="guide">
  <div class="container guide__wrap guide__wrap--wide">
    <nav class="crumbs" aria-label="Você está em">
      <a href="{raiz}">Início</a><span aria-hidden="true">›</span><span aria-current="page">Guias de plantas</span>
    </nav>

    <header class="guide__head">
      <p class="eyebrow">Guias de cuidados</p>
      <h1 class="h2">Como cuidar das suas plantas</h1>
      <p class="guide__meta">Atualizado em {data_extenso(atualizado)} · Equipe FlorAI</p>
      <p class="guide__intro">Respostas diretas para as dúvidas do dia a dia: quando regar, quanta luz dar, como adubar e o que fazer quando algo dá errado. Cada guia traz ajustes para o clima do Sul, Sudeste, Nordeste, Norte e Centro-Oeste.</p>
    </header>

    <h2 class="index-title">Dicas, problemas e apps</h2>
    <ul class="topic-grid">
{dicas}
    </ul>

    <h2 class="index-title">Guias por planta</h2>
    <ul class="plant-grid">
{cards}
    </ul>

    <aside class="id-callout">
      <svg class="i"><use href="#i-camera"/></svg>
      <p><b>Não sabe o nome da sua planta?</b> Tire uma foto no FlorAI: a IA identifica a espécie em segundos e mostra luz, rega, temperatura e solo ideais.</p>
      <a class="btn btn--ghost btn--sm" href="{PLAY}">Identificar pela foto</a>
    </aside>

    <div class="guide__body">
    <section id="perguntas">
      <h2>Perguntas frequentes sobre cuidados com plantas</h2>
{faqs}
    </section>
    </div>
{cta_final("Descubra o nome e os cuidados de qualquer planta", raiz)}
  </div>
</main>
"""
    return cabecalho(titulo, descricao, url, raiz, jsonld(schema)) + corpo + rodape(raiz)


# ---------------------------------------------------------------- sitemap e llms.txt

def sitemap(slugs, atualizado):
    urls = ["/", "/guia/"] + [f"/guia/{s}/" for s in slugs] + ["/termos.html", "/privacidade.html"]
    itens = "\n".join(
        f"  <url><loc>{SITE}{u}</loc><lastmod>{atualizado}</lastmod></url>" for u in urls
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{itens}
</urlset>
"""


def llms(plantas, artigos):
    topicos = "\n".join(f"- [{a['curto']}]({SITE}/guia/{a['slug']}/): {a['descricao']}" for a in artigos)
    guias = "\n".join(
        f"- [{cap(p['nome'])} ({sci_curto(p)})]({SITE}/guia/{p['slug']}/): rega — {p['resumo']['rega'].lower()}; "
        f"luz — {p['resumo']['luz'].lower()}."
        for p in plantas
    )
    return f"""# FlorAI

> {ENTIDADE}

## Fatos sobre o aplicativo

- Plataforma: Android, no Google Play ({PLAY}). A versão para iPhone ainda não foi lançada.
- Idioma: português do Brasil.
- Identificação de plantas por foto da câmera ou da galeria, com nome comum, nome científico e grau de confiança.
- Cuidados por espécie: luz, rega, temperatura e solo.
- Coleção pessoal de plantas, organizada em coleções (por exemplo, sala, varanda, escritório).
- Lembretes de rega nos planos pagos.
- Em desenvolvimento (ainda não disponível): Médico de IA, para analisar pela foto sinais de pragas e doenças. Será incluído no plano Premium.
- Sem anúncios.
- Planos mensais: Gratuito (R$ 0, 3 identificações por dia, 1 coleção, até 3 plantas); Básico (R$ 9,99, 5 identificações por dia, até 20 plantas, coleções ilimitadas, lembretes de rega); Pro (R$ 19,99, 15 identificações por dia, plantas ilimitadas, lembretes de rega); Premium (R$ 49,99, 40 identificações por dia, plantas ilimitadas, lembretes de rega e, quando lançado, o Médico de IA).
- Desenvolvedor: João Vitor Machado, Belo Horizonte (MG), Brasil.

## Dicas, problemas e comparativos de apps

{topicos}

## Guias de cuidados por planta

{guias}

## Outras páginas

- [Início]({SITE}/): apresentação do aplicativo, recursos e planos.
- [Todos os guias]({SITE}/guia/): índice dos guias e perguntas frequentes gerais sobre rega, adubo e identificação.
- [Termos de Uso]({SITE}/termos.html)
- [Política de Privacidade]({SITE}/privacidade.html)
"""


# ---------------------------------------------------------------- main

def main():
    dados = json.loads((RAIZ / "ferramentas" / "plantas.json").read_text(encoding="utf-8"))
    artigos = json.loads((RAIZ / "ferramentas" / "artigos.json").read_text(encoding="utf-8"))["artigos"]
    sem_acento = lambda s: unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()
    plantas = sorted(dados["plantas"], key=lambda p: sem_acento(p["nome"]))
    atualizado = dados["atualizado"]
    por_slug = {p["slug"]: p for p in plantas}

    SLUGS.update(por_slug)
    SLUGS.update(a["slug"] for a in artigos)
    if len(SLUGS) != len(plantas) + len(artigos):
        raise SystemExit("slug repetido entre plantas.json e artigos.json")

    rotulos = {p["slug"]: (cap(p["nome"]), sci_curto(p)) for p in plantas}
    rotulos.update({a["slug"]: (a["curto"], a["eyebrow"]) for a in artigos})

    def escrever(rel, conteudo):
        arquivo = RAIZ / rel
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(conteudo, encoding="utf-8", newline="\n")
        print("escrito", rel)

    for p in plantas:
        escrever(f"guia/{p['slug']}/index.html", pagina_planta(p, por_slug, atualizado))
    for a in artigos:
        escrever(f"guia/{a['slug']}/index.html", pagina_artigo(a, rotulos, atualizado))
    escrever("guia/index.html", pagina_indice(plantas, artigos, atualizado))
    escrever("sitemap.xml", sitemap([a["slug"] for a in artigos] + [p["slug"] for p in plantas], atualizado))
    escrever("llms.txt", llms(plantas, artigos))


if __name__ == "__main__":
    main()
