from html import escape
from typing import Any


def e(value: Any) -> str:
    return escape(str(value if value is not None else ""))


def tipo_resposta_label(value: str | None) -> str:
    labels = {
        "escolha_unica": "Escolha única",
        "multipla_escolha": "Múltipla escolha",
        "eleicao": "Eleição de nomes",
    }
    return labels.get(value or "", value or "-")


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
    :root {{ font-family: Arial, Helvetica, sans-serif; color: #1f2937; background: #f6f7fb; }}
    body {{ margin: 0; }}
    .nav {{ display: flex; gap: 14px; align-items: center; padding: 12px 18px; background: #0f172a; color: white; flex-wrap: wrap; }}
    .nav a {{ color: white; text-decoration: none; font-weight: 700; }}
    .grow {{ flex: 1; }}
    main {{ max-width: 1120px; margin: 22px auto; padding: 0 14px; }}
    .card {{ background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 18px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(15,23,42,.06); }}
    .tight {{ max-width: 520px; margin: 60px auto; }}
    h1, h2, h3 {{ margin-top: 0; letter-spacing: 0; }}
    h1 {{ font-size: 26px; }}
    h2 {{ font-size: 20px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ background: #eef2f7; }}
    label {{ display: block; font-weight: 700; margin-top: 12px; }}
    input, select, textarea {{ width: 100%; padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; box-sizing: border-box; font: inherit; }}
    textarea {{ min-height: 112px; }}
    small {{ color: #64748b; font-weight: 400; }}
    .btn, button {{ display: inline-block; padding: 9px 12px; border-radius: 8px; border: 0; background: #2563eb; color: white; font-weight: 700; text-decoration: none; cursor: pointer; margin: 2px; }}
    .btn.secondary, button.secondary {{ background: #475569; }}
    .btn.danger, button.danger {{ background: #dc2626; }}
    .btn.ok, button.ok {{ background: #16803a; }}
    .alert {{ padding: 12px; border-radius: 8px; margin-bottom: 12px; }}
    .error {{ background: #fee2e2; color: #991b1b; }}
    .success {{ background: #dcfce7; color: #166534; }}
    .note {{ background: #eef6ff; color: #1e3a5f; }}
    .status {{ font-weight: 700; padding: 4px 8px; border-radius: 999px; background: #e2e8f0; white-space: nowrap; }}
    .status.ativa {{ background: #dcfce7; color: #166534; }}
    .status.encerrada {{ background: #e0e7ff; color: #3730a3; }}
    .status.invalidada {{ background: #fee2e2; color: #991b1b; }}
    .meeting {{ display: grid; grid-template-columns: minmax(0, 1fr) 380px; gap: 16px; align-items: stretch; }}
    .stage {{ min-height: 430px; background: #111827; color: white; border-radius: 8px; display: flex; flex-direction: column; justify-content: space-between; padding: 18px; }}
    .stage-title {{ font-size: 20px; font-weight: 700; }}
    .stage-muted {{ color: #cbd5e1; }}
    .poll-panel {{ background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px; }}
    .poll-meta {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 12px 0; }}
    .metric {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; }}
    .metric strong {{ display: block; color: #0f172a; }}
    .choice {{ display: flex; gap: 8px; align-items: flex-start; padding: 10px; border: 1px solid #e2e8f0; border-radius: 8px; margin: 8px 0; font-weight: 600; }}
    .choice input {{ width: auto; margin-top: 2px; }}
    .progress {{ background: #e5e7eb; border-radius: 999px; overflow: hidden; height: 18px; }}
    .bar {{ background: #2563eb; height: 18px; min-width: 2px; }}
    .muted {{ color: #64748b; }}
    @media (max-width: 860px) {{ .meeting {{ grid-template-columns: 1fr; }} .stage {{ min-height: 240px; }} }}
    @media (max-width: 720px) {{ table, thead, tbody, tr, td, th {{ display: block; }} th {{ display:none; }} td {{ border-bottom: 1px solid #e2e8f0; }} .nav {{ display:block; }} .nav a {{ display:inline-block; margin: 5px 8px 5px 0; }} .poll-meta {{ grid-template-columns: 1fr; }} }}
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
    <section class='card tight'>
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
    rows = "".join(_votacao_row(v, user) for v in votacoes[:6]) or "<tr><td colspan='7'>Nenhuma votação cadastrada.</td></tr>"
    body = f"""
    <section class='card'>
      <h1>Votações da assembleia</h1>
      <p>O administrador prepara as enquetes antes da reunião e libera cada votação no momento certo, como em uma reunião com Polls.</p>
    </section>
    <section class='card'>
      <h2>Votações recentes</h2>
      <table>
        <thead><tr><th>Reunião</th><th>Pauta</th><th>Votação</th><th>Resposta</th><th>Tempo</th><th>Status</th><th>Comandos</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
    """
    return base("Dashboard", body, user)


def votacoes(user: dict[str, Any], votacoes: list[dict[str, Any]], message: str = "", error: str = "") -> str:
    rows = "".join(_votacao_row(v, user) for v in votacoes) or "<tr><td colspan='7'>Nenhuma votação cadastrada.</td></tr>"
    msg = f"<div class='alert success'>{e(message)}</div>" if message else ""
    err = f"<div class='alert error'>{e(error)}</div>" if error else ""
    body = f"""
    <section class='card'>
      <h1>Gestão de votações</h1>
      {msg}{err}
      {"<p><a class='btn' href='/votacoes/nova'>Nova votação</a></p>" if user.get('tipo_usuario') == 'administrador' else ""}
      <table>
        <thead><tr><th>Reunião vinculada</th><th>Pauta</th><th>Votação</th><th>Resposta</th><th>Tempo</th><th>Status</th><th>Comandos</th></tr></thead>
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
    if v["status"] in {"encerrada", "invalidada"}:
        cmds.append(f"<a class='btn secondary' href='/votacoes/{v['id_votacao']}/resultado'>Resultados</a>")
    if user.get("tipo_usuario") == "administrador":
        if v["status"] == "agendada":
            cmds.append(f"<form method='post' action='/votacoes/{v['id_votacao']}/iniciar' style='display:inline'><button class='ok'>Iniciar</button></form>")
        if v["status"] in {"ativa", "agendada"}:
            cmds.append(f"<form method='post' action='/votacoes/{v['id_votacao']}/encerrar' style='display:inline'><button class='danger'>Encerrar</button></form>")
    return f"""
    <tr>
      <td>{e(v['reuniao_titulo'])}</td>
      <td>{e(v['pauta_assunto'])}</td>
      <td>{e(v['assunto'])}</td>
      <td>{tipo_resposta_label(v.get('tipo_resposta'))}</td>
      <td>{e(v['tempo_resposta'])} min</td>
      <td><span class='status {status}'>{status}</span></td>
      <td>{''.join(cmds) or '-'}</td>
    </tr>
    """


def form_votacao(user: dict[str, Any], reunioes: list[dict[str, Any]], pautas_por_reuniao: dict[int, list[dict[str, Any]]], error: str = "") -> str:
    err = f"<div class='alert error'>{e(error)}</div>" if error else ""
    options = []
    for reuniao in reunioes:
        for pauta in pautas_por_reuniao.get(reuniao["id_reuniao"], []):
            options.append(f"<option value='{pauta['id_pauta']}'>{e(reuniao['titulo'])} - {e(pauta['assunto'])}</option>")
    pauta_options = "".join(options) or "<option value=''>Cadastre uma reunião com pauta antes de criar votação</option>"
    body = f"""
    <section class='card'>
      <h1>Criar votação</h1>
      <p class='muted'>Configure a enquete antes da reunião e deixe para iniciar somente quando o assunto for apresentado.</p>
      {err}
      <form method='post' action='/votacoes/nova'>
        <label>Reunião e pauta vinculada*</label>
        <select name='id_pauta' required>{pauta_options}</select>

        <label>Assunto da votação* <small>até 255 caracteres</small></label>
        <input name='assunto' maxlength='255' required value='Aprovação das Contas de 2025'>

        <label>Tipo de votação*</label>
        <select name='tipo_votacao'>
          <option value='aberta'>Aberta</option>
          <option value='fechada'>Fechada</option>
        </select>

        <label>Tipo de resposta*</label>
        <select name='tipo_resposta'>
          <option value='escolha_unica'>Escolha única</option>
          <option value='multipla_escolha'>Múltipla escolha</option>
          <option value='eleicao'>Eleição de nomes</option>
        </select>

        <label>Quantidade máxima de marcações <small>usada em múltipla escolha</small></label>
        <input name='max_marcacoes' type='number' min='1' value='1'>

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
    votacao = data["votacao"]
    err = f"<div class='alert error'>{e(error)}</div>" if error else ""
    msg = f"<div class='alert success'>{e(message)}</div>" if message else ""
    encerramento = votacao.get("encerra_em") or ""
    end_iso = e(str(encerramento).replace(" ", "T")[:19])
    disabled = "disabled" if message else ""
    max_marcacoes = int(votacao.get("max_marcacoes") or 1)
    input_type = "checkbox" if votacao.get("tipo_resposta") == "multipla_escolha" else "radio"
    required_attr = "required" if input_type == "radio" else ""
    choices = "".join(
        f"<label class='choice'><input type='{input_type}' name='id_opcao' value='{o['id_opcao']}' {required_attr} {disabled}> <span>{e(o['descricao'])}</span></label>"
        for o in opcoes
    )
    regra = f"Selecione até {max_marcacoes} opção(ões)." if input_type == "checkbox" else "Selecione uma opção."
    limit_script = ""
    if input_type == "checkbox":
        limit_script = f"""
        <script>
          const maxChoices = {max_marcacoes};
          document.querySelectorAll("input[name='id_opcao']").forEach((box) => {{
            box.addEventListener("change", () => {{
              const selected = document.querySelectorAll("input[name='id_opcao']:checked").length;
              if (selected > maxChoices) {{
                box.checked = false;
                alert("Selecione no máximo " + maxChoices + " opção(ões).");
              }}
            }});
          }});
        </script>
        """
    body = f"""
    <section class='meeting'>
      <div class='stage'>
        <div>
          <div class='stage-title'>Reunião: {e(votacao['reuniao_titulo'])}</div>
          <p class='stage-muted'>Player externo incorporado: Google Meet, Microsoft Teams ou Zoom.</p>
        </div>
        <div class='stage-muted'>A votação aparece para os presentes quando o administrador inicia a enquete.</div>
      </div>
      <aside class='poll-panel'>
        <h1>{e(votacao['assunto'])}</h1>
        {err}{msg}
        <p><strong>Pauta:</strong> {e(votacao['pauta_assunto'])}</p>
        <p><strong>Pergunta:</strong> {e(votacao['pergunta'])}</p>
        <div class='poll-meta'>
          <div class='metric'><strong id='countdown' data-end='{end_iso}'>--:--</strong><span>Tempo restante</span></div>
          <div class='metric'><strong>{peso:.2f}</strong><span>Seu peso de voto</span></div>
        </div>
        <form method='post' action='/votacoes/{votacao['id_votacao']}/votar'>
          <h2>Selecione sua opção</h2>
          <p class='muted'>{regra}</p>
          {choices}
          <p><button type='submit' {disabled}>Confirmar voto</button></p>
        </form>
      </aside>
    </section>
    <script>
      const target = document.getElementById("countdown");
      function tick() {{
        if (!target || !target.dataset.end) return;
        const end = new Date(target.dataset.end).getTime();
        const remaining = Math.max(0, end - Date.now());
        const totalSeconds = Math.floor(remaining / 1000);
        const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
        const seconds = String(totalSeconds % 60).padStart(2, "0");
        target.textContent = `${{minutes}}:${{seconds}}`;
      }}
      tick();
      setInterval(tick, 1000);
    </script>
    {limit_script}
    """
    return base("Votação ativa", body, user)


def resultado(user: dict[str, Any], result: dict[str, Any], error: str = "") -> str:
    votacao = result["votacao"]
    if error:
        body = f"""
        <section class='card'>
          <div class='alert error'>{e(error)}</div>
          <p><a class='btn secondary' href='/votacoes'>Voltar</a></p>
        </section>
        """
        return base("Resultado", body, user)

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

    alerta = ""
    if votacao["status"] == "invalidada":
        alerta = "<div class='alert error'>Votação invalidada por tentativa de voto não autorizado. O resultado não deve ser usado como deliberação.</div>"

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
      <h1>Resultado da votação</h1>
      {alerta}
      <p><strong>Status:</strong> <span class='status {e(votacao['status'])}'>{e(votacao['status'])}</span></p>
      <p><strong>Assunto:</strong> {e(votacao['assunto'])}</p>
      <p><strong>Visibilidade:</strong> {e(votacao['tipo_votacao']).title()} | <strong>Resposta:</strong> {tipo_resposta_label(votacao.get('tipo_resposta'))}</p>
      <p><strong>Total de votantes:</strong> {result['total_votos']} | <strong>Peso computado:</strong> {result['total_peso']:.2f}</p>
      <h2>Resultado consolidado</h2>
      <table><thead><tr><th>Opção</th><th>Votos/seleções</th><th>Peso acumulado</th><th>Percentual por peso</th></tr></thead><tbody>{rows}</tbody></table>
      {nominais}
      <p><a class='btn secondary' href='/votacoes'>Voltar</a></p>
    </section>
    """
    return base("Resultado", body, user)


def logs(user: dict[str, Any], logs: list[dict[str, Any]]) -> str:
    rows = "".join(
        f"<tr><td>{e(l['data_hora'])}</td><td>{e(l['nome_completo'] or 'Sistema')}</td><td>{e(l['acao'])}</td><td>{e(l['entidade'])}</td><td>{e(l['ip'])}</td><td>{e(l['navegador'])}</td></tr>"
        for l in logs
    )
    body = f"""
    <section class='card'>
      <h1>Auditoria</h1>
      <table><thead><tr><th>Data/Hora</th><th>Usuário</th><th>Ação</th><th>Entidade</th><th>IP</th><th>Navegador</th></tr></thead><tbody>{rows}</tbody></table>
    </section>
    """
    return base("Auditoria", body, user)
