# Análise de Design — `gerenciador_original.py`

## 1. Violações de princípios SOLID

### SRP (Single Responsibility Principle)

A classe `GerenciadorEmprestimo` tem, no mínimo, **cinco razões para mudar**, todas misturadas nos mesmos métodos:

- Acesso a banco de dados (`conectar_banco`, comandos SQL espalhados por `realizar_emprestimo` e `calcular_multa`);
- Regra de negócio de empréstimo (verificar disponibilidade, decidir entre emprestar ou reservar);
- Regra de negócio de multa (calcular dias de atraso e valor);
- Envio de notificação por email (bloco `smtplib`/`MIMEText` repetido em dois métodos);
- Geração de comprovante em PDF (`reportlab.canvas`).

Isso viola diretamente o SRP: uma mudança no provedor de email, no layout do comprovante, no motor de banco de dados ou na regra de cálculo de multa obriga a alterar a **mesma classe**, aumentando o risco de introduzir bugs em partes não relacionadas à mudança.

### OCP (Open/Closed Principle)

A regra de multa está *hardcoded* dentro de `calcular_multa` (`multa = dias_atraso * 2.0`). Para criar uma nova política de multa (por exemplo, valor diferente por categoria de livro, teto máximo de multa, ou desconto para leitores frequentes) seria necessário **modificar o método existente**, em vez de estender o comportamento por meio de uma nova implementação. O mesmo vale para o canal de notificação: hoje só existe email; adicionar SMS exigiria editar os métodos já existentes.

### DIP (Dependency Inversion Principle)

`GerenciadorEmprestimo` depende diretamente de **implementações concretas**, não de abstrações:

- `sqlite3.connect(...)` chamado diretamente dentro da classe de regra de negócio;
- `smtplib.SMTP(...)` instanciado diretamente, inclusive com credenciais fixas no código (`'biblioteca@exemplo.com', 'senha'`);
- `reportlab.pdfgen.canvas.Canvas(...)` instanciado diretamente.

Isso torna a classe impossível de testar de forma isolada (não há como substituir o banco ou o serviço de email por um dublê/mock em teste unitário) e impossível de reconfigurar sem editar o código-fonte.

### LSP e ISP
O código original não usa herança nem interfaces — não há subclasses substituindo uma classe base, nem uma interface "gorda" forçando implementações desnecessárias. Por isso, **LSP (Liskov Substitution)** e **ISP (Interface Segregation)** não se aplicam a esta versão do código; a refatoração, ao introduzir `IRepositorio` e `INotificador`, é o momento em que esses princípios passam a valer — e ambos são respeitados: cada implementação concreta pode substituir sua abstração sem quebrar o comportamento esperado (LSP), e as interfaces são pequenas e focadas em uma única operação (ISP).

## 2. Problemas de coesão e acoplamento

**Coesão baixa:** os métodos da classe não giram em torno de um único propósito. `realizar_emprestimo` sozinho faz busca em três tabelas, grava em duas, envia email e gera PDF — são pelo menos quatro sub-responsabilidades dentro de um único método.

**Acoplamento problemático:**

- **Acoplamento forte com implementações concretas de infraestrutura** (SQLite, SMTP, ReportLab) em vez de abstrações — qualquer troca de tecnologia exige reescrever a lógica de negócio.
- **Acoplamento por índice posicional de tupla** (`livro[4]`, `leitor[2]`, `emprestimo[4]`): o código depende implicitamente da ordem exata das colunas nas tabelas SQL. Se alguém adicionar uma coluna no meio do schema, o código quebra silenciosamente, sem erro claro.
- **Acoplamento evolutivo/lógico com credenciais e configuração**: o servidor SMTP e a senha estão fixos no meio da lógica de negócio, misturando configuração de infraestrutura com regra de domínio.
- **`except: pass` genérico** em ambos os métodos: qualquer exceção (de rede, de credencial, de disco) é silenciada da mesma forma, dificultando diagnóstico e escondendo falhas reais do serviço de notificação/relatório.

## 3. Sugestões de refatoração

1. **Extrair repositórios** (`RepositorioLivro`, `RepositorioLeitor`, `RepositorioEmprestimo`, `RepositorioReserva`, `RepositorioMulta`), todos implementando uma interface comum `IRepositorio` — isola o acesso a dados (resolve SRP) e permite trocar a fonte de dados sem tocar na regra de negócio (resolve DIP).
2. **Extrair `ServicoNotificacao`**, dependendo de uma abstração `INotificador` (com `NotificadorEmail` como implementação concreta) — permite adicionar SMS ou push no futuro sem alterar quem usa o serviço (resolve OCP).
3. **Extrair `ServicoRelatorio`** para isolar a geração de comprovantes em PDF, desacoplando-a da regra de empréstimo.
4. **Extrair `CalculadoraMulta`**, dependendo de uma abstração `IEstrategiaMulta` — novas políticas de multa passam a ser novas classes, sem modificar a calculadora existente (resolve OCP).
5. **Injetar todas essas dependências no construtor de `GerenciadorEmprestimo`** (DIP), que passa a apenas orquestrar o fluxo de negócio delegando cada etapa ao colaborador correto.
6. **Eliminar acesso por índice posicional**, preferindo nomes de coluna (via `sqlite3.Row` ou mapeamento explícito para dicionários/objetos) para reduzir o acoplamento implícito com o schema.
7. **Substituir números mágicos por constantes nomeadas** (ex.: `PRAZO_EMPRESTIMO_DIAS = 14`), deixando a regra de negócio explícita e fácil de localizar.
8. **Tratar exceções de forma específica e logada**, em vez de `except: pass`, para não mascarar falhas reais dos serviços externos.
9. **Definir timeout na conexão SMTP**: o código original não define timeout ao conectar no servidor de email; em um ambiente sem acesso à rede (ex.: execução em sandbox/CI) isso pode travar a operação de empréstimo indefinidamente. Na refatoração, `NotificadorEmail` recebe um `timeout` configurável, garantindo que a regra de negócio principal nunca fique bloqueada por uma falha de notificação.

A implementação dessas sugestões está em [`src/emprestimo_refatorado.py`](src/emprestimo_refatorado.py).
