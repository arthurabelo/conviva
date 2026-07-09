from __future__ import annotations

from src import models
from src.security import PasswordHasher


def main() -> None:
    db = models.Database()
    db.reset_db()
    hasher = PasswordHasher()
    senha = hasher.hash("senha123")

    id_condominio = db.execute(
        "INSERT INTO condominio (nome, cnpj, endereco, status) VALUES (?, ?, ?, ?)",
        [
            "Condominio Viver Bem",
            "51.826.615/0001-52",
            "Av. Nossa Senhora de Fatima, 1234, Teresina - PI",
            "ativo",
        ],
    )
    id_admin = db.execute(
        """
        INSERT INTO usuario (nome_completo, email, senha_hash, tipo_usuario, ativo)
        VALUES (?, ?, ?, ?, 1)
        """,
        ["Arthur Rabelo de Carvalho", "admin@conviva.com", senha, "administrador"],
    )
    id_diego = db.execute(
        """
        INSERT INTO usuario (nome_completo, email, senha_hash, tipo_usuario, ativo)
        VALUES (?, ?, ?, ?, 1)
        """,
        ["Diego Vinicios Mascarenha Lima", "diego@email.com", senha, "proprietario"],
    )
    id_gabriel = db.execute(
        """
        INSERT INTO usuario (nome_completo, email, senha_hash, tipo_usuario, ativo)
        VALUES (?, ?, ?, ?, 1)
        """,
        ["Gabriel Custodio Andrade Lira", "gabriel@email.com", senha, "proprietario"],
    )
    id_marina = db.execute(
        """
        INSERT INTO usuario (nome_completo, email, senha_hash, tipo_usuario, ativo)
        VALUES (?, ?, ?, ?, 1)
        """,
        ["Marina Sousa Almeida", "marina@email.com", senha, "proprietario"],
    )
    id_procuradora = db.execute(
        """
        INSERT INTO usuario (nome_completo, email, senha_hash, tipo_usuario, ativo)
        VALUES (?, ?, ?, ?, 1)
        """,
        ["Patricia Nunes Pereira", "patricia@email.com", senha, "procurador"],
    )
    db.execute(
        """
        INSERT INTO usuario (nome_completo, email, senha_hash, tipo_usuario, ativo)
        VALUES (?, ?, ?, ?, 1)
        """,
        ["Visitante Externo", "visitante@email.com", senha, "proprietario"],
    )

    lotes = [
        [id_condominio, id_diego, "Bloco A - Apto 302", 1.0, 0],
        [id_condominio, id_diego, "Bloco C - Apto 104", 1.5, 1],
        [id_condominio, id_gabriel, "Bloco B - Apto 201", 2.0, 0],
        [id_condominio, id_marina, "Bloco D - Apto 401", 1.0, 1],
    ]
    db.execute_many(
        """
        INSERT INTO lote (id_condominio, id_usuario, identificacao, peso_original, inadimplente)
        VALUES (?, ?, ?, ?, ?)
        """,
        lotes,
    )

    id_reuniao = db.execute(
        """
        INSERT INTO reuniao
            (id_condominio, titulo, data, hora, assunto, url_video, status, iniciou_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        [
            id_condominio,
            "Assembleia Geral Ordinaria",
            "2026-07-09",
            "14:30",
            "Prestacao de contas e deliberacoes do semestre",
            "https://meet.google.com/demo-conviva",
            "em_andamento",
        ],
    )

    id_pauta_contas = db.execute(
        "INSERT INTO pauta (id_reuniao, assunto, descricao) VALUES (?, ?, ?)",
        [
            id_reuniao,
            "Prestacao de contas",
            "Apresentacao das despesas e receitas do semestre.",
        ],
    )
    id_pauta_playground = db.execute(
        "INSERT INTO pauta (id_reuniao, assunto, descricao) VALUES (?, ?, ?)",
        [
            id_reuniao,
            "Reforma do playground",
            "Avaliacao de orcamento para reforma da area infantil.",
        ],
    )
    db.execute(
        "INSERT INTO anexo_pauta (id_pauta, nome_arquivo, url_arquivo) VALUES (?, ?, ?)",
        [id_pauta_contas, "Prestacao_de_contas_Junho_2026.pdf", "#"],
    )
    db.execute(
        "INSERT INTO anexo_pauta (id_pauta, nome_arquivo, url_arquivo) VALUES (?, ?, ?)",
        [id_pauta_playground, "Orcamento_playground.pdf", "#"],
    )

    for id_usuario in [id_admin, id_diego, id_gabriel, id_marina, id_procuradora]:
        db.execute(
            """
            INSERT INTO convidado_reuniao
                (id_usuario, id_reuniao, status_convite, status_presenca)
            VALUES (?, ?, 'confirmado', 0)
            """,
            [id_usuario, id_reuniao],
        )

    db.execute(
        """
        INSERT INTO procuracao
            (id_reuniao, id_proprietario, id_procurador, documento, ativa)
        VALUES (?, ?, ?, ?, 1)
        """,
        [id_reuniao, id_marina, id_procuradora, "procuracao_marina_patricia.pdf"],
    )

    id_votacao = db.execute(
        """
        INSERT INTO votacao
            (id_pauta, assunto, pergunta, tipo_votacao, tipo_resposta,
             tempo_resposta, max_marcacoes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'agendada')
        """,
        [
            id_pauta_contas,
            "Aprovacao das contas de 2025",
            "Voces aprovam o balanco financeiro apresentado?",
            "aberta",
            "escolha_unica",
            2,
            1,
        ],
    )
    db.execute_many(
        "INSERT INTO opcao_voto (id_votacao, descricao, ordem) VALUES (?, ?, ?)",
        [
            [id_votacao, "Aprovar", 1],
            [id_votacao, "Rejeitar", 2],
            [id_votacao, "Nao sei / nao quero responder", 3],
        ],
    )
    print("Banco criado em data/conviva.sqlite3")
    print("Usuarios de teste: admin@conviva.com, diego@email.com, gabriel@email.com, marina@email.com")
    print("Senha para todos: senha123")


if __name__ == "__main__":
    main()
