from html import escape
from typing import Any


def e(value: Any) -> str:
    return escape(str(value if value is not None else ""))


def base(title: str, body: str, user: dict[str, Any] | None = None) -> str:
    nav = ""
    if user:
        nav = f"""
        <nav class='nav'>
          <a href='/'>Dashboard</a>
          <a href='/votacoes'>Votações</a>
          {"<a href='/votacoes/nova'>Nova votação</a>" if user.get('tipo_usuario') == 'administrador' else ""}
          {"<a href='/logs'>Auditoria</a>" if user.get('tipo_usuario') == 'administrador' else ""}
          <span class='grow'></span>
          <span>{e(user.get('nome_completo'))}</span>
          <a href='/logout'>Sair</a>
        </nav>
        """
    return f"""<!doctype html>
<html lang='pt-BR'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>{e(title)} - CONVIVA</title>
  <style>
    :root {{ font-family: Arial, Helvetica, sans-serif; color: #1f2937; background: #f5f7fb; }}
    body {{ margin: 0; }}
    .nav {{ display: flex; gap: 14px; align-items: center; padding: 12px 18px; background: #0f172a; color: white; flex-wrap: wrap; }}
    .nav a {{ color: white; text-decoration: none; font-weight: 600; }}
    .grow {{ flex: 1; }}
    main {{ max-width: 1120px; margin: 22px auto; padding: 0 14px; }}
    .card {{ background: white; border: 1px solid #e5e7eb; border-radius: 12px; padding: 18px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(15,23,42,.06); }}
    h1, h2, h3 {{ margin-top: 0; }}
    table {{ width: 100%; border-collapse: collapse; background: white; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f1f5f9; }}
    label {{ display: block; font-weight: 700; margin-top: 12px; }}
    input, select, textarea {{ width: 100%; padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; box-sizing: border-box; }}
    textarea {{ min-height: 92px; }}
    .btn, button {{ display: inline-block; padding: 9px 12px; border-radius: 8px; border: 0; background: #2563eb; color: white; font-weight: 700; text-decoration: none; cursor: pointer; margin: 2px; }}
    .btn.secondary {{ background: #475569; }} .btn.danger {{ background: #dc2626; }} .btn.ok {{ background: #16a34a; }}
    .alert {{ padding: 12px; border-radius: 8px; margin-bottom: 12px; }}
    .error {{ background: #fee2e2; color: #991b1b; }} .success {{ background: #dcfce7; color: #166534; }}
    .status {{ font-weight: 700; padding: 4px 8px; border-radius: 999px; background: #e2e8f0; }}
    .status.ativa {{ background: #dcfce7; color: #166534; }} .status.encerrada {{ background: #e0e7ff; color: #3730a3; }} .status.invalidada {{ background: #fee2e2; color: #991b1b; }}
    .video {{ display:flex; align-items:center; justify-content:center; min-height: 220px; background: #111827; color: white; border-radius: 12px; margin-bottom: 14px; }}
    .progress {{ background: #e5e7eb; border-radius: 999px; overflow: hidden; height: 18px; }}
    .bar {{ background: #2563eb; height: 18px; }}
    @media (max-width: 720px) {{ table, thead, tbody, tr, td, th {{ display: block; }} th {{ display:none; }} td {{ border-bottom: 1px solid #e2e8f0; }} .nav {{ display:block; }} .nav a {{ display:inline-block; margin: 5px 8px 5px 0; }} }}
  </style>
</head>
<body>
  {nav}
  <main>{body}</main>
</body>
</html>"""


def login(error: str = "") -> str:
    msg = f"<div class='alert error'>{e(error)}</div>" if error else ""
    body = f"""
    <section class='card' style='max-width:480px;margin:60px auto;'>
      <h1>CONVIVA</h1>
      <h2>Entrar no sistema</h2>
      {msg}
      <form method='post' action='/login'>
        <label>E-mail</label>
        <input name='email' type='email' required autofocus>
        <label>Senha</label>
        <input name='senha' type='password' required>
        <p><button type='submit'>Entrar</button></p>
      </form>
    </section>
    """
    return base("Login", body)


def dashboard(user: dict[str, Any], votacoes: list[dict[str, Any]]) -> str:
    rows = "".join(_votacao_row(v, user) for v in votacoes[:6]) or "<tr><td colspan='6'>Nenhuma votação cadastrada.</td></tr>"
    body = f"""
    <section class='card'>
      <h1>Dashboard do Sistema de Votação</h1>
      <p>Arquitetura MVC Web em monólito modular para o recorte: entrar, criar votação, executar votação e verificar resultado.</p>
    </section>
    <section class='card'>
      <h2>Votações recentes</h2>
      <table>
        <thead><tr><th>Reunião</th><th>Pauta</th><th>Assunto</th><th>Tipo</th><th>Status</th><th>Comandos</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
    """
    return base("Dashboard", body, user)


