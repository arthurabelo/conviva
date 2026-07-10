from __future__ import annotations

from html import escape
from typing import Any


def h(value: Any) -> str:
    return escape("" if value is None else str(value), quote=True)


def base(title: str, content: str, user: dict[str, Any] | None = None, script: str = "") -> str:
    nav = ""
    if user:
        admin_link = "<a href='/usuarios'>Usuários</a><a href='/logs'>Auditoria</a>" if user["tipo_usuario"] == "administrador" else ""
        nav = f"""
        <header class="topbar">
            <a class="brand" href="/">CONVIVA</a>
            <nav>
                <a href="/">Inicio</a>
                <a href="/votacoes">Votacoes</a>
                {admin_link}
                <a href="/logout">Sair</a>
            </nav>
            <span class="user-chip">{h(user["nome_completo"])} · {h(user["tipo_usuario"])}</span>
        </header>
        """
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{h(title)} · CONVIVA</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    {nav}
    <main class="page">
        {content}
    </main>
    {script}
</body>
</html>"""


def status_badge(status: str) -> str:
    label = h(status.replace("_", " "))
    return f"<span class='badge badge-{h(status)}'>{label}</span>"


def alert(message: str, kind: str = "info") -> str:
    if not message:
        return ""
    return f"<div class='alert {h(kind)}'>{h(message)}</div>"


def login(error: str = "") -> str:
    content = f"""
    <section class="login-shell">
        <form method="post" action="/login" class="login-card">
            <div class="login-mark">CONVIVA</div>
            <h1>Entrar no sistema</h1>
            <p class="muted">Acesse a area de assembleia e votacao do condominio.</p>
            {alert(error, "error")}
            <label>E-mail
                <input name="email" type="email" autocomplete="username" required autofocus>
            </label>
            <label>Senha
                <input name="senha" type="password" autocomplete="current-password" required>
            </label>
            <button class="primary" type="submit">Entrar</button>
        </form>
    </section>
    """
    return base("Entrar", content)


def dashboard(user: dict[str, Any], reunioes: list[dict[str, Any]], votacoes: list[dict[str, Any]], search: str = "", message: str = "") -> str:
    reunioes_rows = "".join(
        f"""
        <tr>
            <td><strong>{h(r["titulo"])}</strong><span>{h(r["condominio_nome"])}</span></td>
            <td>{h(r["data"])} às {h(r["hora"])}</td>
            <td>{status_badge(r["status"])}</td>
            <td><a class="button small" href="/reunioes/{r["id_reuniao"]}">Entrar na reuniao</a></td>
        </tr>
        """
        for r in reunioes
    )
    votacoes_rows = "".join(
        f"""
        <tr>
            <td><strong>{h(v["assunto"])}</strong><span>{h(v["pergunta"])}</span></td>
            <td>{h(v["reuniao_titulo"])}</td>
            <td>{status_badge(v["status"])}</td>
            <td><a class="button small secondary" href="/votacoes/{v["id_votacao"]}/resultado">Resultado</a></td>
        </tr>
        """
        for v in votacoes[:5]
    )
    content = f"""
    <section class="section-head">
        <div>
            <p class="eyebrow">Painel</p>
            <h1>Assembleias e votacoes</h1>
        </div>
        {"<a class='button primary' href='/votacoes/nova'>Criar votacao</a>" if user["tipo_usuario"] == "administrador" else ""}
    </section>
    {alert(message, "info")}
    <section class="panel">
        <div class="panel-head">
            <h2>Reunioes disponiveis</h2>
            <form class="search-form" method="get" action="/">
                <input name="busca" value="{h(search)}" placeholder="Buscar reuniao, condominio ou assunto">
                <button class="small secondary" type="submit">Buscar</button>
            </form>
        </div>
        <div class="table-wrap">
            <table>
                <thead><tr><th>Reuniao</th><th>Data</th><th>Status</th><th></th></tr></thead>
                <tbody>{reunioes_rows or "<tr><td colspan='4'>Nenhuma reuniao disponivel.</td></tr>"}</tbody>
            </table>
        </div>
    </section>
    <section class="panel">
        <div class="panel-head">
            <h2>Votacoes recentes</h2>
            <form class="search-form" method="get" action="/">
                <input name="busca" value="{h(search)}" placeholder="Buscar votacao, pauta ou reuniao">
                <button class="small secondary" type="submit">Buscar</button>
            </form>
        </div>
        <div class="table-wrap">
            <table>
                <thead><tr><th>Votacao</th><th>Reuniao</th><th>Status</th><th></th></tr></thead>
                <tbody>{votacoes_rows or "<tr><td colspan='4'>Nenhuma votacao cadastrada.</td></tr>"}</tbody>
            </table>
        </div>
    </section>
    """
    return base("Inicio", content, user)


def votacoes(user: dict[str, Any], votacoes_list: list[dict[str, Any]], search: str = "", message: str = "", error: str = "") -> str:
    rows = []
    for v in votacoes_list:
        admin_actions = ""
        if user["tipo_usuario"] == "administrador":
            if v["status"] == "agendada":
                admin_actions += f"<form method='post' action='/votacoes/{v['id_votacao']}/iniciar'><button class='small primary'>Iniciar</button></form>"
            if v["status"] in {"ativa", "agendada"}:
                admin_actions += f"<form method='post' action='/votacoes/{v['id_votacao']}/encerrar'><button class='small secondary'>Encerrar</button></form>"
        actions = f"""
            <div class="row-actions">
                {admin_actions}
                {f"<a class='button small secondary' href='/votacoes/{v['id_votacao']}/editar'>Editar</a>" if user["tipo_usuario"] == "administrador" and v["status"] == "agendada" else ""}
                <a class="button small secondary" href="/votacoes/{v["id_votacao"]}/resultado">Resultado</a>
            </div>
        """
        rows.append(
            f"""
            <tr>
                <td><strong>{h(v["assunto"])}</strong><span>{h(v["pergunta"])}</span></td>
                <td>{h(v["reuniao_titulo"])}<span>{h(v["pauta_assunto"])}</span></td>
                <td>{h(v["tipo_votacao"])}</td>
                <td>{h(v["tempo_resposta"])} min</td>
                <td>{status_badge(v["status"])}</td>
                <td>{actions}</td>
            </tr>
            """
        )
    content = f"""
    <section class="section-head">
        <div><p class="eyebrow">Gestao</p><h1>Votacoes</h1></div>
        {"<a class='button primary' href='/votacoes/nova'>Nova votacao</a>" if user["tipo_usuario"] == "administrador" else ""}
    </section>
    {alert(message, "success")}
    {alert(error, "error")}
    <section class="panel">
        <div class="panel-head">
            <h2>Lista de votacoes</h2>
            <form class="search-form" method="get" action="/votacoes">
                <input name="busca" value="{h(search)}" placeholder="Buscar por assunto, pergunta ou pauta">
                <button class="small secondary" type="submit">Buscar</button>
            </form>
        </div>
        <div class="table-wrap">
            <table>
                <thead><tr><th>Votacao</th><th>Vinculo</th><th>Tipo</th><th>Tempo</th><th>Status</th><th></th></tr></thead>
                <tbody>{"".join(rows) or "<tr><td colspan='6'>Nenhuma votacao cadastrada.</td></tr>"}</tbody>
            </table>
        </div>
    </section>
    """
    return base("Votacoes", content, user)


def form_votacao(
    user: dict[str, Any],
    pautas: list[dict[str, Any]],
    error: str = "",
    votacao: dict[str, Any] | None = None,
    opcoes_text: str = "",
    action: str = "/votacoes/nova",
    title: str = "Cadastro de votacao",
    submit_label: str = "Salvar votacao",
) -> str:
    votacao = votacao or {}
    opcoes_text = opcoes_text or "Aprovar\nRejeitar\nNao sei / nao quero responder"
    pauta_options = "".join(
        f"<option value='{p['id_pauta']}' {'selected' if str(p['id_pauta']) == str(votacao.get('id_pauta', '')) else ''}>{h(p['reuniao_titulo'])} · {h(p['assunto'])}</option>"
        for p in pautas
    )
    content = f"""
    <section class="section-head">
        <div><p class="eyebrow">Votacao</p><h1>{h(title)}</h1></div>
    </section>
    <form class="panel form-grid" method="post" action="{h(action)}">
        {alert(error, "error")}
        <label>Pauta vinculada
            <select name="id_pauta" required>{pauta_options}</select>
        </label>
        <label>Assunto
            <input name="assunto" maxlength="255" required placeholder="Aprovacao das contas de 2025" value="{h(votacao.get('assunto', ''))}">
        </label>
        <label>Visibilidade
            <select name="tipo_votacao">
                <option value="aberta" {'selected' if votacao.get('tipo_votacao', 'aberta') == 'aberta' else ''}>Aberta</option>
                <option value="fechada" {'selected' if votacao.get('tipo_votacao') == 'fechada' else ''}>Fechada</option>
            </select>
        </label>
        <label>Tipo de resposta
            <select name="tipo_resposta" id="tipo_resposta">
                <option value="escolha_unica" {'selected' if votacao.get('tipo_resposta', 'escolha_unica') == 'escolha_unica' else ''}>Escolha unica</option>
                <option value="multipla_escolha" {'selected' if votacao.get('tipo_resposta') == 'multipla_escolha' else ''}>Multipla escolha</option>
                <option value="eleicao" {'selected' if votacao.get('tipo_resposta') == 'eleicao' else ''}>Eleicao de nomes</option>
            </select>
        </label>
        <label>Tempo para responder (minutos)
            <input name="tempo_resposta" type="number" min="1" value="{int(votacao.get('tempo_resposta', 1) or 1)}" required>
        </label>
        <label>Quantidade maxima de marcacoes
            <input name="max_marcacoes" type="number" min="1" value="{int(votacao.get('max_marcacoes', 1) or 1)}">
        </label>
        <label class="wide">Pergunta
            <input name="pergunta" maxlength="255" required placeholder="Voce aprova o balanco financeiro apresentado?" value="{h(votacao.get('pergunta', ''))}">
        </label>
        <label class="wide">Opcoes de resposta, uma por linha
            <textarea name="opcoes" rows="5" required>{h(opcoes_text)}</textarea>
        </label>
        <div class="wide form-actions">
            <a class="button secondary" href="/votacoes">Cancelar</a>
            <button class="primary" type="submit">{h(submit_label)}</button>
        </div>
    </form>
    """
    return base(title, content, user)


def reuniao(
    user: dict[str, Any],
    reuniao: dict[str, Any],
    pautas: list[dict[str, Any]],
    participantes: list[dict[str, Any]],
    votacoes: list[dict[str, Any]],
    active_vote_html: str,
) -> str:
    pauta_list = "".join(f"<li><strong>{h(p['assunto'])}</strong><span>{h(p.get('descricao', ''))}</span></li>" for p in pautas)
    participant_rows = "".join(
        f"<li><span>{h(p['nome_completo'])}</span>{'<b>online</b>' if p['status_presenca'] else '<em>ausente</em>'}</li>"
        for p in participantes
    )
    controls = ""
    if user["tipo_usuario"] == "administrador":
        items = []
        for v in votacoes:
            action = ""
            if v["status"] == "agendada":
                action = f"<form method='post' action='/votacoes/{v['id_votacao']}/iniciar'><button class='small primary'>Iniciar</button></form>"
            elif v["status"] == "ativa":
                action = f"<form method='post' action='/votacoes/{v['id_votacao']}/encerrar'><button class='small secondary'>Encerrar</button></form>"
            items.append(f"<li><span>{h(v['assunto'])}</span>{status_badge(v['status'])}{action}</li>")
        controls = f"""
        <section class="admin-control">
            <h2>Controle de votacoes</h2>
            <ul class="control-list">{''.join(items) or '<li>Nenhuma votacao cadastrada.</li>'}</ul>
        </section>
        """
    script = f"""
    <script>
    window.CONVIVA_MEETING_ID = {int(reuniao["id_reuniao"])};
    </script>
    <script src="/static/reuniao.js"></script>
    """
    content = f"""
    <section class="meeting-head">
        <div>
            <p class="eyebrow">Reuniao em andamento</p>
            <h1>{h(reuniao["titulo"])}</h1>
            <p>{h(reuniao["assunto"])} · {h(reuniao["data"])} às {h(reuniao["hora"])}</p>
        </div>
        <form method="post" action="/reunioes/{reuniao["id_reuniao"]}/sair">
            <button class="secondary" type="submit">Sair da reuniao</button>
        </form>
    </section>
    <section class="meeting-grid">
        <div class="video-stage">
            <div class="video-topline">
                <span>Video integrado</span>
                <span>{h(reuniao["url_video"] or "link de videoconferencia")}</span>
            </div>
            <div class="video-placeholder">
                <strong>Assembleia online</strong>
                <span>Area reservada para Google Meet, Zoom ou Teams embutido.</span>
            </div>
        </div>
        <aside class="vote-side">
            <div id="active-vote-panel">{active_vote_html}</div>
        </aside>
    </section>
    <section class="meeting-lower">
        <div class="panel">
            <h2>Pautas</h2>
            <ul class="agenda-list">{pauta_list}</ul>
        </div>
        <div class="panel">
            <h2>Participantes</h2>
            <ul class="participant-list">{participant_rows}</ul>
        </div>
        {controls}
    </section>
    """
    return base("Reuniao", content, user, script)


def vote_panel(user: dict[str, Any], payload: dict[str, Any], message: str = "", error: str = "") -> str:
    votacao = payload.get("active")
    if not votacao:
        return f"""
        <section class="poll-box empty">
            <h2>Votacao</h2>
            {alert(message or payload.get("message", "Nenhuma votacao ativa no momento."), "info")}
        </section>
        """
    options = payload.get("options", [])
    input_type = "checkbox" if votacao["tipo_resposta"] == "multipla_escolha" else "radio"
    option_html = "".join(
        f"""
        <label class="choice">
            <input type="{input_type}" name="id_opcao" value="{o["id_opcao"]}">
            <span>{h(o["descricao"])}</span>
        </label>
        """
        for o in options
    )
    if payload.get("already_voted"):
        form_html = "<div class='alert success'>Voto ja registrado para esta pauta.</div>"
    elif not payload.get("can_vote"):
        form_html = f"<div class='alert error'>{h(payload.get('blocked_reason') or 'Usuario sem permissao de voto.')}</div>"
    else:
        form_html = f"""
        <form method="post" action="/votacoes/{votacao["id_votacao"]}/votar" data-vote-form>
            <div class="choices">{option_html}</div>
            <button class="primary" type="submit">Confirmar voto</button>
        </form>
        """
    return f"""
    <section class="poll-box" data-active-vote="{votacao["id_votacao"]}">
        <p class="eyebrow">Votacao ativa</p>
        <h2>{h(votacao["assunto"])}</h2>
        {alert(message, "success")}
        {alert(error, "error")}
        <dl class="poll-meta">
            <div><dt>Pauta</dt><dd>{h(votacao["pauta_assunto"])}</dd></div>
            <div><dt>Tempo restante</dt><dd><span data-countdown="{int(payload.get("seconds_left", 0))}">{format_seconds(int(payload.get("seconds_left", 0)))}</span></dd></div>
            <div><dt>Seu peso</dt><dd>{float(payload.get("weight", 0)):.2f}</dd></div>
            <div><dt>Tipo</dt><dd>{h(votacao["tipo_votacao"])}</dd></div>
        </dl>
        <p class="question">{h(votacao["pergunta"])}</p>
        {form_html}
    </section>
    """


def format_seconds(total: int) -> str:
    minutes, seconds = divmod(max(0, total), 60)
    return f"{minutes:02d}:{seconds:02d}"


def resultado(user: dict[str, Any], result: dict[str, Any], warning: str = "") -> str:
    votacao = result["votacao"]
    option_rows = ""
    for op in result["opcoes"]:
        option_rows += f"""
        <div class="result-row">
            <div>
                <strong>{h(op["descricao"])}</strong>
                <span>{op["votos"]} voto(s) · peso {op["peso"]:.2f}</span>
            </div>
            <div class="bar"><i style="width:{op["percentual"]:.2f}%"></i></div>
            <b>{op["percentual"]:.1f}%</b>
        </div>
        """
    nominal = ""
    if votacao["tipo_votacao"] == "aberta" and result["nominais"]:
        rows = "".join(
            f"""
            <tr>
                <td>{h(v["id_voto"])}</td>
                <td>{h(v["responsavel_nome"])}</td>
                <td>{h(v["representado_nome"])}</td>
                <td>{h(v["imoveis"] or "-")}</td>
                <td>{h(v["voto"])}</td>
                <td>{float(v["peso_aplicado"]):.2f}</td>
                <td>{h(v["data_hora_voto"])}</td>
            </tr>
            """
            for v in result["nominais"]
        )
        nominal = f"""
        <section class="panel">
            <h2>Relatorio nominal</h2>
            <div class="table-wrap">
                <table>
                    <thead><tr><th>Cod.</th><th>Responsavel</th><th>Representado</th><th>Imovel</th><th>Voto</th><th>Peso</th><th>Horario</th></tr></thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
        </section>
        """
    elif votacao["tipo_votacao"] == "fechada":
        nominal = "<section class='panel'><h2>Relatorio nominal</h2><p class='muted'>Votacao fechada: a identificacao nominal dos votos nao e exibida.</p></section>"
    content = f"""
    <section class="section-head">
        <div><p class="eyebrow">Resultado</p><h1>{h(votacao["assunto"])}</h1></div>
        <button class="secondary" onclick="window.print()">Imprimir relatorio</button>
    </section>
    {alert(warning, "info")}
    <section class="panel result-summary">
        <div><span>Status</span><strong>{status_badge(votacao["status"])}</strong></div>
        <div><span>Total de votos</span><strong>{result["total_votos"]}</strong></div>
        <div><span>Peso computado</span><strong>{result["total_peso"]:.2f}</strong></div>
        <div><span>Visibilidade</span><strong>{h(votacao["tipo_votacao"])}</strong></div>
    </section>
    <section class="panel">
        <h2>Resultado consolidado</h2>
        <div class="result-list">{option_rows or "<p>Nenhum voto computado.</p>"}</div>
    </section>
    {nominal}
    """
    return base("Resultado", content, user)


def tipo_usuario_label(tipo: str) -> str:
    return {"administrador": "Administrador/Síndico", "proprietario": "Proprietário", "procurador": "Procurador"}.get(tipo, tipo.title())


def usuarios(user: dict[str, Any], rows: list[dict[str, Any]], nome: str = "", tipo: str = "", message: str = "", error: str = "") -> str:
    body = []
    for usuario in rows:
        user_id = int(usuario["id_usuario"])
        lote_action = f"<a class='button small secondary' href='/usuarios/{user_id}/lotes'>Gerenciar lotes</a>" if usuario["tipo_usuario"] == "proprietario" else ""
        body.append(f"""
        <tr>
            <td><span class="code-cell">{user_id:04d}</span></td>
            <td><strong>{h(usuario["nome_completo"])}</strong></td>
            <td><span class="profile-pill profile-{h(usuario['tipo_usuario'])}">{h(tipo_usuario_label(str(usuario["tipo_usuario"])))}</span></td>
            <td>{h(usuario["email"])}</td>
            <td><div class="row-actions user-actions">
                <a class="button small secondary" href="/usuarios/{user_id}">Visualizar</a>
                <a class="button small secondary" href="/usuarios/{user_id}/editar">Alterar</a>
                {lote_action}
                <form method="post" action="/usuarios/{user_id}/excluir" onsubmit="return confirm('Confirma a exclusão deste usuário?')"><button class="small danger-outline" type="submit">Excluir</button></form>
            </div></td>
        </tr>""")
    content = f"""
    <section class="section-head">
        <div><p class="eyebrow">Administração</p><h1>Gestão de usuários</h1><p class="muted">Cadastre acessos e gerencie as unidades dos proprietários.</p></div>
        <a class="button primary" href="/usuarios/novo">Novo usuário</a>
    </section>
    {alert(message, "success")}{alert(error, "error")}
    <section class="panel filter-panel">
        <div class="panel-head"><div><p class="eyebrow">Filtros</p><h2>Pesquisa por usuários</h2></div></div>
        <form class="user-filter" method="get" action="/usuarios">
            <label>Nome<input name="nome" value="{h(nome)}" placeholder="Digite o nome do usuário"></label>
            <label>Tipo<select name="tipo">
                <option value="" {'selected' if not tipo else ''}>Todos</option>
                <option value="administrador" {'selected' if tipo == 'administrador' else ''}>Administrador/Síndico</option>
                <option value="proprietario" {'selected' if tipo == 'proprietario' else ''}>Proprietário</option>
            </select></label>
            <button class="primary" type="submit">Pesquisar</button><a class="button secondary" href="/usuarios">Limpar</a>
        </form>
    </section>
    <section class="panel">
        <div class="panel-head"><div><p class="eyebrow">Cadastros</p><h2>Tabela de usuários</h2></div><span class="result-count">{len(rows)} usuário(s)</span></div>
        <div class="table-wrap"><table class="users-table"><thead><tr><th>Código</th><th>Nome</th><th>Tipo</th><th>E-mail</th><th>Comandos</th></tr></thead><tbody>{''.join(body) or "<tr><td colspan='5' class='empty-cell'>Nenhum usuário encontrado.</td></tr>"}</tbody></table></div>
    </section>"""
    return base("Gestão de usuários", content, user)


def form_usuario(user: dict[str, Any], usuario: dict[str, Any], error: str = "", id_usuario: int | None = None) -> str:
    editing = id_usuario is not None
    action = f"/usuarios/{id_usuario}/editar" if editing else "/usuarios/novo"
    title = "Editar usuário" if editing else "Novo usuário"
    tipo = str(usuario.get("tipo_usuario", "proprietario"))
    code = f"{id_usuario:04d}" if id_usuario is not None else "Gerado automaticamente"
    content = f"""
    <section class="section-head"><div><p class="eyebrow">Gestão de usuários</p><h1>{title}</h1><p class="muted">Preencha os dados de acesso. Campos com * são obrigatórios.</p></div><a class="button secondary" href="/usuarios">Voltar à lista</a></section>
    <form class="panel form-grid user-form" method="post" action="{action}">
        {alert(error, "error")}<div class="wide form-section-title"><span>Dados cadastrais</span></div>
        <label>Código<input value="{code}" disabled><small>Identificador protegido pelo sistema.</small></label>
        <label>Tipo de usuário *<select name="tipo_usuario" required><option value="administrador" {'selected' if tipo == 'administrador' else ''}>Administrador/Síndico</option><option value="proprietario" {'selected' if tipo == 'proprietario' else ''}>Proprietário</option></select></label>
        <label class="wide">Nome completo *<input name="nome_completo" maxlength="255" required value="{h(usuario.get('nome_completo', ''))}" placeholder="Nome e sobrenome"></label>
        <label>E-mail *<input name="email" type="email" maxlength="255" autocomplete="username" required value="{h(usuario.get('email', ''))}" placeholder="usuario@email.com"><small>Este endereço será usado para entrar no sistema.</small></label>
        <label>{'Nova senha' if editing else 'Senha temporária *'}<input name="senha" type="password" minlength="6" autocomplete="new-password" {'required' if not editing else ''} placeholder="{'Deixe em branco para manter' if editing else 'Mínimo de 6 caracteres'}"><small>{'Preencha somente se desejar redefinir a senha.' if editing else 'A senha será armazenada de forma criptografada.'}</small></label>
        <div class="wide form-actions"><a class="button secondary" href="/usuarios">Cancelar</a><button class="primary" type="submit">Salvar usuário</button></div>
    </form>"""
    return base(title, content, user)


def visualizar_usuario(user: dict[str, Any], usuario: dict[str, Any], lotes: list[dict[str, Any]]) -> str:
    user_id = int(usuario["id_usuario"])
    total = sum(float(lote["peso_original"]) for lote in lotes)
    efetivo = sum(float(lote["peso_original"]) for lote in lotes if not lote["inadimplente"])
    lot_summary = ""
    if usuario["tipo_usuario"] == "proprietario":
        lot_summary = f"""<section class="panel"><div class="panel-head"><div><p class="eyebrow">Propriedade</p><h2>Lotes vinculados</h2></div><a class="button small secondary" href="/usuarios/{user_id}/lotes">Gerenciar lotes</a></div><div class="summary-cards"><div><span>Unidades</span><strong>{len(lotes)}</strong></div><div><span>Peso acumulado</span><strong>{total:.2f}</strong></div><div><span>Peso efetivo</span><strong>{efetivo:.2f}</strong></div></div></section>"""
    content = f"""
    <section class="section-head"><div><p class="eyebrow">Gestão de usuários</p><h1>Detalhes do usuário</h1></div><div class="row-actions"><a class="button secondary" href="/usuarios">Voltar</a><a class="button primary" href="/usuarios/{user_id}/editar">Alterar cadastro</a></div></section>
    <section class="panel detail-panel"><div class="avatar">{h(str(usuario['nome_completo'])[:1].upper())}</div><div><span>Código</span><strong>{user_id:04d}</strong></div><div><span>Nome completo</span><strong>{h(usuario['nome_completo'])}</strong></div><div><span>E-mail</span><strong>{h(usuario['email'])}</strong></div><div><span>Tipo de usuário</span><strong>{h(tipo_usuario_label(str(usuario['tipo_usuario'])))}</strong></div></section>{lot_summary}"""
    return base("Detalhes do usuário", content, user)


def lotes_table(id_usuario: int, lotes: list[dict[str, Any]]) -> str:
    rows = []
    total = 0.0
    efetivo = 0.0
    for lote in lotes:
        peso = float(lote["peso_original"])
        inadimplente = bool(lote["inadimplente"])
        total += peso
        efetivo += 0 if inadimplente else peso
        lot_id = int(lote["id_lote"])
        status = "Inadimplente (Dívida Ativa)" if inadimplente else "Adimplente"
        rows.append(f"""
        <tr><td><strong>{h(lote['identificacao'])}</strong></td><td>{peso:.2f}</td><td class="{'debt-status' if inadimplente else 'ok-status'}">{status}</td><td><strong>{0.0 if inadimplente else peso:.2f}</strong></td><td><div class="row-actions">
            <button class="small secondary" type="button" data-lote-edit data-id="{lot_id}" data-identificacao="{h(lote['identificacao'])}" data-peso="{peso:.2f}" data-inadimplente="{1 if inadimplente else 0}">Editar</button>
            <button class="small danger-outline" type="button" data-lote-delete="{lot_id}" data-owner="{id_usuario}">Excluir</button>
        </div></td></tr>""")
    return f"""<div class="table-wrap"><table class="lots-table">
        <thead><tr><th>Lote/Unidade</th><th>Peso original</th><th>Status financeiro</th><th>Peso efetivo no voto</th><th>Comandos</th></tr></thead>
        <tbody>{''.join(rows) or "<tr><td colspan='5' class='empty-cell'>Nenhum lote vinculado.</td></tr>"}</tbody>
        <tfoot><tr><th colspan="2">Total de peso acumulado: <strong data-total-original>{total:.2f}</strong></th><th colspan="3">Total efetivo: <strong data-total-effective>{efetivo:.2f}</strong></th></tr></tfoot>
    </table></div>"""


def gerenciar_lotes(user: dict[str, Any], usuario: dict[str, Any], condominio: dict[str, Any], lotes: list[dict[str, Any]], message: str = "", error: str = "") -> str:
    user_id = int(usuario["id_usuario"])
    content = f"""
    <section class="section-head"><div><p class="eyebrow">Gestão de usuários</p><h1>Gerenciamento de lotes</h1><p class="muted">{h(condominio['nome'])}</p></div><a class="button secondary" href="/usuarios">Finalizar vínculos</a></section>
    <section class="owner-banner"><div class="avatar small-avatar">{h(str(usuario['nome_completo'])[:1].upper())}</div><div><span>Proprietário selecionado</span><strong>Código {user_id:04d} · {h(usuario['nome_completo'])}</strong></div></section>
    <div id="lot-feedback">{alert(message, 'success')}{alert(error, 'error')}</div>
    <section class="panel">
        <div class="panel-head"><div><p class="eyebrow">Unidade</p><h2 id="lot-form-title">Vincular novo lote/unidade</h2></div><button class="small secondary hidden" id="cancel-lot-edit" type="button">Cancelar edição</button></div>
        <form class="lot-form" id="lot-form" method="post" action="/api/usuarios/{user_id}/lotes">
            <input type="hidden" name="id_lote" id="id_lote">
            <label>Identificação do lote *<input name="identificacao" id="identificacao" required placeholder="Bloco A - Apto 302"></label>
            <label>Peso *<input name="peso_original" id="peso_original" type="number" min="0.01" step="0.01" required value="1.00"><small>Número decimal correspondente ao peso político do voto.</small></label>
            <label>Inadimplente *<select name="inadimplente" id="inadimplente"><option value="0">Não</option><option value="1">Sim</option></select><small>Se “Sim”, o peso efetivo torna-se 0.00 automaticamente.</small></label>
            <div class="lot-preview"><span>Peso efetivo previsto</span><strong id="effective-preview">1.00</strong></div>
            <button class="primary" type="submit" id="lot-submit">Vincular lote</button>
        </form>
    </section>
    <section class="panel"><div class="panel-head"><div><p class="eyebrow">Frações ideais</p><h2>Tabela de lotes vinculados</h2></div></div><div id="lots-table-container">{lotes_table(user_id, lotes)}</div></section>"""
    return base("Gerenciamento de lotes", content, user, '<script src="/static/usuarios.js"></script>')


def logs(user: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    body = "".join(
        f"""
        <tr>
            <td>{h(row["data_hora"])}</td>
            <td>{h(row.get("nome_completo") or "-")}</td>
            <td>{h(row["acao"])}</td>
            <td>{h(row["entidade"])}</td>
            <td>{h(row.get("ip") or "-")}</td>
        </tr>
        """
        for row in rows
    )
    content = f"""
    <section class="section-head"><div><p class="eyebrow">Auditoria</p><h1>Logs da plataforma</h1></div></section>
    <section class="panel">
        <div class="table-wrap">
            <table>
                <thead><tr><th>Data e hora</th><th>Usuario</th><th>Acao</th><th>Entidade</th><th>IP</th></tr></thead>
                <tbody>{body or "<tr><td colspan='5'>Nenhum log registrado.</td></tr>"}</tbody>
            </table>
        </div>
    </section>
    """
    return base("Auditoria", content, user)


def message_page(title: str, message: str, user: dict[str, Any] | None = None) -> str:
    return base(title, f"<section class='panel narrow'><h1>{h(title)}</h1><p>{h(message)}</p><a class='button secondary' href='/'>Voltar</a></section>", user)


def not_found(user: dict[str, Any] | None = None) -> str:
    return message_page("Pagina nao encontrada", "O endereco acessado nao existe.", user)
