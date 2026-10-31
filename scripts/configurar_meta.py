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

GRAPH = f"https://graph.instagram.com/{os.environ.get('GRAPH_VERSION', 'v23.0')}"
REPO = "GenildoNunes/social-dra-manuela"
INSTAGRAM = "dramanuelagondim"


def gh_exe():
    candidatos = [shutil.which("gh"), os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\GitHub.cli_Microsoft.Winget.Source_8wekyb3d8bbwe\bin\gh.exe")]
    for c in candidatos:
        if c and os.path.exists(c):
            return c
    sys.exit("GitHub CLI (gh) não encontrado.")


def salvar_segredo(gh, nome, valor):
    subprocess.run([gh, "secret", "set", nome, "-R", REPO], input=valor, text=True, check=True)


def main():
    print("== Configuração do Instagram ==\n(o que você colar não aparece na tela)\n")
    token = getpass.getpass("Token do Instagram (painel do app): ").strip()

    dados = requests.get(f"{GRAPH}/me", params={"fields": "user_id,username", "access_token": token},
                         timeout=30).json()
    if "error" in dados:
        sys.exit(f"Erro do Meta: {dados['error'].get('message')}")
    if dados.get("username") != INSTAGRAM:
        sys.exit(f"Esse token é da conta @{dados.get('username')}, não da @{INSTAGRAM}. Nada foi salvo.")
    print(f"✓ Conta confirmada: @{INSTAGRAM} ({dados['user_id']})")

    gh = gh_exe()
    salvar_segredo(gh, "IG_TOKEN", token)
    salvar_segredo(gh, "IG_USER_ID", str(dados["user_id"]))
    print("✓ Segredos IG_TOKEN e IG_USER_ID salvos no GitHub.")

    print("\nRenovação automática: cole o token do GitHub (fine-grained, permissão Secrets: leitura e escrita).")
    pat = getpass.getpass("Token do GitHub (Enter para pular): ").strip()
    if pat:
        salvar_segredo(gh, "GH_PAT", pat)
        print("✓ GH_PAT salvo — o robô vai renovar o token do Instagram toda semana.")
    else:
        print("⚠ Sem GH_PAT o token do Instagram vence em ~60 dias. Rode este script de novo para configurar.")


if __name__ == "__main__":
    main()
