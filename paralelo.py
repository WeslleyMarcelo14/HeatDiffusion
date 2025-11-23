import threading
import time
from typing import List

import numpy as np


class DifusaoCalorParalela:

    def __init__(self, largura, altura, num_threads, temp_inicial=0.0, temp_borda=100.0):
        self.largura = largura
        self.altura = altura
        linhas_uteis = max(1, altura - 2)
        self.num_threads = max(1, min(num_threads, linhas_uteis))
        self.temp_inicial = temp_inicial
        self.temp_borda = temp_borda

        self.grade = np.full((altura, largura), temp_inicial, dtype=np.float64)

        self.grade[0, :] = temp_borda
        self.grade[-1, :] = temp_borda
        self.grade[:, 0] = temp_borda
        self.grade[:, -1] = temp_borda

        self.nova_grade = self.grade.copy()

        self.barreira_inicio = threading.Barrier(self.num_threads + 1)
        self.barreira_fim = threading.Barrier(self.num_threads + 1)
        self.evento_parada = threading.Event()
        self.difs_max_locais = [0.0] * self.num_threads

        self.faixas_threads = self._calcular_faixas_threads()

        self.threads: List[threading.Thread] = []
        self._iniciar_trabalhadores()

    def _calcular_faixas_threads(self):
        linhas_uteis = max(1, self.altura - 2)
        linhas_por_thread = linhas_uteis // self.num_threads
        resto = linhas_uteis % self.num_threads

        faixas = []
        inicio = 1

        for i in range(self.num_threads):
            linhas = linhas_por_thread + (1 if i < resto else 0)
            fim = min(self.altura - 1, inicio + linhas)
            faixas.append((inicio, fim))
            inicio = fim

        return faixas

    def _iniciar_trabalhadores(self):
        for id_thread, (linha_inicio, linha_fim) in enumerate(self.faixas_threads):
            thread = threading.Thread(
                target=self._loop_trabalhador,
                args=(id_thread, linha_inicio, linha_fim),
                daemon=True,
            )
            self.threads.append(thread)
            thread.start()

    def _atualizar_regiao(self, linha_inicio, linha_fim):
        if linha_inicio >= linha_fim:
            return 0.0

        novos_valores = 0.25 * (
            self.grade[linha_inicio - 1 : linha_fim - 1, 1:-1]
            + self.grade[linha_inicio + 1 : linha_fim + 1, 1:-1]
            + self.grade[linha_inicio:linha_fim, 0:-2]
            + self.grade[linha_inicio:linha_fim, 2:]
        )
        valores_antigos = self.grade[linha_inicio:linha_fim, 1:-1]
        self.nova_grade[linha_inicio:linha_fim, 1:-1] = novos_valores
        return float(np.max(np.abs(novos_valores - valores_antigos))) if valores_antigos.size else 0.0

    def _loop_trabalhador(self, id_thread, linha_inicio, linha_fim):
        while True:
            self.barreira_inicio.wait()
            if self.evento_parada.is_set():
                self.barreira_fim.wait()
                break

            self.difs_max_locais[id_thread] = self._atualizar_regiao(linha_inicio, linha_fim)

            self.barreira_fim.wait()

    def _parar_trabalhadores(self):
        self.evento_parada.set()
        self.barreira_inicio.wait()
        self.barreira_fim.wait()

        for thread in self.threads:
            thread.join()

    def atualizar(self):
        self.barreira_inicio.wait()
        self.barreira_fim.wait()

        dif_maxima = max(self.difs_max_locais) if self.difs_max_locais else 0.0

        self.grade, self.nova_grade = self.nova_grade, self.grade
        return dif_maxima

    def simular(self, iteracoes, limite_convergencia=1e-6):
        iteracoes_reais = 0
        try:
            for iteracao in range(iteracoes):
                dif_maxima = self.atualizar()
                iteracoes_reais = iteracao + 1

                if dif_maxima < limite_convergencia:
                    break
        finally:
            self._parar_trabalhadores()

        return iteracoes_reais

    def obter_grade(self):
        return self.grade.copy()

    def obter_temp_media(self):
        return np.mean(self.grade[1:-1, 1:-1])


def executar_simulacao_paralela(largura, altura, iteracoes, num_threads, detalhado=True):
    tempo_inicio = time.time()

    simulacao = DifusaoCalorParalela(largura, altura, num_threads)
    iteracoes_reais = simulacao.simular(iteracoes)

    tempo_fim = time.time()
    tempo_execucao = tempo_fim - tempo_inicio

    if detalhado:
        print(f"Simulacao Paralela:")
        print(f"  Tamanho: {largura}x{altura}")
        print(f"  Threads: {num_threads}")
        print(f"  Iteracoes: {iteracoes_reais}")
        print(f"  Tempo de execucao: {tempo_execucao:.4f} segundos")
        print(f"  Temperatura media: {simulacao.obter_temp_media():.4f}C")

    return tempo_execucao


if __name__ == "__main__":
    print("=== Simulacao Paralela de Difusao de Calor ===\n")

    largura, altura = 500, 500
    iteracoes = 1000
    contagens_threads = [1, 2, 4, 8]

    for num_threads in contagens_threads:
        executar_simulacao_paralela(largura, altura, iteracoes, num_threads)
        print()
