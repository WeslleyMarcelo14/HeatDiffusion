import argparse
import time
import json
import csv
from typing import List, Dict, Tuple
import matplotlib.pyplot as plt
import numpy as np

from benchmark import executar_simulacao_sequencial
from benchmark import executar_simulacao_paralela
from benchmark import executar_servidor_distribuido, executar_trabalhador_distribuido
import subprocess
import sys
import os


class ExecutorBenchmark:
    
    def __init__(self, diretorio_saida='resultados'):
        self.diretorio_saida = diretorio_saida
        os.makedirs(diretorio_saida, exist_ok=True)
        self.resultados = []
    
    def executar_benchmark_sequencial(self, tamanhos: List[Tuple[int, int]], iteracoes: int):
        print("\n" + "="*60)
        print("BENCHMARK SEQUENCIAL")
        print("="*60)
        
        for largura, altura in tamanhos:
            print(f"\nTestando tamanho {largura}x{altura}...")
            tempo_execucao = executar_simulacao_sequencial(largura, altura, iteracoes, detalhado=True)
            
            self.resultados.append({
                'versao': 'sequencial',
                'largura': largura,
                'altura': altura,
                'iteracoes': iteracoes,
                'threads': 1,
                'trabalhadores': 1,
                'tempo_execucao': tempo_execucao
            })
    
    def executar_benchmark_paralelo(self, tamanhos: List[Tuple[int, int]], iteracoes: int, 
                               contagens_threads: List[int]):
        print("\n" + "="*60)
        print("BENCHMARK PARALELO")
        print("="*60)
        
        for largura, altura in tamanhos:
            for num_threads in contagens_threads:
                print(f"\nTestando tamanho {largura}x{altura} com {num_threads} threads...")
                tempo_execucao = executar_simulacao_paralela(
                    largura, altura, iteracoes, num_threads, detalhado=True
                )
                
                self.resultados.append({
                    'versao': 'paralelo',
                    'largura': largura,
                    'altura': altura,
                    'iteracoes': iteracoes,
                    'threads': num_threads,
                    'trabalhadores': 1,
                    'tempo_execucao': tempo_execucao
                })
    
    def executar_benchmark_distribuido(self, tamanhos: List[Tuple[int, int]], iteracoes: int,
                                  contagens_trabalhadores: List[int], porta_inicial=8888):
        print("\n" + "="*60)
        print("BENCHMARK DISTRIBUÍDO")
        print("="*60)
        
        for largura, altura in tamanhos:
            for num_trabalhadores in contagens_trabalhadores:
                print(f"\nTestando tamanho {largura}x{altura} com {num_trabalhadores} trabalhadores...")
                print(f"Iniciando {num_trabalhadores} trabalhadores...")
                
                processos_trabalhadores = []
                porta = porta_inicial
                
                for i in range(num_trabalhadores):
                    proc = subprocess.Popen(
                        [sys.executable, 'distribuido.py', 'worker', 'localhost', str(porta)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    processos_trabalhadores.append(proc)
                
                time.sleep(1)
                
                tempo_execucao = executar_servidor_distribuido(
                    largura, altura, iteracoes, num_trabalhadores, porta, detalhado=True
                )
                
                for proc in processos_trabalhadores:
                    proc.wait()
                
                self.resultados.append({
                    'versao': 'distribuido',
                    'largura': largura,
                    'altura': altura,
                    'iteracoes': iteracoes,
                    'threads': 1,
                    'trabalhadores': num_trabalhadores,
                    'tempo_execucao': tempo_execucao
                })
    
    def salvar_resultados(self, nome_arquivo='resultados_benchmark.json'):
        caminho_arquivo = os.path.join(self.diretorio_saida, nome_arquivo)
        with open(caminho_arquivo, 'w') as f:
            json.dump(self.resultados, f, indent=2)
        print(f"\nResultados salvos em {caminho_arquivo}")
    
    def salvar_csv(self, nome_arquivo='resultados_benchmark.csv'):
        caminho_arquivo = os.path.join(self.diretorio_saida, nome_arquivo)
        if not self.resultados:
            return
        
        nomes_campos = ['versao', 'largura', 'altura', 'iteracoes', 'threads', 'trabalhadores', 'tempo_execucao']
        with open(caminho_arquivo, 'w', newline='') as f:
            escritor = csv.DictWriter(f, fieldnames=nomes_campos)
            escritor.writeheader()
            escritor.writerows(self.resultados)
        print(f"Resultados CSV salvos em {caminho_arquivo}")
    
    def gerar_tabela_comparativa(self):
        if not self.resultados:
            print("Nenhum resultado para exibir.")
            return
        
        print("\n" + "="*80)
        print("TABELA COMPARATIVA DE DESEMPENHO")
        print("="*80)
        print(f"{'Versão':<15} {'Tamanho':<15} {'Threads':<10} {'Trabalhadores':<15} {'Tempo (s)':<15}")
        print("-"*80)
        
        for resultado in self.resultados:
            tamanho_str = f"{resultado['largura']}x{resultado['altura']}"
            print(f"{resultado['versao']:<15} {tamanho_str:<15} {resultado['threads']:<10} "
                  f"{resultado['trabalhadores']:<15} {resultado['tempo_execucao']:<15.4f}")
    
    def plotar_tamanho_vs_tempo(self):
        if not self.resultados:
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        versoes = ['sequencial', 'paralelo', 'distribuido']
        cores = {'sequencial': 'blue', 'paralelo': 'green', 'distribuido': 'red'}
        
        for versao in versoes:
            resultados_versao = [r for r in self.resultados if r['versao'] == versao]
            if not resultados_versao:
                continue
            
            if versao == 'paralelo':
                resultados_versao = [r for r in resultados_versao if r['threads'] == max(set(r['threads'] for r in resultados_versao))]
            elif versao == 'distribuido':
                resultados_versao = [r for r in resultados_versao if r['trabalhadores'] == max(set(r['trabalhadores'] for r in resultados_versao))]
            
            tamanhos = [r['largura'] * r['altura'] for r in resultados_versao]
            tempos = [r['tempo_execucao'] for r in resultados_versao]
            
            ax.plot(tamanhos, tempos, marker='o', label=versao, color=cores[versao])
        
        ax.set_xlabel('Tamanho do Problema (largura × altura)')
        ax.set_ylabel('Tempo de Execução (segundos)')
        ax.set_title('Desempenho vs Tamanho do Problema')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        caminho_arquivo = os.path.join(self.diretorio_saida, 'tamanho_vs_tempo.png')
        plt.savefig(caminho_arquivo, dpi=300)
        print(f"Gráfico salvo em {caminho_arquivo}")
        plt.close()
    
    def plotar_threads_vs_speedup(self):
        resultados_paralelos = [r for r in self.resultados if r['versao'] == 'paralelo']
        if not resultados_paralelos:
            return
        
        tamanhos = set((r['largura'], r['altura']) for r in resultados_paralelos)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        for largura, altura in tamanhos:
            resultados_tamanho = [r for r in resultados_paralelos 
                          if r['largura'] == largura and r['altura'] == altura]
            resultados_tamanho.sort(key=lambda x: x['threads'])
            
            tempo_sequencial = next(
                (r['tempo_execucao'] for r in self.resultados 
                 if r['versao'] == 'sequencial' and r['largura'] == largura and r['altura'] == altura),
                None
            )
            
            if not tempo_sequencial:
                continue
            
            threads = [r['threads'] for r in resultados_tamanho]
            speedups = [tempo_sequencial / r['tempo_execucao'] for r in resultados_tamanho]
            
            rotulo = f"{largura}x{altura}"
            ax.plot(threads, speedups, marker='o', label=rotulo)
        
        ax.set_xlabel('Número de Threads')
        ax.set_ylabel('Speedup')
        ax.set_title('Speedup vs Número de Threads (Paralelo)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        caminho_arquivo = os.path.join(self.diretorio_saida, 'threads_vs_speedup.png')
        plt.savefig(caminho_arquivo, dpi=300)
        print(f"Gráfico salvo em {caminho_arquivo}")
        plt.close()
    
    def plotar_trabalhadores_vs_speedup(self):
        resultados_distribuidos = [r for r in self.resultados if r['versao'] == 'distribuido']
        if not resultados_distribuidos:
            return
        
        tamanhos = set((r['largura'], r['altura']) for r in resultados_distribuidos)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        for largura, altura in tamanhos:
            resultados_tamanho = [r for r in resultados_distribuidos 
                          if r['largura'] == largura and r['altura'] == altura]
            resultados_tamanho.sort(key=lambda x: x['trabalhadores'])
            
            tempo_sequencial = next(
                (r['tempo_execucao'] for r in self.resultados 
                 if r['versao'] == 'sequencial' and r['largura'] == largura and r['altura'] == altura),
                None
            )
            
            if not tempo_sequencial:
                continue
            
            trabalhadores = [r['trabalhadores'] for r in resultados_tamanho]
            speedups = [tempo_sequencial / r['tempo_execucao'] for r in resultados_tamanho]
            
            rotulo = f"{largura}x{altura}"
            ax.plot(trabalhadores, speedups, marker='o', label=rotulo)
        
        ax.set_xlabel('Número de Trabalhadores')
        ax.set_ylabel('Speedup')
        ax.set_title('Speedup vs Número de Trabalhadores (Distribuído)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        caminho_arquivo = os.path.join(self.diretorio_saida, 'trabalhadores_vs_speedup.png')
        plt.savefig(caminho_arquivo, dpi=300)
        print(f"Gráfico salvo em {caminho_arquivo}")
        plt.close()


def obter_info_sistema():
    import platform
    import psutil
    
    info = {
        'SO': platform.system(),
        'Versao SO': platform.version(),
        'CPU': platform.processor(),
        'Nucleos CPU': psutil.cpu_count(logical=False),
        'Threads CPU': psutil.cpu_count(logical=True),
        'Memoria (GB)': round(psutil.virtual_memory().total / (1024**3), 2),
        'Versao Python': platform.python_version()
    }
    
    return info


def main():
    parser = argparse.ArgumentParser(description='Benchmark de Difusão de Calor')
    parser.add_argument('--sizes', nargs='+', type=int, default=[100, 200, 500],
                       help='Tamanhos da grade (largura)')
    parser.add_argument('--iterations', type=int, default=1000,
                       help='Número de iterações')
    parser.add_argument('--threads', nargs='+', type=int, default=[1, 2, 4, 8],
                       help='Números de threads para teste paralelo')
    parser.add_argument('--workers', nargs='+', type=int, default=[1, 2, 4],
                       help='Números de trabalhadores para teste distribuído')
    parser.add_argument('--sequential', action='store_true',
                       help='Executar apenas benchmark sequencial')
    parser.add_argument('--parallel', action='store_true',
                       help='Executar apenas benchmark paralelo')
    parser.add_argument('--distributed', action='store_true',
                       help='Executar apenas benchmark distribuído')
    parser.add_argument('--output-dir', type=str, default='resultados',
                       help='Diretório para salvar resultados')
    
    args = parser.parse_args()
    
    executar_todos = not (args.sequential or args.parallel or args.distributed)
    
    tamanhos = [(s, s) for s in args.sizes]
    
    print("="*60)
    print("INFORMAÇÕES DO SISTEMA")
    print("="*60)
    info_sistema = obter_info_sistema()
    for chave, valor in info_sistema.items():
        print(f"{chave}: {valor}")
    
    executor = ExecutorBenchmark(args.output_dir)
    
    if executar_todos or args.sequential:
        executor.executar_benchmark_sequencial(tamanhos, args.iterations)
    
    if executar_todos or args.parallel:
        executor.executar_benchmark_paralelo(tamanhos, args.iterations, args.threads)
    
    if executar_todos or args.distributed:
        executor.executar_benchmark_distribuido(tamanhos, args.iterations, args.workers)
    
    executor.gerar_tabela_comparativa()
    executor.salvar_resultados()
    executor.salvar_csv()
    executor.plotar_tamanho_vs_tempo()
    executor.plotar_threads_vs_speedup()
    executor.plotar_trabalhadores_vs_speedup()
    
    print("\n" + "="*60)
    print("BENCHMARK CONCLUÍDO")
    print("="*60)


if __name__ == "__main__":
    main()

