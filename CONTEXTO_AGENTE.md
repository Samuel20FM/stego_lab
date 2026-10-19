# Contexto para continuar o trabalho — StegoLab

> Documento de passagem de testemunho para outro agente de IA.
> Estado em **2026-10-18**. Leia isto antes de mexer no código. A secção 9 descreve a extensão multiformato, a mais recente.

## 1. Quem é o utilizador e o que é o projecto

- **Utilizador:** Samuel Massinga, estudante de Licenciatura em Informática na Universidade Pedagógica de Maputo (Moçambique). Escreve em **português**; responda em português (norma europeia/moçambicana, com grafia como "projecto", "activar" e "selecção", que é a usada no enunciado).
- **Trabalho:** trabalho prático de **Segurança Informática**. Docente: **Martina de Barros**. Grupo: **Samuel Massinga e Adilson Chaguala**. 2.º semestre de 2026.
- **Projecto:** **StegoLab — Protótipo de Esteganografia em Python**. É uma app Streamlit local que esconde uma mensagem de texto numa imagem com **LSB** (Least Significant Bit) e depois a recupera. Tem encriptação opcional.
- **Enunciado original:** o utilizador colou um brief longo, que não está guardado no repositório. Pontos essenciais:
  - LSB implementado à mão, sem bibliotecas que façam a esteganografia automaticamente;
  - UTF-8; cabeçalho com identificador e comprimento; validação de capacidade e limites;
  - saída sem perdas (nunca JPEG); a extracção tem de funcionar depois de reiniciar a app;
  - encriptação opcional com Fernet;
  - interface escura e elegante (azul-marinho com azul eléctrico ou esmeralda);
  - testes pytest; README em português; roteiro de apresentação de 5–7 minutos.
- **Importante:** o enunciado tem também uma tarefa com **Steghide/Stegosuite**, que este protótipo **não cobre**. Não afirme que o projecto cumpre todo o enunciado, a menos que a docente tenha dispensado essa tarefa. O README e o separador "Sobre" já o dizem.
- **Prioridades do utilizador:** algoritmo correcto, recuperação fiável, interface bonita e estabilidade no dia da apresentação.

## 2. Localização, ambiente e comandos

- Pasta do projecto (é a raiz do repositório): `/home/samuel-coder/Programming/School/SI Job`
- Linux, Python 3.12.3. O ambiente virtual está em `.venv/` e já tem tudo instalado: Streamlit 1.65.0, Pillow 12.3.0, cryptography 50.0.2, pytest 9.1.1. O NumPy entra só como dependência do Streamlit.

```bash
cd "/home/samuel-coder/Programming/School/SI Job"
source .venv/bin/activate
streamlit run app.py          # http://localhost:8501
python -m pytest              # 96 testes, todos a passar (vídeo precisa de FFmpeg)
python scripts/gerar_imagem_demo.py   # recria assets/demo_paisagem.png
```

- Git: ramo `main`. Commits:
  - `0c23d1e` StegoLab: protótipo de esteganografia LSB em Python
  - `03ad2ad` Página de resultado com navegação no cabeçalho
- Estado actual não commitado: `app.py` tem apenas uma linha em branco extra (por volta da linha 526, feita pelo utilizador). `Notes.txt` (notas do utilizador) e este ficheiro não estão em git. **Só faça commit quando o utilizador pedir.** As mensagens de commit terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## 3. Arquitectura

```
app.py                  Interface Streamlit (só UI; o núcleo não depende do Streamlit)
steganography/
  payload.py            Cabeçalho + conversão bytes <-> bits
  encoder.py            embed_bits (LSB), hide_message, required_bytes, MAX_MESSAGE_BYTES=100 000
  decoder.py            extract_bits, read_header, reveal_message -> RevealResult
  image_utils.py        load_image (validação pelo conteúdo), capacidade, formatos de saída
  crypto.py             Fernet + PBKDF2-HMAC-SHA256 (480 000 iterações, sal de 16 B)
  errors.py             Excepções com mensagens em português (base: StegoError)
ui/components.py        HTML/CSS reutilizável (brand, header_tag, notice, chips, capacity_meter,
                        stats, secret_box, copy_button, scroll_to_top, fmt_bytes/fmt_int/fmt_pct)
ui/styles.py            CSS do tema escuro
tests/                  conftest (imagens geradas), test_encoder, test_decoder, test_roundtrip, test_app (AppTest)
scripts/gerar_imagem_demo.py   Imagem sintética para a demo
assets/                 logo.svg, favicon.png, demo_paisagem.png (960×600)
.streamlit/config.toml  Tema escuro, maxUploadSize=25, telemetria desligada
```

