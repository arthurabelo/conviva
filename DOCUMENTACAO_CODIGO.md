# Documentacao do Codigo

Este documento concentra a explicacao das classes, metodos e funcoes implementadas nos arquivos Python do sistema CONVIVA.

## `app.py`

Arquivo de entrada da aplicacao web. Ele configura o servidor HTTP, recebe requisicoes do navegador e encaminha tudo para o controller principal.

### Constantes

- `HOST`: define o endereco em que o servidor escuta. Por padrao usa `0.0.0.0`.
- `PORT`: define a porta do servidor. Por padrao usa `8000`, podendo ser alterada pela variavel de ambiente `PORT`.

### Classe `ConvivaHandler`

Herda de `BaseHTTPRequestHandler` e funciona como adaptador entre o servidor HTTP da biblioteca padrao do Python e a camada de controller do sistema.

#### Atributos

- `controller`: instancia unica de `ApplicationController`, responsavel por executar as regras de roteamento e chamar os casos de uso.

#### Metodo `do_GET(self) -> None`

Executado automaticamente pelo servidor quando chega uma requisicao HTTP `GET`.

#### Metodo `do_POST(self) -> None`

Executado automaticamente pelo servidor quando chega uma requisicao HTTP `POST`.

#### Metodo `log_message(self, format: str, *args) -> None`

Controla a exibicao de logs HTTP no terminal. Por padrao, o sistema nao imprime cada requisicao. Se a variavel `CONVIVA_HTTP_LOG` estiver como `1`, o comportamento padrao de log do `BaseHTTPRequestHandler` e ativado.

#### Metodo `_dispatch(self) -> None`

Converte a requisicao HTTP em uma chamada para `ApplicationController.dispatch`. Ele extrai caminho, metodo, query string, cabecalhos, corpo da requisicao e endereco IP do cliente. Depois recebe um objeto `Response` e envia status, cabecalhos e corpo de volta ao navegador.

### Funcao `main() -> None`

Inicializa o banco de dados, cria o servidor `ThreadingHTTPServer`, mostra a URL local no terminal e mantem a aplicacao rodando com `serve_forever`.

## `seed.py`

Arquivo usado para recriar o banco PostgreSQL/Supabase e popular dados de demonstração.

### Funcao `main() -> None`

Recria o banco do zero, gera a senha padrao `senha123`, cadastra condominio, usuarios, lotes, reuniao, pautas, anexos, convites, uma procuracao e uma votacao inicial agendada. Ao final, imprime os dados de acesso para teste.

## `conviva/__init__.py`

Arquivo que marca a pasta `conviva` como pacote Python. Nao contem classes, metodos ou funcoes de negocio.

## `conviva/security.py`

Arquivo responsavel por recursos de seguranca: hash de senha, verificacao de senha, assinatura de tokens e leitura de cookies.

### Classe `PasswordHasher`

Encapsula a geracao e validacao de hashes de senha usando PBKDF2 (Password-Based Key Derivation Function 2) com SHA-256.

#### Metodo `hash(self, password: str, salt: bytes | None = None) -> str`

Gera um hash seguro para a senha recebida. Se nenhum salt for informado, cria um salt aleatorio com `os.urandom`. O resultado final e uma string no formato `salt$hash`, ambos codificados em Base64.

#### Metodo `verify(self, password: str, stored: str) -> bool`

Compara uma senha digitada com o hash armazenado. A funcao separa o salt e o digest gravados, recalcula o PBKDF2 e usa `hmac.compare_digest` para evitar comparacoes inseguras. Retorna `True` quando a senha confere e `False` quando nao confere ou quando o valor armazenado esta invalido.

### Classe `TokenSigner`

Cria, assina, valida e resume tokens de sessao. Usa HMAC com SHA-256 para impedir adulteracao do token.

#### Metodo `__init__(self, secret_key: str)`

Recebe a chave secreta da aplicacao e a guarda em bytes para uso nas assinaturas HMAC.

#### Metodo `_sign(self, payload: bytes) -> bytes`

