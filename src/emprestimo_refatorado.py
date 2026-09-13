"""
Versão refatorada do gerenciamento de empréstimos da biblioteca.

Aplica:
- SRP  (Single Responsibility Principle): cada classe tem uma única razão
  para mudar (persistência, notificação, relatório, cálculo de multa e
  orquestração são responsabilidades separadas).
- OCP  (Open/Closed Principle): novas políticas de multa e novos canais de
  notificação podem ser adicionados criando novas classes, sem modificar
  as classes existentes.
- DIP  (Dependency Inversion Principle): `GerenciadorEmprestimo` depende
  apenas de abstrações (recebidas por injeção no construtor), nunca de
  implementações concretas de banco de dados, email ou geração de PDF.

Mantém o mesmo comportamento observável de `gerenciador_original.py`
(mesmas mensagens de retorno e mesmos efeitos no banco de dados).
"""

import sqlite3
import smtplib
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from reportlab.pdfgen import canvas


# =====================================================================
# Camada de persistência (Repositórios) — SRP + DIP
# =====================================================================

class IRepositorio(ABC):
    """Interface para operações de persistência (contrato comum a todo repositório)."""

    @abstractmethod
    def buscar(self, id):
        """Busca uma entidade pelo seu identificador."""
        raise NotImplementedError

    @abstractmethod
    def salvar(self, entidade):
        """Persiste (insere/atualiza) uma entidade."""
        raise NotImplementedError


class RepositorioLivro(IRepositorio):
    """Responsável apenas por operações com livros no banco de dados."""

    def __init__(self, db_path='biblioteca.db'):
        self.db_path = db_path

    def _conectar(self):
        return sqlite3.connect(self.db_path)

    def buscar(self, isbn):
        conn = self._conectar()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM livros WHERE isbn = ?", (isbn,))
            return cursor.fetchone()
        finally:
            conn.close()

    def salvar(self, livro):
        """Atualiza os dados de um livro já existente (dict com as colunas da tabela)."""
        conn = self._conectar()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE livros
                   SET titulo = ?, autor = ?, categoria = ?, exemplares_disponiveis = ?
                   WHERE isbn = ?""",
                (livro['titulo'], livro['autor'], livro.get('categoria'),
                 livro['exemplares_disponiveis'], livro['isbn']),
            )
            conn.commit()
        finally:
            conn.close()

    def decrementar_exemplar(self, isbn):
        """Reduz em 1 a quantidade de exemplares disponíveis (empréstimo)."""
        conn = self._conectar()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE livros SET exemplares_disponiveis = exemplares_disponiveis - 1 WHERE isbn = ?",
                (isbn,),
            )
            conn.commit()
        finally:
            conn.close()

    def incrementar_exemplar(self, isbn):
        """Aumenta em 1 a quantidade de exemplares disponíveis (devolução)."""
        conn = self._conectar()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE livros SET exemplares_disponiveis = exemplares_disponiveis + 1 WHERE isbn = ?",
                (isbn,),
            )
            conn.commit()
        finally:
            conn.close()


class RepositorioLeitor(IRepositorio):
    """Responsável apenas por operações com leitores no banco de dados."""

    def __init__(self, db_path='biblioteca.db'):
        self.db_path = db_path

    def _conectar(self):
        return sqlite3.connect(self.db_path)

    def buscar(self, cpf):
        conn = self._conectar()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leitores WHERE cpf = ?", (cpf,))
            return cursor.fetchone()
        finally:
            conn.close()

    def salvar(self, leitor):
        conn = self._conectar()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE leitores SET nome = ?, email = ?, telefone = ? WHERE cpf = ?",
                (leitor['nome'], leitor['email'], leitor.get('telefone'), leitor['cpf']),
            )
            conn.commit()
        finally:
            conn.close()


class RepositorioEmprestimo(IRepositorio):
    """Responsável apenas por operações com empréstimos no banco de dados."""

    def __init__(self, db_path='biblioteca.db'):
        self.db_path = db_path

    def _conectar(self):
        return sqlite3.connect(self.db_path)

    def buscar(self, id):
        conn = self._conectar()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM emprestimos WHERE id = ?", (id,))
            return cursor.fetchone()
        finally:
            conn.close()

    def salvar(self, emprestimo):
        """Cria um novo registro de empréstimo e retorna o id gerado."""
        conn = self._conectar()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO emprestimos
                       (livro_isbn, leitor_cpf, data_emprestimo, data_devolucao_prevista)
                   VALUES (?, ?, ?, ?)""",
                (emprestimo['livro_isbn'], emprestimo['leitor_cpf'],
                 emprestimo['data_emprestimo'], emprestimo['data_devolucao_prevista']),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def registrar_devolucao(self, emprestimo_id, data_devolucao):
        conn = self._conectar()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE emprestimos SET data_devolucao = ? WHERE id = ?",
                (data_devolucao, emprestimo_id),
            )
            conn.commit()
        finally:
            conn.close()


