# StegoLab — Guia de explicação para a apresentação

Segurança Informática · Docente Martina de Barros · Universidade Pedagógica de Maputo · 2.º semestre 2026
Grupo: Samuel Massinga e Adilson Chaguala

Este guia explica cada parte do StegoLab: o que é, como funciona, as vantagens, as desvantagens e para que serve. Cada secção acaba com uma frase curta, **"Para dizer"**, que pode ser usada tal como está na apresentação.

> **Aviso de honestidade:** o enunciado tem também uma tarefa com Steghide/Stegosuite, que este protótipo não cobre. Não o apresentem como resposta completa ao enunciado, a menos que a docente tenha dispensado essa tarefa.

---

## 1. Esteganografia: a ideia central

**O que é.** Esteganografia (do grego *steganos*, "coberto", e *graphein*, "escrever") é esconder uma mensagem dentro de algo que parece inofensivo: uma fotografia, uma música, um documento. O objectivo é que ninguém **suspeite** que a mensagem existe.

**Diferença para a encriptação.**

| | Esteganografia | Encriptação |
|---|---|---|
| Protege | A **existência** da mensagem | O **conteúdo** da mensagem |
| Um observador vê | Um ficheiro normal | Texto ilegível: sabe que há um segredo |
| Se for descoberta | Pode ser lida | Continua ilegível sem a chave |

O StegoLab **combina as duas**: primeiro encripta (opcional) e depois esconde.

**Vantagens da esteganografia hoje.**
- **Discrição:** uma mensagem cifrada chama a atenção, uma fotografia de férias não. Isto é útil em países com censura, onde usar criptografia pode, por si só, ser suspeito.
- **Marcas de água digitais:** editoras, estúdios e bancos de imagens escondem identificadores em imagens, músicas e filmes para provar autoria e descobrir quem divulgou uma cópia.
- **Rastreio de documentos:** as impressoras a cores imprimem pontos amarelos quase invisíveis com o número de série e a data.
- **Integridade e autenticidade:** pode esconder-se um código de verificação dentro do próprio ficheiro.
- **Ensino e investigação:** perceber como funciona é o primeiro passo para a detectar.

**Desvantagens e riscos.**
- Não é indetectável: a **esteganálise** (análise estatística) consegue detectar alterações.
- É frágil: comprimir, redimensionar ou converter destrói a mensagem.
- Também é usada por **malware**, que esconde código ou comandos em imagens, e para **fugas de dados** de empresas. É por isso que interessa à Segurança Informática: quem defende uma rede tem de saber que este canal existe.

**Para dizer:** "A criptografia torna a mensagem ilegível; a esteganografia torna-a invisível. O StegoLab faz as duas coisas."

---

## 2. O que são os canais RGB (pergunta do `Notes.txt`)

Uma imagem digital é uma grelha de **píxeis**. Cada píxel tem três números, os **canais**:

- **R** (*Red*, vermelho), **G** (*Green*, verde) e **B** (*Blue*, azul);
- cada canal vai de **0 a 255**, ou seja, ocupa **8 bits** (1 byte);
- a cor que vemos é a mistura dos três: `(255, 0, 0)` é vermelho puro, `(255, 255, 255)` é branco e `(58, 123, 213)` é um azul.

Algumas imagens têm um quarto canal, o **alfa** (transparência). O StegoLab **não lhe toca**: só usa R, G e B.

**Ligação ao LSB:** cada canal tem 8 bits, e o último é o bit menos significativo. Por isso **cada píxel guarda 3 bits da mensagem**, um em cada canal.

**Para dizer:** "Cada píxel tem três números, vermelho, verde e azul, de 0 a 255. Nós alteramos apenas o último bit de cada um."

---

## 3. O algoritmo LSB (o coração do projecto)

**Como funciona.** O **LSB** (*Least Significant Bit*) é o bit da direita, o que vale menos. Trocá-lo altera o valor em **no máximo 1**:

```
Canal vermelho = 200 = 1100100[0]
Bit da mensagem = 1
(200 & 0b11111110) | 1 = 1100100[1] = 201     ← a cor passou de 200 para 201
```

- `& 0b11111110` apaga o último bit;
- `| bit` escreve o bit da mensagem;
- para ler, basta `valor & 1`.