Metodo interno que calcula a assinatura HMAC de um payload.

#### Metodo `build(self, user_id: int, expires_at: int) -> str`

Cria um token de sessao contendo ID do usuario, data de expiracao em timestamp e um trecho aleatorio. O payload e assinado e depois codificado em Base64 URL-safe.

#### Metodo `parse(self, token: str) -> int | None`

Valida um token recebido do cookie. A funcao decodifica o Base64, separa payload e assinatura, confere se a assinatura e valida e verifica se o token ainda nao expirou. Retorna o ID do usuario quando o token e valido; caso contrario retorna `None`.

#### Metodo estatico `token_hash(token: str) -> str`

Gera um SHA-256 do token. Esse resumo e armazenado no banco para que o token completo nao precise ser persistido.

### Funcao `parse_cookie(header: str | None) -> dict[str, str]`

Converte o cabecalho HTTP `Cookie` em um dicionario simples, permitindo recuperar valores como `conviva_session`.

## `conviva/models.py`

Arquivo da camada Model/Repository. Contém entidades simples, conexão com PostgreSQL/Supabase e repositórios responsáveis por consultas e comandos SQL.

### Constantes

- `BASE_DIR`: pasta base da implementacao.
- `SCHEMA_PATH`: caminho para `schema.sql`.
- `DATABASE_URL`: URL de conexao PostgreSQL, lida de `DATABASE_URL`, `STORAGE_POSTGRES_URL`, `STORAGE_POSTGRES_PRISMA_URL` ou `STORAGE_POSTGRES_URL_NON_POOLING`.

### Classe `Usuario`

Dataclass imutavel que representa um usuario ativo do sistema.

#### Atributos

- `id_usuario`: identificador no banco.
- `nome_completo`: nome exibido nas telas e relatorios.
- `email`: e-mail usado no login.
- `tipo_usuario`: perfil do usuario, como `administrador`, `proprietario` ou `procurador`.
- `ativo`: indica se o usuario esta ativo.

#### Metodo de classe `from_row(cls, row: dict[str, Any]) -> Usuario`

Converte um dicionario vindo do banco em um objeto `Usuario`, garantindo os tipos corretos dos campos principais.

### Classe `Votacao`

Dataclass imutavel que representa uma votacao junto com seus dados essenciais de reuniao e condominio.

#### Atributos

- `id_votacao`: identificador da votacao.
- `id_pauta`: pauta vinculada.
- `id_reuniao`: reuniao vinculada.
- `id_condominio`: condominio da reuniao.
- `assunto`: assunto da votacao.
- `pergunta`: pergunta exibida ao eleitor.
- `tipo_votacao`: `aberta` ou `fechada`.
- `tipo_resposta`: `escolha_unica`, `multipla_escolha` ou `eleicao`.
- `tempo_resposta`: tempo configurado em minutos.
- `max_marcacoes`: quantidade maxima de opcoes selecionaveis.
- `status`: `agendada`, `ativa`, `encerrada` ou `invalidada`.
- `iniciou_em`: data e hora de inicio.
- `encerra_em`: data e hora prevista de encerramento.
- `encerrada_em`: data e hora de encerramento real.

#### Metodo de classe `from_row(cls, row: dict[str, Any]) -> Votacao`

Converte uma linha do banco em objeto `Votacao`, normalizando campos numericos e mantendo campos opcionais de data/hora.

### Classe `Database`

Classe de infraestrutura que centraliza conexao, criacao do banco e execucao de SQL.

#### Metodo `__init__(self, url: str | None = DATABASE_URL)`

Define a URL PostgreSQL/Supabase usada pela instância.

#### Metodo `connect(self) -> psycopg.Connection`

Abre conexão PostgreSQL usando `psycopg` e configura retorno de linhas como dicionários.

#### Metodo `init_db(self) -> None`

Executa o script `schema.sql` para criar as tabelas que ainda nao existirem.

#### Metodo `reset_db(self) -> None`

Remove as tabelas conhecidas em ordem segura e depois recria o schema. E usado pelo `seed.py` para reiniciar a base de demonstracao.

