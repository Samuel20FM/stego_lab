# StegoLab — Protótipo de Esteganografia em Python

**StegoLab · Laboratório de Esteganografia** é uma aplicação web local que permite **esconder uma mensagem de texto dentro de uma imagem** e, mais tarde, **recuperá-la** a partir da imagem resultante. Usa a técnica **LSB (Least Significant Bit)**, implementada de raiz em Python, e tem encriptação opcional por palavra-passe.

---

## 1. Contexto académico

| | |
|---|---|
| **Instituição** | Universidade Pedagógica de Maputo — Faculdade de Engenharias e Tecnologias |
| **Curso** | Licenciatura em Informática |
| **Disciplina** | Segurança Informática (Fundamentos de Segurança Informática) |
| **Docente** | Martina de Barros |
| **Integrantes** | Samuel Massinga · Adilson Chaguala |
| **Período** | 2.º Semestre · 2026 |

**Objectivo:** implementar uma técnica de esteganografia que esconda informação numa imagem e permita recuperá-la, de forma visual e didáctica.

> **Nota sobre o enunciado:** o enunciado tem também uma tarefa com as ferramentas **Steghide** e **Stegosuite**. Este protótipo cobre **apenas a implementação em Python** e não usa essas ferramentas. Só deve ser apresentado como resposta completa ao enunciado se a docente tiver dispensado essa tarefa.

---

## 2. Tecnologias

| Tecnologia | Para que serve |
|---|---|
| **Python 3.11+** (testado com 3.12.3) | Linguagem e algoritmo LSB explícito |
| **Pillow** | Ler, validar e gravar imagens |
| **Streamlit** | Interface web local, aberta no navegador |
| **cryptography** | Encriptação opcional (Fernet + PBKDF2) |
| **pytest** | Testes automatizados |

O NumPy não é usado directamente (o algoritmo trabalha com `bytearray`, o que é mais fácil de explicar). É instalado apenas porque o Streamlit depende dele.

---

## 3. O que é esteganografia?

**Esteganografia** é esconder uma mensagem dentro de outro conteúdo que parece inofensivo, como uma fotografia, para que ninguém **suspeite que a mensagem existe**.

### Esteganografia vs. encriptação

| | Esteganografia | Encriptação |
|---|---|---|
| O que protege | A **existência** da mensagem | O **conteúdo** da mensagem |
| O que um observador vê | Uma imagem normal | Um texto ilegível (sabe que há um segredo) |
| Se for descoberta | A mensagem pode ser lida | Sem a chave, continua ilegível |

O StegoLab pode **combinar as duas**: primeiro encripta a mensagem (opcional) e depois esconde-a na imagem.

---

## 4. O algoritmo LSB

Cada píxel de uma imagem RGB tem 3 canais (vermelho, verde e azul), e cada canal tem um valor de 0 a 255, guardado em 8 bits. O **bit menos significativo (LSB)** é o último desses 8 bits. Alterá-lo muda o valor da cor em **no máximo 1 unidade**, o que o olho humano não nota.

```
Canal vermelho = 200 = 1100100[0]
Bit da mensagem = 1
Novo valor      = (200 & 0b11111110) | 1 = 1100100[1] = 201
```

### Codificação (`steganography/encoder.py`)
1. Valida a mensagem (não pode estar vazia; limite de 100 000 bytes).
2. Converte o texto em bytes **UTF-8**, o que suporta acentos e emojis.
3. Se houver palavra-passe, encripta os bytes (ver secção 5).
4. Acrescenta o **cabeçalho** de 14 bytes (ver tabela abaixo).
5. Verifica a **capacidade**: largura × altura × 3 bits ÷ 8 − 14 bytes.
6. Converte tudo em bits e escreve-os, por ordem, nos LSB dos canais R, G, B, R, G, B…
7. Devolve uma **nova** imagem com as mesmas dimensões. A original não é alterada, e o canal alfa (transparência) é preservado.

### Extracção (`steganography/decoder.py`)
1. Lê os primeiros 112 LSB (14 bytes) e valida o identificador `STGL`.
2. Valida a versão, os indicadores e o **comprimento**, que tem de caber na imagem.
3. Lê **apenas** os bits indicados pelo comprimento, sem nunca ler para além da imagem.
4. Confirma o **CRC32**, que detecta dados truncados ou corrompidos.
5. Desencripta, se for o caso, e descodifica em UTF-8.

### Formato do payload

| Campo | Tamanho | Função |
|---|---|---|
| `MAGIC = "STGL"` | 4 bytes | Identifica uma imagem do StegoLab |
| `VERSÃO` | 1 byte | Versão do formato (1) |
| `FLAGS` | 1 byte | Bit 0 = mensagem encriptada |
| `COMPRIMENTO` | 4 bytes | Número de bytes de dados |
| `CRC32` | 4 bytes | Verificação de integridade |
| `DADOS` | N bytes | Mensagem UTF-8 (ou sal + token Fernet) |

