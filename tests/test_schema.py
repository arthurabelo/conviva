import unittest
import os
import tempfile
from pathlib import Path

from conviva_votacao import models, security, services
from seed import main as seed_main


class SchemaInitializationTests(unittest.TestCase):
    def test_schema_is_idempotent(self) -> None:
        schema_sql = Path("schema.sql").read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS condominio", schema_sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS usuario", schema_sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS sessao_usuario", schema_sql)
        self.assertNotIn("DROP TABLE", schema_sql.upper())


class VotingFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_ENGINE"] = "sqlite"
        os.environ.pop("DATABASE_URL", None)
        models.configure(sqlite_path=Path(self.tmp.name) / "test.sqlite3")
        seed_main()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_login_blocks_second_active_session(self) -> None:
        user = security.authenticate("admin@conviva.com", "senha123")
        self.assertIsNotNone(user)

        first_token = security.create_session(user["id_usuario"], "127.0.0.1", "test")
        with self.assertRaises(RuntimeError):
            security.create_session(user["id_usuario"], "127.0.0.2", "test")

        security.delete_session(first_token)
        second_token = security.create_session(user["id_usuario"], "127.0.0.3", "test")
        self.assertTrue(second_token)

    def test_multiple_choice_voting_uses_registered_weight(self) -> None:
        admin = models.query_one("SELECT * FROM usuario WHERE email = ?", ["admin@conviva.com"])
        diego = models.query_one("SELECT * FROM usuario WHERE email = ?", ["diego@email.com"])
        pauta = models.query_one("SELECT id_pauta FROM pauta ORDER BY id_pauta LIMIT 1")

        id_votacao = services.create_votacao(
            {
                "id_pauta": pauta["id_pauta"],
                "assunto": "Escolha de prioridades",
                "pergunta": "Quais prioridades devem entrar no plano?",
                "tipo_votacao": "aberta",
                "tipo_resposta": "multipla_escolha",
                "max_marcacoes": "2",
                "tempo_resposta": "5",
                "opcoes": "Segurança\nPiscina\nJardim",
            },
            admin,
            "127.0.0.1",
            "test",
        )
        services.iniciar_votacao(id_votacao, admin, "127.0.0.1", "test")
        opcoes = services.get_opcoes(id_votacao)
        services.registrar_voto(id_votacao, [opcoes[0]["id_opcao"], opcoes[1]["id_opcao"]], diego, "127.0.0.2", "test")

        result = services.resultado_votacao(id_votacao)
        self.assertEqual(result["total_votos"], 1)
        self.assertEqual(result["total_peso"], 1.0)
        self.assertEqual(result["total_peso_opcoes"], 2.0)


if __name__ == "__main__":
    unittest.main()
