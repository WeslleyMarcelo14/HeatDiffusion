import numpy as np
import socket
import struct
import pickle
import time
import threading
from typing import List, Tuple, Optional


class DifusaoCalorDistribuida:
    
    def __init__(self, largura, altura, temp_inicial=0.0, temp_borda=100.0):
        self.largura = largura
        self.altura = altura
        self.temp_inicial = temp_inicial
        self.temp_borda = temp_borda
        
        self.grade = np.full((altura, largura), temp_inicial, dtype=np.float64)
        
        self.grade[0, :] = temp_borda
        self.grade[-1, :] = temp_borda
        self.grade[:, 0] = temp_borda
        self.grade[:, -1] = temp_borda
        
        self.nova_grade = self.grade.copy()
        
        self.trabalhadores: List[socket.socket] = []
        self.faixas_trabalhadores: List[Tuple[int, int]] = []
    
    def adicionar_trabalhador(self, socket_trabalhador: socket.socket, linha_inicio: int, linha_fim: int):
        self.trabalhadores.append(socket_trabalhador)
        self.faixas_trabalhadores.append((linha_inicio, linha_fim))
    
    def _enviar_fatia_grade(self, socket_trabalhador: socket.socket, linha_inicio: int, linha_fim: int):
        inicio_envio = max(0, linha_inicio - 1)
        fim_envio = min(self.altura, linha_fim + 1)
        
        dados_fatia = self.grade[inicio_envio:fim_envio, :].copy()
        
        dados = pickle.dumps(dados_fatia, protocol=pickle.HIGHEST_PROTOCOL)
        tamanho = len(dados)
        
        socket_trabalhador.sendall(struct.pack('!I', tamanho))
        socket_trabalhador.sendall(dados)
    
    def _receber_fatia_grade(self, socket_trabalhador: socket.socket, linha_inicio: int, linha_fim: int):
        dados_tamanho = socket_trabalhador.recv(4)
        if len(dados_tamanho) < 4:
            raise ConnectionError("Falha ao receber tamanho dos dados")
        
        tamanho = struct.unpack('!I', dados_tamanho)[0]
        
        dados = b''
        while len(dados) < tamanho:
            pedaco = socket_trabalhador.recv(tamanho - len(dados))
            if not pedaco:
                raise ConnectionError("Conexão fechada durante recebimento")
            dados += pedaco
        
        dados_fatia = pickle.loads(dados)
        
        inicio_real = max(1, linha_inicio)
        fim_real = min(self.altura - 1, linha_fim)
        fatia_inicio = inicio_real - (linha_inicio - 1 if linha_inicio > 0 else 0)
        fatia_fim = fatia_inicio + (fim_real - inicio_real)
        
        self.nova_grade[inicio_real:fim_real, 1:-1] = dados_fatia[fatia_inicio:fatia_fim, 1:-1]
    
    def atualizar(self):
        for socket_trabalhador, (linha_inicio, linha_fim) in zip(self.trabalhadores, self.faixas_trabalhadores):
            self._enviar_fatia_grade(socket_trabalhador, linha_inicio, linha_fim)
        
        for socket_trabalhador, (linha_inicio, linha_fim) in zip(self.trabalhadores, self.faixas_trabalhadores):
            self._receber_fatia_grade(socket_trabalhador, linha_inicio, linha_fim)
        
        self.grade, self.nova_grade = self.nova_grade, self.grade
    
    def simular(self, iteracoes, limite_convergencia=1e-6):
        for iteracao in range(iteracoes):
            grade_antiga = self.grade.copy()
            self.atualizar()
            
            dif_maxima = np.max(np.abs(self.grade - grade_antiga))
            if dif_maxima < limite_convergencia:
                return iteracao + 1
        
        return iteracoes
    
    def obter_grade(self):
        return self.grade.copy()
    
    def obter_temp_media(self):
        return np.mean(self.grade[1:-1, 1:-1])
    
    def fechar(self):
        for socket_trabalhador in self.trabalhadores:
            try:
                socket_trabalhador.close()
            except:
                pass
        self.trabalhadores.clear()


