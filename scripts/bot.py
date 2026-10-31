"""Bot de aprovação no Telegram ("Sandra").

    python scripts/bot.py processar   # lê respostas: ✅ aprova, ❌ recusa, ✏️ pede ajuste (texto da Dra.)
    python scripts/bot.py enviar      # manda para aprovação os rascunhos novos ou refeitos

Roda no GitHub Actions (.github/workflows/bot.yml). Variáveis de ambiente:
    TELEGRAM_TOKEN, TELEGRAM_CHAT_IDS (separados por vírgula), REPO_RAW_URL
O bot não usa IA (custo zero): pedidos de ajuste ficam anotados no post e a rotina diária do agente aplica.

Quem aprova é só quem está em TELEGRAM_CHAT_IDS; mensagens de outras pessoas são ignoradas.
"""
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

import requests

import posts

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHATS = {int(c) for c in os.environ.get("TELEGRAM_CHAT_IDS", "").split(",") if c.strip()}
RAW = os.environ.get("REPO_RAW_URL", "").rstrip("/")
ESTADO = posts.RAIZ / "estado" / "telegram.json"

ROTULO = {"aprovado": "✅ Aprovado", "recusado": "❌ Recusado", "ajuste": "✏️ Em ajuste"}


def tg(metodo, **params):
    r = requests.post(f"https://api.telegram.org/bot{TOKEN}/{metodo}", json=params, timeout=60).json()
    if not r.get("ok"):
        # Nunca imprimir a URL (contém o token).
        raise RuntimeError(f"Telegram {metodo}: {r.get('description')}")
    return r["result"]


def responder(chat, texto, **extra):
    return tg("sendMessage", chat_id=chat, text=texto, **extra)


# ---------- enviar ----------

def url_imagem(pasta: Path, img: Path):
    # ?v=<hash> fura o cache do raw.githubusercontent quando a arte é refeita com o mesmo nome.
    versao = hashlib.sha1(img.read_bytes()).hexdigest()[:10]
    return f"{RAW}/posts/{pasta.name}/{img.name}?v={versao}"


def resumo(pasta: Path, post: dict):
    dias = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
    data = datetime.date.fromisoformat(str(post["data"]))
    quando = f"{dias[data.weekday()]} {data:%d/%m} às {posts.hora(post)}"
    tags = " ".join("#" + t.lstrip("#") for t in post.get("hashtags", []))
    legenda = (post.get("legenda") or "").strip()
    texto = f"📅 {quando} · {post.get('formato')} · {post.get('pilar', '')}\n\n{legenda}\n\n{tags}".strip()
    if post.get("revisar"):
        texto = "⚠️ Confira as informações clínicas deste post.\n\n" + texto
    if post.get("bloqueio"):
        texto = f"⏸ Bloqueado: {post['bloqueio']} (mesmo aprovado, só publica depois de liberado)\n\n" + texto
    return texto[:4000]


def botoes(pasta: Path):
    return {"inline_keyboard": [[
        {"text": "✅ Aprovar", "callback_data": f"ok|{pasta.name}"},
        {"text": "✏️ Ajustar", "callback_data": f"aj|{pasta.name}"},
        {"text": "❌ Recusar", "callback_data": f"no|{pasta.name}"},
    ]]}


def enviar():
    for pasta in posts.todos():
        post = posts.carregar(pasta)
        if post.get("status", "rascunho") != "rascunho" or post.get("telegram_msg"):
            continue
        imagens = sorted(pasta.glob("slide-*.jpg"))
        if not imagens:
            continue
        antiga = post.pop("substitui_msg", None)
        for chat in CHATS:
            if antiga:  # tira os botões da versão anterior para não aprovar a errada
                try:
                    tg("editMessageText", chat_id=chat, message_id=antiga,
                       text="🔄 Substituído por uma versão nova (logo abaixo).")
                except RuntimeError:
                    pass
            midia = [{"type": "photo", "media": url_imagem(pasta, i)} for i in imagens[:10]]
            if len(midia) == 1:
                tg("sendPhoto", chat_id=chat, photo=midia[0]["media"])
            else:
                tg("sendMediaGroup", chat_id=chat, media=midia)
            msg = responder(chat, resumo(pasta, post), reply_markup=botoes(pasta))
        post["telegram_msg"] = msg["message_id"]
        post.pop("aguardando_ajuste", None)
        posts.salvar(pasta, post)
        print(f"enviado: {pasta.name}")


