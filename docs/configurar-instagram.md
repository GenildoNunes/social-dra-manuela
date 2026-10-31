# Configurar a publicação no Instagram (uma vez só)

Caminho usado: **API do Instagram com login pelo Instagram** — conecta direto na conta profissional
@dramanuelagondim, sem depender de Página do Facebook.

## 1. Criar o app no Meta for Developers

1. https://developers.facebook.com → **Meus apps** → **Criar app** (logado no Facebook da Manuela).
2. Nome: `Social Dra Manuela`.
3. Caso de uso: filtro **Gerenciamento de conteúdo** → **Gerenciar mensagens e conteúdo no Instagram**.
4. Empresa: **Não quero conectar um portfólio empresarial agora**.
5. Avançar até **Criar app**.

> O app fica em **modo de desenvolvimento** — suficiente, porque só a própria conta vai usá-lo.

## 2. Gerar o token do Instagram

1. No painel do app: **Casos de uso → Gerenciar mensagens e conteúdo no Instagram → Personalizar**
   → **Configuração da API com login do Instagram**.
2. Em **Gerar tokens de acesso**, clique em **Adicionar conta** e entre com o **Instagram @dramanuelagondim**.
   Autorize as permissões (é a Dra. Manuela/vocês quem decide e confirma).
3. Ao lado da conta adicionada, clique em **Gerar token** e copie (não envie a ninguém).

## 3. Token do GitHub para a renovação automática (opcional, recomendado)

O token do Instagram vale 60 dias; o robô renova toda segunda — para isso ele precisa de permissão
para atualizar o segredo:

1. https://github.com/settings/personal-access-tokens/new
2. Nome `renovar-token-instagram` · Expiração: a maior possível.
3. **Repository access → Only select repositories → social-dra-manuela**.
4. **Permissions → Repository permissions → Secrets: Read and write**.
5. **Generate token** e copie.

## 4. Rodar o configurador

```
python scripts/configurar_meta.py
```

Cole o token do Instagram e, em seguida, o token do GitHub. Nada aparece na tela nem fica salvo no PC.

## 5. Testar

GitHub → **Actions → Publicar no Instagram → Run workflow** (deixe "Só simular" marcado).
