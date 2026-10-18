# StegoLab — Protótipo de Esteganografia em Python

**StegoLab · Laboratório de Esteganografia** é uma aplicação web local que permite **esconder uma mensagem de texto — ou um ficheiro inteiro — dentro de outro ficheiro** e, mais tarde, **recuperá-lo**. O portador principal é a imagem, com a técnica **LSB (Least Significant Bit)** implementada de raiz em Python. A aplicação aceita também **áudio WAV, vídeo, texto, PDF e documentos Office**, tem encriptação opcional por palavra-passe e permite definir uma **data de validade** para o segredo.

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
| **FFmpeg** *(opcional)* | Ler e escrever vídeo; sem ele, tudo o resto funciona |

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
| `FLAGS` | 1 byte | Bit 0 = encriptado · Bit 1 = com metadados |
| `COMPRIMENTO` | 4 bytes | Número de bytes de dados |
| `CRC32` | 4 bytes | Verificação de integridade |
| `DADOS` | N bytes | Mensagem UTF-8 (ou sal + token Fernet) |

Quando o segredo é um **ficheiro** ou tem **data de validade**, o bit 1 das FLAGS fica activo e os dados (antes de serem encriptados) começam com um bloco de metadados: `TIPO (1 B: texto/ficheiro) | VALIDADE (8 B, data Unix) | COMPRIMENTO DO NOME (1 B) | NOME`. Uma mensagem de texto simples, sem validade, não usa este bloco, por isso o formato é exactamente o da primeira versão e as imagens antigas continuam a ser lidas.

Como a extracção lê estes dados directamente dos píxeis do ficheiro, **funciona depois de fechar e voltar a abrir a aplicação**. Nada fica guardado em memória ou em disco.

---

## 5. Encriptação opcional

- A chave é derivada da palavra-passe com **PBKDF2-HMAC-SHA256** (480 000 iterações e sal aleatório de 16 bytes).
- A mensagem é cifrada com **Fernet** (AES-128-CBC + HMAC-SHA256), da biblioteca `cryptography`. Não foi criado nenhum algoritmo próprio.
- O código está em `steganography/crypto.py`, separado da lógica LSB.
- Na extracção, a aplicação lê a flag do cabeçalho e **só pede a palavra-passe quando é necessária**. Uma palavra-passe errada dá uma mensagem de erro clara.

---

## 6. Outros ficheiros de cobertura

O tipo de ficheiro é detectado pelos **primeiros bytes** (assinatura), nunca pela extensão. Cada tipo usa a técnica mais adequada:

| Portador | Técnica | Capacidade | Resultado |
|---|---|---|---|
| **Imagem** (PNG, BMP, TIFF, WebP, JPEG) | LSB nos canais R, G, B | largura × altura × 3 ÷ 8 − 14 bytes | PNG/BMP/TIFF/WebP sem perdas |
| **Áudio WAV** (PCM 8/16/24/32 bits) | LSB no byte baixo de cada amostra | amostras × canais ÷ 8 − 14 bytes | WAV com os mesmos parâmetros e o mesmo tamanho |
| **Vídeo** (MP4, MOV, MKV, WebM) — requer FFmpeg | LSB nas amostras da **faixa de áudio** | ≈ 12 KB por segundo de som estéreo a 48 kHz | `.mkv`: vídeo copiado sem recodificar + áudio PCM |
| **Texto** (TXT, MD, CSV…) | Caracteres Unicode de largura zero (2 bits por carácter) | até 64 KB | O mesmo texto visível, com caracteres invisíveis |
| **PDF** | Comentários `%STGL:` (base64) antes de `startxref` | até 2 MB | PDF válido, com o mesmo aspecto |
| **Office / ZIP** (DOCX, XLSX, PPTX, ODT, ODS, ODP, EPUB, ZIP) | Comentário do arquivo ZIP | até 64 KB | Documento que abre normalmente |

**Porque é que o vídeo usa a faixa de áudio?** Para esconder bits nos píxeis, o vídeo inteiro teria de ser gravado sem perdas. Num teste com 10 s em 720p, o ficheiro passou de 4,7 MB para cerca de 130 MB (FFV1). Copiar o vídeo e usar o áudio em PCM só acrescenta cerca de 1,9 MB por cada 10 s de som. Se o vídeo não tiver som, é criada uma faixa silenciosa.