#### Metodo `query(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]`

Executa uma consulta SQL que retorna varias linhas. Converte cada linha para dicionario.

#### Metodo `query_one(self, sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None`

Executa uma consulta SQL esperando no maximo uma linha. Retorna um dicionario quando encontra registro ou `None` quando nao encontra.

#### Metodo `execute(self, sql: str, params: Iterable[Any] = ()) -> int`

Executa comando SQL de escrita, confirma a transacao e retorna o `lastrowid`, util para inserts.

#### Metodo `execute_many(self, sql: str, seq_of_params: Iterable[Iterable[Any]]) -> None`

Executa o mesmo comando SQL para varios conjuntos de parametros, usado para inserts em lote.

### Classe `UsuarioRepository`

Repositorio de acesso aos usuarios.

#### Metodo `__init__(self, db: Database)`

Recebe a instancia de banco usada pelo repositorio.

#### Metodo `by_email(self, email: str) -> dict[str, Any] | None`

Busca um usuario ativo pelo e-mail. Normaliza o e-mail removendo espacos e convertendo para minusculas.

#### Metodo `by_id(self, id_usuario: int) -> dict[str, Any] | None`

Busca um usuario ativo pelo ID.

### Classe `ReuniaoRepository`

Repositorio de acesso a reunioes, convites, presenca, pautas e anexos de pauta.

#### Metodo `__init__(self, db: Database)`

Recebe a instancia de banco usada pelo repositorio.

#### Metodo `get(self, id_reuniao: int) -> dict[str, Any] | None`

Busca uma reuniao pelo ID e inclui o nome do condominio.

#### Metodo `list_for_user(self, user: dict[str, Any]) -> list[dict[str, Any]]`

Lista reunioes visiveis para um usuario. Administradores visualizam todas; outros perfis visualizam apenas reunioes em que constam como convidados.

#### Metodo `list_all(self) -> list[dict[str, Any]]`

Lista todas as reunioes ordenadas por data e hora.

#### Metodo `is_invited(self, id_usuario: int, id_reuniao: int) -> bool`

Verifica se um usuario recebeu convite confirmado para uma reuniao.

#### Metodo `is_present(self, id_usuario: int, id_reuniao: int) -> bool`

Verifica se o usuario esta marcado como presente na reuniao.

#### Metodo `mark_present(self, id_usuario: int, id_reuniao: int, now: str) -> None`

Marca o usuario como presente, registra horario de entrada se ainda nao existir e limpa horario de saida.

#### Metodo `mark_absent(self, id_usuario: int, id_reuniao: int, now: str) -> None`

Marca o usuario como ausente e registra o horario de saida.

#### Metodo `participantes(self, id_reuniao: int) -> list[dict[str, Any]]`

Lista participantes convidados da reuniao com nome, perfil, convite, presenca, entrada e saida.

#### Metodo `pautas(self, id_reuniao: int) -> list[dict[str, Any]]`

Lista as pautas vinculadas a uma reuniao.

#### Metodo `anexos_pauta(self, id_pauta: int) -> list[dict[str, Any]]`

Lista anexos cadastrados para uma pauta.

#### Metodo `all_pautas(self) -> list[dict[str, Any]]`

Lista todas as pautas com dados da reuniao correspondente, usada no formulario de criacao de votacao.

### Classe `VotacaoRepository`

Repositorio de acesso a votacoes, opcoes, votos, pesos, procuracoes e resultados.

#### Metodo `__init__(self, db: Database)`

Recebe a instancia de banco usada pelo repositorio.

#### Metodo `list_all(self) -> list[dict[str, Any]]`

Lista todas as votacoes com assunto da pauta e titulo da reuniao.

#### Metodo `list_for_meeting(self, id_reuniao: int) -> list[dict[str, Any]]`

Lista as votacoes vinculadas a uma reuniao especifica.

#### Metodo `get(self, id_votacao: int) -> dict[str, Any] | None`