**Passo a passo para esconder** (ficheiro `steganography/encoder.py`):
1. O texto é convertido em bytes **UTF-8**, o que suporta acentos e emojis ("á" ocupa 2 bytes).
2. Se houver palavra-passe, os bytes são encriptados.
3. É acrescentado um **cabeçalho** de 14 bytes (secção 4).
4. Tudo é convertido em bits: cada byte dá 8 bits.
5. Os bits são escritos, por ordem, nos LSB dos canais R, G, B, R, G, B…, linha a linha, a partir do canto superior esquerdo.
6. É criada uma **imagem nova**. A original nunca é alterada.

**Passo a passo para revelar** (ficheiro `steganography/decoder.py`):
1. Lê os primeiros 112 LSB (14 bytes) e verifica se começam por `STGL`.
2. Lê o **comprimento** e valida-o contra a capacidade.
3. Lê **apenas** os bits necessários.
4. Verifica o **CRC32**, desencripta se for preciso e converte para texto.

**Porque é invisível.** Uma diferença de 1 em 255 (0,4%) está muito abaixo do que o olho humano distingue. Cerca de **metade** dos bits já tem o valor certo e nem muda. Por isso, na página de resultado, "Canais alterados" é aproximadamente metade de "Bits escritos".

**Vantagens:** simples, rápido, capacidade grande e diferença imperceptível.
**Desvantagens:**
- frágil: JPEG, redimensionar ou recortar destroem a mensagem;
- detectável por esteganálise, por exemplo com o teste do qui-quadrado sobre os pares de valores;
- os bits ficam todos no início da imagem, sem dispersão aleatória.

**Para dizer:** "Mudamos cada cor no máximo em 1 unidade em 255. O olho não vê, mas o computador lê."

---

## 4. O cabeçalho STGL e o CRC32

Antes da mensagem, o StegoLab escreve 14 bytes:

| Campo | Tamanho | Para que serve |
|---|---|---|
| `STGL` | 4 B | "Assinatura": sem ela, a app diz que não há segredo |
| Versão | 1 B | Permite evoluir o formato |
| Flags | 1 B | Bit 0 = encriptado · Bit 1 = tem metadados (ficheiro/validade) |
| Comprimento | 4 B | Quantos bytes ler (sabemos onde a mensagem acaba) |
| CRC32 | 4 B | Código de verificação: detecta dados corrompidos |

**Porque é importante:** sem cabeçalho, a app não sabe se existe mensagem nem onde termina. Leria "lixo". Com o CRC32, se alguém alterar a imagem (por exemplo, convertê-la para JPEG), a app **detecta** o problema em vez de mostrar texto errado.

**Para dizer:** "O cabeçalho é como o envelope da carta: diz que há carta, de que tamanho é, e tem um selo que prova que ninguém a abriu."

---

## 5. Capacidade e "capacidade usada" (pergunta do `Notes.txt`)

**Capacidade** (imagem) = largura × altura × 3 bits ÷ 8 − 14 bytes de cabeçalho.
Exemplo: a imagem de demonstração tem 960 × 600 píxeis → 960 × 600 × 3 ÷ 8 − 14 = **215 986 bytes** (cerca de 211 KB).

**Capacidade usada** = bits do payload (cabeçalho + dados) ÷ bits disponíveis × 100.
Exemplo: uma mensagem de 44 bytes dá 58 bytes de payload = 464 bits. A imagem tem 1 728 000 bits disponíveis, logo usa **0,03%**.

**Não é** o tamanho do ficheiro, **nem** a percentagem de píxeis alterados. Quanto menor, mais discreta é a mensagem: menos bits alterados significam menos sinais estatísticos.

**Para dizer:** "Usámos três centésimas por cento da capacidade. É quase nada, e por isso é muito difícil de detectar."

---

## 6. Porque é que o tamanho do ficheiro muda (pergunta do `Notes.txt`)

**O LSB não muda o número de píxeis nem de bytes de cor.** O que muda o tamanho do *ficheiro* é outra coisa:

1. **Compressão sem perdas refeita:** o PNG é comprimido. O StegoLab volta a gravá-lo com o nível de compressão do Pillow, que pode ser maior ou menor do que o do programa original. Por isso o ficheiro pode **diminuir**, como no vosso teste.
2. **Metadados descartados:** EXIF (dados da câmara), perfil de cor ICC e textos internos.
3. **Ruído nos LSB:** bits aleatórios comprimem pior. Uma mensagem grande pode **aumentar** um pouco o PNG.

