# Política de segurança

## Versões suportadas

| Versão | Suporte |
|---|---|
| 0.1.x | sim |

## Como reportar uma vulnerabilidade

**Não abra uma issue pública para uma vulnerabilidade.** Use o canal privado do GitHub:
[Security Advisories](https://github.com/alisonglima/forja/security/advisories/new).

Inclua, se possível:

- versão do Forja e do Docker/Compose;
- sistema operacional e arquitetura;
- passos para reproduzir, com o menor comando possível;
- impacto observado e o que você já descartou;
- saída literal de erro, **sem chaves, senhas ou dados pessoais**.

Você receberá uma confirmação em até 7 dias. Corrigiremos e coordenaremos a divulgação responsável
antes de tornar o problema público.

## Escopo

O Forja roda localmente e não tem servidor próprio. Os pontos de atenção são:

- a CLI e o kit (execução de subprocessos, caminhos, YAML/JSON, cache);
- o container (usuário não-root, capacidades, volumes, portas);
- o Chromium opcional (CDP só em loopback, perfil e senha);
- prompts e documentação que possam induzir a más práticas.

Não fazem parte do escopo: vulnerabilidades do ffmpeg/Chrome/Remotion/Docker em si (reporte ao
projeto upstream), contas de terceiros e conteúdo de mídia que você não forneceu.

## Boas práticas para usuários

- Não use o kit com mídia ou `storyboard.yaml` de origem desconhecida sem revisar.
- Mantenha o navegador opcional apenas em `127.0.0.1` e com senha.
- Se você optar por um provedor de voz por API, mantenha a chave só no `.env`.
- Rode `./kit.sh browser-reset` e revogue a sessão ao terminar em máquina compartilhada.