**Imagem, WAV e vídeo** usam LSB verdadeiro. **Texto, PDF e Office** usam ocultação na **estrutura** do ficheiro: é simples e fiável, mas quem abrir o ficheiro num editor hexadecimal ou de texto vê o bloco escondido. Por isso convém usar sempre palavra-passe.

O código de cada portador está em `steganography/carriers/`. Todos partilham o mesmo cabeçalho `STGL`, CRC32, encriptação e validade.

## 7. Esconder ficheiros e data de validade

- **Ficheiro como segredo:** em vez de texto, pode esconder qualquer ficheiro (PDF, ZIP, imagem…) até 2 MB, se couber no portador. O nome é guardado (sem caminhos) e, na extracção, aparece um botão para o descarregar. O StegoLab **nunca abre nem executa** o ficheiro recuperado.
- **Data de validade:** *1 hora*, *24 horas*, *7 dias* ou uma data personalizada. Depois dessa data, a aplicação **recusa revelar** o segredo.
  - **Com palavra-passe**, a data fica dentro da cifra e é autenticada pelo HMAC do Fernet: não pode ser alterada sem a palavra-passe.
  - **Sem palavra-passe**, quem conhecer o formato pode alterar a data.
  - **Limite honesto:** é uma regra aplicada pela aplicação. Quem tiver a palavra-passe e modificar o código-fonte consegue ignorá-la. Nenhuma aplicação consegue apagar cópias de um ficheiro que já saiu do seu controlo.

---

## 8. Estrutura das pastas