Como a extracção lê estes dados directamente dos píxeis do ficheiro, **funciona depois de fechar e voltar a abrir a aplicação**. Nada fica guardado em memória ou em disco.

---

## 5. Encriptação opcional

- A chave é derivada da palavra-passe com **PBKDF2-HMAC-SHA256** (480 000 iterações e sal aleatório de 16 bytes).
- A mensagem é cifrada com **Fernet** (AES-128-CBC + HMAC-SHA256), da biblioteca `cryptography`. Não foi criado nenhum algoritmo próprio.
- O código está em `steganography/crypto.py`, separado da lógica LSB.
- Na extracção, a aplicação lê a flag do cabeçalho e **só pede a palavra-passe quando é necessária**. Uma palavra-passe errada dá uma mensagem de erro clara.

---

## 6. Estrutura das pastas

```
SI Job/                      (raiz do projecto)
├── app.py                   Interface Streamlit (só interface)
├── steganography/           Núcleo — não depende do Streamlit
│   ├── __init__.py          API pública
│   ├── payload.py           Formato do cabeçalho, conversão bytes ↔ bits
│   ├── encoder.py           Codificação LSB
│   ├── decoder.py           Extracção LSB
│   ├── image_utils.py       Validação, capacidade, gravação de imagens
│   ├── crypto.py            Encriptação opcional (Fernet)
│   └── errors.py            Erros com mensagens em português
├── ui/
│   ├── components.py        Componentes visuais (cabeçalho, cartões, barra…)
│   └── styles.py            CSS do tema escuro
├── tests/                   Testes pytest (imagens geradas nos testes)
│   ├── conftest.py
│   ├── test_encoder.py
│   ├── test_decoder.py
│   ├── test_roundtrip.py
│   └── test_app.py          Teste de arranque da interface
├── scripts/
│   └── gerar_imagem_demo.py Gera a imagem de teste da demonstração
├── assets/                  Logótipo, favicon e imagem de demonstração
├── .streamlit/config.toml   Tema e limite de upload
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## 7. Instalação

**Requisitos:** Python 3.11 ou superior e ligação à Internet **apenas** para instalar as dependências. A aplicação funciona offline depois de instalada.

### Linux

```bash
cd "SI Job"                      # pasta do projecto
python3 -m venv .venv            # criar o ambiente virtual
source .venv/bin/activate        # activar
pip install -r requirements.txt  # instalar dependências
```

> Em Ubuntu/Debian, se `python3 -m venv` falhar: `sudo apt install python3-venv`.

### Windows (PowerShell)

```powershell
cd "SI Job"
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Se o PowerShell bloquear a activação: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
> No `cmd.exe`, use `.venv\Scripts\activate.bat`.

---

## 8. Executar a aplicação

Com o ambiente virtual activado:

```bash
streamlit run app.py
```

Abra **http://localhost:8501** no navegador. Para parar o servidor, use `Ctrl+C`.

## 9. Executar os testes

```bash
python -m pytest          # resumo
python -m pytest -v       # lista de cada teste
```

Os testes cobrem: mensagens simples, acentos portugueses, Unicode e emojis, mensagens longas, preservação das dimensões, imagem original não alterada, alteração máxima de ±1 por canal, canal alfa, capacidade excedida (com e sem encriptação), mensagens vazias, ficheiros inválidos e extensões falsas, imagens sem payload, comprimentos inválidos, payload truncado (imagem recortada), dados corrompidos (CRC), destruição pelo JPEG, todos os formatos de saída (PNG, BMP, TIFF, WebP sem perdas), encriptação, palavra-passe em falta ou errada, **extracção num processo Python separado** (simula reiniciar a aplicação) e arranque da interface.

Resultado no ambiente de desenvolvimento (Linux, Python 3.12.3): **57 testes passaram**.

---

## 10. Como esconder uma mensagem

1. Abra o separador **Esconder mensagem**.
2. Carregue uma imagem (PNG, BMP, TIFF, WebP ou JPEG). Aparecem a pré-visualização, as dimensões, o formato, o tamanho e a **capacidade**.
3. Escreva a mensagem. O contador de caracteres e a barra de ocupação são actualizados quando sai do campo ou carrega em `Ctrl+Enter`.
4. *(Opcional)* Active **Proteger o conteúdo com palavra-passe** e introduza-a duas vezes.
5. Escolha o formato de saída (**PNG** recomendado).
6. Clique em **Esconder mensagem**. A aplicação reabre automaticamente o ficheiro gerado para confirmar que a mensagem é recuperável.
7. Compare as imagens lado a lado, veja o zoom dos píxeis alterados e clique em **Descarregar imagem**.