**Prova:** BMP → BMP (sem compressão) dá **exactamente o mesmo tamanho** (1 728 054 bytes, medido).

**E com encriptação?** O payload fica maior porque o Fernet acrescenta:
- sal de 16 bytes;
- versão, data, IV e HMAC (57 bytes);
- 1 a 16 bytes de enchimento.

São cerca de **74 a 89 bytes a mais**. São mais bits alterados, mas o efeito no tamanho do ficheiro é desprezável: o tamanho depende sobretudo da compressão.

**Para dizer:** "O LSB não acrescenta píxeis. O tamanho muda por causa da compressão e dos metadados, e um BMP prova-o: fica com o mesmo tamanho ao byte."

---

## 7. Encriptação opcional (Fernet + PBKDF2)

**Como funciona.**
1. A palavra-passe passa pelo **PBKDF2-HMAC-SHA256** com 480 000 iterações e um **sal** aleatório de 16 bytes. O resultado é uma chave de 256 bits. As 480 000 iterações tornam muito lento adivinhar palavras-passe por força bruta.
2. A mensagem é cifrada com **Fernet** (AES-128 em modo CBC + **HMAC-SHA256**), da biblioteca `cryptography`. Não criámos nenhum algoritmo próprio, o que é uma boa prática.
3. O HMAC garante **autenticidade**: com a palavra-passe errada, ou se alguém alterar um único bit, a desencriptação falha com um erro claro.

**Vantagens:** mesmo que alguém descubra a mensagem escondida, não a consegue ler.
**Desvantagens:** uma palavra-passe fraca continua fraca. Se a palavra-passe se perder, a mensagem perde-se.

**Para dizer:** "Se a esteganografia falhar e alguém encontrar a mensagem, a encriptação é a segunda porta fechada."

---

## 8. Os outros portadores

O tipo de ficheiro é reconhecido pelos **primeiros bytes** (a "assinatura"), nunca pela extensão. Um ficheiro `foto.png` que na verdade é texto é tratado como texto.

### 8.1 Áudio WAV — LSB nas amostras

**Como funciona.** Um WAV guarda o som como uma sequência de **amostras**, números que descrevem a posição da onda sonora milhares de vezes por segundo (44 100 vezes, num CD). Num WAV de 16 bits, cada amostra vai de −32 768 a 32 767. O StegoLab muda o LSB de cada amostra: uma diferença de **1 em 65 536**, que é inaudível.

- **Capacidade:** amostras × canais ÷ 8 − 14 bytes. Um minuto em estéreo a 44,1 kHz dá cerca de 646 KB.
- **Vantagens:** grande capacidade, o ficheiro fica com **exactamente o mesmo tamanho** e é o mesmo LSB das imagens.
- **Desvantagens:** converter para MP3/AAC, ou enviar por WhatsApp, destrói a mensagem. MP3, OGG e FLAC não são aceites como portador.
- **Usos reais:** marcas de água em músicas, para identificar cópias piratas.

**Para dizer:** "No som é igual às imagens: em vez de cores, mudamos a amplitude da onda em 1 unidade em 65 536."

### 8.2 Vídeo — LSB na faixa de áudio (requer FFmpeg)

**Como funciona.**
1. O FFmpeg lê o vídeo (MP4, MOV, MKV, WebM).
2. O **fluxo de imagem é copiado sem recodificar**: não perde qualidade nem é alterado.
3. A **faixa de som** é convertida em PCM de 16 bits (sem perdas) e o segredo é escrito nos LSB das amostras, como no WAV.
4. Vídeo e som são juntos num ficheiro **.mkv** (Matroska). Se o vídeo não tiver som, é criada uma faixa silenciosa.

**Porque não nos píxeis dos fotogramas?** Foi testado. Para os bits sobreviverem, o vídeo inteiro teria de ser gravado sem perdas: um clipe de 10 s em 720p passou de **4,7 MB para cerca de 130 MB**. Também testámos comprimir sem perdas só os primeiros fotogramas, mas os bits não ficaram idênticos. Com a faixa de áudio, o mesmo vídeo passou de **4,7 MB para 5,7 MB**.