```
SI Job/                      (raiz do projecto)
├── app.py                   Interface Streamlit (só interface)
├── steganography/           Núcleo — não depende do Streamlit
│   ├── __init__.py          API pública
│   ├── payload.py           Formato do cabeçalho e metadados, conversão bytes ↔ bits
│   ├── secret.py            Segredo (texto/ficheiro), validade, encriptação
│   ├── encoder.py           Codificação LSB
│   ├── decoder.py           Extracção LSB
│   ├── carriers/            Um módulo por tipo de ficheiro de cobertura
│   │   ├── __init__.py      Detecção pelo conteúdo, hide() e reveal()
│   │   ├── base.py          Interface comum (e LSB genérico)
│   │   ├── image.py         Imagens
│   │   ├── audio.py         WAV
│   │   ├── video.py         Vídeo (FFmpeg, faixa de áudio)
│   │   ├── text.py          Texto (caracteres de largura zero)
│   │   ├── pdf.py           PDF (comentários)
│   │   └── archive.py       Office/ZIP (comentário do ZIP)
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
│   ├── test_carriers.py     WAV, vídeo, texto, PDF, Office, ficheiros, validade
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

## 9. Instalação

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

### FFmpeg (opcional, só para vídeo)

- **Linux (Ubuntu/Debian):** `sudo apt install ffmpeg`
- **Windows:** `winget install Gyan.FFmpeg` (depois, feche e volte a abrir o terminal)
- Verificar: `ffmpeg -version`. Sem FFmpeg, os vídeos são recusados com uma mensagem clara e os testes de vídeo são ignorados.

---

## 10. Executar a aplicação

Com o ambiente virtual activado:

```bash
streamlit run app.py
```

Abra **http://localhost:8501** no navegador. Para parar o servidor, use `Ctrl+C`.

## 11. Executar os testes

```bash
python -m pytest          # resumo
python -m pytest -v       # lista de cada teste
```

Os testes cobrem: mensagens simples, acentos portugueses, Unicode e emojis, mensagens longas, preservação das dimensões, imagem original não alterada, alteração máxima de ±1 por canal, canal alfa, capacidade excedida (com e sem encriptação), mensagens vazias, ficheiros inválidos e extensões falsas, imagens sem payload, comprimentos inválidos, payload truncado (imagem recortada), dados corrompidos (CRC), destruição pelo JPEG, todos os formatos de saída (PNG, BMP, TIFF, WebP sem perdas), encriptação, palavra-passe em falta ou errada, **extracção num processo Python separado** (simula reiniciar a aplicação) e arranque da interface.

Os testes de `test_carriers.py` cobrem também: ida e volta em WAV, texto, PDF, DOCX e vídeo; ficheiros como segredo (com palavra-passe); detecção pelo conteúdo; WAV de 8, 16 e 24 bits; texto visível inalterado; PDF e ficheiros internos do ZIP intactos; limites de capacidade; validade antes e depois do prazo; nomes de ficheiro perigosos (`../../etc/passwd`).

Resultado no ambiente de desenvolvimento (Linux, Python 3.12.3, FFmpeg 6.1.1): **96 testes passaram**.

---

## 12. Como esconder um segredo

1. Abra o separador **Esconder mensagem**.
2. Carregue o **ficheiro de cobertura**: imagem, WAV, vídeo, texto, PDF ou documento Office. Aparecem a pré-visualização, os detalhes do ficheiro, a **capacidade** e a técnica usada.
3. Escolha **Mensagem de texto** (escreva-a) ou **Ficheiro** (carregue o ficheiro a esconder).
4. *(Opcional)* Active **Proteger o conteúdo com palavra-passe** e introduza-a duas vezes.
5. *(Opcional)* Escolha a **validade** do segredo.
6. Nas imagens, escolha o formato de saída (**PNG** recomendado). Nos restantes tipos, o formato é automático.
7. Clique em **Esconder segredo**. A aplicação reabre o ficheiro gerado para confirmar que o segredo é recuperável e **abre a página de resultado**: estatísticas, comparação adequada ao tipo de ficheiro (imagens lado a lado, leitores de áudio, caracteres invisíveis à vista, bloco do PDF…) e botão **Descarregar**.
8. O botão no cabeçalho, sempre visível, alterna entre **Voltar ao laboratório** e **Ver resultado**. **Esconder outro segredo** limpa o formulário.

## 13. Como extrair um segredo

1. Abra o separador **Extrair mensagem**.
2. Carregue o ficheiro gerado pelo StegoLab (por exemplo, `foto_stego.png`, `musica_stego.wav` ou `video_stego.mkv`).
3. A aplicação analisa o cabeçalho e mostra se encontrou um segredo, a técnica, o tamanho e se está encriptado.
4. Se estiver encriptado, introduza a palavra-passe.
5. Clique em **Extrair segredo**. Se for texto, pode **copiá-lo** ou **guardá-lo como .txt**. Se for um ficheiro, aparece o botão para o **descarregar** com o nome original. Se a validade tiver passado, aparece o erro "Segredo expirado".

---

## 14. Limitações conhecidas

- **Não é indetectável:** técnicas de esteganálise (por exemplo, o teste qui-quadrado sobre os LSB) podem detectar a alteração.
- **Fragilidade:** redimensionar, recortar, rodar, editar ou comprimir com perdas (JPEG, WhatsApp, Facebook…) **destrói a mensagem**. Partilhe sempre o ficheiro original, por exemplo como "documento".
- **Sem encriptação, não há confidencialidade:** quem conhecer o formato `STGL` consegue ler a mensagem.
- Os bits são escritos sequencialmente a partir do canto superior esquerdo. Não há dispersão pseudo-aleatória.
- O JPEG é aceite **apenas como imagem de partida**: o resultado é sempre gravado sem perdas e o JPEG nunca é oferecido como formato de saída.
- Limites: ficheiros até 25 MB (vídeos até 100 MB, incluindo o resultado), imagens até 40 megapíxeis, mensagens até 100 000 bytes e ficheiros escondidos até 2 MB. Em imagens animadas, só é usado o primeiro quadro.
- **Áudio e vídeo:** converter para MP3/AAC/MP4, editar o som ou partilhar em redes sociais destrói o segredo. O `.mkv` gerado abre no VLC ou no mpv, mas alguns navegadores não o reproduzem. MP3, OGG e FLAC não são aceites como portador: converta para WAV.
- **Texto:** algumas aplicações removem caracteres de largura zero ao copiar e colar.
- **PDF e Office:** não é LSB, por isso o bloco é visível num editor hexadecimal. Voltar a gravar o documento no Word ou noutro editor de PDF remove-o.
- **Validade:** é aplicada pela aplicação e não apaga cópias do ficheiro (ver secção 7).
- Os textos internos do componente de upload do Streamlit (por exemplo, "Upload" e "100MB per file") aparecem em inglês.
- **A esteganografia não oferece segurança absoluta.** Este é um protótipo académico.

## 15. Segurança e privacidade

- Os ficheiros são validados pelo **conteúdo** (Pillow `verify()` + reabertura), não pela extensão.
- Ficheiros carregados nunca são executados. Só os vídeos são gravados, numa pasta temporária que é apagada logo a seguir, porque o FFmpeg precisa de ler o ficheiro do disco.
- O FFmpeg é chamado sem shell e com tempo limite. O demultiplexador (`mov` ou `matroska`) é imposto a partir da assinatura do ficheiro, para que um ficheiro malicioso não consiga activar outro formato. Por essa razão, o AVI não é aceite.
- Os nomes dos ficheiros escondidos são limpos (sem caminhos nem caracteres de controlo), e o ficheiro recuperado só é entregue para download.
- Mensagens e palavras-passe não são registadas em logs. A telemetria do Streamlit está desactivada.
- Os erros aparecem como mensagens compreensíveis, sem stack traces.

---

## 16. Preparação da demonstração

**Antes da aula:**
1. Instale as dependências e corra `python -m pytest`. Todos os testes devem passar.
2. Gere a imagem de teste, caso não exista: `python scripts/gerar_imagem_demo.py` (cria `assets/demo_paisagem.png`).
3. Inicie a aplicação com `streamlit run app.py` e deixe o navegador aberto.
4. Prepare uma mensagem fictícia, por exemplo: `Encontro às 15h na biblioteca — código: Maçã 🍎`. **Não use dados pessoais ou confidenciais.**
5. Tenha um plano B: deixe já uma imagem gerada (`demo_paisagem_stego.png`) e a palavra-passe anotada.

**Roteiro sugerido (5–7 minutos):** o guião detalhado, com a explicação de cada técnica, está em [GUIA_APRESENTACAO.md](GUIA_APRESENTACAO.md).

| Tempo | Quem | Conteúdo |
|---|---|---|
| 0:00–1:00 | Samuel | **Problema e objectivo:** comunicar sem levantar suspeitas. Esteganografia ≠ encriptação. |
| 1:00–2:30 | Adilson | **LSB na imagem:** carregar `demo_paisagem.png`, escrever a mensagem, activar a palavra-passe e esconder. Na página de resultado, mostrar as estatísticas e o zoom dos píxeis, e descarregar. |
| 2:30–3:30 | Samuel | **Extrair:** palavra-passe errada (erro claro), depois a correcta. Mostrar o erro "Nenhum segredo encontrado" com a imagem original. |
| 3:30–4:30 | Adilson | **Outros portadores:** um `.txt` com os caracteres invisíveis à vista e um vídeo (a mensagem vai na faixa de áudio). |
| 4:30–5:30 | Samuel | **Ficheiro + validade:** esconder um PDF com validade de 1 hora e recuperá-lo. Explicar o limite honesto da validade. |
| 5:30–6:30 | Adilson | **Testes e limitações:** `python -m pytest`; JPEG/MP3 destroem os LSB; PDF e Office são detectáveis num editor. |
| 6:30–7:00 | Samuel | **Conclusão:** a combinação esconder + encriptar é mais forte, mas não absoluta. |

**Perguntas prováveis:**
- *Porque não JPEG?* A compressão com perdas altera os LSB, e o CRC32 detecta-o (ver teste `test_jpeg_compression_destroys_payload`).
- *Quanto cabe numa imagem?* Largura × altura × 3 ÷ 8 − 14 bytes. Numa imagem de 960×600 cabem cerca de 211 KB.
- *Como sabe onde a mensagem acaba?* Pelo campo `COMPRIMENTO` do cabeçalho, validado contra a capacidade da imagem.
- *É seguro?* Esconde, mas não é indetectável. A encriptação protege o conteúdo se a mensagem for descoberta.