def votacoes(user: dict[str, Any], votacoes: list[dict[str, Any]], message: str = "", error: str = "") -> str:
    rows = "".join(_votacao_row(v, user) for v in votacoes) or "<tr><td colspan='6'>Nenhuma votação cadastrada.</td></tr>"
    msg = f"<div class='alert success'>{e(message)}</div>" if message else ""
    err = f"<div class='alert error'>{e(error)}</div>" if error else ""
    body = f"""
    <section class='card'>
      <h1>Gestão de Votações</h1>
      {msg}{err}
      {"<p><a class='btn' href='/votacoes/nova'>Nova votação</a></p>" if user.get('tipo_usuario') == 'administrador' else ""}
      <table>
        <thead><tr><th>Reunião vinculada</th><th>Pauta</th><th>Assunto</th><th>Tipo</th><th>Status</th><th>Comandos</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
    """
    return base("Votações", body, user)


def _votacao_row(v: dict[str, Any], user: dict[str, Any]) -> str:
    status = e(v["status"])
    cmds = []
    if v["status"] == "ativa":
        cmds.append(f"<a class='btn ok' href='/votacoes/{v['id_votacao']}/votar'>Votar</a>")
    if v["status"] == "encerrada":
        cmds.append(f"<a class='btn secondary' href='/votacoes/{v['id_votacao']}/resultado'>Resultados</a>")
    if user.get("tipo_usuario") == "administrador":
        if v["status"] == "agendada":
            cmds.append(f"<form method='post' action='/votacoes/{v['id_votacao']}/iniciar' style='display:inline'><button class='btn ok'>Iniciar</button></form>")
        if v["status"] in {"ativa", "agendada"}:
            cmds.append(f"<form method='post' action='/votacoes/{v['id_votacao']}/encerrar' style='display:inline'><button class='btn danger'>Encerrar</button></form>")
        if v["status"] != "ativa":
            cmds.append(f"<a class='btn secondary' href='/votacoes/{v['id_votacao']}/resultado'>Resultado</a>")
    return f"""
    <tr>
      <td>{e(v['reuniao_titulo'])}</td>
      <td>{e(v['pauta_assunto'])}</td>
      <td>{e(v['assunto'])}</td>
      <td>{e(v['tipo_votacao']).title()}</td>
      <td><span class='status {status}'>{status}</span></td>
      <td>{''.join(cmds) or '-'}</td>
    </tr>
    """


def form_votacao(user: dict[str, Any], reunioes: list[dict[str, Any]], pautas_por_reuniao: dict[int, list[dict[str, Any]]], error: str = "") -> str:
    err = f"<div class='alert error'>{e(error)}</div>" if error else ""
    options = []
    for reuniao in reunioes:
        for pauta in pautas_por_reuniao.get(reuniao["id_reuniao"], []):
            options.append(f"<option value='{pauta['id_pauta']}'>{e(reuniao['titulo'])} — {e(pauta['assunto'])}</option>")
    body = f"""
    <section class='card'>
      <h1>Criar votação</h1>
      {err}
      <form method='post' action='/votacoes/nova'>
        <label>Reunião e pauta vinculada*</label>
        <select name='id_pauta' required>{''.join(options)}</select>
        <label>Assunto da votação* <small>até 255 caracteres</small></label>
        <input name='assunto' maxlength='255' required value='Aprovação das Contas de 2025'>
        <label>Tipo de votação*</label>
        <select name='tipo_votacao'>
          <option value='aberta'>Aberta</option>
          <option value='fechada'>Fechada</option>
        </select>
        <label>Tempo para responder* (minutos)</label>
        <input name='tempo_resposta' type='number' min='1' value='10' required>
        <label>Pergunta* <small>até 255 caracteres</small></label>
        <input name='pergunta' maxlength='255' required value='Vocês aprovam o balanço financeiro apresentado?'>
        <label>Opções de voto* <small>uma por linha</small></label>
        <textarea name='opcoes' required>Aprovar
Rejeitar
Não sei / não quero responder</textarea>
        <p><button type='submit'>Salvar votação</button> <a href='/votacoes' class='btn secondary'>Cancelar</a></p>
      </form>
    </section>
    """
    return base("Criar votação", body, user)


