"""Renderiza os posts (posts/<pasta>/post.yaml) em imagens JPEG e gera uma prévia HTML.

Uso:
    python scripts/render.py                 # renderiza todos os posts sem imagens
    python scripts/render.py --todos         # re-renderiza tudo
    python scripts/render.py posts/2026-11-03-mito-aparelho
"""
import argparse
import base64
import html
import re
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup, escape
from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent.parent
POSTS = RAIZ / "posts"
MARCA = RAIZ / "marca"
FEED = (1080, 1350)
STORY = (1080, 1920)


def enfase(texto):
    """*palavra* vira <em>palavra</em> (destaque rosa itálico); quebra de linha vira <br>."""
    seguro = str(escape(texto or ""))
    seguro = re.sub(r"\*(.+?)\*", r"<em>\1</em>", seguro)
    return Markup(seguro.replace("\n", "<br>"))


def data_uri(caminho: Path):
    """Imagens vão embutidas no HTML: o set_content do navegador não lê arquivos locais."""
    tipo = "image/png" if caminho.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{tipo};base64,{base64.b64encode(caminho.read_bytes()).decode()}"


def foto(nome):
    """`foto: consultorio-amplo.jpg` no post.yaml procura em marca/fotos/ (ou caminho relativo à raiz)."""
    caminho = MARCA / "fotos" / nome
    if not caminho.exists():
        caminho = RAIZ / nome
    return data_uri(caminho)


def carregar_env():
    env = Environment(loader=FileSystemLoader(RAIZ / "templates"), autoescape=True)
    env.filters["enfase"] = enfase
    env.filters["foto"] = foto
    env.globals["logo"] = data_uri(MARCA / "logo.png")
    env.globals["simbolo"] = data_uri(MARCA / "simbolo.png")
    return env


def renderizar_post(pasta: Path, page, env):
    post = yaml.safe_load((pasta / "post.yaml").read_text(encoding="utf-8"))
    story = post.get("formato") == "story"
    w, h = STORY if story else FEED
    page.set_viewport_size({"width": w, "height": h})
    tpl = env.get_template("slide.html.j2")

    for antigo in pasta.glob("slide-*.*"):
        antigo.unlink()

    slides = post["slides"]
    for i, s in enumerate(slides, start=1):
        page.set_content(tpl.render(s=s, idx=i, total=len(slides), w=w, h=h, story=story))
        page.wait_for_load_state("networkidle")
        page.evaluate("document.fonts.ready")
        # A API do Instagram só aceita JPEG.
        page.screenshot(path=str(pasta / f"slide-{i:02d}.jpg"), type="jpeg", quality=92)
    print(f"  ✓ {pasta.name}: {len(slides)} imagem(ns)")
    return post


def gerar_previa(itens):
    """Página única com todos os posts da fila, para revisão/aprovação."""
    cartoes = []
    for pasta, post in itens:
        imgs = "".join(
            f'<img src="{p.relative_to(POSTS).as_posix()}" loading="lazy">'
            for p in sorted(pasta.glob("slide-*.jpg"))
        )
        tags = " ".join("#" + t.lstrip("#") for t in post.get("hashtags", []))
        aviso = '<span class="revisar">⚠ revisar</span>' if post.get("revisar") else ""
        cartoes.append(f"""
        <article>
          <header><b>{html.escape(str(post['data']))} · {html.escape(str(post.get('hora','')))}</b>
            <span>{html.escape(post.get('formato',''))} · {html.escape(post.get('pilar',''))}</span>{aviso}
            <span class="status">{html.escape(post.get('status','rascunho'))}</span></header>
          <div class="slides">{imgs}</div>
          <pre>{html.escape(post.get('legenda','').strip())}\n\n{html.escape(tags)}</pre>
        </article>""")

    (POSTS / "previa.html").write_text(f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Prévia de conteúdo</title>
<style>
body{{font-family:Montserrat,system-ui,sans-serif;background:#FBF4F0;color:#2B2326;margin:0;padding:24px 16px}}
h1{{font-family:'Playfair Display',Georgia,serif;color:#E22B8D;max-width:1100px;margin:0 auto 24px}}
article{{background:#fff;border-radius:16px;padding:18px;max-width:1100px;margin:0 auto 24px;box-shadow:0 2px 12px #0001}}
header{{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:12px}}
header span{{color:#6F6468}} .status{{margin-left:auto;background:#E9DCC4;padding:2px 10px;border-radius:99px;font-size:13px}}
.revisar{{color:#B81C6F!important;font-weight:600}}
.slides{{display:flex;gap:10px;overflow-x:auto;padding-bottom:6px}} .slides img{{height:340px;border-radius:8px;flex:none}}
pre{{white-space:pre-wrap;font-family:inherit;font-size:14px;line-height:1.5;background:#FBF4F0;padding:12px;border-radius:10px}}
</style></head><body><h1>Prévia de conteúdo</h1>{''.join(cartoes)}</body></html>""", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pastas", nargs="*")
    ap.add_argument("--todos", action="store_true")
    args = ap.parse_args()

    todas = sorted(p for p in POSTS.iterdir() if (p / "post.yaml").exists())
    if args.pastas:
        alvo = [Path(p).resolve() for p in args.pastas]
    elif args.todos:
        alvo = todas
    else:
        alvo = [p for p in todas if not any(p.glob("slide-*.jpg"))]

    env = carregar_env()
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        for pasta in alvo:
            renderizar_post(pasta, page, env)
        browser.close()

    itens = [(p, yaml.safe_load((p / "post.yaml").read_text(encoding="utf-8"))) for p in todas]
    pendentes = [(p, d) for p, d in itens if d.get("status", "rascunho") in ("rascunho", "aprovado")]
    gerar_previa(pendentes)
    print(f"Prévia: {POSTS / 'previa.html'}")


if __name__ == "__main__":
    sys.exit(main())