Busca uma votacao por ID, incluindo pauta, reuniao, condominio e status da reuniao.

#### Metodo `active_for_meeting(self, id_reuniao: int) -> dict[str, Any] | None`

Busca a votacao ativa mais recente de uma reuniao.

#### Metodo `options(self, id_votacao: int) -> list[dict[str, Any]]`

Lista as opcoes de voto de uma votacao na ordem configurada.

#### Metodo `create(self, data: dict[str, Any], opcoes: list[str]) -> int`

Insere uma votacao com status `agendada` e cadastra suas opcoes. Retorna o ID da nova votacao.

#### Metodo `start(self, id_votacao: int, iniciou_em: str, encerra_em: str) -> None`

Atualiza a votacao para status `ativa`, registrando horario de inicio e prazo de encerramento.

#### Metodo `close(self, id_votacao: int, encerrada_em: str) -> None`

Atualiza a votacao para status `encerrada`.

#### Metodo `invalidate(self, id_votacao: int, encerrada_em: str) -> None`

Atualiza a votacao para status `invalidada`, usado em tentativa de voto nao autorizado.

#### Metodo `has_active_in_meeting(self, id_reuniao: int, except_id: int | None = None) -> bool`

Verifica se ja existe votacao ativa na reuniao. O parametro `except_id` permite ignorar uma votacao especifica.

#### Metodo `voto_by_representado(self, id_votacao: int, id_eleitor_representado: int) -> dict[str, Any] | None`

Busca voto registrado por um eleitor representado em uma votacao especifica.

#### Metodo `voto_by_pauta_representado(self, id_pauta: int, id_eleitor_representado: int) -> dict[str, Any] | None`

Busca voto registrado por um eleitor representado em qualquer votacao da mesma pauta. E a regra usada para impedir voto duplicado por pauta.

#### Metodo `record_vote(...) -> int`

Registra um voto, incluindo usuario responsavel, eleitor representado, procuracao quando existir, votacao, horario, peso, IP e navegador. Depois insere as opcoes escolhidas em `voto_escolha`. Retorna o ID do voto.

#### Metodo `peso_usuario(self, id_usuario: int, id_condominio: int) -> float`

Calcula o peso valido do usuario somando apenas lotes adimplentes. Lotes inadimplentes contribuem com peso zero.

#### Metodo `total_lotes(self, id_usuario: int, id_condominio: int) -> int`

Conta quantos lotes o usuario possui no condominio.

#### Metodo `proxy_for_owner(self, id_usuario: int, id_reuniao: int) -> dict[str, Any] | None`

Verifica se o proprietario transferiu voto para procurador ativo naquela reuniao.

#### Metodo `proxy_for_attorney(self, id_usuario: int, id_reuniao: int) -> dict[str, Any] | None`

Verifica se o usuario logado e procurador ativo de algum proprietario naquela reuniao.

#### Metodo `option_totals(self, id_votacao: int) -> list[dict[str, Any]]`

Calcula votos e peso acumulado por opcao de uma votacao.

#### Metodo `totalizadores(self, id_votacao: int) -> dict[str, Any]`

Calcula total geral de votos registrados e soma de pesos aplicados.

#### Metodo `votos_nominais(self, id_votacao: int, id_condominio: int) -> list[dict[str, Any]]`

Retorna o relatorio nominal de votos, com responsavel, eleitor representado, imoveis, opcao escolhida, peso e horario. E usado somente quando a votacao e aberta.

### Classe `AuditoriaRepository`

Repositorio de acesso aos logs de auditoria.

#### Metodo `__init__(self, db: Database)`

Recebe a instancia de banco usada pelo repositorio.

#### Metodo `record(self, id_usuario: int | None, acao: str, entidade: str, data_hora: str, ip: str, navegador: str) -> None`

Insere um registro de auditoria com usuario, acao, entidade, data/hora, IP e navegador.

#### Metodo `list_recent(self) -> list[dict[str, Any]]`

Lista os 100 logs mais recentes, incluindo nome do usuario quando existir.

## `conviva/services.py`