def votar(user: dict[str, Any], data: dict[str, Any], opcoes: list[dict[str, Any]], peso: float, error: str = "", message: str = "") -> str:
    err = f"<div class='alert error'>{e(error)}</div>" if error else ""
    msg = f"<div class='alert success'>{e(message)}</div>" if message else ""
    radio = "".join(f"<label><input style='width:auto' type='radio' name='id_opcao' value='{o['id_opcao']}' required> {e(o['descricao'])}</label>" for o in opcoes)
    encerramento = data['votacao'].get('encerra_em') or ""
    disabled = "disabled" if message else ""
    body = f"""
    <section class='card'>
      <div class='video'>[ÁREA DE VÍDEO] Player de vídeo integrado do Google Meet / Zoom / Teams</div>
      <h1>Tela de Votação Ativa</h1>
      {err}{msg}
      <p><strong>Assunto em votação:</strong> {e(data['votacao']['assunto'])}</p>
      <p><strong>Pauta relacionada:</strong> {e(data['votacao']['pauta_assunto'])}</p>
      <p><strong>Pergunta:</strong> {e(data['votacao']['pergunta'])}</p>
      <p><strong>Tempo final programado:</strong> {e(encerramento)}</p>
      <p><strong>Seu peso de voto:</strong> {peso:.2f}</p>
      <form method='post' action='/votacoes/{data['votacao']['id_votacao']}/votar'>
        <h3>Selecione sua opção</h3>
        {radio}
        <p><button type='submit' {disabled}>Confirmar voto</button></p>
      </form>
    </section>
    """
    return base("Votação ativa", body, user)


def resultado(user: dict[str, Any], result: dict[str, Any], error: str = "") -> str:
    votacao = result["votacao"]
    if error:
        return base("Resultado", f"<section class='card'><div class='alert error'>{e(error)}</div></section>", user)
    rows = ""
    for op in result["opcoes"]:
        rows += f"""
        <tr>
          <td>{e(op['descricao'])}</td>
          <td>{op['votos']}</td>
          <td>{op['peso']:.2f}</td>
          <td>{op['percentual']:.1f}%<div class='progress'><div class='bar' style='width:{op['percentual']:.1f}%'></div></div></td>
        </tr>
        """
    nominais = ""
    if votacao["tipo_votacao"] == "aberta":
        nrows = "".join(
            f"<tr><td>{e(n['id_voto'])}</td><td>{e(n['nome_completo'])}</td><td>{e(n['imoveis'])}</td><td>{e(n['voto'])}</td><td>{float(n['peso_aplicado']):.2f}</td><td>{e(n['data_hora_voto'])}</td></tr>"
            for n in result["nominais"]
        ) or "<tr><td colspan='6'>Nenhum voto registrado.</td></tr>"
        nominais = f"""
        <h2>Relatório de votos nominais</h2>
        <table><thead><tr><th>Cód.</th><th>Nome</th><th>Imóvel</th><th>Voto</th><th>Peso</th><th>Horário</th></tr></thead><tbody>{nrows}</tbody></table>
        """
    else:
        nominais = "<p><strong>Votação fechada:</strong> votos nominais ocultados. Exibição somente do resultado consolidado.</p>"
    body = f"""
    <section class='card'>
      <h1>Tela de Resultado da Votação</h1>
      <p><strong>Status:</strong> <span class='status {e(votacao['status'])}'>{e(votacao['status'])}</span></p>
      <p><strong>Assunto:</strong> {e(votacao['assunto'])}</p>
      <p><strong>Visibilidade:</strong> {e(votacao['tipo_votacao']).title()}</p>
      <p><strong>Total de votos:</strong> {result['total_votos']} | <strong>Peso computado:</strong> {result['total_peso']:.2f}</p>
      <h2>Resultado consolidado</h2>
      <table><thead><tr><th>Opção</th><th>Votos</th><th>Peso acumulado</th><th>Percentual por peso</th></tr></thead><tbody>{rows}</tbody></table>
      {nominais}
      <p><a class='btn secondary' href='/votacoes'>Voltar</a></p>
    </section>
    """
    return base("Resultado", body, user)


def logs(user: dict[str, Any], logs: list[dict[str, Any]]) -> str:
    rows = "".join(f"<tr><td>{e(l['data_hora'])}</td><td>{e(l['nome_completo'] or 'Sistema')}</td><td>{e(l['acao'])}</td><td>{e(l['entidade'])}</td><td>{e(l['ip'])}</td><td>{e(l['navegador'])}</td></tr>" for l in logs)
    body = f"""
    <section class='card'>
      <h1>Gestão de Auditoria</h1>
      <table><thead><tr><th>Data/Hora</th><th>Usuário</th><th>Ação</th><th>Entidade</th><th>IP</th><th>Navegador</th></tr></thead><tbody>{rows}</tbody></table>
    </section>
    """
    return base("Auditoria", body, user)