## 11. Como extrair uma mensagem

1. Abra o separador **Extrair mensagem**.
2. Carregue a imagem gerada pelo StegoLab.
3. A aplicação analisa o cabeçalho e mostra se encontrou uma mensagem e se ela está encriptada.
4. Se estiver encriptada, introduza a palavra-passe.
5. Clique em **Extrair mensagem**. Pode **copiar** a mensagem ou **guardá-la como .txt**.

---

## 12. Limitações conhecidas

- **Não é indetectável:** técnicas de esteganálise (por exemplo, o teste qui-quadrado sobre os LSB) podem detectar a alteração.
- **Fragilidade:** redimensionar, recortar, rodar, editar ou comprimir com perdas (JPEG, WhatsApp, Facebook…) **destrói a mensagem**. Partilhe sempre o ficheiro original, por exemplo como "documento".
- **Sem encriptação, não há confidencialidade:** quem conhecer o formato `STGL` consegue ler a mensagem.
- Os bits são escritos sequencialmente a partir do canto superior esquerdo. Não há dispersão pseudo-aleatória.
- O JPEG é aceite **apenas como imagem de partida**: o resultado é sempre gravado sem perdas e o JPEG nunca é oferecido como formato de saída.
- Limites: ficheiros até 25 MB, imagens até 40 megapíxeis, mensagens até 100 000 bytes. Em imagens animadas, só é usado o primeiro quadro.
- Os textos internos do componente de upload do Streamlit (por exemplo, "Upload" e "25MB per file") aparecem em inglês.
- **A esteganografia não oferece segurança absoluta.** Este é um protótipo académico.

## 13. Segurança e privacidade

- Os ficheiros são validados pelo **conteúdo** (Pillow `verify()` + reabertura), não pela extensão.
- Ficheiros carregados nunca são executados nem gravados em disco.
- Mensagens e palavras-passe não são registadas em logs. A telemetria do Streamlit está desactivada.
- Os erros aparecem como mensagens compreensíveis, sem stack traces.

---

## 14. Preparação da demonstração

**Antes da aula:**
1. Instale as dependências e corra `python -m pytest`. Todos os testes devem passar.
2. Gere a imagem de teste, caso não exista: `python scripts/gerar_imagem_demo.py` (cria `assets/demo_paisagem.png`).
3. Inicie a aplicação com `streamlit run app.py` e deixe o navegador aberto.
4. Prepare uma mensagem fictícia, por exemplo: `Encontro às 15h na biblioteca — código: Maçã 🍎`. **Não use dados pessoais ou confidenciais.**
5. Tenha um plano B: deixe já uma imagem gerada (`demo_paisagem_stego.png`) e a palavra-passe anotada.

**Roteiro sugerido (5–7 minutos):**

| Tempo | Quem | Conteúdo |
|---|---|---|
| 0:00–1:00 | Samuel | **Problema e objectivo:** comunicar sem levantar suspeitas. Apresentar o StegoLab. |
| 1:00–2:00 | Samuel | **Conceito:** esteganografia esconde a existência da mensagem. Separador *Como funciona?*, passos 1–4. |
| 2:00–3:00 | Adilson | **LSB:** demo do píxel (alterar os bits R/G/B e ver que a cor é igual) e tabela "do texto aos bits" com "Olá". |
| 3:00–4:15 | Adilson | **Esconder:** carregar `demo_paisagem.png`, escrever a mensagem, activar a palavra-passe, esconder. Mostrar as estatísticas, as imagens lado a lado, o zoom dos píxeis e descarregar. |
| 4:15–5:15 | Samuel | **Extrair:** (opcional: reiniciar a aplicação) carregar o ficheiro descarregado, tentar uma palavra-passe errada (erro claro), depois a correcta, e copiar a mensagem. Carregar a imagem original para mostrar o erro "Nenhuma mensagem encontrada". |
| 5:15–6:15 | Adilson | **Testes e limitações:** correr `python -m pytest`; explicar o cabeçalho, o CRC32, o JPEG e o redimensionamento. |
| 6:15–7:00 | Samuel | **Esconder ≠ encriptar:** cartão de comparação. A combinação das duas é mais forte, mas não absoluta. Conclusão. |

**Perguntas prováveis:**
- *Porque não JPEG?* A compressão com perdas altera os LSB, e o CRC32 detecta-o (ver teste `test_jpeg_compression_destroys_payload`).
- *Quanto cabe numa imagem?* Largura × altura × 3 ÷ 8 − 14 bytes. Numa imagem de 960×600 cabem cerca de 211 KB.
- *Como sabe onde a mensagem acaba?* Pelo campo `COMPRIMENTO` do cabeçalho, validado contra a capacidade da imagem.
- *É seguro?* Esconde, mas não é indetectável. A encriptação protege o conteúdo se a mensagem for descoberta.
