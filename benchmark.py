"""
Script de Benchmark para Comparação de Desempenho

Este script executa testes de desempenho para as três versões:
- Sequencial
- Paralela (com diferentes números de threads)
- Distribuída (com diferentes números de workers)

Gera tabelas e gráficos comparativos.
"""

import argparse
import time
import json
import csv
from typing import List, Dict, Tuple
import matplotlib.pyplot as plt
import numpy as np

from sequential import run_sequential_simulation
from parallel import run_parallel_simulation
from distributed import run_distributed_server, run_distributed_worker
import subprocess
import sys
import os


class BenchmarkRunner:
    """
    Classe para executar benchmarks e coletar resultados.
    """
    
    def __init__(self, output_dir='results'):
        """
        Inicializa o benchmark runner.
        
        Args:
            output_dir: Diretório para salvar resultados
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.results = []
    
    def run_sequential_benchmark(self, sizes: List[Tuple[int, int]], iterations: int):
        """
        Executa benchmark sequencial.
        
        Args:
            sizes: Lista de tuplas (width, height) para testar
            iterations: Número de iterações
        """
        print("\n" + "="*60)
        print("BENCHMARK SEQUENCIAL")
        print("="*60)
        
        for width, height in sizes:
            print(f"\nTestando tamanho {width}x{height}...")
            execution_time = run_sequential_simulation(width, height, iterations, verbose=True)
            
            self.results.append({
                'version': 'sequential',
                'width': width,
                'height': height,
                'iterations': iterations,
                'threads': 1,
                'workers': 1,
                'execution_time': execution_time
            })
    
    def run_parallel_benchmark(self, sizes: List[Tuple[int, int]], iterations: int, 
                               thread_counts: List[int]):
        """
        Executa benchmark paralelo.
        
        Args:
            sizes: Lista de tuplas (width, height) para testar
            iterations: Número de iterações
            thread_counts: Lista de números de threads para testar
        """
        print("\n" + "="*60)
        print("BENCHMARK PARALELO")
        print("="*60)
        
        for width, height in sizes:
            for num_threads in thread_counts:
                print(f"\nTestando tamanho {width}x{height} com {num_threads} threads...")
                execution_time = run_parallel_simulation(
                    width, height, iterations, num_threads, verbose=True
                )
                
                self.results.append({
                    'version': 'parallel',
                    'width': width,
                    'height': height,
                    'iterations': iterations,
                    'threads': num_threads,
                    'workers': 1,
                    'execution_time': execution_time
                })
    
    def run_distributed_benchmark(self, sizes: List[Tuple[int, int]], iterations: int,
                                  worker_counts: List[int], port_start=8888):
        """
        Executa benchmark distribuído.
        
        Args:
            sizes: Lista de tuplas (width, height) para testar
            iterations: Número de iterações
            worker_counts: Lista de números de workers para testar
            port_start: Porta inicial para servidores
        """
        print("\n" + "="*60)
        print("BENCHMARK DISTRIBUÍDO")
        print("="*60)
        
        for width, height in sizes:
            for num_workers in worker_counts:
                print(f"\nTestando tamanho {width}x{height} com {num_workers} workers...")
                print(f"Iniciando {num_workers} workers...")
                
                # Inicia workers em processos separados
                worker_processes = []
                port = port_start
                
                for i in range(num_workers):
                    # Usa subprocess para iniciar workers
                    # Em produção, workers devem estar em máquinas diferentes
                    # Aqui simulamos com processos locais
                    proc = subprocess.Popen(
                        [sys.executable, 'distributed.py', 'worker', 'localhost', str(port)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    worker_processes.append(proc)
                
                # Aguarda workers iniciarem
                time.sleep(1)
                
                # Executa servidor
                execution_time = run_distributed_server(
                    width, height, iterations, num_workers, port, verbose=True
                )
                
                # Aguarda workers terminarem
                for proc in worker_processes:
                    proc.wait()
                
                self.results.append({
                    'version': 'distributed',
                    'width': width,
                    'height': height,
                    'iterations': iterations,
                    'threads': 1,
                    'workers': num_workers,
                    'execution_time': execution_time
                })
    
    def save_results(self, filename='benchmark_results.json'):
        """
        Salva resultados em arquivo JSON.
        
        Args:
            filename: Nome do arquivo de saída
        """
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResultados salvos em {filepath}")
    
    def save_csv(self, filename='benchmark_results.csv'):
        """
        Salva resultados em arquivo CSV.
        
        Args:
            filename: Nome do arquivo de saída
        """
        filepath = os.path.join(self.output_dir, filename)
        if not self.results:
            return
        
        fieldnames = ['version', 'width', 'height', 'iterations', 'threads', 'workers', 'execution_time']
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.results)
        print(f"Resultados CSV salvos em {filepath}")
    
    def generate_comparison_table(self):
        """Gera tabela comparativa dos resultados."""
        if not self.results:
            print("Nenhum resultado para exibir.")
            return
        
        print("\n" + "="*80)
        print("TABELA COMPARATIVA DE DESEMPENHO")
        print("="*80)
        print(f"{'Versão':<15} {'Tamanho':<15} {'Threads':<10} {'Workers':<10} {'Tempo (s)':<15}")
        print("-"*80)
        
        for result in self.results:
            size_str = f"{result['width']}x{result['height']}"
            print(f"{result['version']:<15} {size_str:<15} {result['threads']:<10} "
                  f"{result['workers']:<10} {result['execution_time']:<15.4f}")
    
    def plot_size_vs_time(self):
        """Gera gráfico de tempo vs tamanho do problema."""
        if not self.results:
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Agrupa por versão
        versions = ['sequential', 'parallel', 'distributed']
        colors = {'sequential': 'blue', 'parallel': 'green', 'distributed': 'red'}
        
        for version in versions:
            version_results = [r for r in self.results if r['version'] == version]
            if not version_results:
                continue
            
            # Usa o primeiro número de threads/workers para cada versão
            if version == 'parallel':
                version_results = [r for r in version_results if r['threads'] == max(set(r['threads'] for r in version_results))]
            elif version == 'distributed':
                version_results = [r for r in version_results if r['workers'] == max(set(r['workers'] for r in version_results))]
            
            sizes = [r['width'] * r['height'] for r in version_results]
            times = [r['execution_time'] for r in version_results]
            
            ax.plot(sizes, times, marker='o', label=version, color=colors[version])
        
        ax.set_xlabel('Tamanho do Problema (largura × altura)')
        ax.set_ylabel('Tempo de Execução (segundos)')
        ax.set_title('Desempenho vs Tamanho do Problema')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, 'size_vs_time.png')
        plt.savefig(filepath, dpi=300)
        print(f"Gráfico salvo em {filepath}")
        plt.close()
    
    def plot_threads_vs_speedup(self):
        """Gera gráfico de speedup vs número de threads."""
        parallel_results = [r for r in self.results if r['version'] == 'parallel']
        if not parallel_results:
            return
        
        # Agrupa por tamanho
        sizes = set((r['width'], r['height']) for r in parallel_results)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        for width, height in sizes:
            size_results = [r for r in parallel_results 
                          if r['width'] == width and r['height'] == height]
            size_results.sort(key=lambda x: x['threads'])
            
            # Calcula speedup relativo ao sequencial
            sequential_time = next(
                (r['execution_time'] for r in self.results 
                 if r['version'] == 'sequential' and r['width'] == width and r['height'] == height),
                None
            )
            
            if not sequential_time:
                continue
            
            threads = [r['threads'] for r in size_results]
            speedups = [sequential_time / r['execution_time'] for r in size_results]
            
            label = f"{width}x{height}"
            ax.plot(threads, speedups, marker='o', label=label)
        
        ax.set_xlabel('Número de Threads')
        ax.set_ylabel('Speedup')
        ax.set_title('Speedup vs Número de Threads (Paralelo)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, 'threads_vs_speedup.png')
        plt.savefig(filepath, dpi=300)
        print(f"Gráfico salvo em {filepath}")
        plt.close()
    
    def plot_workers_vs_speedup(self):
        """Gera gráfico de speedup vs número de workers."""
        distributed_results = [r for r in self.results if r['version'] == 'distributed']
        if not distributed_results:
            return
        
        # Agrupa por tamanho
        sizes = set((r['width'], r['height']) for r in distributed_results)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        for width, height in sizes:
            size_results = [r for r in distributed_results 
                          if r['width'] == width and r['height'] == height]
            size_results.sort(key=lambda x: x['workers'])
            
            # Calcula speedup relativo ao sequencial
            sequential_time = next(
                (r['execution_time'] for r in self.results 
                 if r['version'] == 'sequential' and r['width'] == width and r['height'] == height),
                None
            )
            
            if not sequential_time:
                continue
            
            workers = [r['workers'] for r in size_results]
            speedups = [sequential_time / r['execution_time'] for r in size_results]
            
            label = f"{width}x{height}"
            ax.plot(workers, speedups, marker='o', label=label)
        
        ax.set_xlabel('Número de Workers')
        ax.set_ylabel('Speedup')
        ax.set_title('Speedup vs Número de Workers (Distribuído)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, 'workers_vs_speedup.png')
        plt.savefig(filepath, dpi=300)
        print(f"Gráfico salvo em {filepath}")
        plt.close()


def get_system_info():
    """Coleta informações do sistema."""
    import platform
    import psutil
    
    info = {
        'OS': platform.system(),
        'OS Version': platform.version(),
        'CPU': platform.processor(),
        'CPU Cores': psutil.cpu_count(logical=False),
        'CPU Threads': psutil.cpu_count(logical=True),
        'Memory (GB)': round(psutil.virtual_memory().total / (1024**3), 2),
        'Python Version': platform.python_version()
    }
    
    return info


def main():
    parser = argparse.ArgumentParser(description='Benchmark de Difusão de Calor')
    parser.add_argument('--sizes', nargs='+', type=int, default=[100, 200, 500, 1000],
                       help='Tamanhos da grade (largura)')
    parser.add_argument('--iterations', type=int, default=1000,
                       help='Número de iterações')
    parser.add_argument('--threads', nargs='+', type=int, default=[1, 2, 4, 8],
                       help='Números de threads para teste paralelo')
    parser.add_argument('--workers', nargs='+', type=int, default=[1, 2, 4],
                       help='Números de workers para teste distribuído')
    parser.add_argument('--sequential', action='store_true',
                       help='Executar apenas benchmark sequencial')
    parser.add_argument('--parallel', action='store_true',
                       help='Executar apenas benchmark paralelo')
    parser.add_argument('--distributed', action='store_true',
                       help='Executar apenas benchmark distribuído')
    parser.add_argument('--output-dir', type=str, default='results',
                       help='Diretório para salvar resultados')
    
    args = parser.parse_args()
    
    # Se nenhuma versão específica foi escolhida, executa todas
    run_all = not (args.sequential or args.parallel or args.distributed)
    
    # Prepara tamanhos
    sizes = [(s, s) for s in args.sizes]
    
    # Coleta informações do sistema
    print("="*60)
    print("INFORMAÇÕES DO SISTEMA")
    print("="*60)
    system_info = get_system_info()
    for key, value in system_info.items():
        print(f"{key}: {value}")
    
    # Executa benchmarks
    runner = BenchmarkRunner(args.output_dir)
    
    if run_all or args.sequential:
        runner.run_sequential_benchmark(sizes, args.iterations)
    
    if run_all or args.parallel:
        runner.run_parallel_benchmark(sizes, args.iterations, args.threads)
    
    if run_all or args.distributed:
        runner.run_distributed_benchmark(sizes, args.iterations, args.workers)
    
    # Gera relatórios
    runner.generate_comparison_table()
    runner.save_results()
    runner.save_csv()
    runner.plot_size_vs_time()
    runner.plot_threads_vs_speedup()
    runner.plot_workers_vs_speedup()
    
    print("\n" + "="*60)
    print("BENCHMARK CONCLUÍDO")
    print("="*60)


if __name__ == "__main__":
    main()

