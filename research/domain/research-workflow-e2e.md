# Research Workflow End-to-End

> Este documento descreve o workflow completo de um investigador académico (PhD/postdoc), desde a definição de um tópico até à escrita final. O objectivo é mapear cada fase com detalhe suficiente para informar decisões de produto.
>
> **Status:** Draft para revisão por researcher real.
> **Reviewer:** [nome do amigo] — PhD student, valida com experiência própria.

---

## O contexto: o dia-a-dia de um researcher

Um investigador não faz apenas "research". O seu tempo divide-se entre:

- Escrever propostas de grants para financiamento
- Dar aulas / supervisionar alunos (se for professor/TA)
- Tarefas administrativas (relatórios, reuniões, comités)
- Peer review de papers de outros
- **Research propriamente dito** (o que este documento cobre)

Estima-se que ~25-33% do tempo de um researcher é gasto em pesquisa de literatura e gestão de informação, não em investigação original.

---

## Fase 0: Definição do problema / pergunta de investigação

**O que acontece:**
- O investigador identifica (ou o supervisor sugere) uma área/problema
- Pode vir de: gap num paper que leu, sugestão do supervisor, extensão de trabalho anterior, ou intuição
- Nesta fase, a pergunta é vaga: "quero investigar X" sem saber exactamente o quê sobre X

**Dores conhecidas:**
- Dificuldade em avaliar se a pergunta é "original o suficiente"
- Incerteza sobre se já foi feito por alguém
- Medo de investir meses numa direcção errada

**Ferramentas usadas:** Google Scholar (pesquisa inicial), conversa com supervisor/colegas

**Output:** Uma direcção vaga + 2-5 papers de referência iniciais

**Perguntas para o reviewer:**
- [ ] Como é que defines a tua pergunta de investigação? É um processo estruturado ou orgânico?
- [ ] Quanto tempo demoras nesta fase?
- [ ] O teu supervisor dá-te a pergunta ou tens de a descobrir?

---

## Fase 1: Pesquisa exploratória (Discovery)

**O que acontece:**
- A partir dos papers iniciais, o investigador expande a sua compreensão do campo
- Começa tipicamente com survey papers / review articles que cobrem o estado da arte
- Usa citation chasing: segue referências para trás (quem citam?) e para a frente (quem os cita?)
- Pesquisa por palavras-chave em Google Scholar, Semantic Scholar, bases de dados da área

**Dores conhecidas:**
- "Every time I read something, I end up opening tab after tab after tab" (rabbit hole)
- Volume esmagador: "an unfathomable ocean… overwhelmed, and anxiety starts to set in"
- Incerteza sobre cobertura: "not knowing if indeed I'm missing something"
- Difícil distinguir papers importantes de ruído

**Ferramentas usadas:**
- Google Scholar (pesquisa por keywords)
- Semantic Scholar (recomendações, alertas)
- Connected Papers / Research Rabbit / Litmaps (mapas visuais)
- arXiv (preprints, especialmente em CS/ML/Physics)
- Bases de dados específicas: PubMed (medicina), IEEE Xplore (engenharia), etc.

**Output:** 50-200+ papers potencialmente relevantes (a maioria não lidos)

**Perguntas para o reviewer:**
- [ ] Que ferramentas usas para descobrir papers? Em que ordem?
- [ ] Quantos papers costumas encontrar nesta fase?
- [ ] Usas alertas automáticos? Quais?
- [ ] Quando é que decides "já tenho o suficiente para avançar"?
- [ ] Usas alguma ferramenta de mapeamento visual (Connected Papers, etc.)? Se sim, é útil?

---

## Fase 2: Triagem (Triage)

**O que acontece:**
- Dos 50-200 papers encontrados, o investigador decide quais ler a fundo
- Método típico: ler abstract → conclusão → figuras/tabelas → decidir
- Método "three-pass": 1) skim 5min, 2) leitura atenta 1h, 3) leitura profunda 4-5h
- Critérios (implícitos): relevância para a minha pergunta, qualidade do venue, ano de publicação, citações

**Dores conhecidas:**
- "What paralyzed me was choosing what to read"
- Falta de critério explícito de paragem: "When is enough enough?"
- Ansiedade de estar a perder algo importante
- Decisão de triagem é subjectiva e não replicável

**Ferramentas usadas:**
- O próprio PDF (skim rápido)
- Zotero/Mendeley (guardar os que passam a triagem)
- Nenhuma ferramenta específica para triagem — é tudo mental/manual

**Output:** 15-40 papers para leitura aprofundada

