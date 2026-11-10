Você é meu assistente de dublagem. O projeto `projects/<NOME>` já tem `work/transcript.json`. Preciso saber **quem fala em cada trecho** e **quando aparece a tarja com o nome da pessoa** (lower-third) para a legenda nunca cobrir a tarja.

Ciclo: `init` → `transcribe` → `frames` → `cues.json` → `check` → `voices` → `run` → `qa --strict`. Aqui estamos no `frames`.

1. Rode `./kit.sh run --project /projects/<NOME> --json frames --every 2`. Ele grava quadros reduzidos a **640 px** em `work/frames/`, com o **tempo no nome** (`t0004.0s.jpg`), e uma folha de contato `work/frames/contact.jpg`. O tempo de cada quadro é o do nome do arquivo.
2. Olhe a folha de contato e depois os quadros (abra as imagens; não adivinhe pelo nome). Para cada trecho de fala do `transcript.json`, descubra quem fala: pelo quadro em que a pessoa aparece, pelo nome na tarja e pelo contexto. Quando houver dúvida, marque `"confianca": "baixa"` em vez de chutar.
3. Monte a **lista de falantes**: id curto (`narradora`, `voluntario`, `entrevistada`…), nome como aparece na tela, gênero e faixa etária **aparentes** (só para escolher voz depois; trate como palpite e diga que é palpite), e o intervalo de tempo de cada fala.
4. Monte `projects/<NOME>/lower_thirds.json`: lista de `[inicio, fim]` em segundos em que existe tarja de nome na tela. Use quadros a 1 s ou mais finos nas bordas para achar início e fim com precisão de ±0,3 s. Exemplo: `[[7.3, 8.7], [23.7, 25.2]]`.
5. Rode `./kit.sh run --project /projects/<NOME> --json status` e confira `next_actions` antes de seguir.
6. Mostre a tabela (falante, nome, gênero aparente, intervalos) e a lista de tarjas **para eu corrigir** antes de seguir.

Regras: não use reconhecimento facial para dizer quem a pessoa "é" — use só o que está escrito na tarja ou dito no áudio. Dados de pessoas ficam neste computador; não envie as imagens para nenhum serviço que eu não tenha autorizado. Reporte a tabela, as tarjas e as dúvidas. Diga o que **não verificou**: a identidade real das pessoas e a exatidão das bordas da tarja fora dos quadros analisados.
