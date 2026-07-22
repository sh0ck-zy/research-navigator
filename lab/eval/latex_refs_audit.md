# latex_refs audit — LaTeX citation index vs OpenAlex edges

Citing universe: **431 source-parsed papers** (of 683). B restricted to this universe before comparing; B_full = 2663.

| bucket | edges | share of union |
|---|---|---|
| A∩B (both) | 1428 | 1428/3476 (41.1%) |
| A\B (latex only) | 1855 | 1855/3476 (53.4%) |
| B\A (openalex only) | 193 | 193/3476 (5.6%) |
| A∪B (union) | 3476 | — |

A = 3283 (by method: {'title': 1610, 'doi': 426, 'eprint': 1247}); B_restricted = 1621; B_full = 2663.

Of the 193 openalex-only edges, **17** have a near-miss (sim ≥ 0.85) among the citing paper's unmatched refs — likely OUR resolution misses; the rest are plausibly absent from the .bbl or wrong in OpenAlex.

## Delta — subset-exact-year recall fix (2026-07-23, approved)

Sort co-gate waived when the CORPUS title is a strict token-subset of the ref
title AND years agree exactly (the truncated-corpus-title case; the reverse
direction stays gated). Measured against the previously approved run:

| | before | after | Δ |
|---|---|---|---|
| A (latex) | 3182 | 3283 | +101 |
| A∩B (both) | 1381 | 1428 | **+47** |
| A\B (latex only) | 1801 | 1855 | +54 |
| B\A (openalex only) | 240 | 193 | **−47** |
| B\A near-misses | 76 | 17 | −59 |

115 refs matched via the waived gate (`gate: corpus_subset_exact_year` in
resolved.jsonl). The 14 lowest-sort acceptances were spot-checked, including
every corpus record with a ≤2-token title (PALM 2017 = Krishnan & Wu, BOLD
2021 = Dhamala et al., XGBoost 2016 = Chen & Guestrin): all correct — the
exact-year requirement carries the discrimination that token_sort can't.
Decomposition of the remaining 193 (measured post-fix): **29** corpus
duplicate records — the ref MATCHED a twin Wid whose title ≈ the cited title
(up from 14 pre-fix: matching one twin exposes the OA edge to the other; the
mandatory pre-re-cluster dedupe by title+year will collapse these); **18**
near-miss among unmatched refs (residual sort-gate with year≠, delatex brace
artifacts — code fixed, refresh pending); **146** with no similar ref in the
.bbl at all (absent or bad OpenAlex edge).

## A∩B — 10 samples (both indexes agree)

- `W2178314882` **Convergent Learning: Do different neural networks learn the same represe** →
  `W1825675169` **Understanding Neural Networks Through Deep Visualization**
  via `title`, key `yosinski-2015-ICML-DL-understanding-neural-networks`
- `W2970820321` **The Bottom-up Evolution of Representations in the Transformer: A Study w** →
  `W2946417913` **BERT Rediscovers the Classical NLP Pipeline**
  via `title`, key `tenney-etal-2019-bert`
- `W3152409010` **Exploring the Role of BERT Token Representations to Explain Sentence Pro** →
  `W2964204621` **What you can cram into a single $&amp;!#* vector: Probing sentence embed**
  via `doi`, key `conneau-etal-2018-cram`
- `W4378976798` **Toward Transparent AI: A Survey on Interpreting the Inner Structures of ** →
  `W2963483561` **Interpretability Beyond Feature Attribution: Quantitative Testing with C**
  via `title`, key `kim2018interpretability`
- `W4385805111` **Disentangling Neuron Representations with Concept Vectors** →
  `W4296932880` **Toy Models of Superposition**
  via `eprint`, key `elhage2022toy`
- `W4389518433` **Memory Injections: Correcting Multi-Hop Reasoning Failures During Infere** →
  `W4327526719` **Eliciting Latent Predictions from Transformers with the Tuned Lens**
  via `eprint`, key `tuned_lens`
- `W4389520370` **Editing Large Language Models: Problems, Methods, and Opportunities** →
  `W4282980384` **Memory-Based Model Editing at Scale**
  via `title`, key `Mitchell2022MemoryBasedME`
- `W4393146683` **Truth Forest: Toward Multi-Scale Truthfulness in Large Language Models t** →
  `W4310926773` **Discovering Latent Knowledge in Language Models Without Supervision**
  via `eprint`, key `ccs`
- `W4403223051` **Drowzee: Metamorphic Testing for Fact-Conflicting Hallucination Detectio** →
  `W4387355345` **Representation Engineering: A Top-Down Approach to AI Transparency**
  via `eprint`, key ``
- `W7155038902` **Principled Coarse-Grained Acceptance For Speculative Decoding In Speech** →
  `W4385571791` **Analyzing Transformers in Embedding Space**
  via `title`, key `dar-etal-2023-analyzing`

## A\B — 10 samples (we see it, OpenAlex doesn't — verify the ref is real)

