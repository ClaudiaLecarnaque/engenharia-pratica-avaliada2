# Modelagem UML — Sistema BiblioTech

## a) Diagrama de Classes

```mermaid
classDiagram
    class Livro {
        -String isbn
        -String titulo
        -String autor
        -String categoria
        +cadastrar()
        +consultarDisponibilidade() int
    }

    class Exemplar {
        -int numero
        -String status
        +emprestar()
        +devolver()
    }

    class Leitor {
        -String cpf
        -String nome
        -String email
        -String telefone
        +cadastrar()
        +consultarHistorico() List
    }

    class Bibliotecario {
        -String matricula
        -String nome
        +registrarEmprestimo(livro, leitor)
        +registrarDevolucao(emprestimo)
    }

    class Emprestimo {
        -Date dataEmprestimo
        -Date dataDevolucaoPrevista
        -Date dataDevolucao
        +calcularDiasAtraso() int
        +renovar()
    }

    class Reserva {
        -Date dataReserva
        -int posicaoFila
        +notificarLeitor()
        +cancelar()
    }

    class Multa {
        -float valor
        -boolean paga
        +calcularValor() float
        +registrarPagamento()
    }

    Livro "1" --> "1..*" Exemplar : possui
    Bibliotecario "1" --> "0..*" Emprestimo : registra
    Leitor "1" --> "0..*" Emprestimo : realiza
    Exemplar "1" --> "0..*" Emprestimo : é alvo de
    Leitor "1" --> "0..*" Reserva : solicita
    Livro "1" --> "0..*" Reserva : recebe
    Emprestimo "1" --> "0..1" Multa : gera
```

**Notas de modelagem:**
- `Livro` e `Exemplar` são separados porque um mesmo título pode ter vários exemplares físicos, cada um com seu próprio status (disponível/emprestado).
- `Emprestimo` está associado a um `Exemplar` específico (não apenas ao `Livro`), pois é o exemplar físico que efetivamente é emprestado.
- A multiplicidade `0..1` entre `Emprestimo` e `Multa` reflete que nem todo empréstimo gera multa (só os devolvidos com atraso).

---

## b) Diagrama de Sequência — "Realizar empréstimo de um livro"

```mermaid
sequenceDiagram
    actor Bibliotecario
    participant Sistema
    participant Livro
    participant Leitor
    participant Emprestimo

    Bibliotecario->>Sistema: registrarEmprestimo(isbn, cpf)
    activate Sistema

    Sistema->>Livro: buscar(isbn)
    activate Livro
    Livro-->>Sistema: dadosLivro
    deactivate Livro

    Sistema->>Leitor: buscar(cpf)
    activate Leitor
    Leitor-->>Sistema: dadosLeitor
    deactivate Leitor

    Sistema->>Livro: consultarExemplaresDisponiveis()
    activate Livro
    Livro-->>Sistema: quantidadeDisponivel
    deactivate Livro

    alt quantidadeDisponivel > 0
        Sistema->>Emprestimo: criar(livro, leitor, hoje, hoje+14dias)
        activate Emprestimo
        Emprestimo-->>Sistema: emprestimoRegistrado
        deactivate Emprestimo

        Sistema->>Livro: decrementarExemplarDisponivel()
        activate Livro
        Livro-->>Sistema: ok
        deactivate Livro

        Sistema-->>Bibliotecario: "Empréstimo realizado com sucesso"
    else quantidadeDisponivel == 0
        Sistema-->>Bibliotecario: "Livro indisponível. Reserva criada."
    end

    deactivate Sistema
```

---

## c) Diagrama de Atividades — "Devolver livro e processar reservas"

```mermaid
flowchart TD
    Start([Início: livro devolvido]) --> RegDev[Registrar devolução do exemplar]
    RegDev --> CalcAtraso{Devolução após a data prevista?}

    CalcAtraso -- Sim --> CalcMulta[Calcular multa por dia de atraso]
    CalcMulta --> RegMulta[Registrar multa no sistema]
    RegMulta --> IncExemplar[Incrementar exemplares disponíveis]

    CalcAtraso -- Não --> IncExemplar

    IncExemplar --> VerifReserva{Existe reserva pendente para o livro?}

    VerifReserva -- Sim --> SelecLeitor[Selecionar primeiro leitor da fila de reservas]
    SelecLeitor --> Notificar[Notificar leitor por email]
    Notificar --> RemoverReserva[Remover reserva da fila]
    RemoverReserva --> FimComNotif([Fim: com notificação de reserva])

    VerifReserva -- Não --> FimSemNotif([Fim: sem notificação de reserva])
```

**Leitura do fluxo:** o caminho `CalcAtraso` cobre os dois estados finais em relação à multa (com/sem multa), e o caminho `VerifReserva` cobre os dois estados finais em relação à notificação (com/sem notificação) — as quatro combinações possíveis (com multa + com notificação, com multa + sem notificação, sem multa + com notificação, sem multa + sem notificação) são alcançáveis combinando os dois desvios.
