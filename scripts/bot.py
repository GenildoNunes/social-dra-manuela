"""Bot de aprovação no Telegram ("Sandra").

    python scripts/bot.py processar   # lê respostas: ✅ aprova, ❌ recusa, ✏️ pede ajuste (texto da Dra.)
    python scripts/bot.py enviar      # manda para aprovação os rascunhos novos ou refeitos

Roda no GitHub Actions (.github/workflows/bot.yml). Variáveis de ambiente:
    TELEGRAM_TOKEN, TELEGRAM_CHAT_IDS (separados por vírgula), REPO_RAW_URL
    ANTHROPIC_API_KEY (opcional): sem ela, o pedido de ajuste fica anotado no post para o agente semanal.

Quem aprova é só quem está em TELEGRAM_CHAT_IDS; mensagens de outras pessoas são ignoradas.
"""
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import requests
import yaml

import posts

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHATS = {int(c) for c in os.environ.get("TELEGRAM_CHAT_IDS", "").split(",") if c.strip()}
RAW = os.environ.get("REPO_RAW_URL", "").rstrip("/")
ESTADO = posts.RAIZ / "estado" / "telegram.json"
PRECISA_RENDER = posts.RAIZ / ".precisa_render"  # pastas a re-renderizar, uma por linha

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
        for chat in CHATS:
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
        tg("answerCallbackQuery", callback_query_id=cb["id"], text="Esse post não existe mais.")
        return
    post = posts.carregar(pasta)
    if post.get("status") == "publicado":
        tg("answerCallbackQuery", callback_query_id=cb["id"], text="Esse post já foi publicado.")
        return

    if acao == "ok":
        post["status"] = "aprovado"
        tg("answerCallbackQuery", callback_query_id=cb["id"], text="Aprovado! ✅")
        marcar_mensagem(cb, ROTULO["aprovado"])
    elif acao == "no":
        post["status"] = "recusado"
        tg("answerCallbackQuery", callback_query_id=cb["id"], text="Recusado.")
        marcar_mensagem(cb, ROTULO["recusado"])
    elif acao == "aj":
        for outra in posts.todos():  # só um ajuste aguardando por vez
            p = posts.carregar(outra)
            if p.pop("aguardando_ajuste", None):
                posts.salvar(outra, p)
        post["aguardando_ajuste"] = True
        tg("answerCallbackQuery", callback_query_id=cb["id"])
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

    post = posts.carregar(pendente)
    post.pop("aguardando_ajuste", None)
    post.setdefault("pedidos_ajuste", []).append(texto)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        posts.salvar(pendente, post)
        responder(chat, "Anotei o seu pedido ✍️ O ajuste será feito na próxima rodada de criação dos posts.")
        return

    responder(chat, "Ajustando… em alguns minutos te mando a nova versão ⏳")
    try:
        novo = reescrever(post, texto)
    except Exception as e:  # falha da IA não pode travar o bot
        print(f"ajuste falhou: {type(e).__name__}: {e}")
        posts.salvar(pendente, post)
        responder(chat, "Não consegui ajustar agora 😕 Deixei o pedido anotado para a próxima rodada.")
        return
    posts.salvar(pendente, novo)
    with PRECISA_RENDER.open("a", encoding="utf-8") as f:
        f.write(pendente.name + "\n")
    print(f"ajustado: {pendente.name}")


def reescrever(post: dict, pedido: str) -> dict:
    import anthropic

    contexto = "\n\n".join((posts.RAIZ / arq).read_text(encoding="utf-8")
                           for arq in ("CLAUDE.md", "marca/guia.md", "marca/estrategia.md"))
    atual = {k: v for k, v in post.items() if k not in ("telegram_msg", "pedidos_ajuste")}
    resposta = anthropic.Anthropic().beta.messages.create(
        model="claude-opus-5-5",
        max_tokens=16000,
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=[{"type": "text", "text": contexto, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": (
            "A Dra. Manuela pediu um ajuste neste post. Reescreva o post.yaml aplicando o pedido, "
            "respeitando o guia de marca e as regras do CFO. Mantenha data e hora, a menos que ela peça para mudar. "
            "Responda somente com o YAML completo, sem explicações.\n\n"
            f"Pedido da Dra.: {pedido}\n\npost.yaml atual:\n"
            + yaml.safe_dump(atual, allow_unicode=True, sort_keys=False, default_flow_style=False))}],
    )
    if resposta.stop_reason == "refusal":
        raise RuntimeError("pedido recusado pelo modelo")
    texto = next(b.text for b in resposta.content if b.type == "text")
    texto = re.sub(r"^```(?:yaml)?\s*|\s*```$", "", texto.strip())
    novo = yaml.safe_load(texto)
    if not isinstance(novo, dict) or not novo.get("slides"):
        raise ValueError("resposta sem slides")
    novo["status"] = "rascunho"  # volta para aprovação
    novo["pedidos_ajuste"] = post.get("pedidos_ajuste", [])
    return novo


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