Arquivo da camada de servicos. Contem regras de negocio e orquestra os repositorios.

### Constante

- `DATE_FMT`: formato padrao de data e hora usado pelo sistema.

### Funcao `now_str() -> str`

Retorna a data e hora atual no formato `YYYY-MM-DD HH:MM:SS`.

### Funcao `parse_datetime(value: Any) -> datetime | None`

Converte strings de data/hora ou objetos `datetime` em `datetime`. Retorna `None` quando nao consegue converter.

### Classe `RequestMeta`

Dataclass imutavel que agrupa metadados da requisicao.

#### Atributos

- `ip`: endereco IP do cliente.
- `navegador`: conteudo do cabecalho `User-Agent`.

### Classe `AuditoriaService`

Servico que registra acoes relevantes do sistema.

#### Metodo `__init__(self, auditoria_repo: models.AuditoriaRepository)`

Recebe o repositorio responsavel por persistir logs.

#### Metodo `registrar(self, user: dict[str, Any] | None, acao: str, entidade: str, meta: RequestMeta) -> None`

Grava uma acao de auditoria usando usuario, acao, entidade, horario atual, IP e navegador.

### Classe `AuthService`

Servico de autenticacao, sessao e verificacao de perfil.

#### Metodo `__init__(self, db, usuarios, auditoria)`

Recebe banco, repositorio de usuarios e servico de auditoria. Tambem configura hasher de senha, duracao da sessao e assinador de tokens.

#### Metodo `authenticate(self, email: str, password: str, meta: RequestMeta) -> tuple[dict[str, Any] | None, str | None]`

Valida e-mail e senha. Quando a autenticacao e bem-sucedida, cria sessao, registra auditoria e retorna usuario e token. Quando falha, retorna `(None, None)`.

#### Metodo `create_session(self, id_usuario: int, meta: RequestMeta) -> str`

Encerra sessoes expiradas, impede sessao simultanea ativa para o mesmo usuario, cria token assinado e persiste o hash do token no banco.

#### Metodo `current_user(self, cookie_header: str | None) -> dict[str, Any] | None`

Recupera o usuario logado a partir do cookie de sessao. Valida assinatura do token, expiracao e existencia de sessao ativa no banco.

#### Metodo `logout(self, cookie_header: str | None, meta: RequestMeta) -> None`

Encerra a sessao atual no banco e registra a saida do usuario nos logs.

#### Metodo `cleanup_expired_sessions(self) -> None`

Marca como encerradas as sessoes expiradas.

#### Metodo estatico `is_admin(user: dict[str, Any] | None) -> bool`

Retorna `True` quando o usuario existe e possui perfil `administrador`.

### Classe `ReuniaoService`

Servico dos casos de uso ligados a reuniao e presenca.

#### Metodo `__init__(self, reunioes, auditoria)`

Recebe o repositorio de reunioes e o servico de auditoria.

#### Metodo `list_for_user(self, user: dict[str, Any]) -> list[dict[str, Any]]`

Lista reunioes disponiveis para o usuario, delegando a regra de consulta ao repositorio.

#### Metodo `enter(self, id_reuniao: int, user: dict[str, Any], meta: RequestMeta) -> dict[str, Any]`

Valida existencia da reuniao, confirma que o usuario foi convidado, marca presenca, registra auditoria e retorna os dados da reuniao.

#### Metodo `leave(self, id_reuniao: int, user: dict[str, Any], meta: RequestMeta) -> None`

Marca o usuario como ausente quando ele e convidado e registra auditoria de saida.

#### Metodo `participantes(self, id_reuniao: int) -> list[dict[str, Any]]`

Lista participantes da reuniao.

#### Metodo `pautas(self, id_reuniao: int) -> list[dict[str, Any]]`

Lista pautas da reuniao.

### Classe `VotingService`

Servico principal do modulo de votacao. Implementa as regras de criar, iniciar, encerrar, votar e apurar resultados.

#### Metodo `__init__(self, votacoes, reunioes, auditoria)`

Recebe repositorio de votacoes, repositorio de reunioes e servico de auditoria.

