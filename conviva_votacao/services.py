from datetime import datetime, timedelta
from typing import Any

from . import models

DATE_FMT = "%Y-%m-%d %H:%M:%S"


def now_str() -> str:
    return datetime.now().strftime(DATE_FMT)


def audit(user: dict[str, Any] | None, acao: str, entidade: str, ip: str = "", navegador: str = "") -> None:
    models.execute(
        "INSERT INTO log_auditoria (id_usuario, acao, entidade, data_hora, ip, navegador) VALUES (?, ?, ?, ?, ?, ?)",
        [user["id_usuario"] if user else None, acao, entidade, now_str(), ip, navegador],
    )


def list_reunioes() -> list[dict[str, Any]]:
    return [dict(r) for r in models.query("SELECT * FROM reuniao ORDER BY data DESC, hora DESC")]


def list_pautas_by_reuniao(id_reuniao: int) -> list[dict[str, Any]]:
    return [dict(r) for r in models.query("SELECT * FROM pauta WHERE id_reuniao = ? ORDER BY id_pauta", [id_reuniao])]


def list_votacoes() -> list[dict[str, Any]]:
    rows = models.query(
        """
        SELECT v.*, p.assunto AS pauta_assunto, r.titulo AS reuniao_titulo, r.id_reuniao
        FROM votacao v
        JOIN pauta p ON p.id_pauta = v.id_pauta
        JOIN reuniao r ON r.id_reuniao = p.id_reuniao
        ORDER BY v.id_votacao DESC
        """
    )
    return [dict(r) for r in rows]


def get_votacao(id_votacao: int) -> dict[str, Any] | None:
    row = models.query_one(
        """
        SELECT v.*, p.assunto AS pauta_assunto, p.descricao AS pauta_descricao,
               r.titulo AS reuniao_titulo, r.id_reuniao, r.id_condominio
        FROM votacao v
        JOIN pauta p ON p.id_pauta = v.id_pauta
        JOIN reuniao r ON r.id_reuniao = p.id_reuniao
        WHERE v.id_votacao = ?
        """,
        [id_votacao],
    )
    return dict(row) if row else None


def get_opcoes(id_votacao: int) -> list[dict[str, Any]]:
    return [dict(r) for r in models.query("SELECT * FROM opcao_voto WHERE id_votacao = ? ORDER BY ordem", [id_votacao])]


def create_votacao(data: dict[str, Any], user: dict[str, Any], ip: str, navegador: str) -> int:
    assunto = data.get("assunto", "").strip()
    pergunta = data.get("pergunta", "").strip()
    tipo_votacao = data.get("tipo_votacao", "aberta").strip()
    tempo_resposta = int(data.get("tempo_resposta") or 0)
    id_pauta = int(data.get("id_pauta") or 0)
    opcoes_texto = [o.strip() for o in data.get("opcoes", "").splitlines() if o.strip()]

    if not assunto or len(assunto) > 255:
        raise ValueError("O assunto da votação é obrigatório e deve ter até 255 caracteres.")
    if not pergunta or len(pergunta) > 255:
        raise ValueError("A pergunta da votação é obrigatória e deve ter até 255 caracteres.")
    if tipo_votacao not in {"aberta", "fechada"}:
        raise ValueError("Tipo de votação inválido.")
    if tempo_resposta <= 0:
        raise ValueError("O tempo de resposta deve ser maior que zero.")
    if len(opcoes_texto) < 2:
        raise ValueError("Cadastre pelo menos duas opções de voto.")
    pauta = models.query_one("SELECT id_pauta FROM pauta WHERE id_pauta = ?", [id_pauta])
    if not pauta:
        raise ValueError("A pauta vinculada não existe.")

    id_votacao = models.execute(
        """
        INSERT INTO votacao (id_pauta, assunto, pergunta, tipo_votacao, tipo_resposta, tempo_resposta, max_marcacoes, status)
        VALUES (?, ?, ?, ?, 'escolha_unica', ?, 1, 'agendada')
        """,
        [id_pauta, assunto, pergunta, tipo_votacao, tempo_resposta],
    )
    models.execute_many(
        "INSERT INTO opcao_voto (id_votacao, descricao, ordem) VALUES (?, ?, ?)",
        [[id_votacao, descricao, ordem] for ordem, descricao in enumerate(opcoes_texto, start=1)],
    )
    audit(user, "criou votação", f"votacao:{id_votacao}", ip, navegador)
    return id_votacao


