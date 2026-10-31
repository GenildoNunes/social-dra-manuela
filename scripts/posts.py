"""Leitura e escrita dos post.yaml, mantendo textos longos legíveis (bloco `|`)."""
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
POSTS = RAIZ / "posts"


class _Dumper(yaml.SafeDumper):
    pass


def _str(dumper, valor):
    estilo = "|" if "\n" in valor else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", valor, style=estilo)


_Dumper.add_representer(str, _str)


def carregar(pasta: Path) -> dict:
    return yaml.safe_load((pasta / "post.yaml").read_text(encoding="utf-8"))


def salvar(pasta: Path, post: dict):
    texto = yaml.dump(post, Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=1000)
    (pasta / "post.yaml").write_text(texto, encoding="utf-8")


def hora(post: dict) -> str:
    """'HH:MM'. O YAML lê `12:00` sem aspas como 720 (minutos, base 60) — normaliza os dois casos."""
    h = post.get("hora", "12:00")
    return f"{h // 60:02d}:{h % 60:02d}" if isinstance(h, int) else str(h)


def todos():
    return sorted(p for p in POSTS.iterdir() if (p / "post.yaml").exists())
