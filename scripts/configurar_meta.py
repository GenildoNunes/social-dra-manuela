"""Configura o acesso ao Instagram e salva nos segredos do GitHub (rodar uma vez, no seu PC).

Pede o token gerado no painel do app (Instagram → Configuração da API com login do Instagram),
confere que ele é da conta certa e grava IG_TOKEN e IG_USER_ID como segredos do repositório.
Opcionalmente grava também GH_PAT, usado pelo robô para renovar o token sozinho.
Nenhum token é exibido ou salvo em disco.

Uso:  python scripts/configurar_meta.py
"""
import getpass
import os
import shutil
import subprocess
import sys

import requests

VERSAO = os.environ.get("GRAPH_VERSION", "v23.0")
REPO = "GenildoNunes/social-dra-manuela"
INSTAGRAM = "dramanuelagondim"


def gh_exe():
    candidatos = [shutil.which("gh"), os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\GitHub.cli_Microsoft.Winget.Source_8wekyb3d8bbwe\bin\gh.exe")]
    for c in candidatos:
        if c and os.path.exists(c):
            return c
    sys.exit("GitHub CLI (gh) não encontrado.")


def identificar_conta(token):
    """Descobre em qual API o token funciona e qual conta do Instagram ele acessa.

    Tokens do login pelo Instagram respondem em graph.instagram.com; tokens de usuário do sistema
    (login unificado / Facebook) respondem em graph.facebook.com, listando as contas vinculadas.
    """
    r = requests.get(f"https://graph.instagram.com/{VERSAO}/me",
                     params={"fields": "user_id,username", "access_token": token}, timeout=30).json()
    if "error" not in r:
        return "graph.instagram.com", r["user_id"], r.get("username")

    fb = f"https://graph.facebook.com/{VERSAO}"
    r = requests.get(f"{fb}/me/accounts", timeout=30, params={
        "fields": "instagram_business_account{id,username}", "access_token": token}).json()
    for pagina in r.get("data", []):
        conta = pagina.get("instagram_business_account")
        if conta:
            return "graph.facebook.com", conta["id"], conta.get("username")
    # Usuário do sistema pode ter a conta do Instagram atribuída direto, sem Página.
    r = requests.get(f"{fb}/me", timeout=30, params={
        "fields": "instagram_accounts{id,username}", "access_token": token}).json()
    for conta in r.get("instagram_accounts", {}).get("data", []):
        return "graph.facebook.com", conta["id"], conta.get("username")
    sys.exit(f"Não consegui identificar a conta do Instagram com esse token: {r.get('error', r)}")


def salvar_segredo(gh, nome, valor):
    subprocess.run([gh, "secret", "set", nome, "-R", REPO], input=valor, text=True, check=True)


def main():
    print("== Configuração do Instagram ==\n(o que você colar não aparece na tela)\n")
    token = getpass.getpass("Token do Instagram (painel do app): ").strip()

    host, ig_id, username = identificar_conta(token)
    if username != INSTAGRAM:
        sys.exit(f"Esse token é da conta @{username}, não da @{INSTAGRAM}. Nada foi salvo.")
    print(f"✓ Conta confirmada: @{INSTAGRAM} ({ig_id}) via {host}")

    gh = gh_exe()
    salvar_segredo(gh, "IG_TOKEN", token)
    salvar_segredo(gh, "IG_USER_ID", str(ig_id))
    salvar_segredo(gh, "IG_API_HOST", host)
    print("✓ Segredos IG_TOKEN, IG_USER_ID e IG_API_HOST salvos no GitHub.")

    if host == "graph.facebook.com":
        print("\nEsse token é de usuário do sistema e não expira — não precisa de renovação automática.")
        return

    print("\nRenovação automática: cole o token do GitHub (fine-grained, permissão Secrets: leitura e escrita).")
    pat = getpass.getpass("Token do GitHub (Enter para pular): ").strip()
    if pat:
        salvar_segredo(gh, "GH_PAT", pat)
        print("✓ GH_PAT salvo — o robô vai renovar o token do Instagram toda semana.")
    else:
        print("⚠ Sem GH_PAT o token do Instagram vence em ~60 dias. Rode este script de novo para configurar.")


if __name__ == "__main__":
    main()