### Formato do payload (14 bytes de cabeçalho + dados)
`MAGIC "STGL" (4) | VERSÃO=1 (1) | FLAGS (1; bit0 = encriptado) | COMPRIMENTO (4, big-endian) | CRC32 dos dados (4) | DADOS`

- Os bits são escritos sequencialmente, do bit mais significativo para o menos, nos LSB de R, G, B, R, G, B… linha a linha, a partir do canto superior esquerdo.
- Na extracção, a app valida o identificador, a versão, as flags e o comprimento (> 0, dentro da capacidade e ≤ 256 KB), lê só os bits necessários e verifica o CRC32.
- O canal alfa é preservado. Os modos P, L e LA são convertidos para RGB.
- Capacidade = largura × altura × 3 ÷ 8 − 14 bytes.
- Encriptado: os dados são o sal (16 B) seguido do token Fernet em binário, sem base64.

### Formatos
- **Entrada** (validada pelo conteúdo com Pillow, não pela extensão): PNG, BMP, TIFF, WEBP, JPEG. O JPEG serve só como imagem de partida.
- **Saída** (todas sem perdas e testadas): PNG (recomendado), BMP, TIFF com LZW, WebP sem perdas (`exact=True`).
- **Limites:** ficheiros até 100 MB (entrada e resultado), imagens até 40 MP, lado mínimo de 8 px.

## 4. Interface (estado actual)

- **Cabeçalho fixo** (`st.container(key="headerbar")`): o sticky é aplicado ao `stLayoutWrapper` pai, através de `:has()`. Mostra o logótipo e o nome à esquerda. À direita mostra a identificação académica e um botão de navegação: **Ver resultado** quando existe um resultado, ou **Voltar ao laboratório** quando se está na página de resultado.
- **Separadores:** Esconder mensagem · Extrair mensagem · Como funciona? · Sobre o projecto. Rodapé com os dados académicos.
- **Esconder:** carregar imagem (pré-visualização, metadados, capacidade) → escrever a mensagem (contador, barra de ocupação) → encriptação opcional (palavra-passe e confirmação) → escolher o formato → botão.
  - O botão fica activo assim que há imagem, e a validação é feita no clique. Motivo: o Streamlit só confirma o texto ao sair do campo, e um botão desactivado obrigaria o utilizador a clicar duas vezes.
  - Depois de esconder, a app reabre o ficheiro gerado e extrai a mensagem de novo (autoverificação). Em seguida muda para a **página de resultado** (`st.session_state.view = "result"`) e faz scroll para o topo.
- **Página de resultado:** confirmação; estatísticas (bits escritos, canais alterados, píxeis alterados, capacidade usada); original e resultado lado a lado; zoom ×12 do canto 40×20 com os píxeis alterados a verde; download; botões "Voltar e editar" e "Esconder outra mensagem".
  - O laboratório continua a ser desenhado, mas fica escondido com CSS (`.st-key-lab_view {display:none}`). Assim, a imagem e a mensagem não se perdem ao voltar. **Não troque isto por um `if` que deixe de desenhar os widgets:** o Streamlit apagaria o estado do `file_uploader`.
- **Extrair:** carregar a imagem → a app analisa o cabeçalho (identificador, versão, tamanho, se está encriptada) → pede a palavra-passe só se for necessária → extrair → caixa com a mensagem, botão Copiar (componente iframe com `navigator.clipboard` e alternativa `execCommand`) e "Guardar como .txt". Há erros claros para imagem sem payload, payload corrompido e palavra-passe errada.
- **Como funciona?:** os 4 passos, a tabela "do texto aos bits", a demonstração interactiva do LSB de um píxel, a tabela do formato do payload, e "Esteganografia ≠ Encriptação" com as limitações.

## 5. Verificação já feita