**Perguntas para o reviewer:**
- [ ] Como decides se um paper vale a pena ler? Que critérios usas?
- [ ] Quanto tempo demoras a triagar um paper?
- [ ] Tens um sistema de categorização (ler agora / ler depois / descartar)?
- [ ] Já sentiste que perdeste um paper importante por triagem errada?
- [ ] Quantos papers acabas por ler a fundo para um projecto típico?

---

## Fase 3: Leitura e extracção

**O que acontece:**
- Leitura atenta dos papers seleccionados
- Highlights e anotações directamente no PDF
- Notas separadas: o que este paper contribui, como se liga ao meu trabalho, limitações, métodos usados
- Alguns investigadores usam "reading notes" estruturadas, outros são caóticos

**Dores conhecidas:**
- "At some point, I just forgot 90% of what I read and cry"
- "I end up downloading the same paper again and again because I am not able to find it when needed"
- Highlights e anotações que não sincronizam entre dispositivos
- Falta de ligação entre "porque guardei isto" e as notas
- Notas que se acumulam sem processamento

**Ferramentas usadas:**
- Zotero PDF reader (anotações integradas)
- Mendeley (deprecated por muitos)
- iPad + Apple Pencil (anotação manual)
- Obsidian/Notion (notas separadas, com ou sem integração Zotero)
- Google Docs / Word (notas soltas)
- Paperpile (browser-based)

**Output:** Papers anotados + notas soltas (com diferentes graus de estrutura)

**Perguntas para o reviewer:**
- [ ] Onde é que tomas notas? No PDF, em ficheiro separado, ou ambos?
- [ ] Tens um template de notas de leitura? Se sim, que campos tem?
- [ ] Consegues encontrar facilmente notas que fizeste há 3 meses?
- [ ] As tuas anotações sincronizam bem entre dispositivos?
- [ ] Quanto tempo demoras a ler e anotar um paper em média?

---

## Fase 4: Organização e gestão

**O que acontece:**
- Manter a biblioteca organizada: pastas, tags, colecções
- Gerir duplicados
- Manter metadados correctos (autores, ano, venue)
- Backup e sincronização entre dispositivos

**Dores conhecidas:**
- "My library became more messy. Eventually, I gave up"
- Tags automáticas que poluem a organização
- "There's nothing worse than not being able to find the statement, reference, or experiment in a stack of 50 papers"
- Migração entre ferramentas é dolorosa e arriscada

**Ferramentas usadas:**
- Zotero (colecções, tags)
- Mendeley (colecções)
- File system (pastas com PDFs)
- Google Drive (backup)

**Output:** Biblioteca "organizada" (na teoria) com PDFs, metadados e anotações

**Perguntas para o reviewer:**
- [ ] Como organizas a tua biblioteca? Pastas? Tags? Colecções?
- [ ] Quantos papers tens na tua biblioteca total?
- [ ] Já tiveste problemas de duplicados ou metadados errados?
- [ ] Já mudaste de ferramenta de gestão? Como foi a migração?
- [ ] O teu sistema actual funciona bem ou é um caos controlado?

---

## Fase 5: Síntese e mapeamento

**O que acontece:**
- O investigador tenta encontrar padrões no que leu
- Organizar papers por tema, metodologia, ou cronologia
- Criar tabelas comparativas (método vs resultado vs dataset)
- Identificar o que é consenso, o que é controverso, o que falta (gaps)
- Esta é a fase mais difícil e mais importante

**Dores conhecidas:**
- "One says it covers all the major works, another says the related work section is very lacking"
- Enumeração vs narrativa: tendência para listar papers em vez de sintetizar
- Scope creep: "my introduction is a review article… much more extensive than I previously planned"
- Dificuldade em formular o "gap real" com confiança

**Ferramentas usadas:**
- Spreadsheets (Google Sheets / Excel) — tabelas de comparação
- Obsidian (notas interligadas)
- Papel e caneta (mapas mentais)
- Nenhuma ferramenta especializada para síntese de research

**Output:** Tabelas comparativas, mapas de temas, identificação de gaps

**Perguntas para o reviewer:**
- [ ] Como fazes a síntese? Usas algum método ou ferramenta específica?
- [ ] Fazes tabelas comparativas? Que colunas usas?
- [ ] Como identificas gaps? É intuição ou tens um processo?
- [ ] Quanto tempo demoras nesta fase relativamente às outras?
- [ ] Já usaste AI (ChatGPT, etc.) para ajudar na síntese? Se sim, como?

---

## Fase 6: Escrita (Related Work / Literature Review)

