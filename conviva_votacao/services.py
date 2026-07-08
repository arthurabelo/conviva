from datetime import datetime, timedelta
from typing import Any, Iterable

from . import models

DATE_FMT = "%Y-%m-%d %H:%M:%S"


def now_str() -> str:
    return datetime.now().strftime(DATE_FMT)


class VotingService:
    def audit(self, user: dict[str, Any] | None, acao: str, entidade: str, ip: str = "", navegador: str = "") -> None:
        models.execute(
            "INSERT INTO log_auditoria (id_usuario, acao, entidade, data_hora, ip, navegador) VALUES (?, ?, ?, ?, ?, ?)",
            [user["id_usuario"] if user else None, acao, entidade, now_str(), ip, navegador],
        )

    def list_reunioes(self) -> list[dict[str, Any]]:
        return models.query("SELECT * FROM reuniao ORDER BY data DESC, hora DESC")

    def list_pautas_by_reuniao(self, id_reuniao: int) -> list[dict[str, Any]]:
        return models.query("SELECT * FROM pauta WHERE id_reuniao = ? ORDER BY id_pauta", [id_reuniao])

    def list_votacoes(self) -> list[dict[str, Any]]:
        self.auto_encerrar_expiradas()
        return models.query(
            """
            SELECT v.*, p.assunto AS pauta_assunto, r.titulo AS reuniao_titulo, r.id_reuniao
            FROM votacao v
            JOIN pauta p ON p.id_pauta = v.id_pauta
            JOIN reuniao r ON r.id_reuniao = p.id_reuniao
            ORDER BY v.id_votacao DESC
            """
        )

    def get_votacao(self, id_votacao: int) -> dict[str, Any] | None:
        row = models.query_one(
            """
            SELECT v.*, p.assunto AS pauta_assunto, p.descricao AS pauta_descricao,
                   r.titulo AS reuniao_titulo, r.id_reuniao, r.id_condominio, r.status AS reuniao_status
            FROM votacao v
            JOIN pauta p ON p.id_pauta = v.id_pauta
            JOIN reuniao r ON r.id_reuniao = p.id_reuniao
            WHERE v.id_votacao = ?
            """,
            [id_votacao],
        )
        return dict(row) if row else None

    def get_opcoes(self, id_votacao: int) -> list[dict[str, Any]]:
        return models.query("SELECT * FROM opcao_voto WHERE id_votacao = ? ORDER BY ordem", [id_votacao])

    def create_votacao(self, data: dict[str, Any], user: dict[str, Any], ip: str, navegador: str) -> int:
        assunto = str(data.get("assunto", "")).strip()
        pergunta = str(data.get("pergunta", "")).strip()
        tipo_votacao = str(data.get("tipo_votacao", "aberta")).strip()
        tipo_resposta = str(data.get("tipo_resposta", "escolha_unica")).strip()
        tempo_resposta = int(data.get("tempo_resposta") or 0)
        id_pauta = int(data.get("id_pauta") or 0)
        opcoes_texto = [o.strip() for o in str(data.get("opcoes", "")).splitlines() if o.strip()]
        max_marcacoes = int(data.get("max_marcacoes") or 1)

        if not assunto or len(assunto) > 255:
            raise ValueError("O assunto da votação é obrigatório e deve ter até 255 caracteres.")
        if not pergunta or len(pergunta) > 255:
            raise ValueError("A pergunta da votação é obrigatória e deve ter até 255 caracteres.")
        if tipo_votacao not in {"aberta", "fechada"}:
            raise ValueError("Tipo de votação inválido.")
        if tipo_resposta not in {"escolha_unica", "multipla_escolha", "eleicao"}:
            raise ValueError("Tipo de resposta inválido.")
        if tempo_resposta <= 0:
            raise ValueError("O tempo de resposta deve ser maior que zero.")
        if len(opcoes_texto) < 2:
            raise ValueError("Cadastre pelo menos duas opções de voto.")
        if tipo_resposta != "multipla_escolha":
            max_marcacoes = 1
        if max_marcacoes < 1 or max_marcacoes > len(opcoes_texto):
            raise ValueError("A quantidade de marcações deve estar entre 1 e o total de opções.")

        pauta = models.query_one(
            """
            SELECT p.id_pauta
            FROM pauta p
            JOIN reuniao r ON r.id_reuniao = p.id_reuniao
            WHERE p.id_pauta = ?
            """,
            [id_pauta],
        )
        if not pauta:
            raise ValueError("A pauta vinculada não existe.")

        id_votacao = models.execute(
            """
            INSERT INTO votacao
                (id_pauta, assunto, pergunta, tipo_votacao, tipo_resposta, tempo_resposta, max_marcacoes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'agendada')
            """,
            [id_pauta, assunto, pergunta, tipo_votacao, tipo_resposta, tempo_resposta, max_marcacoes],
        )
        models.execute_many(
            "INSERT INTO opcao_voto (id_votacao, descricao, ordem) VALUES (?, ?, ?)",
            [[id_votacao, descricao, ordem] for ordem, descricao in enumerate(opcoes_texto, start=1)],
        )
        self.audit(user, "criou votação", f"votacao:{id_votacao}", ip, navegador)
        return id_votacao

    def iniciar_votacao(self, id_votacao: int, user: dict[str, Any], ip: str, navegador: str) -> None:
        votacao = self.get_votacao(id_votacao)
        if not votacao:
            raise ValueError("Votação não encontrada.")
        if votacao["status"] != "agendada":
            raise ValueError("Somente votação agendada pode ser iniciada.")
        if votacao["reuniao_status"] != "em_andamento":
            raise ValueError("A votação só pode ser iniciada durante a reunião vinculada.")

        inicio = datetime.now()
        fim = inicio + timedelta(minutes=int(votacao["tempo_resposta"]))
        models.execute(
            "UPDATE votacao SET status = 'ativa', iniciou_em = ?, encerra_em = ? WHERE id_votacao = ?",
            [inicio.strftime(DATE_FMT), fim.strftime(DATE_FMT), id_votacao],
        )
        self.audit(user, "iniciou votação", f"votacao:{id_votacao}", ip, navegador)

    def encerrar_votacao(self, id_votacao: int, user: dict[str, Any], ip: str, navegador: str) -> None:
        votacao = self.get_votacao(id_votacao)
        if not votacao:
            raise ValueError("Votação não encontrada.")
        if votacao["status"] not in {"ativa", "agendada"}:
            raise ValueError("A votação já está encerrada ou invalidada.")
        models.execute(
            "UPDATE votacao SET status = 'encerrada', encerrada_em = ? WHERE id_votacao = ?",
            [now_str(), id_votacao],
        )
        self.audit(user, "encerrou votação", f"votacao:{id_votacao}", ip, navegador)

    def auto_encerrar_expiradas(self) -> None:
        for row in models.query("SELECT id_votacao FROM votacao WHERE status = 'ativa' AND encerra_em IS NOT NULL"):
            self.auto_encerrar_se_expirada(int(row["id_votacao"]))

    def auto_encerrar_se_expirada(self, id_votacao: int) -> None:
        votacao = self.get_votacao(id_votacao)
        if not votacao or votacao["status"] != "ativa":
            return

        encerra_em = self._parse_datetime(votacao.get("encerra_em"))
        if encerra_em and datetime.now() >= encerra_em:
            models.execute(
                "UPDATE votacao SET status = 'encerrada', encerrada_em = ? WHERE id_votacao = ?",
                [now_str(), id_votacao],
            )

    def _parse_datetime(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            for fmt in (DATE_FMT, "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(value[:19], fmt)
                except ValueError:
                    pass
        return None

    def usuario_presente_na_reuniao(self, id_usuario: int, id_reuniao: int) -> bool:
        row = models.query_one(
            "SELECT 1 FROM convidado_reuniao WHERE id_usuario = ? AND id_reuniao = ? AND status_presenca = 1",
            [id_usuario, id_reuniao],
        )
        return bool(row)

    def calcular_peso_usuario(self, id_usuario: int, id_condominio: int) -> float:
        row = models.query_one(
            """
            SELECT COALESCE(SUM(CASE WHEN inadimplente = 1 THEN 0 ELSE peso_original END), 0) AS peso
            FROM lote
            WHERE id_usuario = ? AND id_condominio = ?
            """,
            [id_usuario, id_condominio],
        )
        return float(row["peso"] if row else 0)

    def usuario_ja_votou(self, id_usuario: int, id_votacao: int) -> bool:
        return bool(models.query_one("SELECT 1 FROM voto WHERE id_usuario = ? AND id_votacao = ?", [id_usuario, id_votacao]))

    def registrar_voto(self, id_votacao: int, ids_opcoes: int | str | Iterable[int | str], user: dict[str, Any], ip: str, navegador: str) -> int:
        self.auto_encerrar_se_expirada(id_votacao)
        votacao = self.get_votacao(id_votacao)
        if not votacao:
            raise ValueError("Votação não encontrada.")
        if votacao["status"] != "ativa":
            raise ValueError("A votação não está ativa.")
        if not self.usuario_presente_na_reuniao(user["id_usuario"], votacao["id_reuniao"]):
            models.execute("UPDATE votacao SET status = 'invalidada', encerrada_em = ? WHERE id_votacao = ?", [now_str(), id_votacao])
            self.audit(user, "tentativa de voto não autorizado; votação invalidada", f"votacao:{id_votacao}", ip, navegador)
            raise ValueError("Usuário não está presente na reunião. Votação invalidada por voto não autorizado.")
        if self.usuario_ja_votou(user["id_usuario"], id_votacao):
            raise ValueError("Este usuário já votou nesta votação.")

        escolhas = self._normalizar_escolhas(ids_opcoes)
        max_marcacoes = int(votacao.get("max_marcacoes") or 1)
        if not escolhas:
            raise ValueError("Selecione pelo menos uma opção.")
        if len(escolhas) != len(set(escolhas)):
            raise ValueError("A mesma opção não pode ser marcada mais de uma vez.")
        if votacao["tipo_resposta"] != "multipla_escolha" and len(escolhas) != 1:
            raise ValueError("Esta votação permite apenas uma opção.")
        if len(escolhas) > max_marcacoes:
            raise ValueError(f"Selecione no máximo {max_marcacoes} opção(ões).")

        opcoes_validas = {int(o["id_opcao"]) for o in self.get_opcoes(id_votacao)}
        if not set(escolhas).issubset(opcoes_validas):
            raise ValueError("Opção de voto inválida.")

        peso = self.calcular_peso_usuario(user["id_usuario"], votacao["id_condominio"])
        id_voto = models.execute(
            "INSERT INTO voto (id_usuario, id_votacao, data_hora_voto, peso_aplicado, ip, navegador) VALUES (?, ?, ?, ?, ?, ?)",
            [user["id_usuario"], id_votacao, now_str(), peso, ip, navegador],
        )
        models.execute_many(
            "INSERT INTO voto_escolha (id_voto, id_opcao) VALUES (?, ?)",
            [[id_voto, id_opcao] for id_opcao in escolhas],
        )
        self.audit(user, "registrou voto", f"votacao:{id_votacao}", ip, navegador)
        return id_voto

    def _normalizar_escolhas(self, ids_opcoes: int | str | Iterable[int | str]) -> list[int]:
        if isinstance(ids_opcoes, (int, str)):
            valores = [ids_opcoes]
        else:
            valores = list(ids_opcoes or [])
        escolhas = []
        for valor in valores:
            if str(valor).strip():
                escolhas.append(int(valor))
        return escolhas

    def resultado_votacao(self, id_votacao: int) -> dict[str, Any]:
        self.auto_encerrar_se_expirada(id_votacao)
        votacao = self.get_votacao(id_votacao)
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
        totalizadores = models.query_one(
            "SELECT COUNT(*) AS total_votos, COALESCE(SUM(peso_aplicado), 0) AS total_peso FROM voto WHERE id_votacao = ?",
            [id_votacao],
        ) or {"total_votos": 0, "total_peso": 0}

        total_peso_computado = float(totalizadores["total_peso"] or 0)
        total_votos = int(totalizadores["total_votos"] or 0)
        total_peso_opcoes = sum(float(r["peso_acumulado"] or 0) for r in rows)

        opcoes = []
        for row in rows:
            peso = float(row["peso_acumulado"] or 0)
            percentual = (peso / total_peso_opcoes * 100) if total_peso_opcoes else 0
            opcoes.append(
                {
                    "descricao": row["descricao"],
                    "peso": peso,
                    "votos": int(row["total_votos"] or 0),
                    "percentual": percentual,
                }
            )

        return {
            "votacao": votacao,
            "opcoes": opcoes,
            "total_peso": total_peso_computado,
            "total_peso_opcoes": total_peso_opcoes,
            "total_votos": total_votos,
            "nominais": self._votos_nominais(votacao),
        }

    def _votos_nominais(self, votacao: dict[str, Any]) -> list[dict[str, Any]]:
        rows = models.query(
            """
            SELECT v.id_voto, u.nome_completo, l.identificacao, o.descricao AS voto,
                   v.peso_aplicado, v.data_hora_voto
            FROM voto v
            JOIN usuario u ON u.id_usuario = v.id_usuario
            JOIN voto_escolha ve ON ve.id_voto = v.id_voto
            JOIN opcao_voto o ON o.id_opcao = ve.id_opcao
            LEFT JOIN lote l ON l.id_usuario = u.id_usuario AND l.id_condominio = ?
            WHERE v.id_votacao = ?
            ORDER BY v.data_hora_voto, v.id_voto, o.ordem
            """,
            [votacao["id_condominio"], votacao["id_votacao"]],
        )
        agrupados: dict[int, dict[str, Any]] = {}
        for row in rows:
            id_voto = int(row["id_voto"])
            item = agrupados.setdefault(
                id_voto,
                {
                    "id_voto": id_voto,
                    "nome_completo": row["nome_completo"],
                    "imoveis_set": set(),
                    "votos_set": set(),
                    "peso_aplicado": row["peso_aplicado"],
                    "data_hora_voto": row["data_hora_voto"],
                },
            )
            if row.get("identificacao"):
                item["imoveis_set"].add(row["identificacao"])
            if row.get("voto"):
                item["votos_set"].add(row["voto"])

        nominais = []
        for item in agrupados.values():
            nominais.append(
                {
                    "id_voto": item["id_voto"],
                    "nome_completo": item["nome_completo"],
                    "imoveis": ", ".join(sorted(item["imoveis_set"])) or "-",
                    "voto": ", ".join(sorted(item["votos_set"])) or "-",
                    "peso_aplicado": item["peso_aplicado"],
                    "data_hora_voto": item["data_hora_voto"],
                }
            )
        return nominais

    def list_logs(self) -> list[dict[str, Any]]:
        return models.query(
            """
            SELECT l.*, u.nome_completo
            FROM log_auditoria l
            LEFT JOIN usuario u ON u.id_usuario = l.id_usuario
            ORDER BY l.id_log DESC
            LIMIT 100
            """
        )


service = VotingService()


def audit(user: dict[str, Any] | None, acao: str, entidade: str, ip: str = "", navegador: str = "") -> None:
    service.audit(user, acao, entidade, ip, navegador)


def list_reunioes() -> list[dict[str, Any]]:
    return service.list_reunioes()


def list_pautas_by_reuniao(id_reuniao: int) -> list[dict[str, Any]]:
    return service.list_pautas_by_reuniao(id_reuniao)


def list_votacoes() -> list[dict[str, Any]]:
    return service.list_votacoes()


def get_votacao(id_votacao: int) -> dict[str, Any] | None:
    return service.get_votacao(id_votacao)


def get_opcoes(id_votacao: int) -> list[dict[str, Any]]:
    return service.get_opcoes(id_votacao)


def create_votacao(data: dict[str, Any], user: dict[str, Any], ip: str, navegador: str) -> int:
    return service.create_votacao(data, user, ip, navegador)


def iniciar_votacao(id_votacao: int, user: dict[str, Any], ip: str, navegador: str) -> None:
    service.iniciar_votacao(id_votacao, user, ip, navegador)


def encerrar_votacao(id_votacao: int, user: dict[str, Any], ip: str, navegador: str) -> None:
    service.encerrar_votacao(id_votacao, user, ip, navegador)


def auto_encerrar_se_expirada(id_votacao: int) -> None:
    service.auto_encerrar_se_expirada(id_votacao)


def usuario_presente_na_reuniao(id_usuario: int, id_reuniao: int) -> bool:
    return service.usuario_presente_na_reuniao(id_usuario, id_reuniao)


def calcular_peso_usuario(id_usuario: int, id_condominio: int) -> float:
    return service.calcular_peso_usuario(id_usuario, id_condominio)


def usuario_ja_votou(id_usuario: int, id_votacao: int) -> bool:
    return service.usuario_ja_votou(id_usuario, id_votacao)


def registrar_voto(id_votacao: int, ids_opcoes: int | str | Iterable[int | str], user: dict[str, Any], ip: str, navegador: str) -> int:
    return service.registrar_voto(id_votacao, ids_opcoes, user, ip, navegador)


def resultado_votacao(id_votacao: int) -> dict[str, Any]:
    return service.resultado_votacao(id_votacao)


def list_logs() -> list[dict[str, Any]]:
    return service.list_logs()