- 57 testes pytest a passar. Cobrem acentos, Unicode e emojis, mensagens longas, dimensões, original não alterado, diferença máxima de ±1, alfa, capacidade com e sem encriptação, mensagem vazia, ficheiros inválidos e extensão falsa, imagem sem payload, comprimento inválido, imagem recortada (payload truncado), CRC, JPEG que destrói o payload, todos os formatos de saída, palavra-passe errada ou em falta, **extracção num processo Python separado** (equivale a reiniciar a app) e arranque da UI.
- Teste no browser (Playwright + Chrome headless, num venv temporário fora do projecto): esconder com palavra-passe → descarregar → **reiniciar o servidor** → extrair. A palavra-passe errada foi rejeitada e a correcta devolveu o texto exacto. A imagem sem payload deu o erro esperado. A navegação da página de resultado, o sticky e o layout de telemóvel (390 px) também foram verificados.
- **Problemas conhecidos e pequenos:** o texto do uploader do Streamlit ("Upload", "25MB per file") aparece em inglês. Ao gravar, a app descarta metadados, incluindo o perfil ICC.

## 6. Perguntas que o utilizador já fez (e respostas dadas)

1. **"O tamanho do ficheiro gerado diminui; é compressão?"** O LSB não altera o número de píxeis nem de bytes de píxeis. O tamanho do *ficheiro* muda porque:
   - a compressão sem perdas é refeita pelo Pillow (PNG com nível 6);
   - os metadados (EXIF, ICC, texto) são descartados;
   - os tipos de cor podem ser convertidos.

   Medições com a imagem de demo: PNG de entrada com 1 688,7 / 529,1 / 415,3 / 674,0 KB → saída sempre com 478,7 KB e as mesmas dimensões. BMP → BMP ficou com o tamanho exactamente igual (1 728 054 bytes). O JPEG (com perdas) destrói os LSB. Ficou **oferecido, mas não feito:** preservar o perfil ICC e mostrar na página de resultado a explicação da diferença de tamanho.
2. **"O que é a 'capacidade usada'?"** É a percentagem de bits do payload (cabeçalho de 14 B + dados, ou a cifra se estiver encriptado, × 8) em relação aos bits LSB disponíveis (largura × altura × 3). Exemplo: 58 B = 464 bits ÷ 1 728 000 = 0,03%. Não é o tamanho do ficheiro nem a percentagem de píxeis ou canais alterados: cerca de metade dos LSB já tinha o valor certo, por isso "Canais alterados" ≈ "Bits escritos" ÷ 2. Uma percentagem baixa é mais discreta face à esteganálise.

## 7. Pendente / próximos passos possíveis

- `Notes.txt` (notas do utilizador) tem uma pergunta **ainda não respondida:** *"No que consiste os canais (RGB)?"* Explique que cada píxel tem três intensidades (Vermelho, Verde, Azul) de 0 a 255, ou seja, 8 bits por canal; que o LSB é o último desses bits; e que cada píxel guarda por isso 3 bits da mensagem. Ligue a explicação à demonstração do píxel no separador "Como funciona?".
- A nota também diz *"Explicar porque que a imagem criptografada aumenta de tamanho"*. A resposta geral está na pergunta 1. Acrescente que, com encriptação, o payload fica maior (sal de 16 B + token Fernet: versão, timestamp, IV, padding AES e HMAC, cerca de 73–88 B a mais), por isso mais LSB são alterados. Isto quase não afecta o tamanho do ficheiro, que depende sobretudo da compressão.
- Opcional, só se o utilizador pedir: preservar o ICC; explicar o tamanho na página de resultado; criar uma página de resultado também para a extracção; fazer commit do estado actual.

## 8. Regras de trabalho observadas

- Não destrua ficheiros existentes sem autorização. Não invente resultados de testes: corra-os.
- Mantenha a lógica de esteganografia independente do Streamlit e a encriptação separada do LSB.
- Mantenha dependências mínimas.
- Depois de mudar a UI, verifique no browser real. O `AppTest` do Streamlit não testa o upload de ficheiros.
- Para reiniciar o servidor, **não use `pkill -f "streamlit run app.py"`** dentro de um comando bash que contenha esse texto, porque mata a própria shell. Guarde o PID num ficheiro e use `kill`.

## 9. Extensão multiformato (2026-10-18, ainda não commitada)

