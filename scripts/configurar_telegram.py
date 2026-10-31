"""Configura o bot do Telegram e salva nos segredos do GitHub (rodar uma vez, no seu PC).

Antes: crie o bot no @BotFather e peça para a Dra. (e você, se quiser) mandar /start para ele.
O script lê o token da área de transferência (ou colado, invisível), descobre quem mandou /start,
grava TELEGRAM_TOKEN e TELEGRAM_CHAT_IDS e manda uma mensagem de teste. Nenhum token é exibido.

Uso:  python scripts/configurar_telegram.py
"""
import getpass
import sys

import requests

from configurar_meta import extrair_token, gh_exe, ler_area_de_transferencia, limpar_area_de_transferencia, salvar_segredo


def tg(token, metodo, **params):
    r = requests.post(f"https://api.telegram.org/bot{token}/{metodo}", json=params, timeout=30).json()
    if not r.get("ok"):
        # Nunca imprimir a URL nem o token; só a descrição do erro.
        sys.exit(f"Erro do Telegram em {metodo}: {r.get('description')}")
    return r["result"]


def main():
    print("== Configuração do bot do Telegram ==\n")
    print("1. Copie o token que o @BotFather enviou (o texto com ':' no meio).")
    while True:
        colado = getpass.getpass("2. Cole aqui (fica invisível) ou só aperte Enter: ")
        token = extrair_token(colado or ler_area_de_transferencia())
        if ":" in token and len(token) > 30:
            break
        print("   Não encontrei um token do Telegram. Copie de novo e tente.\n")
    limpar_area_de_transferencia()

    bot = tg(token, "getMe")
    print(f"✓ Bot: @{bot['username']} ({bot['first_name']})")

    conversas = {}
    for u in tg(token, "getUpdates"):
        msg = u.get("message") or {}
        chat = msg.get("chat") or {}
        if chat.get("type") == "private":
            nome = " ".join(filter(None, [chat.get("first_name"), chat.get("last_name")]))
            conversas[chat["id"]] = nome or chat.get("username", "?")
    if not conversas:
        sys.exit(f"Ninguém mandou mensagem ainda. Abra t.me/{bot['username']}, toque em Começar (/start) "
                 "e rode este script de novo.")

    print("\nPessoas que falaram com o bot:")
    ids = list(conversas)
    for i, cid in enumerate(ids, 1):
        print(f"  {i}. {conversas[cid]}")
    escolha = input("Quem vai receber e aprovar os posts? (números separados por vírgula, Enter = todos): ").strip()
    if escolha:
        ids = [ids[int(n) - 1] for n in escolha.split(",")]

    gh = gh_exe()
    salvar_segredo(gh, "TELEGRAM_TOKEN", token)
    salvar_segredo(gh, "TELEGRAM_CHAT_IDS", ",".join(str(i) for i in ids))
    print("✓ Segredos TELEGRAM_TOKEN e TELEGRAM_CHAT_IDS salvos no GitHub.")

    for cid in ids:
        tg(token, "sendMessage", chat_id=cid, text=(
            "Olá! 💖 Eu sou o assistente de conteúdo do consultório.\n\n"
            "Toda semana vou te mandar os posts prontos aqui. Para cada um você poderá:\n"
            "✅ Aprovar · ✏️ Pedir ajuste · ❌ Recusar\n\n"
            "Nada é publicado sem o seu ✅."))
    print(f"✓ Mensagem de teste enviada para {len(ids)} pessoa(s).")


if __name__ == "__main__":
    main()
