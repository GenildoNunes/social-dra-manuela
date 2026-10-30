# Social Dra. Manuela Gondim 🦷💖

Esteira automática de conteúdo para o Instagram **@dramanuelagondim**.

```
Agente (semanal) ──► posts/ (rascunho) ──► aprovação no Telegram ──► publicador diário ──► Instagram
```

## Estrutura

| Pasta | O que tem |
|---|---|
| `marca/` | Guia de marca, tom de voz, regras do CFO e estratégia editorial |
| `posts/` | Um post por pasta: `post.yaml` + imagens `slide-XX.png` geradas |
| `pautas/` | Pedidos pontuais para o agente (ex.: "falar de clareamento antes do Natal") |
| `templates/` | Template HTML das artes (identidade visual) |
| `scripts/render.py` | Gera as imagens a partir do `post.yaml` e a `posts/previa.html` |
| `CLAUDE.md` | Instruções do agente de conteúdo |

## Status de um post

`rascunho` → `aprovado` → `publicado` (ou `recusado`)

## Rodar localmente

```bash
pip install -r requirements.txt
python -m playwright install chromium
python scripts/render.py --todos
```

Abra `posts/previa.html` para ver a semana.

## Roadmap

- [x] Guia de marca, estratégia e templates
- [x] Gerador de artes + prévia
- [ ] Publicador automático (Instagram Graph API + GitHub Actions)
- [ ] Bot do Telegram: aprovação e envio de vídeos pela Dra.
- [ ] Agente semanal agendado na nuvem
- [ ] Relatório mensal de desempenho
