# HBJ Novo — Hinário Brados de Júbilo (PWA)

App instalável (Android e iPhone) com os 541 hinos do HBJ, para a Igreja Adventista da Promessa — Vila Camargo.

- **Link público:** https://brado-de-jubilo.netlify.app/
- **Hospedagem:** Netlify, projeto `brado-de-jubilo` (time da conta digitalmktsilvana), publica sozinho a cada `git push` na branch `main`
- **Repositório:** https://github.com/interalibpofinanceiro-dotcom/hbj-novo
- **Funciona offline** depois do 1º acesso (service worker em `sw.js`).

## Arquivos

| Arquivo | O que é |
|---|---|
| `index.html` | O app inteiro (lista, busca, favoritos, leitor, Sobre/DEMAP, instalação) |
| `hinos.json` | Os 541 hinos — `numero`, `titulo`, `creditos`, `tom`, `estrofes`, `coros` (índices das estrofes em itálico no original), `nota` |
| `sw.js` | Cache offline. **Trocar `VERSAO` a cada publicação.** |
| `manifest.webmanifest`, `icons/` | Ícones gerados do logo da Promessa |
| `tools/extract.py` + `tools/build_hymns.py` | Regeneram `hinos.json` a partir do PDF |
| `tools/data/` | Intermediários (fora do git) |

## Fidelidade ao texto

As palavras são **exatamente** as do PDF `HBJ - Hinário Brados de Júbilo.pdf.pdf`. O `build_hymns.py`
verifica isso a cada execução (para se qualquer palavra divergir). O script só decide as quebras
de linha/estrofe, porque o PDF (Canva) quebra linhas pela largura da caixa.

Casos conhecidos do PDF original:
- Hinos **30** e **324** não têm título no PDF — títulos tirados do índice do próprio hinário ("Refúgio", "Graças dou").
- Hino **124** não tem letra no PDF (só título e créditos) — o app avisa isso.

## Corrigir um hino

Editar direto o `hinos.json` (ex.: uma quebra de linha), trocar `VERSAO` no `sw.js` e publicar:

```
git add -A
git commit -m "Corrige hino N"
git push
```

Em ~1 min o Netlify atualiza; os celulares pegam a versão nova na próxima abertura com internet.

## Regenerar tudo a partir do PDF

```
cd tools
python extract.py "../../HBJ - Hinário Brados de Júbilo.pdf.pdf" data/stage1.json
python build_hymns.py data/stage1.json data/index_titles.json ../hinos.json
```
(Atenção: isso sobrescreve correções manuais feitas no `hinos.json`.)
