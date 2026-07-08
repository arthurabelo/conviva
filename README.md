# CONVIVA - Módulo de Votação

Protótipo acadêmico do módulo de votação do CONVIVA, baseado no documento `CONVIVA_ERSW_9_0.pdf`.

## Funcionalidades

- Entrar no sistema por e-mail e senha.
- Bloquear sessão simultânea da mesma conta.
- Criar votação vinculada a uma reunião e pauta.
- Configurar votação aberta ou fechada.
- Configurar tipo de resposta: escolha única, múltipla escolha ou eleição de nomes.
- Iniciar e encerrar votação durante a reunião.
- Registrar voto apenas de participante presente.
- Calcular resultado por peso de voto.
- Ocultar resultado até o encerramento.
- Exibir relatório nominal apenas em votação aberta.
- Registrar logs de auditoria.

## Arquitetura

A implementação usa MVC Web em Python, organizada como monólito modular:

- `app.py`: entrada HTTP/WSGI e roteamento.
- `conviva_votacao/controllers.py`: controle das requisições.
- `conviva_votacao/services.py`: regras de negócio.
- `conviva_votacao/models.py`: acesso ao banco de dados.
- `conviva_votacao/templates.py`: HTML das telas.
- `conviva_votacao/security.py`: autenticação, senha e sessão.
- `schema.sql`: modelo relacional.
- `seed.py`: carga inicial para demonstração.

O banco padrão local é SQLite, por ser suficiente para a apresentação e não exigir Docker. PostgreSQL continua disponível quando `DATABASE_URL` estiver configurado.

## Como executar localmente

```bash
python app.py
```

Acesse:

```text
http://localhost:8000
```

O arquivo `app.py` prepara o banco local e insere dados de demonstração automaticamente.

## Executar com PostgreSQL e Docker

```bash
docker compose up --build
```

O `docker-compose.yml` configura PostgreSQL 16 e passa a `DATABASE_URL` para a aplicação.

## Usuários de teste

| Perfil | E-mail | Senha |
|---|---|---|
| Administrador/Síndico | admin@conviva.com | senha123 |
| Proprietário | diego@email.com | senha123 |
| Proprietário | gabriel@email.com | senha123 |

## Roteiro rápido

1. Entrar como `admin@conviva.com`.
2. Abrir **Votações**.
3. Criar uma votação pré-configurada.
4. Iniciar a votação.
5. Sair e entrar como `diego@email.com`.
6. Registrar voto.
7. Sair e entrar como `gabriel@email.com`.
8. Registrar outro voto.
9. Voltar como administrador.
10. Encerrar a votação.
11. Abrir o resultado.
12. Conferir a auditoria.