#### Metodo `list_all(self) -> list[dict[str, Any]]`

Encerra automaticamente votacoes expiradas e lista todas as votacoes.

#### Metodo `list_for_meeting(self, id_reuniao: int) -> list[dict[str, Any]]`

Encerra votacoes expiradas e lista votacoes de uma reuniao.

#### Metodo `create(self, form: dict[str, Any], user: dict[str, Any], meta: RequestMeta) -> int`

Valida que o usuario e administrador, extrai dados do formulario, valida configuracao, cria a votacao, registra auditoria e retorna o ID criado.

#### Metodo `_validate_voting_config(self, data: dict[str, Any], opcoes: list[str]) -> None`

Valida regras de cadastro: pauta obrigatoria, assunto e pergunta preenchidos, tipo de votacao valido, tipo de resposta valido, tempo positivo, pelo menos duas opcoes e limite de marcacoes coerente.

#### Metodo `start(self, id_votacao: int, user: dict[str, Any], meta: RequestMeta) -> None`

Valida permissao de administrador, votacao agendada, reuniao em andamento e ausencia de outra votacao ativa na mesma reuniao. Depois ativa a votacao, calcula horario de encerramento e registra auditoria.

#### Metodo `close(self, id_votacao: int, user: dict[str, Any], meta: RequestMeta) -> None`

Valida permissao de administrador e encerra votacoes agendadas ou ativas. Registra auditoria.

#### Metodo `active_payload_for_meeting(self, id_reuniao: int, user: dict[str, Any]) -> dict[str, Any]`

Monta os dados usados pelo painel de votacao da tela de reuniao. Verifica presenca, busca votacao ativa, calcula peso, identifica se o usuario pode votar, informa se ja votou e calcula segundos restantes.

#### Metodo `register_vote(self, id_votacao, escolhas_raw, user, meta) -> int`

Registra um voto. Antes, verifica expiracao, status ativo, convite, presenca, contexto de procuracao, voto duplicado por pauta e validade das escolhas. Depois grava voto, opcoes escolhidas e auditoria.

#### Metodo `_voter_context(self, votacao: dict[str, Any], user: dict[str, Any], fail_hard: bool) -> dict[str, Any]`

Determina quem e o eleitor representado e qual peso deve ser usado. Bloqueia proprietario que transferiu voto por procuracao, libera procurador ativo quando houver e calcula peso do proprietario comum.

#### Metodo `_validate_choices(self, votacao: dict[str, Any], escolhas: list[int], opcoes_validas: set[int]) -> None`

Valida se pelo menos uma opcao foi selecionada, se nao ha duplicidade, se as opcoes pertencem a votacao, se a votacao permite multiplas escolhas e se o limite de marcacoes foi respeitado.

#### Metodo `result(self, id_votacao: int) -> dict[str, Any]`

Apura o resultado de uma votacao. Encerra automaticamente se estiver expirada, calcula totais por opcao, total geral de votos, peso total e relatorio nominal quando a votacao e aberta.

#### Metodo `seconds_left(self, votacao: dict[str, Any]) -> int`

Calcula quantos segundos faltam para a votacao encerrar.

#### Metodo `auto_close_expired(self) -> None`

Percorre votacoes ativas com prazo definido e encerra as que ja expiraram.

#### Metodo `auto_close_if_expired(self, id_votacao: int) -> None`

Verifica uma votacao especifica e encerra quando o horario limite ja passou.

#### Metodo `_get_required(self, id_votacao: int) -> dict[str, Any]`

Busca uma votacao e gera erro quando ela nao existe.

#### Metodo estatico `_normalizar_escolhas(raw: int | str | Iterable[int | str]) -> list[int]`

Converte a entrada de escolhas vinda do formulario em lista de inteiros.

## `conviva/controllers.py`

Arquivo da camada Controller. Recebe requisicoes HTTP, valida sessao/perfil e chama os servicos.

### Classe `NotAuthenticated`