class TrabalhadorDistribuido:
    
    def __init__(self, host='localhost', porta=8888):
        self.host = host
        self.porta = porta
        self.socket: Optional[socket.socket] = None
    
    def conectar(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.porta))
    
    def processar_fatia(self):
        dados_tamanho = self.socket.recv(4)
        if len(dados_tamanho) < 4:
            raise ConnectionError("Falha ao receber tamanho dos dados")
        
        tamanho = struct.unpack('!I', dados_tamanho)[0]
        
        dados = b''
        while len(dados) < tamanho:
            pedaco = self.socket.recv(tamanho - len(dados))
            if not pedaco:
                raise ConnectionError("Conexão fechada durante recebimento")
            dados += pedaco
        
        grade_fatia = pickle.loads(dados)
        altura, largura = grade_fatia.shape
        
        nova_fatia = grade_fatia.copy()
        
        nova_fatia[1:-1, 1:-1] = 0.25 * (
            grade_fatia[0:-2, 1:-1] +
            grade_fatia[2:, 1:-1] +
            grade_fatia[1:-1, 0:-2] +
            grade_fatia[1:-1, 2:]
        )
        
        dados_resultado = pickle.dumps(nova_fatia, protocol=pickle.HIGHEST_PROTOCOL)
        tamanho_resultado = len(dados_resultado)
        
        self.socket.sendall(struct.pack('!I', tamanho_resultado))
        self.socket.sendall(dados_resultado)
        
        return nova_fatia
    
    def fechar(self):
        if self.socket:
            self.socket.close()


def executar_servidor_distribuido(largura, altura, iteracoes, num_trabalhadores, porta=8888, detalhado=True):
    socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    socket_servidor.bind(('localhost', porta))
    socket_servidor.listen(num_trabalhadores)
    
    if detalhado:
        print(f"Aguardando {num_trabalhadores} trabalhadores conectarem na porta {porta}...")
    
    simulacao = DifusaoCalorDistribuida(largura, altura)
    
    linhas_por_trabalhador = (altura - 2) // num_trabalhadores
    resto = (altura - 2) % num_trabalhadores
    
    linha_inicio = 1
    for i in range(num_trabalhadores):
        socket_trabalhador, addr = socket_servidor.accept()
        if detalhado:
            print(f"Trabalhador {i+1} conectado de {addr}")
        
        linhas = linhas_por_trabalhador + (1 if i < resto else 0)
        linha_fim = linha_inicio + linhas
        
        simulacao.adicionar_trabalhador(socket_trabalhador, linha_inicio, linha_fim)
        linha_inicio = linha_fim
    
    if detalhado:
        print("Todos os trabalhadores conectados. Iniciando simulação...\n")
    
    tempo_inicio = time.time()
    iteracoes_reais = simulacao.simular(iteracoes)
    tempo_fim = time.time()
    tempo_execucao = tempo_fim - tempo_inicio
    
    if detalhado:
        print(f"Simulação Distribuída:")
        print(f"  Tamanho: {largura}x{altura}")
        print(f"  Trabalhadores: {num_trabalhadores}")
        print(f"  Iterações: {iteracoes_reais}")
        print(f"  Tempo de execução: {tempo_execucao:.4f} segundos")
        print(f"  Temperatura média: {simulacao.obter_temp_media():.4f}°C")
    
    simulacao.fechar()
    socket_servidor.close()
    
    return tempo_execucao


def executar_trabalhador_distribuido(host='localhost', porta=8888, iteracoes=None):
    trabalhador = TrabalhadorDistribuido(host, porta)
    trabalhador.conectar()
    
    try:
        iteracao = 0
        while True:
            if iteracoes and iteracao >= iteracoes:
                break
            
            try:
                trabalhador.processar_fatia()
                iteracao += 1
            except (ConnectionError, EOFError):
                break
    finally:
        trabalhador.fechar()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'worker':
        host = sys.argv[2] if len(sys.argv) > 2 else 'localhost'
        porta = int(sys.argv[3]) if len(sys.argv) > 3 else 8888
        executar_trabalhador_distribuido(host, porta)
    else:
        print("=== Simulação Distribuída de Difusão de Calor ===\n")
        print("Para executar trabalhadores, use: python distribuido.py worker [host] [porta]")
        print("Para executar servidor, use: python teste_desempenho.py --distributed\n")

