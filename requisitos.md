# Engenharia de Requisitos — Sistema BiblioTech

## Contexto analisado

> "Precisamos de um sistema onde bibliotecários possam cadastrar livros no acervo (título, autor, ISBN, categoria, quantidade de exemplares). Os leitores devem se cadastrar informando nome, CPF, email e telefone. Quando um leitor quiser um livro, o bibliotecário registra o empréstimo (data de empréstimo e data prevista de devolução em 14 dias). Se todos os exemplares estiverem emprestados, o leitor pode fazer uma reserva. Quando o livro for devolvido, o primeiro leitor da fila de reservas é notificado por email. O sistema também deve permitir renovar empréstimos (desde que não haja reservas) e aplicar multas por atraso (R$ 2,00 por dia)."

## Requisitos Funcionais

| ID | Descrição | Prioridade |
|----|-----------|------------|
| RF01 | O sistema deve permitir que o bibliotecário cadastre livros no acervo, informando título, autor, ISBN, categoria e quantidade de exemplares. | Alta |
| RF02 | O sistema deve permitir que um leitor se cadastre informando nome, CPF, email e telefone. | Alta |
| RF03 | O sistema deve permitir que o bibliotecário registre o empréstimo de um exemplar disponível a um leitor cadastrado. | Alta |
| RF04 | O sistema deve calcular automaticamente a data prevista de devolução como 14 dias após a data do empréstimo. | Alta |
| RF05 | O sistema deve permitir que um leitor solicite reserva de um livro quando não houver exemplares disponíveis. | Alta |
| RF06 | O sistema deve manter uma fila de reservas por livro, respeitando a ordem de chegada (FIFO). | Média |
| RF07 | O sistema deve notificar por email o primeiro leitor da fila de reservas assim que um exemplar do livro for devolvido. | Alta |
| RF08 | O sistema deve permitir a renovação de um empréstimo, desde que não existam reservas pendentes para o livro. | Média |
| RF09 | O sistema deve calcular e registrar multa por atraso na devolução, no valor de R$ 2,00 por dia de atraso. | Alta |
| RF10 | O sistema deve permitir o registro da devolução de um exemplar emprestado. | Alta |
| RF11 | O sistema deve permitir consultar a quantidade de exemplares disponíveis de um livro. | Média |
| RF12 | O sistema deve permitir consultar o histórico de empréstimos de um leitor. | Baixa |

## Requisitos Não-Funcionais

| ID | Categoria | Descrição | Métrica |
|----|-----------|-----------|---------|
| RNF01 | Desempenho | Consultas de disponibilidade de acervo devem responder rapidamente mesmo com muitos acessos simultâneos. | Tempo de resposta ≤ 2s para 95% das requisições. |
| RNF02 | Segurança | Dados pessoais dos leitores (CPF, email, telefone) devem ser protegidos contra acesso não autorizado. | 100% dos campos sensíveis armazenados de forma criptografada em repouso. |
| RNF03 | Usabilidade | O fluxo de registro de empréstimo deve ser simples o suficiente para um bibliotecário sem treinamento prévio. | Registro de empréstimo em no máximo 3 passos/telas. |
| RNF04 | Disponibilidade | O sistema deve estar acessível durante o horário de funcionamento das bibliotecas atendidas. | Disponibilidade ≥ 99% no horário de funcionamento. |
| RNF05 | Escalabilidade | O sistema deve suportar o crescimento do acervo e da base de leitores sem perda perceptível de desempenho. | Suporte a pelo menos 10.000 livros e 5.000 leitores cadastrados. |
| RNF06 | Confiabilidade | Falhas em serviços externos (envio de email, geração de comprovante) não podem impedir a conclusão da operação principal (empréstimo). | 100% das operações de empréstimo concluídas mesmo com falha do serviço de notificação. |

## Regras de Negócio

| ID | Descrição |
|----|-----------|
| RN01 | O prazo padrão de um empréstimo é de 14 dias corridos a partir da data do empréstimo. |
| RN02 | A multa por atraso é de R$ 2,00 por dia corrido de atraso na devolução. |
| RN03 | Um leitor só pode reservar um livro quando não houver exemplares disponíveis no momento da solicitação. |
| RN04 | A renovação de um empréstimo só é permitida se não houver nenhuma reserva pendente para o livro. |
| RN05 | Quando um exemplar é devolvido e existe fila de reservas, apenas o primeiro leitor da fila (ordem de chegada) é notificado. |
| RN06 | Um exemplar físico só pode estar emprestado a um único leitor por vez. |

## User Stories (formato INVEST)

### US01 — Cadastro de livros

```
Como bibliotecário
Quero cadastrar livros no acervo com título, autor, ISBN, categoria e quantidade de exemplares
Para manter o catálogo da biblioteca sempre atualizado e disponível para consulta e empréstimo

Critérios de Aceitação:
- [ ] Todos os campos (título, autor, ISBN, categoria, quantidade de exemplares) são obrigatórios
- [ ] O sistema rejeita o cadastro de um ISBN já existente
- [ ] Após o cadastro, o livro aparece imediatamente disponível para empréstimo

Story Points: 3
```

### US02 — Cadastro de leitores

```
Como visitante da biblioteca
Quero me cadastrar como leitor informando nome, CPF, email e telefone
Para poder solicitar empréstimos e reservas de livros

Critérios de Aceitação:
- [ ] Nome, CPF, email e telefone são obrigatórios
- [ ] O sistema não permite CPF duplicado
- [ ] O leitor recebe confirmação de que o cadastro foi concluído com sucesso

Story Points: 2
```

### US03 — Registro de empréstimo

```
Como bibliotecário
Quero registrar o empréstimo de um livro a um leitor cadastrado
Para controlar quais exemplares estão emprestados e quando devem ser devolvidos

Critérios de Aceitação:
- [ ] O sistema verifica se o livro e o leitor existem antes de registrar o empréstimo
- [ ] Se houver exemplar disponível, o sistema registra data de empréstimo e data de devolução prevista (+14 dias)
- [ ] Se não houver exemplar disponível, o sistema informa o bibliotecário e oferece a opção de reserva

Story Points: 5
```

### US04 — Reserva de livro indisponível

```
Como leitor
Quero reservar um livro que está com todos os exemplares emprestados
Para ser atendido assim que um exemplar for devolvido

Critérios de Aceitação:
- [ ] A reserva só é aceita quando não há exemplares disponíveis
- [ ] O leitor entra em uma fila de reservas ordenada pela data da solicitação
- [ ] O leitor recebe uma confirmação de que a reserva foi registrada

Story Points: 3
```

### US05 — Renovação de empréstimo

```
Como bibliotecário
Quero renovar o prazo de um empréstimo em andamento
Para dar mais tempo ao leitor quando não há outro leitor esperando pelo livro

Critérios de Aceitação:
- [ ] A renovação é bloqueada se existir reserva pendente para o livro
- [ ] Ao renovar, a nova data de devolução é recalculada em +14 dias a partir da renovação
- [ ] O leitor é informado da nova data de devolução

Story Points: 3
```

### US06 — Notificação de reserva disponível

```
Como leitor com uma reserva ativa
Quero ser notificado por email quando o livro reservado for devolvido
Para poder retirá-lo o quanto antes na biblioteca

Critérios de Aceitação:
- [ ] A notificação é enviada automaticamente ao primeiro leitor da fila assim que o exemplar é devolvido
- [ ] A reserva atendida é removida da fila após a notificação
- [ ] Caso o envio do email falhe, a devolução do livro não é impedida

Story Points: 2
```
