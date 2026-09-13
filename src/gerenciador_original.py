import sqlite3
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas

class GerenciadorEmprestimo:
    def __init__(self, db_path='biblioteca.db'):
        self.db_path = db_path
    
    def conectar_banco(self):
        """Conecta ao banco de dados SQLite"""
        return sqlite3.connect(self.db_path)
    
    def realizar_emprestimo(self, livro_isbn, leitor_cpf):
        """Realiza empréstimo de um livro"""
        conn = self.conectar_banco()
        cursor = conn.cursor()
        
        # Busca livro
        cursor.execute("SELECT * FROM livros WHERE isbn = ?", (livro_isbn,))
        livro = cursor.fetchone()
        
        if not livro:
            conn.close()
            return False, "Livro não encontrado"
        
        # Busca leitor
        cursor.execute("SELECT * FROM leitores WHERE cpf = ?", (leitor_cpf,))
        leitor = cursor.fetchone()
        
        if not leitor:
            conn.close()
            return False, "Leitor não encontrado"
        
        # Verifica disponibilidade
        exemplares_disponiveis = livro[4]  # Índice da coluna exemplares_disponiveis
        
        if exemplares_disponiveis > 0:
            # Registra empréstimo
            data_emprestimo = datetime.now().strftime('%Y-%m-%d')
            data_devolucao = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
            
            cursor.execute("""
                INSERT INTO emprestimos (livro_isbn, leitor_cpf, data_emprestimo, data_devolucao_prevista)
                VALUES (?, ?, ?, ?)
            """, (livro_isbn, leitor_cpf, data_emprestimo, data_devolucao))
            
            # Atualiza disponibilidade
            cursor.execute("""
                UPDATE livros 
                SET exemplares_disponiveis = exemplares_disponiveis - 1 
                WHERE isbn = ?
            """, (livro_isbn,))
            
            conn.commit()
            emprestimo_id = cursor.lastrowid
            
            # Envia email
            try:
                msg = MIMEText(f"Empréstimo realizado: {livro[1]}")
                msg['Subject'] = 'Empréstimo Realizado'
                msg['To'] = leitor[2]  # email do leitor
                
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login('biblioteca@exemplo.com', 'senha')
                server.send_message(msg)
                server.quit()
            except:
                pass  # Ignora erro de email
            
            # Gera PDF
            try:
                c = canvas.Canvas(f'comprovante_{emprestimo_id}.pdf')
                c.drawString(100, 750, f'Empréstimo #{emprestimo_id}')
                c.drawString(100, 730, f'Livro: {livro[1]}')
                c.drawString(100, 710, f'Leitor: {leitor[1]}')
                c.drawString(100, 690, f'Devolução: {data_devolucao}')
                c.save()
            except:
                pass  # Ignora erro de PDF
            
            conn.close()
            return True, "Empréstimo realizado com sucesso"
        else:
            # Cria reserva
            data_reserva = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("""
                INSERT INTO reservas (livro_isbn, leitor_cpf, data_reserva)
                VALUES (?, ?, ?)
            """, (livro_isbn, leitor_cpf, data_reserva))
            
            conn.commit()
            conn.close()
            return False, "Livro indisponível. Reserva criada."
    
    def calcular_multa(self, emprestimo_id):
        """Calcula multa por atraso"""
        conn = self.conectar_banco()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM emprestimos WHERE id = ?", (emprestimo_id,))
        emprestimo = cursor.fetchone()
        
        if not emprestimo:
            conn.close()
            return 0
        
        data_devolucao_prevista = datetime.strptime(emprestimo[4], '%Y-%m-%d')
        
        if datetime.now() > data_devolucao_prevista:
            dias_atraso = (datetime.now() - data_devolucao_prevista).days
            multa = dias_atraso * 2.0
            
            # Salva multa
            cursor.execute("""
                INSERT INTO multas (emprestimo_id, valor)
                VALUES (?, ?)
            """, (emprestimo_id, multa))
            
            conn.commit()
            
            # Busca leitor para notificar
            leitor_cpf = emprestimo[2]
            cursor.execute("SELECT * FROM leitores WHERE cpf = ?", (leitor_cpf,))
            leitor = cursor.fetchone()
            
            # Envia email de multa
            try:
                msg = MIMEText(f"Multa de R$ {multa:.2f} aplicada")
                msg['Subject'] = 'Multa por Atraso'
                msg['To'] = leitor[2]
                
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login('biblioteca@exemplo.com', 'senha')
                server.send_message(msg)
                server.quit()
            except:
                pass
            
            conn.close()
            return multa
        
        conn.close()
        return 0