- **Capacidade:** cerca de 11,7 KB por segundo de som estéreo a 48 kHz.
- **Vantagens:** o vídeo fica intacto, o ficheiro cresce pouco e o segredo pode ser um ficheiro.
- **Desvantagens:**
  - precisa de FFmpeg;
  - o .mkv com som PCM é invulgar, e um analista atento pode estranhar;
  - converter para MP4 ou publicar numa rede social destrói a mensagem;
  - alguns navegadores não reproduzem o .mkv (use o VLC).

**Passo a passo para revelar um segredo num vídeo (na demonstração):**
1. Abrir o separador **Extrair mensagem**.
2. Carregar o ficheiro `nome_stego.mkv` descarregado do StegoLab. A pré-visualização mostra o primeiro fotograma.
3. A app usa o FFmpeg para extrair a faixa de áudio em PCM e lê os primeiros 112 LSB das amostras. Aparecem os indicadores **Identificador STGL ✓**, **Técnica: LSB nas amostras da faixa de áudio**, o tamanho e se está **encriptado**.
4. Se estiver encriptado, escrever a palavra-passe.
5. Clicar em **Extrair segredo**.
6. Se for texto, aparece na caixa verde (com Copiar e Guardar como .txt). Se for um ficheiro, aparece o cartão com o nome e o botão **Descarregar**. Se a validade tiver passado, aparece **Segredo expirado**.
7. *Contraprova:* carregar o vídeo **original** (.mp4) → "Nenhum segredo StegoLab encontrado".

**Para dizer:** "Não tocámos numa única imagem do vídeo. O segredo viaja no som, e a diferença é de uma unidade em 65 mil."

### 8.3 Texto — caracteres invisíveis (largura zero)

**Como funciona.** O Unicode tem caracteres que **não ocupam espaço** no ecrã. O StegoLab usa quatro deles, e cada um representa **2 bits**:

| Carácter | Bits |
|---|---|
| U+200B (*zero width space*) | 00 |
| U+200C (*zero width non-joiner*) | 01 |
| U+200D (*zero width joiner*) | 10 |
| U+2060 (*word joiner*) | 11 |

Cada byte do segredo passa a ser 4 caracteres invisíveis, inseridos depois do primeiro espaço do texto. O texto **visível fica exactamente igual**. Na página de resultado, os caracteres aparecem como blocos coloridos.

- **Vantagens:** funciona com texto simples; o "esconderijo" é muito discreto à vista.
- **Desvantagens:**
  - o ficheiro cresce 12 bytes por cada byte escondido (cada carácter invisível ocupa 3 bytes em UTF-8);
  - algumas aplicações removem estes caracteres ao copiar e colar;
  - um editor que mostre caracteres especiais revela-os;
  - limite de 64 KB.
- **Usos reais:** "impressões digitais" em textos internos de empresas, para descobrir quem divulgou um documento.

**Para dizer:** "O texto parece igual, mas entre duas palavras há centenas de caracteres que não se vêem."

### 8.4 PDF — comentários na estrutura

**Como funciona.** Em PDF, tudo o que começa por `%` até ao fim da linha é um **comentário** e é ignorado pelos leitores. O StegoLab codifica o segredo em base64 e escreve-o em linhas `%STGL:...` logo **antes** da palavra `startxref`, no fim do ficheiro.

Como o bloco fica depois da tabela de referências (*xref*), nenhum endereço interno muda, e o PDF continua **válido e igual**. Foi verificado com o `pdfinfo`.

- **Vantagens:** simples, capacidade até 2 MB, o PDF abre e imprime normalmente.
- **Desvantagens:** **não é LSB**. É "ocultação na estrutura", e quem abrir o PDF num editor de texto vê o bloco. Programas que voltam a gravar ou "optimizam" o PDF removem os comentários. **Use sempre palavra-passe.**

**Para dizer:** "No PDF não há píxeis para alterar. Usamos os comentários do próprio formato, que nenhum leitor mostra."

### 8.5 Word, Excel, PowerPoint, LibreOffice — comentário do ZIP

**Como funciona.** Um `.docx`, `.xlsx`, `.pptx` ou `.odt` é na verdade um **arquivo ZIP** com ficheiros XML lá dentro. O formato ZIP permite um **comentário** de até 65 535 bytes no fim. O Word, o Excel e o LibreOffice ignoram-no. O StegoLab escreve aí o segredo, sem tocar em nenhum ficheiro interno. Foi testado: um DOCX com segredo abriu e converteu-se no LibreOffice sem problemas.

