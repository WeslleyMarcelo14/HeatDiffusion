import numpy as np
from sequencial import DifusaoCalorSequencial
from paralelo import DifusaoCalorParalela


def testar_sequencial():
    print("Testando versão sequencial...")
    sim = DifusaoCalorSequencial(50, 50)
    iteracoes = sim.simular(100)
    temp_media = sim.obter_temp_media()
    print(f"  ✓ Sequencial: {iteracoes} iterações, temp média: {temp_media:.4f}°C")
    return sim.obter_grade()


def testar_paralelo():
    print("Testando versão paralela...")
    sim = DifusaoCalorParalela(50, 50, num_threads=4)
    iteracoes = sim.simular(100)
    temp_media = sim.obter_temp_media()
    print(f"  ✓ Paralela: {iteracoes} iterações, temp média: {temp_media:.4f}°C")
    return sim.obter_grade()


def comparar_resultados(grade_seq, grade_par):
    print("\nComparando resultados sequencial vs paralelo...")
    dif = np.abs(grade_seq - grade_par)
    dif_maxima = np.max(dif)
    dif_media = np.mean(dif)
    
    print(f"  Diferença máxima: {dif_maxima:.6f}°C")
    print(f"  Diferença média: {dif_media:.6f}°C")
    
    if dif_maxima < 0.1:
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
        grade_seq = testar_sequencial()
        
        grade_par = testar_paralelo()
        
        consistente = comparar_resultados(grade_seq, grade_par)
        
        print("\n" + "="*60)
        if consistente:
            print("✓ TODOS OS TESTES PASSARAM")
        else:
            print("⚠ ALGUNS TESTES FALHARAM - Verifique as implementações")
        print("="*60)
        
        print("\nNota: Para testar a versão distribuída, use:")
        print("  python executar_distribuido.py --width 50 --height 50 --iterations 100 --workers 2")
        
    except Exception as e:
        print(f"\n✗ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

