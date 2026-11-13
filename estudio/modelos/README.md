# Modelos de peças Instagram (LEO / Lions)

Duas camadas. Marcas: **so LEO e Lions**. O programa Leo-Lion nao e marca de pagina; so entra em publicacao pontual que o mencione. Dos gráficos oficiais usamos **apenas a parte artistica**.

Duas camadas. **`default/` é a referência 1:1 dos gráficos oficiais** e não se altera por personalização. **`personalizacoes/` guarda só configuração** que herda dele.

```
estudio/modelos/
  default/
    templates/            HTML dos modelos oficiais (sem clube, sem AL)
    pecas.json            peças default (texto oficial em inglês)
    medidas.json          medidas do oficial (entrada do gate de paridade)
  personalizacoes/
    leo/                              marca LEO (emblema LEO no lugar do lockup Leo-Lion)
      distrito-leo-lc6/               Distrito LEO LC-6
        clube-taquaritinga/           LEO Clube de Taquaritinga
    lions/                            marca Lions
      distrito-lc6/                   Distrito LC-6
        clube-taquaritinga/           Lions Clube de Taquaritinga
```

## Herança
`default` → marca (`leo`/`lions`) → distrito → clube. Cada pasta tem um `custom.json` com `extends` apontando para o nível acima. Uma mudança no `default` vale para todos; uma mudança de clube não afeta outro clube.

## O que uma personalização pode mudar
`nome`, `marca`, `textos` (clube, período, copy padrão), `logos` (principal e extras, ver abaixo), `hashtags`, `fotos`.

## O que ela NÃO pode mudar
Fonte, cores da paleta, opacidades, geometria das faixas e da cunha, posição e tamanho dos elementos: tudo o que está em `default/medidas.json`. Quem precisar disso muda o `default` (e o gate de paridade confere).

## Story e zona segura
O `default` vertical mantem o texto a 110 px da base, igual ao oficial (o verificador de zona segura de story acusa 1 aviso). A elevacao do bloco de texto acontece **apenas** na personalizacao do story (`formatos.story.elevacao_zona_segura`), nunca no `default`. Decisao do dono, 2026-11-13.

## Logos adicionais (AL do clube e do distrito)
Entram na personalização, ao lado do emblema principal, em slots definidos pelo `default`. As regras de espaço livre, tamanho mínimo e co-branding **vêm do relatório de análise dos guias** (`.work/reports/an-guias-lions-01.md`); o slot só é desenhado depois dele.

## Estado
- Pronto: `default` vertical (1080×1920) e quadrado (1080×1080), com emblema LEO (branco onde o oficial usa logo branca, colorido onde usa colorida). O emblema branco e **derivado** do oficial (`logos/Derivados_LEO/`, fora do repo): a biblioteca so tem 2 cores.
- Pendente: horizontal 1920×1080 (a largura de 1080 px está fixa em templates, no compose e no render), gate de paridade, resolvedor de herança, personalizações.
- Os arquivos oficiais (imagens, logos, fontes) ficam no acervo privado e **não** entram neste repositório.