- **Vantagens:** o documento abre normalmente e os ficheiros internos ficam idênticos.
- **Desvantagens:** limite de 64 KB; **não é LSB** e é visível num editor hexadecimal; se o documento for **gravado de novo** no Word, o comentário desaparece.

**Para dizer:** "Um ficheiro Word é um ZIP disfarçado. Escondemos o segredo no comentário do ZIP, que o Word nem lê."

### Resumo comparativo

| Portador | Técnica | Discrição | Robustez | Capacidade |
|---|---|---|---|---|
| Imagem | LSB (cores) | Alta | Baixa (JPEG destrói) | Alta |
| WAV | LSB (amostras) | Alta | Baixa (MP3 destrói) | Alta |
| Vídeo | LSB (áudio) | Média (.mkv + PCM) | Baixa (MP4 destrói) | Média |
| Texto | Largura zero | Média | Baixa (copiar e colar) | Baixa |
| PDF | Comentários | Baixa (editor de texto) | Média | Alta |
| Office | Comentário ZIP | Baixa (editor hexadecimal) | Baixa (gravar de novo) | Baixa |

---

## 9. Esconder ficheiros (não só texto)

**Como funciona.** Em vez de uma mensagem, pode esconder-se um **ficheiro** qualquer (PDF, ZIP, imagem…) até 2 MB, se couber no portador. O StegoLab guarda o **nome** do ficheiro num pequeno bloco de metadados:
- tipo (1 byte);
- validade (8 bytes);
- comprimento do nome (1 byte);
- o nome.

Esse bloco também é encriptado se houver palavra-passe.

**Segurança:** o nome é limpo (`../../etc/passwd` passa a `passwd`) e o ficheiro recuperado **nunca é aberto nem executado** pela aplicação: só é entregue para download.

**Usos:** enviar um documento confidencial dentro de uma fotografia; guardar uma chave ou um certificado dentro de um ficheiro inocente.

**Para dizer:** "Não escondemos só frases: escondemos um PDF inteiro dentro de um vídeo, com palavra-passe."

---

## 10. Data de validade (autodestruição limitada)

**Como funciona.** Ao esconder, escolhe-se *1 hora*, *24 horas*, *7 dias* ou uma data. A data vai no bloco de metadados. Ao revelar, se a data já passou, a aplicação mostra **"Segredo expirado"** e recusa revelar.

**Com palavra-passe**, a data fica **dentro da cifra** e é autenticada pelo HMAC: quem não tem a palavra-passe não a consegue alterar. Sem palavra-passe, a app avisa que a data pode ser alterada.

**Limite honesto (importante dizer à docente):** o ficheiro gerado é uma cópia que sai da aplicação. **Nenhuma aplicação consegue apagar cópias que já estão noutro computador.** A validade é uma regra aplicada pelo StegoLab: quem tiver a palavra-passe **e** modificar o código-fonte consegue ignorá-la.

Uma destruição "verdadeira" exigiria guardar a chave num servidor e apagá-la no fim do prazo (*crypto-shredding*). Escolhemos não o fazer, para que a extracção funcione em qualquer computador sem depender de um servidor.

**Para dizer:** "A mensagem tem prazo. Depois disso o StegoLab recusa abri-la, e com palavra-passe ninguém consegue alterar esse prazo. Mas não fingimos que apagamos ficheiros que já saíram da aplicação."

---

## 11. Arquitectura do código

```
app.py                 Interface (Streamlit) — só apresentação
steganography/         Núcleo — não depende da interface
  payload.py           Cabeçalho STGL, metadados, bytes ↔ bits
  secret.py            Segredo (texto/ficheiro), validade, encriptação
  encoder.py/decoder.py  LSB explícito: (v & 0xFE) | bit  e  v & 1
  crypto.py            Fernet + PBKDF2
  carriers/            Um módulo por tipo de ficheiro (imagem, WAV, vídeo, texto, PDF, ZIP)
tests/                 96 testes automáticos
```

**Porque está organizado assim:**
- A lógica **não depende** da interface: pode ser testada sozinha.
- A encriptação está **separada** do LSB.
- Todos os portadores partilham o **mesmo** cabeçalho, CRC32, encriptação e validade. Para acrescentar um formato novo, basta um módulo novo.

