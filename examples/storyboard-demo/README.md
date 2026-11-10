# Exemplo: vídeo por cenas

Demonstração mínima do workflow `storyboard`: uma cena com clipe, narração, legenda e trilha, e
outra com um card. Os assets são gerados localmente (sem direitos autorais) por `make-assets.sh`.

## Como rodar

Dentro do kit:

```bash
./kit.sh run --json init /projects/demo-cenas
cp examples/storyboard-demo/storyboard.yaml projects/demo-cenas/
cp examples/storyboard-demo/make-assets.sh projects/demo-cenas/
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/projects/demo-cenas:/w" -w /w \
  --entrypoint sh forja:0.1 make-assets.sh
```

A narração da cena `abertura` é gerada **por você**, com a sua conta/ferramenta: salve um WAV PCM
válido em `projects/demo-cenas/voices/abertura.wav`. O caminho é o mesmo `id` da cena no
`storyboard.yaml`.

Para um teste **sem voz** (só para conferir o pipeline), use o provedor `mock`:

```bash
# em projects/demo-cenas/config.yaml
voices:
  provider: mock
```

Depois:

```bash
./kit.sh run --json --project /projects/demo-cenas run
./kit.sh run --json --project /projects/demo-cenas qa --strict
```

O resultado fica em `projects/demo-cenas/out/video.mp4` (1280×720, com áudio) e
`projects/demo-cenas/out/legendas.srt`.

## O que o exemplo mostra

- `clip`: vídeo de fundo (`assets/clip.mp4`).
- `narration`: fala da cena; a duração da cena vem da narração + respiros.
- `captions`: legenda queimada, alinhada à fala.
- `card`: imagem (`assets/card.png`) centralizada na segunda cena.
- `music`: trilha (`assets/trilha.wav`) com `license.kind: cc0` (gerada localmente).
