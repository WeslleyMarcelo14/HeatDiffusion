"""
Script para análise detalhada dos resultados do benchmark.

Gera análises estatísticas e visualizações adicionais.
"""

import json
import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def load_results(filepath):
    """Carrega resultados do arquivo JSON."""
    with open(filepath, 'r') as f:
        return json.load(f)


def calculate_speedup(results):
    """Calcula speedup para cada resultado relativo ao sequencial."""
    # Encontra tempos sequenciais por tamanho
    sequential_times = {}
    for result in results:
        if result['version'] == 'sequential':
            key = (result['width'], result['height'])
            sequential_times[key] = result['execution_time']
    
    # Calcula speedup
    for result in results:
        key = (result['width'], result['height'])
        if key in sequential_times:
            result['speedup'] = sequential_times[key] / result['execution_time']
        else:
            result['speedup'] = None
    
    return results


def calculate_efficiency(results):
    """Calcula eficiência (speedup / número de recursos)."""
    for result in results:
        if result['speedup'] is not None:
            if result['version'] == 'parallel':
                resources = result['threads']
            elif result['version'] == 'distributed':
                resources = result['workers']
            else:
                resources = 1
            
            result['efficiency'] = result['speedup'] / resources if resources > 0 else 0
        else:
            result['efficiency'] = None
    
    return results


def generate_detailed_table(results):
    """Gera tabela detalhada com speedup e eficiência."""
    df = pd.DataFrame(results)
    
    # Filtra resultados sem speedup
    df = df[df['speedup'].notna()]
    
    print("\n" + "="*100)
    print("TABELA DETALHADA DE DESEMPENHO")
    print("="*100)
    print(f"{'Versão':<15} {'Tamanho':<15} {'Threads':<10} {'Workers':<10} "
          f"{'Tempo (s)':<15} {'Speedup':<12} {'Eficiência':<12}")
    print("-"*100)
    
    for _, row in df.iterrows():
        size_str = f"{int(row['width'])}x{int(row['height'])}"
        print(f"{row['version']:<15} {size_str:<15} {int(row['threads']):<10} "
              f"{int(row['workers']):<10} {row['execution_time']:<15.4f} "
              f"{row['speedup']:<12.4f} {row['efficiency']:<12.4f}")
    
    return df


