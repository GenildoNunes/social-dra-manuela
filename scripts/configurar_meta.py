"""Configura o acesso ao Instagram e salva nos segredos do GitHub (rodar uma vez, no seu PC).

Pede o App ID, a Chave Secreta do app e o token curto gerado no Graph API Explorer.
Troca por um token de Página que não expira, descobre o ID do Instagram e grava
IG_TOKEN e IG_USER_ID como segredos do repositório. Nenhum token é exibido ou salvo em disco.

Uso:  python scripts/configurar_meta.py
"""
import getpass
import os
import shutil
import subprocess
import sys

import requests

GRAPH = f"https://graph.facebook.com/{os.environ.get('GRAPH_VERSION', 'v23.0')}"
REPO = "GenildoNunes/social-dra-manuela"
INSTAGRAM = "dramanuelagondim"


def get(caminho, **params):
    dados = requests.get(f"{GRAPH}/{caminho}", params=params, timeout=30).json()
    if "error" in dados:
        sys.exit(f"Erro do Meta: {dados['error'].get('message')}")
    return dados


def gh_exe():
    candidatos = [shutil.which("gh"), os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\GitHub.cli_Microsoft.Winget.Source_8wekyb3d8bbwe\bin\gh.exe")]
    for c in candidatos:
        if c and os.path.exists(c):
            return c
    sys.exit("GitHub CLI (gh) não encontrado.")


def main():
    print("== Configuração do Instagram ==\n(o que você colar não aparece na tela)\n")
    app_id = input("App ID: ").strip()
    app_secret = getpass.getpass("Chave Secreta do app: ").strip()
    token_curto = getpass.getpass("Token do Graph API Explorer: ").strip()

    longo = get("oauth/access_token", grant_type="fb_exchange_token", client_id=app_id,
                client_secret=app_secret, fb_exchange_token=token_curto)["access_token"]

    paginas = get("me/accounts", access_token=longo,
                  fields="name,access_token,instagram_business_account{id,username}")["data"]
    escolhida = next((p for p in paginas
                      if p.get("instagram_business_account", {}).get("username") == INSTAGRAM), None)
    if not escolhida:
        nomes = ", ".join(p["name"] for p in paginas) or "nenhuma"
        sys.exit(f"Não achei a Página vinculada ao @{INSTAGRAM}. Páginas liberadas: {nomes}.\n"
                 "Gere o token de novo marcando a Página da clínica na autorização.")

    ig_id = escolhida["instagram_business_account"]["id"]
    token_pagina = escolhida["access_token"]

    validade = get("debug_token", input_token=token_pagina,
                   access_token=f"{app_id}|{app_secret}")["data"].get("expires_at", 0)
    print(f"\n✓ Página: {escolhida['name']}  ·  Instagram: @{INSTAGRAM} ({ig_id})")
    print("✓ Token sem validade" if validade == 0 else "⚠ Token com validade — refaça daqui a ~60 dias")

    gh = gh_exe()
    for nome, valor in (("IG_TOKEN", token_pagina), ("IG_USER_ID", ig_id)):
        subprocess.run([gh, "secret", "set", nome, "-R", REPO], input=valor, text=True, check=True)
    print("\n✓ Segredos IG_TOKEN e IG_USER_ID salvos no GitHub. Pronto!")


if __name__ == "__main__":
    main()
