Você é meu assistente de instalação da skill. O **Forja** já está preparado (`./kit.sh doctor` passou) e a pasta do kit é `<CAMINHO_DO_KIT>`.

Objetivo: instalar a skill da `forja` no **meu agente** (Claude Code, Codex, Gemini CLI ou outro), para que ele saiba operar a CLI sem eu repetir as regras.

Passos:
1. Copie a pasta `skills/forja/` do kit para o diretório de skills do meu agente:
   - **Claude Code pessoal**: `~/.claude/skills/forja/` (vale para todos os projetos).
   - **Claude Code do projeto**: `.claude/skills/forja/` (fica junto do projeto).
   - **Agentes que leem `AGENTS.md`** (Codex, Gemini CLI e outros): acrescente ao `AGENTS.md` do projeto o bloco do `AGENTS.md` do kit, ou aponte para `skills/forja/SKILL.md`.
2. Não copie `.env`, chaves, `projects/` nem `work/` para o diretório de skills. A skill é só texto.
3. Verifique a instalação pedindo ao agente (em uma sessão nova) para rodar `forja --json describe` — ou `./kit.sh run --json describe` dentro do kit — e relatar: comandos, workflows `dub` e `storyboard`, passos e códigos de saída. Se ele não souber responder, a skill não foi carregada.
4. Explique em **3 linhas** o ciclo que a skill ensina:
   - `status`: `forja --json status` mostra o estado e a próxima ação (`next_actions`).
   - próximo passo: o agente faz o que só ele pode fazer (escrever `cues.json`, `storyboard.yaml`, `config.yaml`) ou roda o passo indicado.
   - `run` e `qa`: `forja --json run` executa o que mudou e `forja --json qa --strict` é o gate antes de entregar (exit 1 = reprovado).
5. Faça um teste curto: peça ao agente para listar os passos do workflow `dub` e dizer onde ficam `out/video.mp4` e `out/qa.json`.

Critério de pronto: o agente novo responde ao `describe` e repete o ciclo sem eu explicar. Reporte o caminho onde a skill foi instalada, a resposta do agente e o que ficou pendente. Diga o que **não verificou**: se o agente realmente carrega a skill em todas as sessões e se ele respeita as regras de segurança na prática.