class RepositorioReserva(IRepositorio):
    """Responsável apenas por operações com reservas no banco de dados."""

    def __init__(self, db_path='biblioteca.db'):
        self.db_path = db_path

    def _conectar(self):
        return sqlite3.connect(self.db_path)

    def buscar(self, id):
        conn = self._conectar()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reservas WHERE id = ?", (id,))
            return cursor.fetchone()
        finally:
            conn.close()

    def salvar(self, reserva):
        conn = self._conectar()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO reservas (livro_isbn, leitor_cpf, data_reserva) VALUES (?, ?, ?)",
                (reserva['livro_isbn'], reserva['leitor_cpf'], reserva['data_reserva']),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def buscar_por_livro(self, livro_isbn):
        """Retorna a fila de reservas de um livro, em ordem de chegada (FIFO)."""
        conn = self._conectar()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM reservas WHERE livro_isbn = ? ORDER BY data_reserva ASC, id ASC",
                (livro_isbn,),
            )
            return cursor.fetchall()
        finally:
            conn.close()

    def remover(self, reserva_id):
        conn = self._conectar()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM reservas WHERE id = ?", (reserva_id,))
            conn.commit()
        finally:
            conn.close()


class RepositorioMulta(IRepositorio):
    """Responsável apenas por operações com multas no banco de dados."""

    def __init__(self, db_path='biblioteca.db'):
        self.db_path = db_path

    def _conectar(self):
        return sqlite3.connect(self.db_path)

    def buscar(self, id):
        conn = self._conectar()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM multas WHERE id = ?", (id,))
            return cursor.fetchone()
        finally:
            conn.close()

    def salvar(self, multa):
        conn = self._conectar()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO multas (emprestimo_id, valor) VALUES (?, ?)",
                (multa['emprestimo_id'], multa['valor']),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()


# =====================================================================
# Serviços de apoio — SRP + OCP (canal de notificação é extensível)
# =====================================================================

class INotificador(ABC):
    """Abstração para o canal de envio de notificações."""

    @abstractmethod
    def notificar(self, destinatario, assunto, mensagem):
        raise NotImplementedError


class NotificadorEmail(INotificador):
    """Implementação concreta de notificação via email (SMTP)."""

    def __init__(self, host='smtp.gmail.com', porta=587,
                 usuario='biblioteca@exemplo.com', senha='senha', timeout=5):
        self.host = host
        self.porta = porta
        self.usuario = usuario
        self.senha = senha
        self.timeout = timeout

    def notificar(self, destinatario, assunto, mensagem):
        try:
            msg = MIMEText(mensagem)
            msg['Subject'] = assunto
            msg['To'] = destinatario

            # timeout evita que uma falha de rede trave a operação principal
            server = smtplib.SMTP(self.host, self.porta, timeout=self.timeout)
            server.starttls()
            server.login(self.usuario, self.senha)
            server.send_message(msg)
            server.quit()
            return True
        except Exception:
            # Falha no envio não pode interromper a regra de negócio principal.
            return False


class ServicoNotificacao:
    """Responsável apenas por orquestrar as notificações enviadas aos leitores."""

    def __init__(self, notificador: INotificador = None):
        self.notificador = notificador or NotificadorEmail()

    def notificar_emprestimo(self, leitor_email, titulo_livro):
        self.notificador.notificar(
            leitor_email, 'Empréstimo Realizado',
            f'Empréstimo realizado: {titulo_livro}',
        )

    def notificar_multa(self, leitor_email, valor_multa):
        self.notificador.notificar(
            leitor_email, 'Multa por Atraso',
            f'Multa de R$ {valor_multa:.2f} aplicada',
        )

    def notificar_reserva_disponivel(self, leitor_email, titulo_livro):
        self.notificador.notificar(
            leitor_email, 'Livro Disponível',
            f'O livro "{titulo_livro}" reservado por você já está disponível.',
        )


class ServicoRelatorio:
    """Responsável apenas por gerar comprovantes (PDF)."""

    def gerar_comprovante_emprestimo(self, emprestimo_id, titulo_livro, nome_leitor, data_devolucao):
        try:
            c = canvas.Canvas(f'comprovante_{emprestimo_id}.pdf')
            c.drawString(100, 750, f'Empréstimo #{emprestimo_id}')
            c.drawString(100, 730, f'Livro: {titulo_livro}')
            c.drawString(100, 710, f'Leitor: {nome_leitor}')
            c.drawString(100, 690, f'Devolução: {data_devolucao}')
            c.save()
            return True
        except Exception:
            return False


# =====================================================================
# Cálculo de multa — OCP (novas políticas sem alterar código existente)
# =====================================================================

class IEstrategiaMulta(ABC):
    """Abstração para uma política de cálculo de multa."""

    @abstractmethod
    def calcular(self, dias_atraso: int) -> float:
        raise NotImplementedError


class EstrategiaMultaPorDia(IEstrategiaMulta):
    """Política padrão: valor fixo multiplicado pelos dias de atraso."""

    def __init__(self, valor_por_dia: float = 2.0):
        self.valor_por_dia = valor_por_dia

    def calcular(self, dias_atraso: int) -> float:
        return dias_atraso * self.valor_por_dia


