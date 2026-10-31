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
| `scripts/render.py` | Gera as imagens (JPEG) a partir do `post.yaml` e a `posts/previa.html` |
| `scripts/publicar.py` | Publica os posts `aprovado` no horário (roda no GitHub Actions) |
| `scripts/configurar_meta.py` | Configuração única do token do Instagram |
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
- [x] Publicador automático (Instagram Graph API + GitHub Actions) — falta [configurar o token](docs/configurar-instagram.md)
- [x] Bot do Telegram ("Sandra", @SecretariaDrManuela_bot): aprovação ✅ ✏️ ❌ a cada 10 min (7h–0h)
- [ ] Ajuste por IA no bot — falta o segredo `ANTHROPIC_API_KEY`
- [ ] Envio de vídeos/Reels pela Dra. no bot
- [ ] Agente semanal agendado na nuvem
- [ ] Relatório mensal de desempenho