Excecao usada para diferenciar falta de login de erro de permissao. Quando ocorre, o usuario e redirecionado para `/login`.

### Classe `Response`

Dataclass que representa uma resposta HTTP padronizada.

#### Atributos

- `body`: corpo da resposta em bytes.
- `status`: codigo HTTP.
- `headers`: cabecalhos HTTP.

#### Metodo de classe `html(cls, body: str, status: int = 200, headers: dict[str, str] | None = None) -> Response`

Cria uma resposta HTML com `Content-Type: text/html; charset=utf-8`.

#### Metodo de classe `json(cls, payload: dict[str, Any], status: int = 200) -> Response`

Cria uma resposta JSON com codificacao UTF-8.

### Funcao `redirect(location: str, headers: dict[str, str] | None = None) -> Response`

Cria resposta HTTP 303 com cabecalho `Location`, usada apos login, logout e acoes de formulario.

### Funcao `parse_form(body: bytes) -> dict[str, Any]`

Converte corpo `application/x-www-form-urlencoded` em dicionario. Campos repetidos viram lista.

### Classe `ApplicationController`

Controller principal da aplicacao. Ele instancia repositorios e servicos, roteia requisicoes e retorna `Response`.

#### Metodo `__init__(self) -> None`

Cria a instancia de banco, repositorios, servicos de auditoria, autenticacao, reuniao e votacao.

#### Metodo `ensure_database(self) -> None`

Garante que o banco e suas tabelas existam.

#### Metodo `dispatch(self, method, path, query, headers, body, client_address) -> Response`

Roteia todas as requisicoes HTTP da aplicacao. Trata rotas publicas, arquivos estaticos, login, logout, dashboard, votacoes, reunioes, APIs de votacao, resultado e auditoria. Tambem converte excecoes em respostas HTML apropriadas.

#### Metodo `static_file(self, path: str) -> Response`

Entrega arquivos da pasta `static`, protegendo contra acesso fora desse diretorio.

#### Metodo `require_user(self, headers: Message) -> dict[str, Any]`

Recupera o usuario autenticado pelo cookie. Gera `NotAuthenticated` quando nao existe sessao valida.

#### Metodo `require_admin(self, user: dict[str, Any]) -> None`

Garante que o usuario tem perfil de administrador. Caso contrario gera `PermissionError`.

#### Metodo `login(self, body: bytes, meta: RequestMeta) -> Response`

Processa o formulario de login. Em caso de sucesso cria cookie de sessao e redireciona para o inicio. Em caso de falha retorna a tela de login com erro.

#### Metodo `logout(self, headers: Message, meta: RequestMeta) -> Response`

Encerra a sessao atual, limpa o cookie e redireciona para `/login`.

#### Metodo `dashboard(self, user: dict[str, Any]) -> Response`

Monta a tela inicial com reunioes disponiveis e votacoes recentes.

#### Metodo `nova_votacao_form(self, user: dict[str, Any], error: str = "") -> Response`

Exibe o formulario de cadastro de votacao para administradores.

#### Metodo `nova_votacao_post(self, user: dict[str, Any], body: bytes, meta: RequestMeta) -> Response`

Processa o cadastro de votacao. Se houver erro de validacao, retorna o formulario com mensagem.

#### Metodo `reuniao(self, user: dict[str, Any], id_reuniao: int, meta: RequestMeta) -> Response`

Executa entrada na reuniao, marca presenca, monta painel de votacao ativa, participantes, pautas e controles administrativos.

#### Metodo `sair_reuniao(self, user: dict[str, Any], id_reuniao: int, meta: RequestMeta) -> Response`

Marca saida da reuniao e redireciona para o inicio.

#### Metodo `api_votacao_ativa(self, user: dict[str, Any], id_reuniao: int) -> Response`

Retorna JSON com HTML do painel de votacao ativa. E usado pelo JavaScript da tela de reuniao para atualizar a votacao automaticamente.

#### Metodo `api_votar(self, user: dict[str, Any], id_votacao: int, body: bytes, meta: RequestMeta) -> Response`

