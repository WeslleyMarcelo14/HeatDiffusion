import json
import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def carregar_resultados(caminho_arquivo):
    with open(caminho_arquivo, 'r') as f:
        return json.load(f)


def calcular_speedup(resultados):
    tempos_sequenciais = {}
    for resultado in resultados:
        if resultado['versao'] == 'sequencial':
            chave = (resultado['largura'], resultado['altura'])
            tempos_sequenciais[chave] = resultado['tempo_execucao']
    
    for resultado in resultados:
        chave = (resultado['largura'], resultado['altura'])
        if chave in tempos_sequenciais:
            resultado['speedup'] = tempos_sequenciais[chave] / resultado['tempo_execucao']
        else:
            resultado['speedup'] = None
    
    return resultados


def calcular_eficiencia(resultados):
    for resultado in resultados:
        if resultado['speedup'] is not None:
            if resultado['versao'] == 'paralelo':
                recursos = resultado['threads']
            elif resultado['versao'] == 'distribuido':
                recursos = resultado['workers']
            else:
                recursos = 1
            
            resultado['eficiencia'] = resultado['speedup'] / recursos if recursos > 0 else 0
        else:
            resultado['eficiencia'] = None
    
    return resultados


def gerar_tabela_detalhada(resultados):
    df = pd.DataFrame(resultados)
    
    df = df[df['speedup'].notna()]
    
    print("\n" + "="*100)
    print("TABELA DETALHADA DE DESEMPENHO")
    print("="*100)
    print(f"{'Versão':<15} {'Tamanho':<15} {'Threads':<10} {'Workers':<15} "
          f"{'Tempo (s)':<15} {'Speedup':<12} {'Eficiência':<12}")
    print("-"*100)
    
    for _, linha in df.iterrows():
        tamanho_str = f"{int(linha['largura'])}x{int(linha['altura'])}"
        print(f"{linha['versao']:<15} {tamanho_str:<15} {int(linha['threads']):<10} "
              f"{int(linha['workers']):<15} {linha['tempo_execucao']:<15.4f} "
              f"{linha['speedup']:<12.4f} {linha['eficiencia']:<12.4f}")
    
    return df


