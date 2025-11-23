import subprocess
import sys
import time
import argparse
from distribuido import executar_servidor_distribuido


def main():
    parser = argparse.ArgumentParser(description='Executar simulação distribuída')
    parser.add_argument('--width', type=int, default=500, help='Largura da grade')
    parser.add_argument('--height', type=int, default=500, help='Altura da grade')
    parser.add_argument('--iterations', type=int, default=1000, help='Número de iterações')
    parser.add_argument('--workers', type=int, default=4, help='Número de trabalhadores')
    parser.add_argument('--port', type=int, default=8888, help='Porta do servidor')
    parser.add_argument('--host', type=str, default='localhost', help='Host do servidor')
    
    args = parser.parse_args()
    
    print("="*60)
    print("SIMULAÇÃO DISTRIBUÍDA DE DIFUSÃO DE CALOR")
    print("="*60)
    print(f"Tamanho: {args.width}x{args.height}")
    print(f"Iterações: {args.iterations}")
    print(f"Trabalhadores: {args.workers}")
    print(f"Host: {args.host}")
    print(f"Porta: {args.port}")
    print("="*60)
    
    print(f"\nIniciando {args.workers} trabalhadores...")
    processos_trabalhadores = []
    
    for i in range(args.workers):
        proc = subprocess.Popen(
            [sys.executable, 'distribuido.py', 'worker', args.host, str(args.port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processos_trabalhadores.append(proc)
        print(f"  Trabalhador {i+1} iniciado (PID: {proc.pid})")
    
    print("\nAguardando trabalhadores se conectarem...")
    time.sleep(2)
    
    try:
        print("\nIniciando servidor mestre...\n")
        tempo_execucao = executar_servidor_distribuido(
            args.width, args.height, args.iterations, 
            args.workers, args.port, detalhado=True
        )
        
        print(f"\n{'='*60}")
        print(f"Simulação concluída em {tempo_execucao:.4f} segundos")
        print(f"{'='*60}")
        
    finally:
        print("\nFinalizando trabalhadores...")
        for i, proc in enumerate(processos_trabalhadores):
            proc.wait()
            print(f"  Trabalhador {i+1} finalizado")


if __name__ == "__main__":
    main()

