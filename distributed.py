"""
Implementação Distribuída da Difusão de Calor usando Sockets

Este módulo implementa a simulação de difusão de calor distribuída em múltiplos processos
comunicando-se via sockets TCP/IP.

Arquitetura:
- Servidor mestre coordena a simulação
- Trabalhadores (workers) processam partes da grade
- Comunicação via sockets TCP/IP
"""

import numpy as np
import socket
import struct
import pickle
import time
import threading
from typing import List, Tuple, Optional


class HeatDiffusionDistributed:
    """
    Classe para simulação distribuída de difusão de calor usando sockets.
    """
    
    def __init__(self, width, height, initial_temp=0.0, boundary_temp=100.0):
        """
        Inicializa a simulação distribuída de difusão de calor (servidor mestre).
        
        Args:
            width: Largura da grade (número de colunas)
            height: Altura da grade (número de linhas)
            initial_temp: Temperatura inicial de todas as células
            boundary_temp: Temperatura das bordas (condição de contorno)
        """
        self.width = width
        self.height = height
        self.initial_temp = initial_temp
        self.boundary_temp = boundary_temp
        
        # Inicializa a grade com temperatura inicial
        self.grid = np.full((height, width), initial_temp, dtype=np.float64)
        
        # Define condições de contorno (bordas com temperatura fixa)
        self.grid[0, :] = boundary_temp      # Borda superior
        self.grid[-1, :] = boundary_temp     # Borda inferior
        self.grid[:, 0] = boundary_temp      # Borda esquerda
        self.grid[:, -1] = boundary_temp     # Borda direita
        
        # Grade auxiliar para o método de Jacobi
        self.new_grid = self.grid.copy()
        
        # Lista de workers conectados
        self.workers: List[socket.socket] = []
        self.worker_ranges: List[Tuple[int, int]] = []
    
    def add_worker(self, worker_socket: socket.socket, start_row: int, end_row: int):
        """
        Adiciona um worker à simulação.
        
        Args:
            worker_socket: Socket conectado ao worker
            start_row: Primeira linha que o worker processará
            end_row: Última linha que o worker processará (exclusive)
        """
        self.workers.append(worker_socket)
        self.worker_ranges.append((start_row, end_row))
    
    def _send_grid_slice(self, worker_socket: socket.socket, start_row: int, end_row: int):
        """
        Envia uma fatia da grade para um worker.
        
        Args:
            worker_socket: Socket do worker
            start_row: Primeira linha a enviar
            end_row: Última linha a enviar (exclusive)
        """
        # Inclui uma linha acima e abaixo para os cálculos de borda
        send_start = max(0, start_row - 1)
        send_end = min(self.height, end_row + 1)
        
        slice_data = self.grid[send_start:send_end, :].copy()
        
        # Serializa e envia
        data = pickle.dumps(slice_data)
        size = len(data)
        
        # Envia tamanho e dados
        worker_socket.sendall(struct.pack('!I', size))
        worker_socket.sendall(data)
    
    def _receive_grid_slice(self, worker_socket: socket.socket, start_row: int, end_row: int):
        """
        Recebe uma fatia atualizada da grade de um worker.
        
        Args:
            worker_socket: Socket do worker
            start_row: Primeira linha recebida (na grade original)
            end_row: Última linha recebida (na grade original, exclusive)
        """
        # Recebe tamanho
        size_data = worker_socket.recv(4)
        if len(size_data) < 4:
            raise ConnectionError("Falha ao receber tamanho dos dados")
        
        size = struct.unpack('!I', size_data)[0]
        
        # Recebe dados
        data = b''
        while len(data) < size:
            chunk = worker_socket.recv(size - len(data))
            if not chunk:
                raise ConnectionError("Conexão fechada durante recebimento")
            data += chunk
        
        # Deserializa
        slice_data = pickle.loads(data)
        
        # Calcula índices: o slice enviado inclui uma linha acima (send_start = start_row - 1)
        send_start = max(0, start_row - 1)
        
        # Atualiza apenas as células internas processadas
        actual_start = max(1, start_row)
        actual_end = min(self.height - 1, end_row)
        
        # Índices no slice recebido (slice começa em índice 0)
        slice_actual_start = actual_start - send_start
        slice_actual_end = actual_end - send_start
        
        if slice_actual_start < slice_actual_end:
            self.new_grid[actual_start:actual_end, 1:-1] = \
                slice_data[slice_actual_start:slice_actual_end, 1:-1]
    
    def update(self):
        """
        Executa uma iteração do método de Jacobi usando workers distribuídos.
        """
        # Envia fatias para cada worker
        for worker_socket, (start_row, end_row) in zip(self.workers, self.worker_ranges):
            self._send_grid_slice(worker_socket, start_row, end_row)
        
        # Recebe resultados de cada worker
        for worker_socket, (start_row, end_row) in zip(self.workers, self.worker_ranges):
            self._receive_grid_slice(worker_socket, start_row, end_row)
        
        # Troca as grades (método de Jacobi)
        self.grid, self.new_grid = self.new_grid, self.grid
    
    def simulate(self, iterations, convergence_threshold=1e-6):
        """
        Executa a simulação por um número fixo de iterações ou até convergência.
        
        Args:
            iterations: Número máximo de iterações
            convergence_threshold: Limiar de convergência
        
        Returns:
            Número de iterações executadas
        """
        for iteration in range(iterations):
            old_grid = self.grid.copy()
            self.update()
            
            # Verifica convergência
            max_diff = np.max(np.abs(self.grid - old_grid))
            if max_diff < convergence_threshold:
                return iteration + 1
        
        return iterations
    
    def get_grid(self):
        """Retorna a grade atual de temperaturas."""
        return self.grid.copy()
    
    def get_average_temp(self):
        """Retorna a temperatura média da grade (excluindo bordas)."""
        return np.mean(self.grid[1:-1, 1:-1])
    
    def close(self):
        """Fecha todas as conexões com workers."""
        for worker_socket in self.workers:
            try:
                worker_socket.close()
            except:
                pass
        self.workers.clear()


