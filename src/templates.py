from __future__ import annotations

from html import escape
from typing import Any


def h(value: Any) -> str:
    return escape("" if value is None else str(value), quote=True)


def base(title: str, content: str, user: dict[str, Any] | None = None, script: str = "") -> str:
    nav = ""
    if user:
        admin_link = "<a href='#'>Usuários</a><a href='/logs'>Auditoria</a>" if user["tipo_usuario"] == "administrador" else ""
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
