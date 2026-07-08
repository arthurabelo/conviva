import time

from conviva_votacao import models
from conviva_votacao.security import hash_password
from conviva_votacao.services import now_str


def wait_for_db(retries: int = 30, delay: int = 2) -> None:
    for attempt in range(1, retries + 1):
        try:
            models.ping()
            return
        except Exception as exc:
            if attempt == retries:
                raise RuntimeError("Não foi possível conectar ao banco de dados") from exc
            print(f"Aguardando banco de dados ({attempt}/{retries})...")
            time.sleep(delay)


def main() -> None:
    wait_for_db()
    models.init_db()
    models.execute("UPDATE sessao_usuario SET encerrada_em = ? WHERE encerrada_em IS NULL", [now_str()])
    if models.query_one("SELECT 1 FROM usuario WHERE email = ?", ("admin@conviva.com",)):
        print("Dados iniciais já existem. Pulando seed.")
        return

    senha = hash_password("senha123")

    id_cond = models.execute(
        "INSERT INTO condominio (nome, cnpj, endereco, status) VALUES (?, ?, ?, ?)",
        ["Condomínio Viver Bem", "51.826.615/0001-52", "Av. Nossa Senhora de Fátima, 1234, Teresina - PI", "ativo"],
    )
    id_admin = models.execute(
        "INSERT INTO usuario (nome_completo, email, senha_hash, tipo_usuario, ativo) VALUES (?, ?, ?, ?, 1)",
        ["Arthur Rabelo de Carvalho", "admin@conviva.com", senha, "administrador"],
    )
    id_diego = models.execute(
        "INSERT INTO usuario (nome_completo, email, senha_hash, tipo_usuario, ativo) VALUES (?, ?, ?, ?, 1)",
        ["Diego Vinícios Mascarenha Lima", "diego@email.com", senha, "proprietario"],
    )
    id_gabriel = models.execute(
        "INSERT INTO usuario (nome_completo, email, senha_hash, tipo_usuario, ativo) VALUES (?, ?, ?, ?, 1)",
        ["Gabriel Custodio Andrade Lira", "gabriel@email.com", senha, "proprietario"],
    )
    models.execute(
        "INSERT INTO lote (id_condominio, id_usuario, identificacao, peso_original, inadimplente) VALUES (?, ?, ?, ?, ?)",
        [id_cond, id_diego, "Bloco A - Apto 302", 1.0, 0],
    )
    models.execute(
        "INSERT INTO lote (id_condominio, id_usuario, identificacao, peso_original, inadimplente) VALUES (?, ?, ?, ?, ?)",
        [id_cond, id_diego, "Bloco C - Apto 104", 1.5, 1],
    )
    models.execute(
        "INSERT INTO lote (id_condominio, id_usuario, identificacao, peso_original, inadimplente) VALUES (?, ?, ?, ?, ?)",
        [id_cond, id_gabriel, "Bloco B - Apto 201", 2.0, 0],
    )
    id_reuniao = models.execute(
        "INSERT INTO reuniao (id_condominio, titulo, data, hora, status) VALUES (?, ?, ?, ?, ?)",
        [id_cond, "Assembleia Geral Ordinária", "2026-07-09", "14:30", "em_andamento"],
    )
    models.execute(
        "INSERT INTO pauta (id_reuniao, assunto, descricao) VALUES (?, ?, ?)",
        [id_reuniao, "Prestação de contas", "Apresentação das despesas e receitas do semestre"],
    )
    models.execute(
        "INSERT INTO pauta (id_reuniao, assunto, descricao) VALUES (?, ?, ?)",
        [id_reuniao, "Reforma do playground", "Apresentação das despesas para reforma do playground"],
    )
    for user_id in [id_admin, id_diego, id_gabriel]:
        models.execute(
            "INSERT INTO convidado_reuniao (id_usuario, id_reuniao, status_convite, status_presenca, data_hora_entrada) VALUES (?, ?, 'confirmado', 1, datetime('now'))",
            [user_id, id_reuniao],
        )
    print("Banco criado com dados iniciais.")


if __name__ == "__main__":
    main()