class CalculadoraMulta:
    """Responsável apenas por calcular o valor da multa de um empréstimo em atraso."""

    def __init__(self, estrategia: IEstrategiaMulta = None):
        # Uma nova política de multa pode ser injetada aqui sem alterar
        # esta classe nem quem a utiliza (Open/Closed Principle).
        self.estrategia = estrategia or EstrategiaMultaPorDia()

    def dias_em_atraso(self, data_devolucao_prevista_str: str, referencia: datetime = None) -> int:
        referencia = referencia or datetime.now()
        data_devolucao_prevista = datetime.strptime(data_devolucao_prevista_str, '%Y-%m-%d')
        if referencia > data_devolucao_prevista:
            return (referencia - data_devolucao_prevista).days
        return 0

    def calcular(self, data_devolucao_prevista_str: str) -> float:
        dias = self.dias_em_atraso(data_devolucao_prevista_str)
        if dias <= 0:
            return 0.0
        return self.estrategia.calcular(dias)


# =====================================================================
# Orquestração — GerenciadorEmprestimo (SRP + DIP)
# =====================================================================

class GerenciadorEmprestimo:
    """
    Orquestra o processo de empréstimo, delegando cada responsabilidade a
    um colaborador especializado (repositórios e serviços).

    Depende apenas das abstrações recebidas no construtor (Dependency
    Inversion Principle) — não acessa banco de dados, email ou geração de
    PDF diretamente, o que também facilita testes com dublês/mocks.
    """

    PRAZO_EMPRESTIMO_DIAS = 14

    def __init__(
        self,
        repo_livro: RepositorioLivro = None,
        repo_leitor: RepositorioLeitor = None,
        repo_emprestimo: RepositorioEmprestimo = None,
        repo_reserva: RepositorioReserva = None,
        repo_multa: RepositorioMulta = None,
        servico_notificacao: ServicoNotificacao = None,
        servico_relatorio: ServicoRelatorio = None,
        calculadora_multa: CalculadoraMulta = None,
        db_path: str = 'biblioteca.db',
    ):
        # Implementações padrão (SQLite/Email/PDF) são usadas quando nada é
        # informado, mas qualquer uma pode ser substituída — por exemplo,
        # por dublês em testes — sem alterar esta classe.
        self.repo_livro = repo_livro or RepositorioLivro(db_path)
        self.repo_leitor = repo_leitor or RepositorioLeitor(db_path)
        self.repo_emprestimo = repo_emprestimo or RepositorioEmprestimo(db_path)
        self.repo_reserva = repo_reserva or RepositorioReserva(db_path)
        self.repo_multa = repo_multa or RepositorioMulta(db_path)
        self.servico_notificacao = servico_notificacao or ServicoNotificacao()
        self.servico_relatorio = servico_relatorio or ServicoRelatorio()
        self.calculadora_multa = calculadora_multa or CalculadoraMulta()

    def realizar_emprestimo(self, livro_isbn: str, leitor_cpf: str) -> tuple:
        """Realiza o empréstimo de um livro, aplicando as regras de negócio."""
        livro = self.repo_livro.buscar(livro_isbn)
        if not livro:
            return False, "Livro não encontrado"

        leitor = self.repo_leitor.buscar(leitor_cpf)
        if not leitor:
            return False, "Leitor não encontrado"

        exemplares_disponiveis = livro[4]  # coluna exemplares_disponiveis

        if exemplares_disponiveis > 0:
            data_emprestimo = datetime.now().strftime('%Y-%m-%d')
            data_devolucao = (
                datetime.now() + timedelta(days=self.PRAZO_EMPRESTIMO_DIAS)
            ).strftime('%Y-%m-%d')

            emprestimo_id = self.repo_emprestimo.salvar({
                'livro_isbn': livro_isbn,
                'leitor_cpf': leitor_cpf,
                'data_emprestimo': data_emprestimo,
                'data_devolucao_prevista': data_devolucao,
            })

            self.repo_livro.decrementar_exemplar(livro_isbn)

            self.servico_notificacao.notificar_emprestimo(leitor[2], livro[1])
            self.servico_relatorio.gerar_comprovante_emprestimo(
                emprestimo_id, livro[1], leitor[1], data_devolucao,
            )

            return True, "Empréstimo realizado com sucesso"

        data_reserva = datetime.now().strftime('%Y-%m-%d')
        self.repo_reserva.salvar({
            'livro_isbn': livro_isbn,
            'leitor_cpf': leitor_cpf,
            'data_reserva': data_reserva,
        })
        return False, "Livro indisponível. Reserva criada."

    def calcular_multa(self, emprestimo_id) -> float:
        """Calcula (e registra) a multa por atraso de um empréstimo, se houver."""
        emprestimo = self.repo_emprestimo.buscar(emprestimo_id)
        if not emprestimo:
            return 0

        multa = self.calculadora_multa.calcular(emprestimo[4])
        if multa <= 0:
            return 0

        self.repo_multa.salvar({'emprestimo_id': emprestimo_id, 'valor': multa})

        leitor = self.repo_leitor.buscar(emprestimo[2])
        if leitor:
            self.servico_notificacao.notificar_multa(leitor[2], multa)

        return multa