class DistributedWorker:
    """
    Classe para um worker na simulação distribuída.
    """
    
    def __init__(self, host='localhost', port=8888):
        """
        Inicializa um worker que se conecta ao servidor mestre.
        
        Args:
            host: Endereço do servidor mestre
            port: Porta do servidor mestre
        """
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
    
    def connect(self):
        """Conecta ao servidor mestre."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
    
    def process_slice(self):
        """
        Processa uma fatia da grade recebida do servidor.
        
        Returns:
            Fatia processada da grade
        """
        # Recebe tamanho
        size_data = self.socket.recv(4)
        if len(size_data) < 4:
            raise ConnectionError("Falha ao receber tamanho dos dados")
        
        size = struct.unpack('!I', size_data)[0]
        
        # Recebe dados
        data = b''
        while len(data) < size:
            chunk = self.socket.recv(size - len(data))
            if not chunk:
                raise ConnectionError("Conexão fechada durante recebimento")
            data += chunk
        
        # Deserializa
        slice_grid = pickle.loads(data)
        height, width = slice_grid.shape
        
        # Processa a fatia usando operações NumPy vetorizadas
        # Isso é muito mais rápido que loops Python
        new_slice = slice_grid.copy()
        
        # Atualiza células internas usando operações vetorizadas do NumPy
        # Similar à implementação sequencial, mas apenas para a fatia recebida
        new_slice[1:-1, 1:-1] = (
            slice_grid[0:-2, 1:-1] +  # Norte
            slice_grid[2:, 1:-1] +     # Sul
            slice_grid[1:-1, 0:-2] +   # Oeste
            slice_grid[1:-1, 2:]       # Leste
        ) / 4.0
        
        # Envia resultado de volta
        result_data = pickle.dumps(new_slice)
        result_size = len(result_data)
        
        self.socket.sendall(struct.pack('!I', result_size))
        self.socket.sendall(result_data)
        
        return new_slice
    
    def close(self):
        """Fecha a conexão com o servidor."""
        if self.socket:
            self.socket.close()


def run_distributed_server(width, height, iterations, num_workers, port=8888, verbose=True):
    """
    Executa o servidor mestre da simulação distribuída.
    
    Args:
        width: Largura da grade
        height: Altura da grade
        iterations: Número de iterações
        num_workers: Número de workers esperados
        port: Porta para aceitar conexões
        verbose: Se True, imprime informações sobre a execução
    
    Returns:
        Tempo de execução em segundos
    """
    # Cria socket servidor
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('localhost', port))
    server_socket.listen(num_workers)
    
    if verbose:
        print(f"Aguardando {num_workers} workers conectarem na porta {port}...")
    
    # Cria simulação
    simulation = HeatDiffusionDistributed(width, height)
    
    # Calcula faixas para cada worker
    rows_per_worker = (height - 2) // num_workers  # -2 para excluir bordas
    remainder = (height - 2) % num_workers
    
    # Aceita conexões e atribui faixas
    start_row = 1
    for i in range(num_workers):
        worker_socket, addr = server_socket.accept()
        if verbose:
            print(f"Worker {i+1} conectado de {addr}")
        
        # Calcula faixa para este worker
        rows = rows_per_worker + (1 if i < remainder else 0)
        end_row = start_row + rows
        
        simulation.add_worker(worker_socket, start_row, end_row)
        start_row = end_row
    
    if verbose:
        print("Todos os workers conectados. Iniciando simulação...\n")
    
    # Executa simulação
    start_time = time.time()
    actual_iterations = simulation.simulate(iterations)
    end_time = time.time()
    execution_time = end_time - start_time
    
    if verbose:
        print(f"Simulação Distribuída:")
        print(f"  Tamanho: {width}x{height}")
        print(f"  Workers: {num_workers}")
        print(f"  Iterações: {actual_iterations}")
        print(f"  Tempo de execução: {execution_time:.4f} segundos")
        print(f"  Temperatura média: {simulation.get_average_temp():.4f}°C")
    
    # Fecha conexões
    simulation.close()
    server_socket.close()
    
    return execution_time


def run_distributed_worker(host='localhost', port=8888, iterations=None):
    """
    Executa um worker da simulação distribuída.
    
    Args:
        host: Endereço do servidor mestre
        port: Porta do servidor mestre
        iterations: Número de iterações (None = executa até desconectar)
    """
    worker = DistributedWorker(host, port)
    worker.connect()
    
    try:
        iteration = 0
        while True:
            if iterations and iteration >= iterations:
                break
            
            try:
                worker.process_slice()
                iteration += 1
            except (ConnectionError, EOFError):
                break
    finally:
        worker.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'worker':
        # Modo worker
        host = sys.argv[2] if len(sys.argv) > 2 else 'localhost'
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 8888
        run_distributed_worker(host, port)
    else:
        # Modo servidor (para testes)
        print("=== Simulação Distribuída de Difusão de Calor ===\n")
        print("Para executar workers, use: python distributed.py worker [host] [port]")
        print("Para executar servidor, use: python benchmark.py --distributed\n")

