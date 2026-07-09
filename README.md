# CONVIVA - Modulo de Votacao

Implementacao web em Python puro para o recorte de votacao do sistema CONVIVA.
O projeto segue MVC Web e usa PostgreSQL, com suporte a conexão pelo Supabase.

## Funcionalidades

- Entrar no sistema com e-mail e senha.
- Criar votacao vinculada a uma pauta de reuniao.
- Iniciar e encerrar votacao durante a reuniao.
- Exibir a votacao dentro da tela da reuniao para participantes presentes.
- Bloquear acesso a reuniao para usuarios nao convidados.
- Permitir voto apenas para usuario convidado, logado e presente na reuniao.
- Impedir voto duplicado por pauta.
- Calcular peso do voto pelas unidades vinculadas ao proprietario.
- Registrar voto de inadimplente com peso 0.
- Ocultar resultados ate o encerramento da votacao.
- Exibir relatorio nominal em votacao aberta e manter sigilo em votacao fechada.
- Registrar logs de auditoria com usuario, acao, data/hora, IP e navegador.

## Arquitetura

```text
app.py                         servidor HTTP e roteamento inicial
conviva/controllers.py          controladores MVC e endpoints JSON
conviva/services.py             regras de negocio e casos de uso
conviva/models.py               entidades, banco de dados e repositorios
conviva/templates.py            views HTML
conviva/security.py             hash de senha, token e cookies
static/                         CSS e JavaScript da tela de reuniao
schema.sql                      schema PostgreSQL
seed.py                         massa de dados para demonstracao
```

## Como executar

Requisitos: Python 3.10 ou superior e um banco PostgreSQL/Supabase.

Configure uma das variáveis abaixo com a URL Postgres do Supabase:

```bash
export STORAGE_POSTGRES_URL="postgres://..."
# ou
export DATABASE_URL="postgres://..."
```

Instale as dependências e inicialize os dados de demonstração:

```bash
python seed.py
python app.py
```

Acesse:

```text
http://localhost:8000
```

## Usuarios de teste

Todos usam a senha `senha123`.

| Perfil | E-mail |
|---|---|
| Administrador/Sindico | `admin@conviva.com` |
| Proprietario | `diego@email.com` |
| Proprietario | `gabriel@email.com` |
| Proprietaria inadimplente | `marina@email.com` |
| Procuradora | `patricia@email.com` |
| Usuario nao convidado | `visitante@email.com` |

## Fluxo rapido de apresentacao

1. Entre como `admin@conviva.com`.
2. Abra a reuniao "Assembleia Geral Ordinaria".
3. Inicie a votacao "Aprovacao das contas de 2025".
4. Em outro navegador ou aba anonima, entre como `diego@email.com` e abra a mesma reuniao.
5. A votacao aparece no painel lateral da reuniao; confirme um voto.
6. Repita com `gabriel@email.com` para demonstrar peso diferente.
7. Entre com `marina@email.com` para demonstrar voto registrado com peso 0.
8. Volte ao administrador, encerre a votacao e abra o resultado.

## Observacoes de escopo

A tela de reuniao implementa o necessario para o fluxo de votacao: area de video integrada,
controle de participantes presentes e painel de votacao em tempo real por atualizacao automatica.
Videoconferencia real, transcricao, envio de e-mail e armazenamento de gravacoes ficam fora deste
recorte.
