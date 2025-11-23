# Simulação de Difusão de Calor - Trabalho Prático

Este projeto implementa três versões de uma simulação de difusão de calor para comparação de desempenho entre abordagens sequencial, paralela e distribuída.

## 📋 Descrição

O problema implementado é a simulação de difusão de calor em uma grade 2D usando o método de diferenças finitas (método de Jacobi). A temperatura de cada célula é calculada como a média das temperaturas das células vizinhas (norte, sul, leste, oeste).

### Versões Implementadas

1. **Sequencial** (`sequencial.py`): Processa todas as células da grade de forma sequencial
2. **Paralela** (`paralelo.py`): Utiliza múltiplas threads para processar diferentes faixas da grade simultaneamente
3. **Distribuída** (`distribuido.py`): Utiliza múltiplos processos comunicando-se via sockets TCP/IP

## 🚀 Instalação

### Requisitos

- Python 3.7 ou superior
- pip (gerenciador de pacotes Python)

### Dependências

Instale as dependências usando:

```bash
pip install -r requirements.txt
```

As dependências incluem:

- `numpy`: Para operações com arrays multidimensionais
- `matplotlib`: Para geração de gráficos
- `psutil`: Para coleta de informações do sistema
- `pandas`: Para análise de dados

## 📖 Uso

### Execução Individual

#### Versão Sequencial

```bash
python sequencial.py
```

#### Versão Paralela

```bash
python paralelo.py
```

#### Versão Distribuída

**Servidor (mestre):**

```bash
python benchmark.py --distributed
```

**Workers (em terminais separados ou máquinas diferentes):**

```bash
python distribuido.py worker [host] [porta]
```

### Execução de Benchmarks

Para executar todos os benchmarks e gerar relatórios:

```bash
python benchmark.py
```

#### Opções do Benchmark

```bash
python benchmark.py [opções]

Opções:
  --sizes SIZE [SIZE ...]    Tamanhos da grade (padrão: 100 200 500)
  --iterations ITER          Número de iterações (padrão: 1000)
  --threads T [T ...]        Números de threads (padrão: 1 2 4 8)
  --workers W [W ...]        Números de workers (padrão: 1 2 4)
  --sequential               Executar apenas benchmark sequencial
  --parallel                 Executar apenas benchmark paralelo
  --distributed              Executar apenas benchmark distribuído
  --output-dir DIR           Diretório para resultados (padrão: resultados)
```

#### Exemplos

```bash
# Benchmark completo com tamanhos personalizados
python benchmark.py --sizes 100 300 500 1000 --iterations 500

# Apenas versão paralela com diferentes números de threads
python benchmark.py --parallel --threads 1 2 4 8 16

# Apenas versão distribuída
python benchmark.py --distributed --workers 2 4 8
```

## 📊 Resultados

Os resultados são salvos no diretório `resultados/` (ou o diretório especificado):

- `resultados_benchmark.json`: Resultados em formato JSON
- `resultados_benchmark.csv`: Resultados em formato CSV
- `tamanho_vs_tempo.png`: Gráfico de tempo vs tamanho do problema
- `threads_vs_speedup.png`: Gráfico de speedup vs número de threads
- `workers_vs_speedup.png`: Gráfico de speedup vs número de workers

## 🔬 Metodologia

### Algoritmo

O algoritmo utiliza o método de Jacobi para resolver a equação do calor:

```python
T_nova[i,j] = (T[i-1,j] + T[i+1,j] + T[i,j-1] + T[i,j+1]) / 4
```

Onde:

- `T[i,j]` é a temperatura na posição (i,j)
- A nova temperatura é calculada como a média das 4 células vizinhas

### Condições de Contorno

- Bordas da grade mantêm temperatura fixa (100°C por padrão)
- Células internas começam com temperatura inicial (0°C por padrão)

### Paralelização

**Versão Paralela:**

- Divide a grade em faixas horizontais
- Cada thread processa uma faixa
- Sincronização via `threading.Barrier` após cada iteração

**Versão Distribuída:**

- Servidor mestre coordena a simulação
- Workers processam faixas da grade
- Comunicação via sockets TCP/IP com serialização pickle

## 📈 Análise de Desempenho

### Métricas Coletadas

- Tempo de execução total
- Speedup relativo à versão sequencial
- Eficiência (speedup / número de threads/workers)
- Escalabilidade (comportamento com aumento de recursos)

### Limitações Identificadas

1. **Versão Paralela:**

   - Overhead de sincronização entre threads
   - GIL (Global Interpreter Lock) do Python pode limitar paralelismo real
   - Contenção de memória compartilhada

2. **Versão Distribuída:**
   - Overhead de comunicação via rede
   - Serialização/deserialização de dados (pickle)
   - Latência de rede entre processos

### Melhorias Propostas

1. **Para Paralela:**

   - Usar `multiprocessing` ao invés de `threading` para evitar GIL
   - Implementar divisão mais eficiente do trabalho
   - Reduzir sincronizações desnecessárias

2. **Para Distribuída:**
   - Usar protocolos de comunicação mais eficientes (ex: Protocol Buffers)
   - Implementar compressão de dados
   - Reduzir número de comunicações (batch de iterações)

## 🖥️ Configuração do Sistema

O script de benchmark coleta automaticamente informações do sistema:

- Sistema operacional
- Processador
- Número de cores físicos e lógicos
- Memória total
- Versão do Python

## 📝 Estrutura do Projeto

```text
HeatDiffusion/
├── sequencial.py          # Implementação sequencial
├── paralelo.py            # Implementação paralela com threads
├── distribuido.py         # Implementação distribuída com sockets
├── benchmark.py           # Script de benchmark e análise
├── analisar_resultados.py # Script de análise detalhada
├── teste_rapido.py        # Teste rápido de consistência
├── requirements.txt       # Dependências do projeto
├── README.md              # Este arquivo
└── resultados/            # Diretório de resultados (gerado)
    ├── resultados_benchmark.json
    ├── resultados_benchmark.csv
    ├── tamanho_vs_tempo.png
    ├── threads_vs_speedup.png
    └── workers_vs_speedup.png
```

## 🔍 Verificação de Resultados

Para verificar se as implementações produzem resultados consistentes:

```bash
python teste_rapido.py
```

Ou manualmente:

```python
from sequencial import DifusaoCalorSequencial
from paralelo import DifusaoCalorParalela
import numpy as np

# Teste com mesmos parâmetros
largura, altura = 100, 100
iteracoes = 100

seq = DifusaoCalorSequencial(largura, altura)
seq.simular(iteracoes)

par = DifusaoCalorParalela(largura, altura, num_threads=4)
par.simular(iteracoes)

# Compara resultados (devem ser muito similares)
dif = np.abs(seq.obter_grade() - par.obter_grade())
print(f"Diferença máxima: {np.max(dif)}")
```

## 📚 Referências

- **Método de Jacobi**: Método iterativo clássico para resolução de sistemas lineares
- **Difusão de Calor**: Modelo físico descrito pela equação do calor
- **Paralelização**: Divisão de trabalho entre múltiplos processadores
- **Computação Distribuída**: Processamento em múltiplos nós de rede

## 👥 Autores

Trabalho desenvolvido para a disciplina de Computação Paralela e Distribuída.

## 📄 Licença

Este projeto é destinado exclusivamente para fins educacionais.

---

**Nota**: Para execução distribuída em múltiplas máquinas, certifique-se de que:

1. As máquinas estão na mesma rede
2. As portas necessárias estão abertas no firewall
3. O endereço IP do servidor está acessível pelos workers
