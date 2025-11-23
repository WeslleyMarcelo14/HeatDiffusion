"""
Implementação Sequencial da Difusão de Calor

Este módulo implementa a simulação de difusão de calor usando o método de diferenças finitas
em uma grade 2D. A versão sequencial processa todas as células da grade de forma sequencial.

Algoritmo:
- Utiliza o método de Jacobi para resolver a equação do calor
- Cada iteração calcula a temperatura de cada célula baseada na média das células vizinhas
- Condições de contorno: bordas mantêm temperatura fixa
"""

import numpy as np
import time


class HeatDiffusionSequential:
    """
    Classe para simulação sequencial de difusão de calor.
    """
    
    def __init__(self, width, height, initial_temp=0.0, boundary_temp=100.0):
        """
        Inicializa a simulação de difusão de calor.
        
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
    
    def update(self):
        """
        Executa uma iteração do método de Jacobi.
        Calcula a nova temperatura de cada célula baseada na média das células vizinhas.
        Usa operações NumPy vetorizadas para melhor desempenho.
        """
        # Atualiza células internas usando operações vetorizadas do NumPy
        # Isso é muito mais rápido que loops Python
        self.new_grid[1:-1, 1:-1] = (
            self.grid[0:-2, 1:-1] +  # Norte
            self.grid[2:, 1:-1] +     # Sul
            self.grid[1:-1, 0:-2] +   # Oeste
            self.grid[1:-1, 2:]       # Leste
        ) / 4.0
        
        # Troca as grades (método de Jacobi)
        self.grid, self.new_grid = self.new_grid, self.grid
    
    def simulate(self, iterations, convergence_threshold=1e-6):
        """
        Executa a simulação por um número fixo de iterações ou até convergência.
        
        Args:
            iterations: Número máximo de iterações
            convergence_threshold: Limiar de convergência (diferença máxima entre iterações)
        
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


def run_sequential_simulation(width, height, iterations, verbose=True):
    """
    Função auxiliar para executar uma simulação sequencial completa.
    
    Args:
        width: Largura da grade
        height: Altura da grade
        iterations: Número de iterações
        verbose: Se True, imprime informações sobre a execução
    
    Returns:
        Tempo de execução em segundos
    """
    start_time = time.time()
    
    simulation = HeatDiffusionSequential(width, height)
    actual_iterations = simulation.simulate(iterations)
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    if verbose:
        print(f"Simulação Sequencial:")
        print(f"  Tamanho: {width}x{height}")
        print(f"  Iterações: {actual_iterations}")
        print(f"  Tempo de execução: {execution_time:.4f} segundos")
        print(f"  Temperatura média: {simulation.get_average_temp():.4f}°C")
    
    return execution_time


if __name__ == "__main__":
    # Exemplo de uso
    print("=== Simulação Sequencial de Difusão de Calor ===\n")
    
    # Teste com diferentes tamanhos
    sizes = [(100, 100), (200, 200), (500, 500)]
    iterations = 1000
    
    for width, height in sizes:
        run_sequential_simulation(width, height, iterations)
        print()

