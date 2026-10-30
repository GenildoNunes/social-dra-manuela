# Configurar a publicação no Instagram (uma vez só)

Tempo: ~15 minutos. Use o Facebook que **administra a Página da clínica** (o mesmo do Business Suite).

## 1. Criar o app no Meta for Developers

1. Acesse https://developers.facebook.com/apps e clique em **Criar app**.
   - Se for o primeiro acesso, ele pede para virar desenvolvedor: confirme com o seu Facebook.
2. Nome do app: `Social Dra Manuela` · e-mail: o seu.
3. Caso de uso: escolha **Outro** → tipo **Empresa** (Business).
   - Se pedir um portfólio empresarial, selecione o da clínica (ou "Não quero conectar agora").
4. No painel do app, em **Adicionar produtos**, adicione **Instagram** e escolha a configuração
   **com Login do Facebook** (Instagram API with Facebook Login).

> O app fica em **modo de desenvolvimento** — é o suficiente, porque só a conta da própria
> clínica vai usá-lo. Não precisa passar por revisão do Meta.

## 2. Anotar App ID e Chave Secreta

**Configurações do app → Básico**: copie o **ID do app** e clique em **Mostrar** na **Chave Secreta**.
Não envie essas informações a ninguém (nem no chat) — você vai colar direto no terminal no passo 4.

## 3. Gerar o token no Graph API Explorer

1. Abra https://developers.facebook.com/tools/explorer
2. No canto direito, em **Aplicativo da Meta**, selecione `Social Dra Manuela`.
3. Em **Usuário ou Página**, escolha **Obter token de acesso do usuário**.
4. Em **Permissões**, adicione:
   - `pages_show_list`
   - `pages_read_engagement`
   - `instagram_basic`
   - `instagram_content_publish`
   - `business_management`
5. Clique em **Generate Access Token**. Na janela do Facebook, **marque a Página da clínica e o
   Instagram @dramanuelagondim** e confirme.
6. Copie o token gerado (começa com `EAA...`).

## 4. Rodar o configurador

No terminal, dentro da pasta do projeto:

```
python scripts/configurar_meta.py
```

Cole o App ID, a Chave Secreta e o token quando pedir (eles não aparecem na tela).
O script troca por um token **sem validade**, descobre o ID do Instagram e salva tudo como
segredo no GitHub. Ao final deve aparecer `✓ Segredos IG_TOKEN e IG_USER_ID salvos no GitHub`.

## 5. Testar

No GitHub: **Actions → Publicar no Instagram → Run workflow** (deixe "Só simular" marcado).
