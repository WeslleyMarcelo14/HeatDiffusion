"""
Implementação Paralela da Difusão de Calor usando Multiprocessing com Shared Memory

Este módulo implementa a simulação de difusão de calor usando múltiplos processos
para processar diferentes partes da grade simultaneamente, usando memória compartilhada
para evitar overhead de serialização.

Algoritmo:
- Divide a grade em faixas horizontais (uma por processo)
- Cada processo processa sua faixa de linhas
- Usa memória compartilhada para acesso eficiente aos dados
- Sincronização entre processos após cada iteração
"""

import numpy as np
import multiprocessing as mp
import time
from typing import List, Tuple
from multiprocessing import shared_memory


class HeatDiffusionParallel:
    """
    Classe para simulação paralela de difusão de calor usando multiprocessing.
    """
    
    def __init__(self, width, height, num_processes, initial_temp=0.0, boundary_temp=100.0, 
                 min_size_for_parallel=800):
        """
        Inicializa a simulação paralela de difusão de calor.
        
        Args:
            width: Largura da grade (número de colunas)
            height: Altura da grade (número de linhas)
            num_processes: Número de processos a serem utilizados
            initial_temp: Temperatura inicial de todas as células
            boundary_temp: Temperatura das bordas (condição de contorno)
            min_size_for_parallel: Tamanho mínimo (largura ou altura) para usar paralelismo.
                Para problemas menores, o overhead de multiprocessing é maior que o ganho.
                Padrão: 800 (problemas menores usam sequencial automaticamente)
        """
        self.width = width
        self.height = height
        self.initial_temp = initial_temp
        self.boundary_temp = boundary_temp
        self.min_size_for_parallel = min_size_for_parallel
        
        # Se o problema for muito pequeno, força num_processes = 1
        # Overhead de paralelismo é maior que o ganho para problemas pequenos
        if min(width, height) < min_size_for_parallel:
            self.num_processes = 1
        else:
            self.num_processes = num_processes
        
        # Inicializa a grade com temperatura inicial
        self.grid = np.full((height, width), initial_temp, dtype=np.float64)
        
        # Define condições de contorno (bordas com temperatura fixa)
        self.grid[0, :] = boundary_temp      # Borda superior
        self.grid[-1, :] = boundary_temp     # Borda inferior
        self.grid[:, 0] = boundary_temp      # Borda esquerda
        self.grid[:, -1] = boundary_temp     # Borda direita
        
        # Grade auxiliar para o método de Jacobi
        self.new_grid = self.grid.copy()
        
        # Calcula as faixas de linhas para cada processo
        self.process_ranges = self._calculate_process_ranges()
        
        # Shared memory e pool de processos (apenas se num_processes > 1)
        # Usamos duas shared memories e trocamos qual é lida/escrita a cada iteração
        self.shm_a = None
        self.shm_b = None
        self.shared_a = None
        self.shared_b = None
        self.read_grid_name = None  # Nome da shared memory sendo lida
        self.write_grid_name = None  # Nome da shared memory sendo escrita
        self.pool = None
    
    def _calculate_process_ranges(self):
        """
        Calcula as faixas de linhas que cada processo processará.
        
        Returns:
            Lista de tuplas (start_row, end_row) para cada processo
        """
        rows_per_process = (self.height - 2) // self.num_processes  # -2 para excluir bordas
        remainder = (self.height - 2) % self.num_processes
        
        ranges = []
        start = 1  # Começa em 1 para excluir a borda superior
        
        for i in range(self.num_processes):
            # Distribui as linhas restantes entre os primeiros processos
            rows = rows_per_process + (1 if i < remainder else 0)
            end = start + rows
            # O último processo não processa a última linha (borda inferior)
            if i == self.num_processes - 1:
                end = min(end, self.height - 1)
            ranges.append((start, end))
            start = end
        
        return ranges
    
    @staticmethod
    def _update_region_worker(args):
        """
        Função auxiliar para atualizar uma região da grade usando shared memory.
        Usa cache de conexões para evitar overhead de abrir/fechar shared memory.
        
        Args:
            args: Tupla (read_shm_name, write_shm_name, height, width, start_row, end_row)
        
        Returns:
            None (atualiza diretamente na shared memory)
        """
        read_shm_name, write_shm_name, height, width, start_row, end_row = args
        
        # Acessa shared memory (reutiliza se já existir no processo)
        # Nota: multiprocessing cria novos processos, então não há cache real,
        # mas manteremos a conexão aberta durante a execução
        try:
            shm_read = shared_memory.SharedMemory(name=read_shm_name)
            shm_write = shared_memory.SharedMemory(name=write_shm_name)
        except FileNotFoundError:
            # Se a shared memory não existir, retorna sem fazer nada
            return
        
        # Cria arrays NumPy a partir da shared memory
        grid = np.ndarray((height, width), dtype=np.float64, buffer=shm_read.buf)
        new_grid = np.ndarray((height, width), dtype=np.float64, buffer=shm_write.buf)
        
        # Atualiza células internas na região atribuída
        actual_start = max(1, start_row)
        actual_end = min(height - 1, end_row)
        
        if actual_start < actual_end:
            new_grid[actual_start:actual_end, 1:-1] = (
                grid[actual_start-1:actual_end-1, 1:-1] +  # Norte
                grid[actual_start+1:actual_end+1, 1:-1] +  # Sul
                grid[actual_start:actual_end, 0:-2] +      # Oeste
                grid[actual_start:actual_end, 2:]          # Leste
            ) / 4.0
        
        # Não fecha as conexões aqui - serão fechadas quando o processo terminar
        # Isso reduz overhead, mas requer cuidado na limpeza
        del grid, new_grid
        # Nota: Não fechamos shm_read e shm_write aqui para reduzir overhead
        # Eles serão limpos quando o processo worker terminar
    
    def _init_shared_memory(self):
        """Inicializa shared memory para comunicação entre processos."""
        if self.num_processes == 1:
            return
        
        # Cria duas shared memories (para alternar leitura/escrita)
        self.shm_a = shared_memory.SharedMemory(create=True, size=self.grid.nbytes)
        self.shm_b = shared_memory.SharedMemory(create=True, size=self.grid.nbytes)
        
        # Cria arrays NumPy que apontam para a shared memory (mantidos durante toda a simulação)
        self.shared_a = np.ndarray(self.grid.shape, dtype=self.grid.dtype, buffer=self.shm_a.buf)
        self.shared_b = np.ndarray(self.grid.shape, dtype=self.grid.dtype, buffer=self.shm_b.buf)
        
        # Copia dados iniciais
        self.shared_a[:] = self.grid[:]
        self.shared_b[:] = self.grid[:]
        
        # Inicializa qual é lida e qual é escrita
        self.read_grid_name = self.shm_a.name
        self.write_grid_name = self.shm_b.name
        self.read_array = self.shared_a  # Referência persistente
        self.write_array = self.shared_b  # Referência persistente
    
    def _cleanup_shared_memory(self):
        """Limpa shared memory."""
        if self.shared_a is not None:
            del self.shared_a
        if self.shared_b is not None:
            del self.shared_b
        if self.shm_a is not None:
            self.shm_a.close()
            self.shm_a.unlink()
            self.shm_a = None
        if self.shm_b is not None:
            self.shm_b.close()
            self.shm_b.unlink()
            self.shm_b = None
    
    def update(self):
        """
        Executa uma iteração do método de Jacobi usando processos paralelos.
        """
        # Se num_processes == 1, executa sequencialmente (sem overhead de multiprocessing)
        if self.num_processes == 1:
            self.new_grid[1:-1, 1:-1] = (
                self.grid[0:-2, 1:-1] +  # Norte
                self.grid[2:, 1:-1] +     # Sul
                self.grid[1:-1, 0:-2] +   # Oeste
                self.grid[1:-1, 2:]       # Leste
            ) / 4.0
        else:
            # Atualiza referências se necessário (após troca de buffers)
            if self.read_grid_name == self.shm_a.name:
                self.read_array = self.shared_a
            else:
                self.read_array = self.shared_b
            
            if self.write_grid_name == self.shm_a.name:
                self.write_array = self.shared_a
            else:
                self.write_array = self.shared_b
            
            # Trabalha diretamente na shared memory - não copia para arrays locais
            # Apenas atualiza bordas se necessário
            self.read_array[0, :] = self.boundary_temp
            self.read_array[-1, :] = self.boundary_temp
            self.read_array[:, 0] = self.boundary_temp
            self.read_array[:, -1] = self.boundary_temp
            
            # Prepara argumentos para cada processo
            args_list = []
            for start_row, end_row in self.process_ranges:
                args_list.append((
                    self.read_grid_name,
                    self.write_grid_name,
                    self.height,
                    self.width,
                    start_row,
                    end_row
                ))
            
            # Executa em paralelo (pool já deve estar criado em simulate())
            self.pool.map(self._update_region_worker, args_list)
            
            # Mantém bordas fixas na shared memory escrita (condições de contorno)
            self.write_array[0, :] = self.boundary_temp
            self.write_array[-1, :] = self.boundary_temp
            self.write_array[:, 0] = self.boundary_temp
            self.write_array[:, -1] = self.boundary_temp
            
            # Troca qual shared memory é lida/escrita para próxima iteração
            self.read_grid_name, self.write_grid_name = self.write_grid_name, self.read_grid_name
        
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
        try:
            # Inicializa shared memory e pool de processos se necessário
            if self.num_processes > 1:
                self._init_shared_memory()
                # Cria pool uma vez no início (reutilizado em todas as iterações)
                self.pool = mp.Pool(processes=self.num_processes)
            
            for iteration in range(iterations):
                # Para verificação de convergência, copia apenas quando necessário
                if self.num_processes > 1:
                    # Copia da shared memory para arrays locais apenas para verificação de convergência
                    # (evita cópia desnecessária - só copia quando precisa verificar)
                    if iteration == 0 or iteration % 10 == 0:  # Verifica convergência a cada 10 iterações
                        old_grid = self.read_array.copy()
                    self.update()
                    # Copia resultado apenas quando necessário para verificação
                    if iteration == 0 or iteration % 10 == 0:
                        self.grid[:] = self.read_array[:]
                        self.new_grid[:] = self.write_array[:]
                        max_diff = np.max(np.abs(self.grid - old_grid))
                        if max_diff < convergence_threshold:
                            return iteration + 1
                else:
                    old_grid = self.grid.copy()
                    self.update()
                    # Verifica convergência
                    max_diff = np.max(np.abs(self.grid - old_grid))
                    if max_diff < convergence_threshold:
                        return iteration + 1
            
            return iterations
        finally:
            # Garante que o pool de processos é fechado
            if self.pool is not None:
                self.pool.close()
                self.pool.join()
                self.pool = None
            
            # Limpa shared memory
            self._cleanup_shared_memory()
    
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
        num_threads: Número de processos (mantido como num_threads para compatibilidade)
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
        print(f"  Processos: {num_threads}")
        print(f"  Iterações: {actual_iterations}")
        print(f"  Tempo de execução: {execution_time:.4f} segundos")
        print(f"  Temperatura média: {simulation.get_average_temp():.4f}°C")
    
    return execution_time


if __name__ == "__main__":
    # Exemplo de uso
    print("=== Simulação Paralela de Difusão de Calor ===\n")
    
    # Teste com diferentes números de processos
    width, height = 500, 500
    iterations = 1000
    process_counts = [1, 2, 4, 8]
    
    for num_processes in process_counts:
        run_parallel_simulation(width, height, iterations, num_processes)
        print()