# ---------- processar ----------

def carregar_estado():
    return json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {"offset": 0}


def confirmar_toque(cb, texto=None):
    """O aviso rápido do Telegram expira em minutos; como o bot roda a cada 10 min, é só um bônus."""
    try:
        tg("answerCallbackQuery", callback_query_id=cb["id"], **({"text": texto} if texto else {}))
    except RuntimeError:
        pass


def marcar_mensagem(cb, rotulo):
    """Troca os botões da mensagem pelo resultado, para não clicar duas vezes."""
    msg = cb.get("message") or {}
    texto = (msg.get("text") or "")[:3900]
    try:
        tg("editMessageText", chat_id=msg["chat"]["id"], message_id=msg["message_id"], text=f"{rotulo}\n\n{texto}")
    except RuntimeError:
        pass


def tratar_botao(cb):
    acao, _, nome = cb.get("data", "").partition("|")
    pasta = posts.POSTS / nome
    chat = cb["message"]["chat"]["id"]
    if not (pasta / "post.yaml").exists():
        confirmar_toque(cb, "Esse post não existe mais.")
        return
    post = posts.carregar(pasta)
    if post.get("status") == "publicado":
        confirmar_toque(cb, "Esse post já foi publicado.")
        return

    if acao == "ok":
        post["status"] = "aprovado"
        confirmar_toque(cb, "Aprovado! ✅")
        marcar_mensagem(cb, ROTULO["aprovado"])
    elif acao == "no":
        post["status"] = "recusado"
        confirmar_toque(cb, "Recusado.")
        marcar_mensagem(cb, ROTULO["recusado"])
    elif acao == "aj":
        for outra in posts.todos():  # só um ajuste aguardando por vez
            p = posts.carregar(outra)
            if p.pop("aguardando_ajuste", None):
                posts.salvar(outra, p)
        post["aguardando_ajuste"] = True
        confirmar_toque(cb)
        marcar_mensagem(cb, ROTULO["ajuste"])
        responder(chat, "Me diga o que você quer mudar neste post (título, texto, tom, foto, tema…). "
                        "Pode escrever do seu jeito 💬")
    posts.salvar(pasta, post)
    print(f"{acao}: {nome}")


def tratar_texto(msg):
    chat = msg["chat"]["id"]
    texto = (msg.get("text") or "").strip()
    pendente = next((p for p in posts.todos() if posts.carregar(p).get("aguardando_ajuste")), None)
    if not pendente or texto.startswith("/"):
        responder(chat, "Oi! 💖 Os posts da semana chegam por aqui. Para pedir uma mudança, "
                        "toque em ✏️ Ajustar no post e depois me escreva o que quer.")
        return

    # Sem custo extra: o bot só anota o pedido; quem aplica é a rotina diária do agente (dentro da assinatura).
    post = posts.carregar(pendente)
    post.pop("aguardando_ajuste", None)
    post.setdefault("pedidos_ajuste", []).append(texto)
    posts.salvar(pendente, post)
    responder(chat, "Anotei o seu pedido ✍️ Amanhã cedo te mando a nova versão para aprovar.")
    print(f"pedido de ajuste anotado: {pendente.name}")


def processar():
    estado = carregar_estado()
    for u in tg("getUpdates", offset=estado["offset"], timeout=0):
        estado["offset"] = u["update_id"] + 1
        if "callback_query" in u:
            cb = u["callback_query"]
            if cb["message"]["chat"]["id"] in CHATS:
                tratar_botao(cb)
        elif "message" in u and u["message"]["chat"]["id"] in CHATS:
            tratar_texto(u["message"])
    ESTADO.parent.mkdir(exist_ok=True)
    ESTADO.write_text(json.dumps(estado), encoding="utf-8")


def main():
    if not (TOKEN and CHATS):
        print("TELEGRAM_TOKEN ou TELEGRAM_CHAT_IDS ausentes — nada a fazer.")
        return 0
    {"processar": processar, "enviar": enviar}[sys.argv[1]]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