---

## 12. Testes (como demonstrar)

```bash
python -m pytest -v
```

Resultado: **96 testes passaram** (Linux, Python 3.12.3, FFmpeg 6.1.1). Exemplos que vale a pena mencionar:
- `test_extraction_works_in_a_separate_process`: a extracção funciona depois de reiniciar a app;
- `test_jpeg_compression_destroys_payload`: prova que o JPEG destrói a mensagem e que o CRC o detecta;
- `test_pixel_values_change_at_most_by_one`: nenhuma cor muda mais de 1;
- `test_expired_secret_is_refused`: a validade funciona;
- `test_zip_members_are_untouched`: o Word continua intacto;
- `test_secret_filename_is_sanitised`: os nomes perigosos são limpos.

---

## 13. Segurança da própria aplicação

- Os ficheiros são validados pelo **conteúdo**, não pela extensão.
- Os ficheiros carregados **nunca são executados**.
- O FFmpeg é chamado sem shell, com tempo limite e com o formato imposto, para que um vídeo malicioso não consiga activar outros formatos (é também por isso que o AVI não é aceite).
- Mensagens e palavras-passe não vão para logs, e a telemetria do Streamlit está desligada.
- Os erros aparecem como mensagens claras, sem detalhes técnicos internos.

---

## 14. Roteiro sugerido (5–7 minutos)

| Tempo | Quem | O que fazer e dizer |
|---|---|---|
| 0:00–1:00 | Samuel | Problema: comunicar sem levantar suspeitas. Esteganografia ≠ encriptação (secção 1). |
| 1:00–2:30 | Adilson | Imagem: carregar `assets/demo_paisagem.png`, escrever a mensagem, activar a palavra-passe e esconder. Na página de resultado, mostrar a capacidade usada, os canais alterados e o zoom (secções 2, 3 e 5). Descarregar. |
| 2:30–3:30 | Samuel | Extrair: palavra-passe errada → erro; correcta → mensagem. Imagem original → "Nenhum segredo encontrado" (secção 4). |
| 3:30–4:30 | Adilson | Texto: um `.txt` com os caracteres invisíveis à vista. Vídeo: esconder e revelar (secção 8.2). |
| 4:30–5:30 | Samuel | Ficheiro + validade: esconder um PDF com validade de 1 hora e recuperá-lo; explicar o limite honesto (secções 9 e 10). |
| 5:30–6:30 | Adilson | `python -m pytest`; limitações: JPEG/MP3/MP4 destroem; PDF e Office são detectáveis (secção 8). |
| 6:30–7:00 | Samuel | Conclusão: esconder + encriptar é mais forte, mas não absoluto. |

**Antes da aula:**
- correr os testes;
- ter os ficheiros de exemplo prontos (imagem, `.txt`, vídeo curto com som, PDF pequeno);
- ter um ficheiro já gerado como plano B, com a palavra-passe anotada;
- confirmar que o FFmpeg está instalado (`ffmpeg -version`).

---

## 15. Perguntas prováveis e respostas

- **"É indetectável?"** Não. A esteganálise estatística (por exemplo, o teste do qui-quadrado) pode detectar o LSB, e o PDF e o Office são visíveis num editor. A encriptação protege o conteúdo se a mensagem for descoberta.
- **"Porque não JPEG ou MP3?"** São compressões **com perdas**: alteram exactamente os bits menos significativos. O CRC32 detecta isso (há um teste que o prova).
- **"Como sabe onde a mensagem acaba?"** Pelo campo **comprimento** do cabeçalho, validado contra a capacidade.
- **"Porque é que o vídeo sai em .mkv?"** Porque o som tem de ficar sem perdas (PCM) e o vídeo é copiado sem recodificar. O Matroska aceita qualquer combinação e mantém a rotação dos vídeos de telemóvel.
- **"A validade apaga a mensagem?"** Não apaga cópias: impede o StegoLab de a revelar (secção 10).
- **"O que acontece com uma palavra-passe errada?"** O HMAC do Fernet falha e a aplicação mostra "Palavra-passe incorrecta". Não aparece texto errado.
- **"Quem usa isto na vida real?"** Marcas de água (música, cinema, fotografia), rastreio de impressoras, jornalistas sob censura. Do lado do ataque, malware que esconde código em imagens. Daí a importância para a Segurança Informática.
