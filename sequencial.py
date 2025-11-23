import numpy as np
import time


class DifusaoCalorSequencial:
    
    def __init__(self, largura, altura, temp_inicial=0.0, temp_borda=100.0):
        self.largura = largura
        self.altura = altura
        self.temp_inicial = temp_inicial
        self.temp_borda = temp_borda
        
        self.grade = np.full((altura, largura), temp_inicial, dtype=np.float64)
        
        self.grade[0, :] = temp_borda
        self.grade[-1, :] = temp_borda
        self.grade[:, 0] = temp_borda
        self.grade[:, -1] = temp_borda
        
        self.nova_grade = self.grade.copy()
    
    def atualizar(self):
        self.nova_grade[1:-1, 1:-1] = 0.25 * (
            self.grade[0:-2, 1:-1] +
            self.grade[2:, 1:-1] +
            self.grade[1:-1, 0:-2] +
            self.grade[1:-1, 2:]
        )
        
        self.grade, self.nova_grade = self.nova_grade, self.grade
    
    def simular(self, iteracoes, limite_convergencia=1e-6):
        for iteracao in range(iteracoes):
            grade_antiga = self.grade.copy()
            self.atualizar()
            
            dif_maxima = np.max(np.abs(self.grade - grade_antiga))
            if dif_maxima < limite_convergencia:
                return iteracao + 1
        
        return iteracoes
    
    def obter_grade(self):
        return self.grade.copy()
    
    def obter_temp_media(self):
        return np.mean(self.grade[1:-1, 1:-1])


def executar_simulacao_sequencial(largura, altura, iteracoes, detalhado=True):
    tempo_inicio = time.time()
    
    simulacao = DifusaoCalorSequencial(largura, altura)
    iteracoes_reais = simulacao.simular(iteracoes)
    
    tempo_fim = time.time()
    tempo_execucao = tempo_fim - tempo_inicio
    
    if detalhado:
        print(f"Simulação Sequencial:")
        print(f"  Tamanho: {largura}x{altura}")
        print(f"  Iterações: {iteracoes_reais}")
        print(f"  Tempo de execução: {tempo_execucao:.4f} segundos")
        print(f"  Temperatura média: {simulacao.obter_temp_media():.4f}°C")
    
    return tempo_execucao


if __name__ == "__main__":
    print("=== Simulação Sequencial de Difusão de Calor ===\n")
    
    tamanhos = [(100, 100), (200, 200), (500, 500)]
    iteracoes = 1000
    
    for largura, altura in tamanhos:
        executar_simulacao_sequencial(largura, altura, iteracoes)
        print()