Recebe voto via endpoint JSON. Retorna HTML atualizado do painel e informa se a operacao foi bem-sucedida.

#### Metodo `iniciar_votacao(self, user: dict[str, Any], id_votacao: int, meta: RequestMeta) -> Response`

Chama o servico para iniciar a votacao e redireciona para a reuniao vinculada.

#### Metodo `encerrar_votacao(self, user: dict[str, Any], id_votacao: int, meta: RequestMeta) -> Response`

Chama o servico para encerrar a votacao e redireciona para a tela de resultado.

#### Metodo `votar_form(self, user: dict[str, Any], id_votacao: int) -> Response`

Renderiza o painel de voto em uma pagina simples. E uma alternativa ao painel embutido na reuniao.

#### Metodo `votar_post(self, user: dict[str, Any], id_votacao: int, body: bytes, meta: RequestMeta) -> Response`

Processa voto enviado por formulario HTML tradicional e redireciona para a reuniao.

#### Metodo `resultado(self, user: dict[str, Any], id_votacao: int, meta: RequestMeta) -> Response`

Exibe resultado somente quando a votacao esta encerrada ou invalidada. Registra auditoria de visualizacao.

#### Metodo `logs(self, user: dict[str, Any]) -> Response`

Exibe os logs de auditoria para administradores.

## `conviva/templates.py`

Arquivo da camada View. Contem funcoes que geram HTML.

### Funcao `h(value: Any) -> str`

Escapa texto para HTML, evitando que dados vindos do banco ou formulario sejam interpretados como marcacao.

### Funcao `base(title: str, content: str, user: dict[str, Any] | None = None, script: str = "") -> str`

Monta a estrutura HTML principal da pagina, incluindo `head`, CSS, menu superior quando ha usuario logado, conteudo e scripts opcionais.

### Funcao `status_badge(status: str) -> str`

Gera um selo visual de status, como `agendada`, `ativa`, `encerrada` ou `invalidada`.

### Funcao `alert(message: str, kind: str = "info") -> str`

Gera bloco HTML de alerta. Retorna string vazia quando nao ha mensagem.

### Funcao `login(error: str = "") -> str`

Monta a pagina de login com campos de e-mail e senha e mensagem de erro opcional.

### Funcao `dashboard(user, reunioes, votacoes) -> str`

Monta a tela inicial com tabela de reunioes disponiveis e ultimas votacoes.

### Funcao `votacoes(user, votacoes_list, message: str = "", error: str = "") -> str`

Monta a tela de gestao/listagem de votacoes, incluindo botoes administrativos quando o usuario e administrador.

### Funcao `form_votacao(user, pautas, error: str = "") -> str`

Monta o formulario de cadastro de votacao, incluindo pauta, assunto, visibilidade, tipo de resposta, tempo, limite de marcacoes, pergunta e opcoes.

### Funcao `reuniao(user, reuniao, pautas, participantes, votacoes, active_vote_html) -> str`

Monta a tela de reuniao com area de video, painel lateral de votacao, lista de pautas, lista de participantes e controles administrativos.

### Funcao `vote_panel(user, payload, message: str = "", error: str = "") -> str`

Monta o painel de votacao ativa. Quando nao existe votacao ativa, exibe mensagem informativa. Quando existe, mostra pauta, tempo restante, peso do usuario, pergunta, opcoes e botao de confirmar voto quando permitido.

### Funcao `format_seconds(total: int) -> str`

Converte segundos em formato `MM:SS`.

### Funcao `resultado(user, result, warning: str = "") -> str`

Monta a tela de resultado com status, total de votos, peso computado, visibilidade, barras percentuais e relatorio nominal quando permitido.

### Funcao `logs(user, rows) -> str`

Monta a tela de auditoria com os registros recentes.

### Funcao `message_page(title: str, message: str, user: dict[str, Any] | None = None) -> str`

Monta pagina simples de mensagem, usada para erros, acesso negado e avisos.

### Funcao `not_found(user: dict[str, Any] | None = None) -> str`

Monta pagina de erro 404.