def plot_efficiency_comparison(df, output_dir):
    """Gera gráfico comparando eficiência entre versões."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Eficiência vs Threads (Paralelo)
    parallel_df = df[df['version'] == 'parallel']
    if not parallel_df.empty:
        sizes = parallel_df[['width', 'height']].drop_duplicates()
        for _, size_row in sizes.iterrows():
            size_data = parallel_df[
                (parallel_df['width'] == size_row['width']) & 
                (parallel_df['height'] == size_row['height'])
            ]
            size_data = size_data.sort_values('threads')
            label = f"{int(size_row['width'])}x{int(size_row['height'])}"
            ax1.plot(size_data['threads'], size_data['efficiency'], 
                    marker='o', label=label)
        
        ax1.set_xlabel('Número de Threads')
        ax1.set_ylabel('Eficiência')
        ax1.set_title('Eficiência vs Threads (Paralelo)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.axhline(y=1.0, color='r', linestyle='--', alpha=0.5, label='Eficiência Ideal')
    
    # Eficiência vs Workers (Distribuído)
    distributed_df = df[df['version'] == 'distributed']
    if not distributed_df.empty:
        sizes = distributed_df[['width', 'height']].drop_duplicates()
        for _, size_row in sizes.iterrows():
            size_data = distributed_df[
                (distributed_df['width'] == size_row['width']) & 
                (distributed_df['height'] == size_row['height'])
            ]
            size_data = size_data.sort_values('workers')
            label = f"{int(size_row['width'])}x{int(size_row['height'])}"
            ax2.plot(size_data['workers'], size_data['efficiency'], 
                    marker='o', label=label)
        
        ax2.set_xlabel('Número de Workers')
        ax2.set_ylabel('Eficiência')
        ax2.set_title('Eficiência vs Workers (Distribuído)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.axhline(y=1.0, color='r', linestyle='--', alpha=0.5, label='Eficiência Ideal')
    
    plt.tight_layout()
    filepath = os.path.join(output_dir, 'efficiency_comparison.png')
    plt.savefig(filepath, dpi=300)
    print(f"\nGráfico de eficiência salvo em {filepath}")
    plt.close()


def plot_scalability(df, output_dir):
    """Gera gráfico de escalabilidade."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Agrupa por versão e tamanho
    versions = ['parallel', 'distributed']
    colors = {'parallel': 'green', 'distributed': 'red'}
    
    for version in versions:
        version_df = df[df['version'] == version]
        if version_df.empty:
            continue
        
        # Pega o maior tamanho para análise de escalabilidade
        max_size = version_df[['width', 'height']].apply(lambda x: x['width'] * x['height'], axis=1).max()
        max_size_df = version_df[version_df.apply(lambda x: x['width'] * x['height'] == max_size, axis=1)]
        
        if version == 'parallel':
            resources = max_size_df['threads'].values
        else:
            resources = max_size_df['workers'].values
        
        speedups = max_size_df['speedup'].values
        
        ax.plot(resources, speedups, marker='o', label=version, color=colors[version])
    
    # Linha ideal (speedup linear)
    if not df.empty:
        max_resources = max(
            df[df['version'] == 'parallel']['threads'].max() if not df[df['version'] == 'parallel'].empty else 0,
            df[df['version'] == 'distributed']['workers'].max() if not df[df['version'] == 'distributed'].empty else 0
        )
        ideal = np.arange(1, max_resources + 1)
        ax.plot(ideal, ideal, 'k--', alpha=0.5, label='Ideal (Linear)')
    
    ax.set_xlabel('Número de Recursos (Threads/Workers)')
    ax.set_ylabel('Speedup')
    ax.set_title('Escalabilidade')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    filepath = os.path.join(output_dir, 'scalability.png')
    plt.savefig(filepath, dpi=300)
    print(f"Gráfico de escalabilidade salvo em {filepath}")
    plt.close()


def generate_statistics(df):
    """Gera estatísticas resumidas."""
    print("\n" + "="*60)
    print("ESTATÍSTICAS RESUMIDAS")
    print("="*60)
    
    for version in ['sequential', 'parallel', 'distributed']:
        version_df = df[df['version'] == version]
        if version_df.empty:
            continue
        
        print(f"\n{version.upper()}:")
        print(f"  Tempo médio: {version_df['execution_time'].mean():.4f} s")
        print(f"  Tempo mínimo: {version_df['execution_time'].min():.4f} s")
        print(f"  Tempo máximo: {version_df['execution_time'].max():.4f} s")
        
        if version != 'sequential':
            print(f"  Speedup médio: {version_df['speedup'].mean():.4f}")
            print(f"  Speedup máximo: {version_df['speedup'].max():.4f}")
            print(f"  Eficiência média: {version_df['efficiency'].mean():.4f}")
            print(f"  Eficiência máxima: {version_df['efficiency'].max():.4f}")


def main():
    parser = argparse.ArgumentParser(description='Analisar resultados do benchmark')
    parser.add_argument('--input', type=str, default='results/benchmark_results.json',
                       help='Arquivo de resultados JSON')
    parser.add_argument('--output-dir', type=str, default='results',
                       help='Diretório para salvar gráficos')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Erro: Arquivo {args.input} não encontrado.")
        print("Execute primeiro: python benchmark.py")
        return
    
    # Carrega resultados
    print(f"Carregando resultados de {args.input}...")
    results = load_results(args.input)
    
    # Calcula métricas
    print("Calculando métricas...")
    results = calculate_speedup(results)
    results = calculate_efficiency(results)
    
    # Gera análises
    df = generate_detailed_table(results)
    generate_statistics(df)
    
    # Gera gráficos
    print("\nGerando gráficos...")
    plot_efficiency_comparison(df, args.output_dir)
    plot_scalability(df, args.output_dir)
    
    # Salva resultados atualizados
    output_file = os.path.join(args.output_dir, 'benchmark_results_analyzed.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResultados analisados salvos em {output_file}")
    
    print("\n" + "="*60)
    print("ANÁLISE CONCLUÍDA")
    print("="*60)


if __name__ == "__main__":
    main()

