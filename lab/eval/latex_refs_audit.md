# latex_refs audit — LaTeX citation index vs OpenAlex edges

Citing universe: **431 source-parsed papers** (of 683). B restricted to this universe before comparing; B_full = 2663.

| bucket | edges | share of union |
|---|---|---|
| A∩B (both) | 1381 | 1381/3422 (40.4%) |
| A\B (latex only) | 1801 | 1801/3422 (52.6%) |
| B\A (openalex only) | 240 | 240/3422 (7.0%) |
| A∪B (union) | 3422 | — |

A = 3182 (by method: {'title': 1509, 'eprint': 1247, 'doi': 426}); B_restricted = 1621; B_full = 2663.

Of the 240 openalex-only edges, **76** have a near-miss (sim ≥ 0.85) among the citing paper's unmatched refs — likely OUR resolution misses; the rest are plausibly absent from the .bbl or wrong in OpenAlex.

## A∩B — 10 samples (both indexes agree)

- `W2178314882` **Convergent Learning: Do different neural networks learn the same represe** →
  `W1825675169` **Understanding Neural Networks Through Deep Visualization**
  via `title`, key `yosinski-2015-ICML-DL-understanding-neural-networks`
- `W2970862333` **Designing and Interpreting Probes with Control Tasks** →
  `W2964204621` **What you can cram into a single $&amp;!#* vector: Probing sentence embed**
  via `title`, key `conneau2018what`
- `W3152884768` **Knowledge Neurons in Pretrained Transformers** →
  `W3172099915` **Attention is Not All You Need: Pure Attention Loses Rank Doubly Exponent**
  via `eprint`, key `att_is_not_all_you_need`
- `W4378976798` **Toward Transparent AI: A Survey on Interpreting the Inner Structures of ** →
  `W4297412003` **In-context Learning and Induction Heads**
  via `title`, key `olsson2022context`
- `W4386076059` **CRAFT: Concept Recursive Activation FacTorization for Explainability** →
  `W2594475271` **Towards A Rigorous Science of Interpretable Machine Learning**
  via `title`, key `doshivelez2017rigorous`
- `W4389518626` **Are Structural Concepts Universal in Transformer Language Models? Toward** →
  `W4288351520` **What do you learn from context? Probing for sentence structure in contex**
  via `title`, key `tenney_what_2019`
- `W4389520370` **Editing Large Language Models: Problems, Methods, and Opportunities** →
  `W4318142410` **Transformer-Patcher: One Mistake worth One Neuron**
  via `title`, key `huang2023transformerpatcher`
- `W4393146683` **Truth Forest: Toward Multi-Scale Truthfulness in Large Language Models t** →
  `W2606347107` **Learning to Generate Reviews and Discovering Sentiment**
  via `eprint`, key `radford2017learning`
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
- `W3196986263` **Neuron-level Interpretation of Deep NLP Models: A Survey** →
  `W2618851150` **A Unified Approach to Interpreting Model Predictions**
  via `title`, key `shappely_NIPS2017_7062`
- `W4316128987` **Tracr: Compiled Transformers as a Laboratory for Interpretability** →
  `W2964303497` **Machine Learning Interpretability: A Survey on Methods and Metrics**
  via `title`, key `carvalho2019machine`
- `W4368304611` **Finding Neurons in a Haystack: Case Studies with Sparse Probing** →
  `W4281657280` **Locating and Editing Factual Associations in GPT**
  via `title`, key `meng2022locating`
- `W4385774833` **Trustworthy LLMs: a Survey and Guideline for Evaluating Large Language M** →
  `W2970641574` **Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks**
  via `eprint`, key `reimers2019sentence`
- `W4387892136` **Towards Understanding Sycophancy in Language Models** →
  `W4298181573` **Improving alignment of dialogue agents via targeted human judgements**
  via `eprint`, key `glaese2022improving`
- `W4391591671` **Rethinking Interpretability in the Era of Large Language Models** →
  `W2195388612` **Explaining nonlinear classification decisions with deep Taylor decomposi**
  via `title`, key `montavon2017explaining`
- `W4399836657` **Transcoders Find Interpretable LLM Feature Circuits** →
  `W4296932880` **Toy Models of Superposition**
  via `eprint`, key `elhage_toy_2022`
- `W4404783416` **Gemma Scope: Open Sparse Autoencoders Everywhere All At Once on Gemma 2** →
  `W4386839891` **Sparse Autoencoders Find Highly Interpretable Features in Language Model**
  via `title`, key `cunningham2023sparse`
- `W7155038902` **Principled Coarse-Grained Acceptance For Speculative Decoding In Speech** →
  `W4322718191` **LLaMA: Open and Efficient Foundation Language Models**
  via `title`, key `touvron2023llamaopenefficientfoundation`

## B\A — 10 samples (OpenAlex sees it, we don't — why?)

- `W2118022153` **Interpretable classifiers using rules and Bayesian analysis: Building a ** →
  `W2026905436` **Comprehensible classification models**
  no similar unmatched ref (best sim=0.0) — absent from .bbl or bad OA edge
- `W2657631929` **Methods for interpreting and understanding deep neural networks** →
  `W2914874661` **Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge**
  no similar unmatched ref (best sim=0.0) — absent from .bbl or bad OA edge
- `W2962772482` **A survey of methods for explaining black box models** →
  `W2614087582` **PALM**
  near-miss in unmatched refs (sim=1.0): “Palm: Machine learning explanations for iterative debugging”
- `W3005086430` **Fooling LIME and SHAP** →
  `W2963483561` **Interpretability Beyond Feature Attribution: Quantitative Testing with C**
  near-miss in unmatched refs (sim=0.986): “Interpretability Beyond Feature Attribution: Quantitative Testing with Concept A”
- `W3170470779` **Transformer visualization via dictionary learning: contextualized embedd** →
  `W2282821441` **"Why Should I Trust You?"**
  no similar unmatched ref (best sim=0.383) — absent from .bbl or bad OA edge
- `W4385571306` **Token-wise Decomposition of Autoregressive Language Model Hidden States ** →
  `W4294955582` **How to Dissect a Muppet: The Structure of Transformer Embedding Spaces**
  near-miss in unmatched refs (sim=0.9): “https://aclanthology.org/2022.tacl-1.57 How to dissect a M uppet: The structure ”
- `W4393147065` **Sparsity-Guided Holistic Explanation for LLMs with Interpretable Inferen** →
  `W2516809705` **“Why Should I Trust You?”: Explaining the Predictions of Any Classifier**
  near-miss in unmatched refs (sim=1.0): “" Why should i trust you?" Explaining the predictions of any classifier”
- `W4403754522` **Not another imputation method: A transformer-based model for missing val** →
  `W3174086521` **TabNet: Attentive Interpretable Tabular Learning**
  no similar unmatched ref (best sim=0.0) — absent from .bbl or bad OA edge
- `W4411523116` **Fairness Mediator: Neutralize Stereotype Associations to Mitigate Bias i** →
  `W3123340107` **BOLD**
  near-miss in unmatched refs (sim=1.0): “Bold: Dataset and metrics for measuring biases in open-ended language generation”
- `W7128589046` **A framework for causal concept-based model explanations** →
  `W2493343568` **European Union Regulations on Algorithmic Decision Making and a “Right t**
  no similar unmatched ref (best sim=0.554) — absent from .bbl or bad OA edge
