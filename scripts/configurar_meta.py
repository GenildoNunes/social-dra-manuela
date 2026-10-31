"""Configura o acesso ao Instagram e salva nos segredos do GitHub (rodar uma vez, no seu PC).

Pede o token gerado no painel do app (Instagram → Configuração da API com login do Instagram),
confere que ele é da conta certa e grava IG_TOKEN e IG_USER_ID como segredos do repositório.
Opcionalmente grava também GH_PAT, usado pelo robô para renovar o token sozinho.
Nenhum token é exibido ou salvo em disco.

Uso:  python scripts/configurar_meta.py
"""
import getpass
import os
import re
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


def consultar(host, caminho, token, fields):
    r = requests.get(f"https://{host}/{VERSAO}/{caminho}",
                     params={"fields": fields, "access_token": token}, timeout=30).json()
    if "error" in r:
        e = r["error"]
        # Nunca imprimir a mensagem crua: a Meta às vezes repete o token dentro dela.
        print(f"   · {host}/{caminho}: erro {e.get('code')}/{e.get('error_subcode', '-')} ({e.get('type')})")
        return None
    return r


def identificar_conta(token):
    """Descobre em qual API o token funciona e qual conta do Instagram ele acessa.

    Tokens do login pelo Instagram respondem em graph.instagram.com/me; tokens do login unificado
    (começam com EAA) respondem em graph.facebook.com consultando o ID da conta diretamente.
    """
    r = consultar("graph.instagram.com", "me", token, "user_id,username")
    if r:
        return "graph.instagram.com", r["user_id"], r.get("username")

    print("\nNo painel da Meta (etapa 2), embaixo de 'dramanuelagondim', aparece um número.")
    ig_id = input("Digite esse número aqui: ").strip()
    for host in ("graph.facebook.com", "graph.instagram.com"):
        r = consultar(host, ig_id, token, "id,username")
        if r:
            return host, r["id"], r.get("username")
    sys.exit("Não consegui acessar a conta com esse token e esse número. Me mande o print desta tela.")


def salvar_segredo(gh, nome, valor):
    subprocess.run([gh, "secret", "set", nome, "-R", REPO], input=valor, text=True, check=True)


def ler_area_de_transferencia():
    r = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
                       capture_output=True, text=True)
    return r.stdout


def limpar_area_de_transferencia():
    subprocess.run(["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value ' '"], capture_output=True)


def extrair_token(texto):
    """Pega o primeiro token do texto copiado (tolera espaços, quebras de linha e colagem duplicada)."""
    texto = re.sub(r"\s+", "", texto or "")
    for n in (2, 3):
        parte = len(texto) // n
        if len(texto) % n == 0 and texto == texto[:parte] * n:
            return texto[:parte]
    return texto


def main():
    print("== Configuração do Instagram ==\n")
    print("1. No Chrome, clique em 'Gerar token' e COPIE o token.")
    while True:
        colado = getpass.getpass("2. Cole aqui (fica invisível) ou só aperte Enter: ")
        token = extrair_token(colado or ler_area_de_transferencia())
        if token.startswith(("EAA", "IG")) and len(token) > 50:
            break
        if token:
            print(f"   Encontrei um texto de {len(token)} caracteres, mas não parece um token. Copie de novo.\n")
        else:
            print("   A área de transferência está vazia. Copie o token no Chrome e tente de novo.\n")
    limpar_area_de_transferencia()
    print(f"Token lido ({len(token)} caracteres, terminando em ...{token[-4:]}). Verificando...")

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