Pedido do utilizador: aceitar outros portadores além da imagem, ter destruição/limite da mensagem e "algo mais interessante". Escolhas do utilizador: WAV, TXT, PDF/Office e vídeo; **só data de validade** (sem estado no servidor); extra **esconder ficheiros**.

- **Formato:** o cabeçalho continua com 14 bytes e VERSION=1. Nova `FLAG_META` (bit 1): os dados começam por `TIPO(1) | VALIDADE(8, Unix) | LEN_NOME(1) | NOME`. Texto sem validade não usa o bloco, por isso o formato é idêntico ao anterior. `MAX_DATA_BYTES` = 2 MB.
- **`steganography/secret.py`:** `Secret.text()` e `Secret.file()`, `make_payload`, `open_payload` (CRC → desencriptar → metadados → validade → UTF-8), `estimate_size`, `RevealResult` (`.message`, `.secret`, `.is_file`). Lança `ExpiredMessageError`.
- **`steganography/carriers/`:** `open_carrier(data, name)` detecta o tipo pela assinatura; `hide(carrier, secret, pw, fmt) -> Output(data, ext, mime)`; `reveal(carrier, pw, now)`.
  - `image.py`: LSB RGB.
  - `audio.py`: WAV, LSB no byte baixo de cada amostra.
  - `video.py`: FFmpeg. O vídeo é copiado com `-c:v copy` e o payload vai em LSB no áudio PCM s16le, num `.mkv`. O demuxer é imposto (`mov`/`matroska`); AVI não é aceite. Se não houver som, cria-se silêncio.
  - `text.py`: largura zero U+200B/200C/200D/2060, 2 bits por carácter, inseridos depois do 1.º espaço.
  - `pdf.py`: linhas `%STGL:` em base64 antes do último `startxref`.
  - `archive.py`: comentário ZIP (DOCX/XLSX/PPTX/ODT/EPUB/ZIP), até 65 535 B.
- **Decisão sobre o vídeo:** os LSB nos fotogramas obrigariam a FFV1 sem perdas (medido: 4,7 MB → 130 MB por 10 s em 720p). As *zones* `q=0` do x264 não são exactas (testado). O áudio dá 4,7 → 5,7 MB.
- **UI (`app.py`):**
  - a cobertura aceita todos os tipos (`COVER_TYPES`), com pré-visualização e avisos por tipo;
  - o segredo pode ser "Mensagem de texto" ou "Ficheiro";
  - validade: Sem limite / 1 hora / 24 horas / 7 dias / Personalizada;
  - a página de resultado é diferente para cada tipo (zoom, leitores de áudio, caracteres invisíveis coloridos, bloco PDF, hexdump do ZIP);
  - a extracção trata ficheiros (download) e segredos expirados.
  - `.streamlit/config.toml`: `maxUploadSize = 100`.
- **Alterações do utilizador que devem ser respeitadas:** retirou os separadores "Como funciona?" e "Sobre" do `main()` (as funções continuam no ficheiro) e mudou o subtítulo e o `header_tag`. **Atenção:** `ui/components.py` `header_tag()` tem um `<div class="sl-tag">` aninhado que não é fechado; o utilizador ainda não foi avisado.
- **Verificação:**
  - 96 testes (`tests/test_carriers.py` é novo; o teste do demo de bits foi substituído porque o separador saiu);
  - um DOCX real criado pelo LibreOffice, com segredo, abriu e converteu-se no LibreOffice;
  - o PDF com segredo passou no `pdfinfo`;
  - Playwright + Chrome: MP4 + PDF secreto + palavra-passe + 24 h → resultado → download do .mkv → palavra-passe errada recusada → PDF recuperado idêntico (`cmp`); TXT com caracteres invisíveis.
  - **Nota para testes no browser:** confirme os campos de palavra-passe com Enter. O Tab vai para o botão "olho" e o Streamlit não confirma o valor.
- **Documentos:** README actualizado (secções 6 e 7 novas, renumeração até 16) e `GUIA_APRESENTACAO.md` (explicação de cada técnica para a apresentação, com as perguntas do `Notes.txt`).
- **Pendente:** hospedar a app (`Notes.txt`: "Hospedar app"). A Vercel não executa Streamlit; o Streamlit Community Cloud precisa de `packages.txt` com `ffmpeg` para o vídeo. Ainda nada foi commitado.