**O que acontece:**
- Transformar a síntese em parágrafos coerentes
- Organizar por temas (não por paper) — cada parágrafo cobre um sub-tópico
- Usar linguagem de contraste: "however", "in contrast", "unlike X, our approach..."
- Citações em formato correcto (BibTeX, etc.)
- Múltiplas revisões e iterações

**Dores conhecidas:**
- "I am at the 'quotable quotes' stage… which makes me feel like a fraud… plagiarising others"
- "Too much of an enumeration of papers… If I expand… will easily expand to 40 pages"
- "The introduction just feels brutal because it forces you to zoom out and stitch everything into one coherent story"
- Inconsistência entre reviewers: uns dizem "comprehensive", outros dizem "lacking"

**Ferramentas usadas:**
- LaTeX / Overleaf (escrita e formatação)
- Google Docs / Word (rascunhos)
- Zotero / Mendeley (inserção de citações)
- Grammarly / ChatGPT (revisão de texto)

**Output:** Secção de Related Work / Literature Review pronta para submissão

**Perguntas para o reviewer:**
- [ ] Quanto tempo demoras a escrever uma secção de related work?
- [ ] Organizas por temas ou por paper? Ou por cronologia?
- [ ] Usas AI para ajudar na escrita? Se sim, como? Confias no resultado?
- [ ] Quantas iterações fazes antes de ficar satisfeito?
- [ ] O teu supervisor revê e pede mudanças? Que tipo de feedback dá?

---

## Fase 7: Manutenção e actualização

**O que acontece:**
- Mesmo depois de publicar, o investigador precisa de se manter actualizado
- Novos papers saem todos os dias
- Para projectos longos (PhD = 3-5 anos), o landscape muda significativamente
- Alertas, newsletters, Twitter/X, conferências

**Dores conhecidas:**
- "As a researcher I simply gave up on being on par with the literature"
- "Daily updates on arXiv… now it's impossible… sheer volume of preprints being uploaded"
- "Near-constant state of being overwhelmed… Reality is, there is no catching up"

**Ferramentas usadas:**
- Google Scholar alerts
- Semantic Scholar alerts / feed
- arXiv daily digest
- Twitter/X (researchers partilham papers)
- Conferências e workshops

**Output:** Actualização contínua (ou tentativa de) da base de conhecimento

**Perguntas para o reviewer:**
- [ ] Como te manténs actualizado na tua área?
- [ ] Usas alertas? De que tipo?
- [ ] Quantos papers novos relevantes surgem por semana na tua área?
- [ ] Sentes que consegues acompanhar? Se não, como lidas com isso?

---

## Diagrama do workflow completo

```
Fase 0: Pergunta de investigação
    ↓
Fase 1: Discovery (explorar o campo)
    ↓
Fase 2: Triage (filtrar o que interessa)
    ↓
Fase 3: Leitura + Extracção (ler e anotar)
    ↓
Fase 4: Organização (gerir a biblioteca)
    ↓
Fase 5: Síntese (encontrar padrões e gaps)
    ↓
Fase 6: Escrita (related work / lit review)
    ↓
Fase 7: Manutenção (manter-se actualizado)
    ↑___________________________________|
```

**Nota:** Este fluxo não é linear. Investigadores saltam entre fases constantemente. Lêem um paper na fase 3, descobrem 5 novos na fase 1, voltam à triagem na fase 2. A síntese (fase 5) frequentemente revela gaps que obrigam a voltar à discovery (fase 1).

---

## O handoff problem (onde o produto pode entrar)

O maior problema não está numa fase individual. Está nas **transições**:

| Transição | O que se perde | Ferramentas actuais |
|-----------|---------------|-------------------|
| Discovery → Triage | Contexto do "porquê encontrei isto" | Nenhuma |
| Triage → Leitura | Decisão de "porquê vou ler isto" | Nenhuma |
| Leitura → Organização | Highlights sem contexto, notas soltas | Zotero (parcial) |
| Organização → Síntese | Estrutura temática, conexões entre papers | Nenhuma |
| Síntese → Escrita | Transformar tabelas/notas em narrativa | Nenhuma |

**A oportunidade de produto está nas transições, não nas fases.**

---

## Para o reviewer

Por favor revê este documento com base na tua experiência real:

1. **O que está errado?** Alguma fase mal descrita ou em falta?
2. **O que está incompleto?** Ferramentas que usas e não estão listadas?
3. **Onde é que sofres mais?** Marca as fases por ordem de dor (1 = maior dor)
4. **Responde às perguntas** de cada fase com a tua experiência
5. **O que eu não perguntei mas devia?**
