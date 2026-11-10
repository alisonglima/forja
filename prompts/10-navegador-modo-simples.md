Você é meu assistente de automação de navegador. O caminho recomendado do kit é usar **as minhas contas na interface do provedor de voz**, sem chave de API. Este prompt monta um Chrome/Chromium visível, com perfil dedicado, que você controla por CDP em `127.0.0.1:9222` sem eu perder o uso normal da máquina.

Fatos medidos que decidem o desenho:
- Janela **minimizada ou totalmente coberta conta como "oculta"** e o Chrome reduz timers e animações; **não** peça para minimizar. O correto é deixar a janela **visível em outra área de trabalho** (Windows: Win+Ctrl+D; macOS: Mission Control; Linux: outro workspace).
- O perfil precisa ser **dedicado** (`--user-data-dir`), nunca o meu perfil diário (o Chrome 136+ ignora a porta de depuração no perfil padrão).
- O login deve ser feito **por mim, dentro desse mesmo navegador**; não copie perfil/cookies entre máquinas — a sessão fica atrelada ao dispositivo. Use uma **conta dedicada** ao projeto, se possível.

Passos:
1. Descubra onde está o Chrome (`google-chrome`, `chromium`, caminho do Windows `%ProgramFiles%\Google\Chrome\Application\chrome.exe`, ou `/Applications/Google Chrome.app`).
2. Abra com: `--user-data-dir=<pasta-do-perfil-dedicado> --remote-debugging-port=9222 --no-first-run --window-size=1280,900 --window-position=60,60 https://aistudio.google.com/` (ou a interface do provedor que eu escolher). A pasta do perfil fica fora do kit e **nunca** entra em backup nem em git.
3. Espere eu fazer o login e me avise quando a página inicial aparecer.
4. Confirme o CDP: `GET http://127.0.0.1:9222/json/version` deve responder com a versão do Chrome. A porta **nunca** pode ser exposta fora de `127.0.0.1` (ela não tem autenticação: quem alcança controla o navegador e as sessões logadas).
5. Para controlar, use o **Playwright MCP** do seu agente apontando para `http://127.0.0.1:9222` (`npx @playwright/mcp@latest --cdp-endpoint http://127.0.0.1:9222`) ou o seu recurso de "computer use". Uma única instância por perfil.
6. Depois do login, use a interface para gerar a voz de cada cue e **salve o WAV** em `projects/<NOME>/voices/<id>.wav`; rode `./kit.sh run --project /projects/<NOME> --json voices --only A,B,C` para o kit validar. O kit não precisa de chave de API nesse modo.

Combine comigo, antes de começar, o que fazer se o provedor pedir captcha ou verificação extra: **pare e me chame** — não tente contornar.

Reporte o navegador encontrado, o perfil usado, o resultado do CDP e se o login apareceu. Diga o que **não verificou**: se a janela continuará ativa por muito tempo, se o provedor vai pedir verificação depois e a qualidade das vozes geradas pela interface.
