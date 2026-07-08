# Guia para apresentação do módulo de votação

## Ideia principal

O CONVIVA é um sistema web para assembleias de condomínio. Nesta entrega foi implementado o recorte pedido na atividade:

- entrar no sistema;
- criar votação;
- executar votação;
- verificar o resultado.

A votação foi organizada no mesmo fluxo de uma enquete de reunião, como o Polls do Microsoft Teams: o administrador deixa as votações cadastradas antes da reunião e só inicia cada uma quando chegar a pauta correspondente.

## Como explicar a arquitetura

A arquitetura escolhida foi MVC Web em Python, em formato de monólito modular.

Fale assim:

> Escolhemos MVC porque a atividade pede um sistema web simples, com fluxo claro e fácil de demonstrar. O projeto separa interface, controle, regras de negócio e banco de dados. Isso evita misturar HTML, validação e persistência no mesmo lugar.

Mapeamento:

- `app.py`: recebe as requisições e chama o controller correto.
- `controllers.py`: decide o que fazer com cada tela e formulário.
- `services.py`: concentra as regras de votação, presença, peso e resultado.
- `models.py`: conversa com o banco de dados.
- `templates.py`: gera as telas HTML.
- `security.py`: autenticação, senha e sessão.
- `schema.sql`: estrutura real das tabelas.

## Por que não usar uma arquitetura mais complexa

Microsserviços, filas e uma SPA completa seriam exagero para o escopo da atividade. Eles fariam sentido em um produto grande, mas aumentariam o risco de configuração e explicação.

Para esta entrega, o monólito modular é suficiente porque:

- o escopo é pequeno;
- o grupo entende Python;
- a regra principal é votação, não distribuição de serviços;
- a demonstração precisa funcionar de forma previsível.

## Banco de dados

O sistema precisa de banco relacional, porque existem dados com relacionamento forte:

- usuário;
- condomínio;
- lote;
- reunião;
- pauta;
- votação;
- opção de voto;
- voto;
- auditoria;
- sessão ativa.

PostgreSQL não é obrigatório para a apresentação. O projeto roda localmente com SQLite, que já vem com Python e reduz problemas de instalação. PostgreSQL continua disponível via `DATABASE_URL` e Docker para um cenário mais próximo de produção.

Forma simples de explicar:

> Para o protótipo, SQLite basta. Para o produto real, PostgreSQL é melhor por concorrência, integridade e operação com muitos usuários simultâneos.

## Requisitos atendidos

Entrar no sistema:

- login por e-mail e senha;
- senha com hash;
- cookie de sessão;
- bloqueio de sessão simultânea da mesma conta;
- log de auditoria.

Criar votação:

- administrador cria votação vinculada a pauta e reunião;
- define assunto, pergunta, tempo, tipo aberto/fechado e opções;
- votação nasce com status `agendada`.

Executar votação:

- administrador inicia a votação;
- status muda para `ativa`;
- sistema calcula horário final;
- participante presente vê a enquete ativa;
- participante vota uma vez;
- sistema aplica o peso conforme lotes adimplentes.

Verificar resultado:

- resultado só aparece depois do encerramento;
- cálculo usa peso de voto, não apenas quantidade de pessoas;
- votação aberta mostra relatório nominal;
- votação fechada mostra apenas consolidado;
- tudo fica registrado na auditoria.

## Demonstração sugerida

1. Rodar `python app.py`.
2. Abrir `http://localhost:8000`.
3. Entrar como administrador:
   - e-mail: `admin@conviva.com`
   - senha: `senha123`
4. Abrir **Votações**.
5. Criar uma nova votação.
6. Mostrar que ela fica como `agendada`.
7. Clicar em **Iniciar**.
8. Mostrar que a votação fica `ativa`.
9. Sair e entrar como `diego@email.com`, senha `senha123`.
10. Votar.
11. Sair e entrar como `gabriel@email.com`, senha `senha123`.
12. Votar.
13. Voltar como administrador.
14. Encerrar a votação.
15. Abrir o resultado.
16. Mostrar percentuais, peso computado e relatório nominal se a votação for aberta.
17. Abrir **Auditoria** e mostrar os registros.

## Frase curta para defender a solução

> A implementação foca no núcleo do módulo de votação: o administrador prepara as votações antes da assembleia, inicia cada enquete durante a reunião, os participantes presentes votam uma única vez, e o resultado é liberado apenas ao final, respeitando votação aberta ou fechada e cálculo por peso.

## Limitações assumidas

Não foram implementados nesta entrega:

- videoconferência real;
- upload real de anexos;
- exportação PDF;
- envio de e-mail;
- ata automática;
- chat;
- moderação real de câmera e microfone.

Esses itens aparecem no documento de requisitos, mas estão fora do recorte mínimo pedido pela atividade.
