"""
Script de teste rápido para verificar se todas as implementações estão funcionando.

Este script executa testes básicos em todas as versões para garantir
que não há erros de implementação.
"""

import numpy as np
from sequential import HeatDiffusionSequential
from parallel import HeatDiffusionParallel


def test_sequential():
    """Testa a implementação sequencial."""
    print("Testando versão sequencial...")
    sim = HeatDiffusionSequential(50, 50)
    iterations = sim.simulate(100)
    avg_temp = sim.get_average_temp()
    print(f"  ✓ Sequencial: {iterations} iterações, temp média: {avg_temp:.4f}°C")
    return sim.get_grid()


def test_parallel():
    """Testa a implementação paralela."""
    print("Testando versão paralela...")
    sim = HeatDiffusionParallel(50, 50, num_threads=4)
    iterations = sim.simulate(100)
    avg_temp = sim.get_average_temp()
    print(f"  ✓ Paralela: {iterations} iterações, temp média: {avg_temp:.4f}°C")
    return sim.get_grid()


def compare_results(seq_grid, par_grid):
    """Compara resultados entre sequencial e paralelo."""
    print("\nComparando resultados sequencial vs paralelo...")
    diff = np.abs(seq_grid - par_grid)
    max_diff = np.max(diff)
    mean_diff = np.mean(diff)
    
    print(f"  Diferença máxima: {max_diff:.6f}°C")
    print(f"  Diferença média: {mean_diff:.6f}°C")
    
    if max_diff < 0.1:  # Tolerância razoável
        print("  ✓ Resultados são consistentes!")
        return True
    else:
        print("  ⚠ Diferenças significativas detectadas")
        return False


def main():
    print("="*60)
    print("TESTE RÁPIDO DAS IMPLEMENTAÇÕES")
    print("="*60)
    print()
    
    try:
        # Testa sequencial
        seq_grid = test_sequential()
        
        # Testa paralela
        par_grid = test_parallel()
        
        # Compara resultados
        consistent = compare_results(seq_grid, par_grid)
        
        print("\n" + "="*60)
        if consistent:
            print("✓ TODOS OS TESTES PASSARAM")
        else:
            print("⚠ ALGUNS TESTES FALHARAM - Verifique as implementações")
        print("="*60)
        
        print("\nNota: Para testar a versão distribuída, use:")
        print("  python run_distributed.py --width 50 --height 50 --iterations 100 --workers 2")
        
    except Exception as e:
        print(f"\n✗ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

