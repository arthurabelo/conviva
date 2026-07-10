from __future__ import annotations

import unittest

from src import services, templates


class FakeAudit:
    def __init__(self):
        self.entries = []

    def registrar(self, user, action, entity, meta):
        self.entries.append((action, entity))


class FakeUsers:
    def __init__(self):
        self.users = {
            2: {"id_usuario": 2, "nome_completo": "Diego Lima", "email": "diego@email.com", "tipo_usuario": "proprietario", "ativo": 1}
        }
        self.lotes = []

    def by_id(self, user_id):
        return self.users.get(user_id)

    def list_active(self, nome="", tipo=""):
        return list(self.users.values())

    def email_in_use(self, email, except_id=None):
        return any(user["email"] == email and user_id != except_id for user_id, user in self.users.items())

    def create(self, nome, email, senha_hash, tipo):
        self.users[3] = {"id_usuario": 3, "nome_completo": nome, "email": email, "senha_hash": senha_hash, "tipo_usuario": tipo, "ativo": 1}
        return 3

    def update(self, *args, **kwargs):
        return None

    def default_condominio(self):
        return {"id_condominio": 1, "nome": "Condomínio Viver Bem"}

    def lots(self, user_id, condominio_id):
        return self.lotes

    def lot_in_use(self, *args):
        return False

    def save_lot(self, user_id, condominio_id, identificacao, peso, inadimplente, lot_id=None):
        self.lotes.append({"id_lote": 10, "id_usuario": user_id, "identificacao": identificacao, "peso_original": peso, "inadimplente": int(inadimplente)})
        return 10


class UserManagementTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeUsers()
        self.audit = FakeAudit()
        self.service = services.UserManagementService(self.repo, self.audit)
        self.admin = {"id_usuario": 1, "tipo_usuario": "administrador"}
        self.meta = services.RequestMeta()

    def test_rejects_duplicate_email_with_required_message(self):
        with self.assertRaisesRegex(ValueError, "E-mail inválido ou já cadastrado"):
            self.service.save(
                {"nome_completo": "Outro Diego", "email": "diego@email.com", "tipo_usuario": "proprietario", "senha": "senha123"},
                self.admin,
                self.meta,
            )

    def test_inadimplente_lot_has_zero_effective_weight(self):
        self.service.save_lot(
            2,
            {"identificacao": "Bloco C - Apto 104", "peso_original": "1,50", "inadimplente": "1"},
            self.admin,
            self.meta,
        )
        html = templates.lotes_table(2, self.repo.lotes)
        self.assertIn("Inadimplente (Dívida Ativa)", html)
        self.assertIn("Total efetivo: <strong data-total-effective>0.00", html)

    def test_rejects_non_positive_weight(self):
        with self.assertRaisesRegex(ValueError, "superior a 0.00"):
            self.service.save_lot(
                2,
                {"identificacao": "Bloco A - Apto 101", "peso_original": "0", "inadimplente": "0"},
                self.admin,
                self.meta,
            )


if __name__ == "__main__":
    unittest.main()