def iniciar_votacao(id_votacao: int, user: dict[str, Any], ip: str, navegador: str) -> None:
    votacao = get_votacao(id_votacao)
    if not votacao:
        raise ValueError("Votação não encontrada.")
    if votacao["status"] != "agendada":
        raise ValueError("Somente votação agendada pode ser iniciada.")
    inicio = datetime.now()
    fim = inicio + timedelta(minutes=int(votacao["tempo_resposta"]))
    models.execute(
        "UPDATE votacao SET status = 'ativa', iniciou_em = ?, encerra_em = ? WHERE id_votacao = ?",
        [inicio.strftime(DATE_FMT), fim.strftime(DATE_FMT), id_votacao],
    )
    audit(user, "iniciou votação", f"votacao:{id_votacao}", ip, navegador)


def encerrar_votacao(id_votacao: int, user: dict[str, Any], ip: str, navegador: str) -> None:
    votacao = get_votacao(id_votacao)
    if not votacao:
        raise ValueError("Votação não encontrada.")
    if votacao["status"] not in {"ativa", "agendada"}:
        raise ValueError("A votação já está encerrada ou invalidada.")
    models.execute(
        "UPDATE votacao SET status = 'encerrada', encerrada_em = ? WHERE id_votacao = ?",
        [now_str(), id_votacao],
    )
    audit(user, "encerrou votação", f"votacao:{id_votacao}", ip, navegador)


def auto_encerrar_se_expirada(id_votacao: int) -> None:
    votacao = get_votacao(id_votacao)

    if not votacao or votacao["status"] != "ativa":
        return

    encerra_em = votacao.get("encerra_em")
    if isinstance(encerra_em, str):
        try:
            encerra_em = datetime.strptime(encerra_em, DATE_FMT)
        except ValueError:
            return

    if encerra_em and datetime.now() >= encerra_em:
        models.execute("UPDATE votacao SET status = 'encerrada', encerrada_em = ? WHERE id_votacao = ?", [now_str(), id_votacao])

def usuario_presente_na_reuniao(id_usuario: int, id_reuniao: int) -> bool:
    row = models.query_one(
        "SELECT 1 FROM convidado_reuniao WHERE id_usuario = ? AND id_reuniao = ? AND status_presenca = 1",
        [id_usuario, id_reuniao],
    )
    return bool(row)


def calcular_peso_usuario(id_usuario: int, id_condominio: int) -> float:
    row = models.query_one(
        """
        SELECT COALESCE(SUM(CASE WHEN inadimplente = 1 THEN 0 ELSE peso_original END), 0) AS peso
        FROM lote
        WHERE id_usuario = ? AND id_condominio = ?
        """,
        [id_usuario, id_condominio],
    )
    return float(row["peso"] if row else 0)


def usuario_ja_votou(id_usuario: int, id_votacao: int) -> bool:
    return bool(models.query_one("SELECT 1 FROM voto WHERE id_usuario = ? AND id_votacao = ?", [id_usuario, id_votacao]))


