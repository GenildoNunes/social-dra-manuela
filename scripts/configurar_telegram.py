"""Configura o bot do Telegram e salva nos segredos do GitHub (rodar uma vez, no seu PC).

Antes: crie o bot no @BotFather e peça para a Dra. (e você, se quiser) mandar /start para ele.
O script lê o token da área de transferência (ou colado, invisível), descobre quem mandou /start,
grava TELEGRAM_TOKEN e TELEGRAM_CHAT_IDS e manda uma mensagem de teste. Nenhum token é exibido.

Uso:  python scripts/configurar_telegram.py
"""
import getpass
import sys
import time

import requests

from pathlib import Path

from configurar_meta import extrair_token, gh_exe, ler_area_de_transferencia, limpar_area_de_transferencia, salvar_segredo

GUARDADO = Path(__file__).resolve().parent.parent / ".segredos" / "telegram.token"


def tg(token, metodo, **params):
    r = requests.post(f"https://api.telegram.org/bot{token}/{metodo}", json=params, timeout=40).json()
    if not r.get("ok"):
        # Nunca imprimir a URL nem o token; só a descrição do erro.
        sys.exit(f"Erro do Telegram em {metodo}: {r.get('description')}")
    return r["result"]


def main():
    # --auto: sem perguntas — lê o token da área de transferência e cadastra todos que mandaram /start.
    auto = "--auto" in sys.argv
    print("== Configuração do bot do Telegram ==\n")
    if auto:
        # O token lido fica num arquivo local (fora do git) até o fim da configuração,
        # para não depender da área de transferência entre uma tentativa e outra.
        token = extrair_token(ler_area_de_transferencia())
        if ":" in token and len(token) > 30:
            GUARDADO.parent.mkdir(exist_ok=True)
            GUARDADO.write_text(token, encoding="utf-8")
        elif GUARDADO.exists():
            token = GUARDADO.read_text(encoding="utf-8").strip()
        else:
            sys.exit("A área de transferência não tem um token do Telegram. Copie o token do @BotFather e rode de novo.")
    else:
        print("1. Copie o token que o @BotFather enviou (o texto com ':' no meio).")
        while True:
            colado = getpass.getpass("2. Cole aqui (fica invisível) ou só aperte Enter: ")
            token = extrair_token(colado or ler_area_de_transferencia())
            if ":" in token and len(token) > 30:
                break
            print("   Não encontrei um token do Telegram. Copie de novo e tente.\n")

    bot = tg(token, "getMe")
    print(f"✓ Bot: @{bot['username']} ({bot['first_name']})")

    conversas = {}
    # Espera até 5 minutos alguém tocar em Começar (/start), para não precisar rodar de novo.
    fim = time.time() + 300
    while True:
        try:
            atualizacoes = tg(token, "getUpdates", timeout=20)
        except requests.RequestException:  # queda de conexão: tenta de novo em seguida
            atualizacoes = []
            time.sleep(3)
        for u in atualizacoes:
            msg = u.get("message") or {}
            chat = msg.get("chat") or {}
            if chat.get("type") == "private":
                nome = " ".join(filter(None, [chat.get("first_name"), chat.get("last_name")]))
                conversas[chat["id"]] = nome or chat.get("username", "?")
        if conversas or time.time() > fim:
            break
        print(f"   aguardando alguém tocar em Começar em t.me/{bot['username']} ...", flush=True)
    if not conversas:
        sys.exit(f"Ninguém mandou mensagem ainda. Abra t.me/{bot['username']}, toque em Começar (/start) "
                 "e rode este script de novo.")

    print("\nPessoas que falaram com o bot:")
    ids = list(conversas)
    for i, cid in enumerate(ids, 1):
        print(f"  {i}. {conversas[cid]}")
    escolha = "" if auto else input(
        "Quem vai receber e aprovar os posts? (números separados por vírgula, Enter = todos): ").strip()
    if escolha:
        ids = [ids[int(n) - 1] for n in escolha.split(",")]

    gh = gh_exe()
    salvar_segredo(gh, "TELEGRAM_TOKEN", token)
    salvar_segredo(gh, "TELEGRAM_CHAT_IDS", ",".join(str(i) for i in ids))
    print("✓ Segredos TELEGRAM_TOKEN e TELEGRAM_CHAT_IDS salvos no GitHub.")
    limpar_area_de_transferencia()  # só no fim: se algo falhar antes, dá para rodar de novo sem copiar outra vez
    GUARDADO.unlink(missing_ok=True)

    for cid in ids:
        tg(token, "sendMessage", chat_id=cid, text=(
            "Olá! 💖 Eu sou o assistente de conteúdo do consultório.\n\n"
            "Toda semana vou te mandar os posts prontos aqui. Para cada um você poderá:\n"
            "✅ Aprovar · ✏️ Pedir ajuste · ❌ Recusar\n\n"
            "Nada é publicado sem o seu ✅."))
    print(f"✓ Mensagem de teste enviada para {len(ids)} pessoa(s).")


if __name__ == "__main__":
    main()
