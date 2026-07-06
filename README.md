# CONVIVA - Módulo de Votação com Docker e PostgreSQL

Protótipo acadêmico do módulo de votação do CONVIVA, baseado no `CONVIVA_ERSW_9_0.docx`.

Funcionalidades implementadas:

- Entrar no sistema por e-mail e senha.
- Criar votação.
- Iniciar, executar e encerrar votação.
- Registrar voto único por usuário presente.
- Calcular resultado por peso de voto.
- Exibir resultado aberto/fechado.
- Registrar logs de auditoria.

## Arquitetura

A implementação usa um monólito modular MVC Web em três camadas, executado por Docker Compose:

- `app-conviva`: aplicação Web Python.
- `db-postgres`: banco PostgreSQL 16.
- `pgdata`: volume Docker para persistência do banco.

## Como executar

Na pasta do projeto:

```bash
docker compose up --build
```

Acesse:

```text
http://localhost:8000
```

O container da aplicação executa `python seed.py` antes de iniciar o servidor. Isso recria as tabelas e popula dados de teste.

## Deploy no Vercel

Para publicar no Vercel automaticamente após cada push na branch `main`, configure o projeto do Vercel e adicione os seguintes segredos no GitHub:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

O repositório usa estes arquivos:
- `vercel.json` para informar o build do Python e rotear todas as requisições para `app.py`.
- `.github/workflows/vercel-deploy.yml` para disparar deploy automático ao fazer push.

No Vercel, defina também a variável de ambiente `DATABASE_URL` com a URL do banco PostgreSQL acessível pelo deploy.

##  Troubleshooting: Docker Engine Stuck "Starting" (Windows/WSL)

Para publicar no Vercel automaticamente após cada push na branch `main`, configure o projeto do Vercel e adicione os seguintes segredos no GitHub:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

O repositório usa estes arquivos:
- `vercel.json` para informar o build do Python e rotear todas as requisições para `app.py`.
- `.github/workflows/vercel-deploy.yml` para disparar deploy automático ao fazer push.

No Vercel, defina também a variável de ambiente `DATABASE_URL` com a URL do banco PostgreSQL acessível pelo deploy.

##  Troubleshooting: Docker Engine Stuck "Starting" (Windows/WSL)

Se o Docker Desktop travar infinitamente na tela de inicialização, o subsistema WSL pode estar corrompido. Siga os passos abaixo no **PowerShell como Administrador** para resetar o ambiente:

1. **Derrube o WSL e limpe as distros do Docker:**
   ```powershell
   wsl --shutdown
   wsl --unregister docker-desktop
   ```
   *(Nota: Se o comando para `docker-desktop-data` der erro de "distribuição não encontrada", ignore. Versões recentes concentram tudo na principal).*

2. **Atualize o WSL:**
   ```powershell
   wsl --update

   ```

3. **Limpe os caches locais (opcional):**
   Exclua as pastas `Docker` em `%AppData%` e `%LocalAppData%` caso o erro persista.

4. **Reinicie o Docker Desktop** para que ele recrie o ambiente do zero.

## Usuários de teste

| Perfil | E-mail | Senha |
|---|---|---|
| Administrador/Síndico | admin@conviva.com | senha123 |
| Proprietário | diego@email.com | senha123 |
| Proprietário | gabriel@email.com | senha123 |

## Roteiro de demonstração

1. Entrar como `admin@conviva.com`.
2. Abrir **Votações**.
3. Criar uma votação nova.
4. Iniciar a votação.
5. Sair e entrar como `diego@email.com`.
6. Registrar um voto.
7. Sair e entrar como `gabriel@email.com`.
8. Registrar outro voto.
9. Voltar como administrador.
10. Encerrar a votação.
11. Abrir o resultado.
12. Conferir a auditoria.

## Observação

O `seed.py` reinicia o banco a cada subida da aplicação.