def plotar_comparacao_eficiencia(df, diretorio_saida):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    df_paralelo = df[df['versao'] == 'paralelo']
    if not df_paralelo.empty:
        tamanhos = df_paralelo[['largura', 'altura']].drop_duplicates()
        for _, linha_tamanho in tamanhos.iterrows():
            dados_tamanho = df_paralelo[
                (df_paralelo['largura'] == linha_tamanho['largura']) & 
                (df_paralelo['altura'] == linha_tamanho['altura'])
            ]
            dados_tamanho = dados_tamanho.sort_values('threads')
            rotulo = f"{int(linha_tamanho['largura'])}x{int(linha_tamanho['altura'])}"
            ax1.plot(dados_tamanho['threads'], dados_tamanho['eficiencia'], 
                    marker='o', label=rotulo)
        
        ax1.set_xlabel('Número de Threads')
        ax1.set_ylabel('Eficiência')
        ax1.set_title('Eficiência vs Threads (Paralelo)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.axhline(y=1.0, color='r', linestyle='--', alpha=0.5, label='Eficiência Ideal')
    
    df_distribuido = df[df['versao'] == 'distribuido']
    if not df_distribuido.empty:
        tamanhos = df_distribuido[['largura', 'altura']].drop_duplicates()
        for _, linha_tamanho in tamanhos.iterrows():
            dados_tamanho = df_distribuido[
                (df_distribuido['largura'] == linha_tamanho['largura']) & 
                (df_distribuido['altura'] == linha_tamanho['altura'])
            ]
            dados_tamanho = dados_tamanho.sort_values('workers')
            rotulo = f"{int(linha_tamanho['largura'])}x{int(linha_tamanho['altura'])}"
            ax2.plot(dados_tamanho['workers'], dados_tamanho['eficiencia'], 
                    marker='o', label=rotulo)
        
        ax2.set_xlabel('Número de Workers')
        ax2.set_ylabel('Eficiência')
        ax2.set_title('Eficiência vs Workers (Distribuído)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.axhline(y=1.0, color='r', linestyle='--', alpha=0.5, label='Eficiência Ideal')
    
    plt.tight_layout()
    caminho_arquivo = os.path.join(diretorio_saida, 'comparacao_eficiencia.png')
    plt.savefig(caminho_arquivo, dpi=300)
    print(f"\nGráfico de eficiência salvo em {caminho_arquivo}")
    plt.close()


def plotar_escalabilidade(df, diretorio_saida):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    versoes = ['paralelo', 'distribuido']
    cores = {'paralelo': 'green', 'distribuido': 'red'}
    
    for versao in versoes:
        df_versao = df[df['versao'] == versao]
        if df_versao.empty:
            continue
        
        tamanho_maximo = df_versao[['largura', 'altura']].apply(lambda x: x['largura'] * x['altura'], axis=1).max()
        df_tamanho_maximo = df_versao[df_versao.apply(lambda x: x['largura'] * x['altura'] == tamanho_maximo, axis=1)]
        
        if versao == 'paralelo':
            recursos = df_tamanho_maximo['threads'].values
        else:
            recursos = df_tamanho_maximo['workers'].values
        
        speedups = df_tamanho_maximo['speedup'].values
        
        ax.plot(recursos, speedups, marker='o', label=versao, color=cores[versao])
    
    if not df.empty:
        max_recursos = max(
            df[df['versao'] == 'paralelo']['threads'].max() if not df[df['versao'] == 'paralelo'].empty else 0,
            df[df['versao'] == 'distribuido']['workers'].max() if not df[df['versao'] == 'distribuido'].empty else 0
        )
        ideal = np.arange(1, max_recursos + 1)
        ax.plot(ideal, ideal, 'k--', alpha=0.5, label='Ideal (Linear)')
    
    ax.set_xlabel('Número de Recursos (Threads/Workers)')
    ax.set_ylabel('Speedup')
    ax.set_title('Escalabilidade')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    caminho_arquivo = os.path.join(diretorio_saida, 'escalabilidade.png')
    plt.savefig(caminho_arquivo, dpi=300)
    print(f"Gráfico de escalabilidade salvo em {caminho_arquivo}")
    plt.close()


def gerar_estatisticas(df):
    print("\n" + "="*60)
    print("ESTATÍSTICAS RESUMIDAS")
    print("="*60)
    
    for versao in ['sequencial', 'paralelo', 'distribuido']:
        df_versao = df[df['versao'] == versao]
        if df_versao.empty:
            continue
        
        print(f"\n{versao.upper()}:")
        print(f"  Tempo médio: {df_versao['tempo_execucao'].mean():.4f} s")
        print(f"  Tempo mínimo: {df_versao['tempo_execucao'].min():.4f} s")
        print(f"  Tempo máximo: {df_versao['tempo_execucao'].max():.4f} s")
        
        if versao != 'sequencial':
            print(f"  Speedup médio: {df_versao['speedup'].mean():.4f}")
            print(f"  Speedup máximo: {df_versao['speedup'].max():.4f}")
            print(f"  Eficiência média: {df_versao['eficiencia'].mean():.4f}")
            print(f"  Eficiência máxima: {df_versao['eficiencia'].max():.4f}")


def main():
    parser = argparse.ArgumentParser(description='Analisar resultados do benchmark')
    parser.add_argument('--input', type=str, default='resultados/resultados_benchmark.json',
                       help='Arquivo de resultados JSON')
    parser.add_argument('--output-dir', type=str, default='resultados',
                       help='Diretório para salvar gráficos')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Erro: Arquivo {args.input} não encontrado.")
        print("Execute primeiro: python teste_desempenho.py")
        return
    
    print(f"Carregando resultados de {args.input}...")
    resultados = carregar_resultados(args.input)
    
    print("Calculando métricas...")
    resultados = calcular_speedup(resultados)
    resultados = calcular_eficiencia(resultados)
    
    df = gerar_tabela_detalhada(resultados)
    gerar_estatisticas(df)
    
    print("\nGerando gráficos...")
    plotar_comparacao_eficiencia(df, args.output_dir)
    plotar_escalabilidade(df, args.output_dir)
    
    arquivo_saida = os.path.join(args.output_dir, 'resultados_benchmark_analisados.json')
    with open(arquivo_saida, 'w') as f:
        json.dump(resultados, f, indent=2)
    print(f"\nResultados analisados salvos em {arquivo_saida}")
    
    print("\n" + "="*60)
    print("ANÁLISE CONCLUÍDA")
    print("="*60)


if __name__ == "__main__":
    main()

