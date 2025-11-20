"""
Implementação Paralela da Difusão de Calor usando Threads

Este módulo implementa a simulação de difusão de calor usando múltiplas threads
para processar diferentes partes da grade simultaneamente.

Algoritmo:
- Divide a grade em faixas horizontais (uma por thread)
- Cada thread processa sua faixa de linhas
- Sincronização entre threads após cada iteração
"""

import numpy as np
import threading
import time
from typing import List


class HeatDiffusionParallel:
    """
    Classe para simulação paralela de difusão de calor usando threads.
    """
    
    def __init__(self, width, height, num_threads, initial_temp=0.0, boundary_temp=100.0):
        """
        Inicializa a simulação paralela de difusão de calor.
        
        Args:
            width: Largura da grade (número de colunas)
            height: Altura da grade (número de linhas)
            num_threads: Número de threads a serem utilizadas
            initial_temp: Temperatura inicial de todas as células
            boundary_temp: Temperatura das bordas (condição de contorno)
        """
        self.width = width
        self.height = height
        self.num_threads = num_threads
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
        
        # Locks para sincronização
        self.lock = threading.Lock()
        self.barrier = threading.Barrier(num_threads)
        
        # Calcula as faixas de linhas para cada thread
        self.thread_ranges = self._calculate_thread_ranges()
    
    def _calculate_thread_ranges(self):
        """
        Calcula as faixas de linhas que cada thread processará.
        
        Returns:
            Lista de tuplas (start_row, end_row) para cada thread
        """
        rows_per_thread = self.height // self.num_threads
        remainder = self.height % self.num_threads
        
        ranges = []
        start = 1  # Começa em 1 para excluir a borda superior
        
        for i in range(self.num_threads):
            # Distribui as linhas restantes entre as primeiras threads
            end = start + rows_per_thread + (1 if i < remainder else 0)
            # A última thread não processa a última linha (borda inferior)
            if i == self.num_threads - 1:
                end = min(end, self.height - 1)
            ranges.append((start, end))
            start = end
        
        return ranges
    
    def _update_region(self, thread_id, start_row, end_row):
        """
        Atualiza uma região específica da grade (executado por uma thread).
        
        Args:
            thread_id: ID da thread
            start_row: Primeira linha a processar (inclusive)
            end_row: Última linha a processar (exclusive)
        """
        # Atualiza células internas na faixa atribuída
        for i in range(start_row, end_row):
            for j in range(1, self.width - 1):
                # Média das 4 células vizinhas
                self.new_grid[i, j] = (
                    self.grid[i-1, j] +      # Norte
                    self.grid[i+1, j] +      # Sul
                    self.grid[i, j-1] +      # Oeste
                    self.grid[i, j+1]        # Leste
                ) / 4.0
    
    def _worker_thread(self, thread_id, start_row, end_row):
        """
        Função executada por cada thread worker.
        
        Args:
            thread_id: ID da thread
            start_row: Primeira linha a processar
            end_row: Última linha a processar
        """
        # Aguarda todas as threads estarem prontas
        self.barrier.wait()
        
        # Processa sua região
        self._update_region(thread_id, start_row, end_row)
        
        # Aguarda todas as threads terminarem antes de trocar as grades
        self.barrier.wait()
    
    def update(self):
        """
        Executa uma iteração do método de Jacobi usando threads paralelas.
        """
        threads = []
        
        # Cria e inicia as threads
        for thread_id, (start_row, end_row) in enumerate(self.thread_ranges):
            thread = threading.Thread(
                target=self._worker_thread,
                args=(thread_id, start_row, end_row)
            )
            threads.append(thread)
            thread.start()
        
        # Aguarda todas as threads terminarem
        for thread in threads:
            thread.join()
        
        # Troca as grades (método de Jacobi)
        # Isso é feito após todas as threads terminarem
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


def run_parallel_simulation(width, height, iterations, num_threads, verbose=True):
    """
    Função auxiliar para executar uma simulação paralela completa.
    
    Args:
        width: Largura da grade
        height: Altura da grade
        iterations: Número de iterações
        num_threads: Número de threads
        verbose: Se True, imprime informações sobre a execução
    
    Returns:
        Tempo de execução em segundos
    """
    start_time = time.time()
    
    simulation = HeatDiffusionParallel(width, height, num_threads)
    actual_iterations = simulation.simulate(iterations)
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    if verbose:
        print(f"Simulação Paralela:")
        print(f"  Tamanho: {width}x{height}")
        print(f"  Threads: {num_threads}")
        print(f"  Iterações: {actual_iterations}")
        print(f"  Tempo de execução: {execution_time:.4f} segundos")
        print(f"  Temperatura média: {simulation.get_average_temp():.4f}°C")
    
    return execution_time


if __name__ == "__main__":
    # Exemplo de uso
    print("=== Simulação Paralela de Difusão de Calor ===\n")
    
    # Teste com diferentes números de threads
    width, height = 500, 500
    iterations = 1000
    thread_counts = [1, 2, 4, 8]
    
    for num_threads in thread_counts:
        run_parallel_simulation(width, height, iterations, num_threads)
        print()