def registrar_voto(id_votacao: int, id_opcao: int, user: dict[str, Any], ip: str, navegador: str) -> int:
    auto_encerrar_se_expirada(id_votacao)
    votacao = get_votacao(id_votacao)
    if not votacao:
        raise ValueError("Votação não encontrada.")
    if votacao["status"] != "ativa":
        raise ValueError("A votação não está ativa.")
    if not usuario_presente_na_reuniao(user["id_usuario"], votacao["id_reuniao"]):
        models.execute("UPDATE votacao SET status = 'invalidada', encerrada_em = ? WHERE id_votacao = ?", [now_str(), id_votacao])
        audit(user, "tentativa de voto não autorizado; votação invalidada", f"votacao:{id_votacao}", ip, navegador)
        raise ValueError("Usuário não está presente na reunião. Votação invalidada por voto não autorizado.")
    if usuario_ja_votou(user["id_usuario"], id_votacao):
        raise ValueError("Este usuário já votou nesta votação.")
    opcao = models.query_one("SELECT id_opcao FROM opcao_voto WHERE id_opcao = ? AND id_votacao = ?", [id_opcao, id_votacao])
    if not opcao:
        raise ValueError("Opção de voto inválida.")
    peso = calcular_peso_usuario(user["id_usuario"], votacao["id_condominio"])
    id_voto = models.execute(
        "INSERT INTO voto (id_usuario, id_votacao, data_hora_voto, peso_aplicado, ip, navegador) VALUES (?, ?, ?, ?, ?, ?)",
        [user["id_usuario"], id_votacao, now_str(), peso, ip, navegador],
    )
    models.execute("INSERT INTO voto_escolha (id_voto, id_opcao) VALUES (?, ?)", [id_voto, id_opcao])
    audit(user, "registrou voto", f"votacao:{id_votacao}", ip, navegador)
    return id_voto


def resultado_votacao(id_votacao: int) -> dict[str, Any]:
    auto_encerrar_se_expirada(id_votacao)
    votacao = get_votacao(id_votacao)
    if not votacao:
        raise ValueError("Votação não encontrada.")
    rows = models.query(
        """
        SELECT o.id_opcao, o.descricao,
               COALESCE(SUM(v.peso_aplicado), 0) AS peso_acumulado,
               COUNT(v.id_voto) AS total_votos
        FROM opcao_voto o
        LEFT JOIN voto_escolha ve ON ve.id_opcao = o.id_opcao
        LEFT JOIN voto v ON v.id_voto = ve.id_voto
        WHERE o.id_votacao = ?
        GROUP BY o.id_opcao, o.descricao, o.ordem
        ORDER BY o.ordem
        """,
        [id_votacao],
    )
    total_peso = sum(float(r["peso_acumulado"] or 0) for r in rows)
    total_votos = sum(int(r["total_votos"] or 0) for r in rows)
    opcoes = []
    for row in rows:
        peso = float(row["peso_acumulado"] or 0)
        percentual = (peso / total_peso * 100) if total_peso else 0
        opcoes.append({"descricao": row["descricao"], "peso": peso, "votos": row["total_votos"], "percentual": percentual})
    nominais = models.query(
        """
        SELECT v.id_voto, u.nome_completo, GROUP_CONCAT(l.identificacao, ', ') AS imoveis,
               o.descricao AS voto, v.peso_aplicado, v.data_hora_voto
        FROM voto v
        JOIN usuario u ON u.id_usuario = v.id_usuario
        JOIN voto_escolha ve ON ve.id_voto = v.id_voto
        JOIN opcao_voto o ON o.id_opcao = ve.id_opcao
        LEFT JOIN lote l ON l.id_usuario = u.id_usuario AND l.id_condominio = ?
        WHERE v.id_votacao = ?
        GROUP BY v.id_voto, u.nome_completo, o.descricao, v.peso_aplicado, v.data_hora_voto
        ORDER BY v.data_hora_voto
        """,
        [votacao["id_condominio"], id_votacao],
    )
    return {
        "votacao": votacao,
        "opcoes": opcoes,
        "total_peso": total_peso,
        "total_votos": total_votos,
        "nominais": [dict(r) for r in nominais],
    }


def list_logs() -> list[dict[str, Any]]:
    rows = models.query(
        """
        SELECT l.*, u.nome_completo
        FROM log_auditoria l
        LEFT JOIN usuario u ON u.id_usuario = l.id_usuario
        ORDER BY l.id_log DESC
        LIMIT 100
        """
    )
    return [dict(r) for r in rows]
