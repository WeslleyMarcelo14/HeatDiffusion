"""
Script auxiliar para executar simulação distribuída facilmente.

Este script facilita a execução da versão distribuída iniciando
automaticamente os workers e o servidor.
"""

import subprocess
import sys
import time
import argparse
from distributed import run_distributed_server


def main():
    parser = argparse.ArgumentParser(description='Executar simulação distribuída')
    parser.add_argument('--width', type=int, default=500, help='Largura da grade')
    parser.add_argument('--height', type=int, default=500, help='Altura da grade')
    parser.add_argument('--iterations', type=int, default=1000, help='Número de iterações')
    parser.add_argument('--workers', type=int, default=4, help='Número de workers')
    parser.add_argument('--port', type=int, default=8888, help='Porta do servidor')
    parser.add_argument('--host', type=str, default='localhost', help='Host do servidor')
    
    args = parser.parse_args()
    
    print("="*60)
    print("SIMULAÇÃO DISTRIBUÍDA DE DIFUSÃO DE CALOR")
    print("="*60)
    print(f"Tamanho: {args.width}x{args.height}")
    print(f"Iterações: {args.iterations}")
    print(f"Workers: {args.workers}")
    print(f"Host: {args.host}")
    print(f"Porta: {args.port}")
    print("="*60)
    
    # Inicia workers em processos separados
    print(f"\nIniciando {args.workers} workers...")
    worker_processes = []
    
    for i in range(args.workers):
        proc = subprocess.Popen(
            [sys.executable, 'distributed.py', 'worker', args.host, str(args.port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        worker_processes.append(proc)
        print(f"  Worker {i+1} iniciado (PID: {proc.pid})")
    
    # Aguarda workers iniciarem
    print("\nAguardando workers se conectarem...")
    time.sleep(2)
    
    try:
        # Executa servidor
        print("\nIniciando servidor mestre...\n")
        execution_time = run_distributed_server(
            args.width, args.height, args.iterations, 
            args.workers, args.port, verbose=True
        )
        
        print(f"\n{'='*60}")
        print(f"Simulação concluída em {execution_time:.4f} segundos")
        print(f"{'='*60}")
        
    finally:
        # Aguarda workers terminarem
        print("\nFinalizando workers...")
        for i, proc in enumerate(worker_processes):
            proc.wait()
            print(f"  Worker {i+1} finalizado")


if __name__ == "__main__":
    main()

