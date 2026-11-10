Você é meu assistente de infraestrutura. Quero o **Chromium rodando dentro de um container Docker**, visível numa aba do meu navegador normal, para eu fazer login com a **minha conta** e usar a interface do provedor de voz sem instalar nada nem aparecer na minha área de trabalho. Este é o caminho recomendado para contas próprias; a chave de API é opcional.

1. Garanta o `.env` (`./kit.sh setup` cria `BROWSER_PASSWORD` aleatória). Não imprima a senha; eu a pego do arquivo.
2. Suba: `./kit.sh browser-up`. Ele inicia o Chromium (imagem `linuxserver/chromium`, `linux/amd64`) e um pequeno proxy que torna o CDP alcançável **somente** em `127.0.0.1:9222` da minha máquina.
3. Eu abro **https://localhost:3001** (aceito o certificado autoassinado, entro com usuário/senha do `.env`) e faço o login do provedor **uma única vez nessa aba**. O perfil fica num **volume Docker** (`chromium-config`), nunca na imagem; sobrevive a reinícios. O login é feito **dentro deste ambiente final**; a sessão **não é movida** entre máquinas.
4. Confirme o CDP: `GET http://127.0.0.1:9222/json/version` responde; um cliente Playwright consegue `connectOverCDP("http://127.0.0.1:9222")` e listar a aba. **Não** conecte pelo nome do container (`browser:9222`): o Chromium recusa Host que não seja IP/localhost (HTTP 500).
5. Para controlar, use o Playwright MCP ou "computer use" do seu agente apontando para esse endereço. Deixe a aba `https://localhost:3001` aberta para eu acompanhar.
6. Depois do login, use a interface para gerar as vozes e salve os WAVs em `projects/<NOME>/voices/<id>.wav`; rode `./kit.sh run --project /projects/<NOME> --json voices --only A,B,C` para o kit validar. Nenhuma chave de API é necessária.

Regras de segurança: nunca publique 3001 nem 9222 fora de `127.0.0.1`; o terminal web da imagem tem `sudo` sem senha, então quem alcançar a tela vira root no container. Para terminar: `./kit.sh browser-down` (mantém o login) ou `./kit.sh browser-reset` (apaga o perfil; depois **saia das sessões** na conta do provedor). Não copie perfil/cookies entre máquinas e não compartilhe a conta.
Se o Chromium não subir por causa do sandbox, me mostre o log (`docker compose logs browser`) antes de relaxar qualquer restrição de segurança.

Reporte o estado dos containers, o resultado do CDP e o que apareceu na tela. Diga o que **não verificou**: se o provedor vai manter a sessão, se a rede da minha máquina bloqueia portas e a qualidade das vozes geradas pela interface.
