"""
FlorAI — avisa os buscadores (Bing, Yandex, Seznam, Naver) sobre páginas novas ou atualizadas.

O IndexNow não exige login: a chave publicada na raiz do site prova que o pedido vem do dono.
O Bing alimenta a busca do ChatGPT e do Copilot, então isso acelera a entrada dos guias nas respostas de IA.
(O Google não usa IndexNow; para ele, envie o sitemap no Search Console.)

Uso, DEPOIS que o site estiver publicado:
  python ferramentas/indexnow.py            # envia todas as URLs do sitemap.xml
  python ferramentas/indexnow.py /guia/jiboia/ /guia/rosa/   # envia só essas
"""

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SITE = "https://florai.cc"
HOST = "florai.cc"
ENDPOINT = "https://api.indexnow.org/indexnow"


def chave():
    arquivos = [p for p in RAIZ.glob("*.txt") if re.fullmatch(r"[0-9a-f]{32}", p.stem)]
    if len(arquivos) != 1:
        raise SystemExit("esperava exatamente um arquivo de chave <32 hex>.txt na raiz do site")
    return arquivos[0].stem


def urls_do_sitemap():
    xml = (RAIZ / "sitemap.xml").read_text(encoding="utf-8")
    return re.findall(r"<loc>([^<]+)</loc>", xml)


def main():
    key = chave()
    key_url = f"{SITE}/{key}.txt"

    # O site devolve a página inicial para endereços desconhecidos, então confira o conteúdo, não só o status.
    # O Cloudflare do site bloqueia o User-Agent padrão do Python (HTTP 403).
    leitura = urllib.request.Request(key_url, headers={"User-Agent": "Mozilla/5.0 (FlorAI IndexNow)"})
    try:
        publicado = urllib.request.urlopen(leitura, timeout=15).read().decode("utf-8", "replace").strip()
    except urllib.error.URLError as e:
        raise SystemExit(f"não consegui abrir {key_url}: {e}")
    if publicado != key:
        raise SystemExit(f"{key_url} ainda não está publicado com a chave. Publique o site e tente de novo.")

    urls = [SITE + u if u.startswith("/") else u for u in sys.argv[1:]] or urls_do_sitemap()
    corpo = json.dumps({"host": HOST, "key": key, "keyLocation": key_url, "urlList": urls}).encode()
    pedido = urllib.request.Request(
        ENDPOINT, data=corpo, method="POST",
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "Mozilla/5.0 (FlorAI IndexNow)"},
    )
    try:
        with urllib.request.urlopen(pedido, timeout=30) as r:
            print(f"IndexNow: HTTP {r.status}, {len(urls)} URLs enviadas")
    except urllib.error.HTTPError as e:
        # 200/202 = aceito; 403 = chave não encontrada; 422 = URL fora do host; 429 = muitas tentativas
        raise SystemExit(f"IndexNow recusou: HTTP {e.code} {e.read().decode('utf-8', 'replace')}")


if __name__ == "__main__":
    main()
