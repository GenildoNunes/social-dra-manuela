"""Publica no Instagram os posts com status `aprovado` cuja data/hora já chegou.

Usa a API do Instagram com login pelo Instagram (graph.instagram.com) — não depende de Página do Facebook.

Roda no GitHub Actions (ver .github/workflows/publicar.yml). Variáveis de ambiente:
    IG_USER_ID      ID da conta profissional do Instagram
    IG_TOKEN        Token de acesso do Instagram (renovado por renovar_token.py)
    REPO_RAW_URL    Base pública das imagens, ex.: https://raw.githubusercontent.com/<dono>/<repo>/main
    GRAPH_VERSION   (opcional) versão da Graph API
    DRY_RUN=1       (opcional) só mostra o que faria, sem publicar

Ao publicar, o post.yaml é atualizado com status `publicado`; o workflow faz o commit.
"""
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import yaml

import posts

RAIZ = Path(__file__).resolve().parent.parent
POSTS = RAIZ / "posts"
RECIFE = timezone(timedelta(hours=-3))

# graph.instagram.com (login pelo Instagram) ou graph.facebook.com (usuário do sistema) — definido pelo configurador.
GRAPH = f"https://{os.environ.get('IG_API_HOST') or 'graph.instagram.com'}/{os.environ.get('GRAPH_VERSION', 'v23.0')}"
IG_USER_ID = os.environ.get("IG_USER_ID", "")
TOKEN = os.environ.get("IG_TOKEN", "")
RAW = os.environ.get("REPO_RAW_URL", "").rstrip("/")
DRY_RUN = os.environ.get("DRY_RUN") == "1"


def api(metodo, caminho, **params):
    params["access_token"] = TOKEN
    r = requests.request(metodo, f"{GRAPH}/{caminho}", data=params if metodo == "POST" else None,
                         params=params if metodo == "GET" else None, timeout=60)
    dados = r.json()
    if "error" in dados:
        raise RuntimeError(f"Graph API: {dados['error'].get('message')}")
    return dados


def aguardar_container(cid, tentativas=30):
    """O Instagram baixa e processa a mídia de forma assíncrona; espera ficar pronta."""
    for _ in range(tentativas):
        status = api("GET", cid, fields="status_code").get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Container {cid} falhou: {status}")
        time.sleep(5)
    raise RuntimeError(f"Container {cid} não ficou pronto a tempo")


def legenda_completa(post):
    tags = " ".join("#" + t.lstrip("#") for t in post.get("hashtags", []))
    return (post.get("legenda", "").strip() + ("\n\n" + tags if tags else "")).strip()


def publicar(pasta: Path, post):
    imagens = sorted(pasta.glob("slide-*.jpg"))
    if not imagens:
        raise RuntimeError("post sem imagens — rode scripts/render.py")
    urls = [f"{RAW}/posts/{pasta.name}/{img.name}" for img in imagens]
    formato = post.get("formato", "carrossel")

    if DRY_RUN:
        print(f"  [simulação] {formato} com {len(urls)} imagem(ns): {urls[0]}")
        return "dry-run"

    if formato == "story":
        cid = api("POST", f"{IG_USER_ID}/media", image_url=urls[0], media_type="STORIES")["id"]
    elif len(urls) == 1:
        cid = api("POST", f"{IG_USER_ID}/media", image_url=urls[0], caption=legenda_completa(post))["id"]
    else:
        filhos = [api("POST", f"{IG_USER_ID}/media", image_url=u, is_carousel_item="true")["id"] for u in urls[:10]]
        for f in filhos:
            aguardar_container(f)
        cid = api("POST", f"{IG_USER_ID}/media", media_type="CAROUSEL",
                  children=",".join(filhos), caption=legenda_completa(post))["id"]

    aguardar_container(cid)
    return api("POST", f"{IG_USER_ID}/media_publish", creation_id=cid)["id"]


def vencido(post, agora):
    data = str(post["data"])
    hora = posts.hora(post)
    quando = datetime.fromisoformat(f"{data}T{hora}").replace(tzinfo=RECIFE)
    return quando <= agora


def main():
    if not DRY_RUN and not (IG_USER_ID and TOKEN and RAW):
        print("Faltam IG_USER_ID, IG_TOKEN ou REPO_RAW_URL — nada a fazer.")
        return 0

    if IG_USER_ID and TOKEN:
        conta = api("GET", IG_USER_ID, fields="username,followers_count,media_count")
        print(f"Conectado a @{conta.get('username')} · {conta.get('followers_count')} seguidores · "
              f"{conta.get('media_count')} posts")

    agora = datetime.now(RECIFE)
    falhas = 0
    for arq in sorted(POSTS.glob("*/post.yaml")):
        post = yaml.safe_load(arq.read_text(encoding="utf-8"))
        if post.get("status") != "aprovado" or not vencido(post, agora):
            continue
        if post.get("bloqueio"):  # ex.: depoimento aguardando validação do CRO-PE
            print(f"⏸ {arq.parent.name}: bloqueado ({post['bloqueio']})")
            continue
        print(f"→ {arq.parent.name}")
        try:
            media_id = publicar(arq.parent, post)
        except Exception as e:  # um post com erro não impede os outros
            falhas += 1
            print(f"  ✗ {e}")
            continue
        if DRY_RUN:
            continue
        post["status"] = "publicado"
        post["publicado_em"] = agora.isoformat(timespec="minutes")
        post["ig_media_id"] = media_id
        posts.salvar(arq.parent, post)
        print(f"  ✓ publicado ({media_id})")

    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