- `W1825675169` **Understanding Neural Networks Through Deep Visualization** →
  `W1899185266` **Object Detectors Emerge in Deep Scene CNNs**
  via `eprint`, key `zhou-2014-arXiv-object-detectors-emerge`
- `W3193068792` **Probing Classifiers: Promises, Shortcomings, and Advances** →
  `W4288351520` **What do you learn from context? Probing for sentence structure in contex**
  via `title`, key `tenney2018what`
- `W4316128987` **Tracr: Compiled Transformers as a Laboratory for Interpretability** →
  `W2906152891` **Analysis Methods in Neural Language Processing: A Survey**
  via `title`, key `belinkov2019analysis`
- `W4368304611` **Finding Neurons in a Haystack: Case Studies with Sparse Probing** →
  `W4296932880` **Toy Models of Superposition**
  via `eprint`, key `elhage2022toy`
- `W4385774833` **Trustworthy LLMs: a Survey and Guideline for Evaluating Large Language M** →
  `W3187467055` **Post-hoc Interpretability for Neural NLP: A Survey**
  via `title`, key `madsen2022post`
- `W4387929831` **Linear Representations of Sentiment in Large Language Models** →
  `W4296932880` **Toy Models of Superposition**
  via `title`, key `elhage2022superposition`
- `W4391591671` **Rethinking Interpretability in the Era of Large Language Models** →
  `W2963483561` **Interpretability Beyond Feature Attribution: Quantitative Testing with C**
  via `eprint`, key `kim2017interpretability`
- `W4399836657` **Transcoders Find Interpretable LLM Feature Circuits** →
  `W4386839891` **Sparse Autoencoders Find Highly Interpretable Features in Language Model**
  via `eprint`, key `cunningham_sparse_2023`
- `W4404783416` **Gemma Scope: Open Sparse Autoencoders Everywhere All At Once on Gemma 2** →
  `W4389518382` **Emergent Linear Representations in World Models of Self-Supervised Seque**
  via `doi`, key `nanda-etal-2023-emergent`
- `W7155038902` **Principled Coarse-Grained Acceptance For Speculative Decoding In Speech** →
  `W4322718191` **LLaMA: Open and Efficient Foundation Language Models**
  via `title`, key `touvron2023llamaopenefficientfoundation`

## B\A — 10 samples (OpenAlex sees it, we don't — why?)

- `W2118022153` **Interpretable classifiers using rules and Bayesian analysis: Building a ** →
  `W2026905436` **Comprehensible classification models**
  no similar unmatched ref (best sim=0.0) — absent from .bbl or bad OA edge
- `W2657631929` **Methods for interpreting and understanding deep neural networks** →
  `W2610018085` **Network Dissection: Quantifying Interpretability of Deep Visual Represen**
  no similar unmatched ref (best sim=0.0) — absent from .bbl or bad OA edge
- `W2962816513` **Pathologies of Neural Models Make Interpretations Difficult** →
  `W2594475271` **Towards A Rigorous Science of Interpretable Machine Learning**
  no similar unmatched ref (best sim=0.558) — absent from .bbl or bad OA edge
- `W3018827121` **Syntactic Structure from Deep Learning** →
  `W2964204621` **What you can cram into a single $&amp;!#* vector: Probing sentence embed**
  no similar unmatched ref (best sim=0.0) — absent from .bbl or bad OA edge
- `W3187467055` **Post-hoc Interpretability for Neural NLP: A Survey** →
  `W2923014074` **GLUE: A Multi-Task Benchmark and Analysis Platform for Natural Language **
  near-miss in unmatched refs (sim=1.0): “GLUE: A Multi-Task Benchmark and Analysis Platform for Natural Language Understa”
- `W4389518797` **Can We Edit Factual Knowledge by In-Context Learning?** →
  `W4322718191` **LLaMA: Open and Efficient Foundation Language Models**
  no similar unmatched ref (best sim=0.621) — absent from .bbl or bad OA edge
- `W4395101889` **Editing Large Language Models** →
  `W4386566901` **Understanding Transformer Memorization Recall Through Idioms**
  no similar unmatched ref (best sim=0.52) — absent from .bbl or bad OA edge
- `W4406533397` **A Non-Ergodic Framework for Understanding Emergent Capabilities in Large** →
  `W4281758439` **FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awaren**
  no similar unmatched ref (best sim=0.0) — absent from .bbl or bad OA edge
- `W4411610300` **What is AI safety? What do we want it to be?** →
  `W4378771755` **Direct Preference Optimization: Your Language Model is Secretly a Reward**
  no similar unmatched ref (best sim=0.0) — absent from .bbl or bad OA edge
- `W7128589046` **A framework for causal concept-based model explanations** →
  `W2493343568` **European Union Regulations on Algorithmic Decision Making and a “Right t**
  no similar unmatched ref (best sim=0.554) — absent from .bbl or bad OA edge
