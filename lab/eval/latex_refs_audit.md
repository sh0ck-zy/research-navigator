# latex_refs audit — LaTeX citation index vs OpenAlex edges

Citing universe: **439 source-parsed papers** (of 683). B restricted to this universe before comparing; B_full = 2663.

| bucket | edges | share of union |
|---|---|---|
| A∩B (both) | 1449 | 1449/3525 (41.1%) |
| A\B (latex only) | 1858 | 1858/3525 (52.7%) |
| B\A (openalex only) | 218 | 218/3525 (6.2%) |
| A∪B (union) | 3525 | — |

A = 3307 (by method: {'doi': 426, 'eprint': 1264, 'title': 1617}); B_restricted = 1667; B_full = 2663.

Of the 218 openalex-only edges, **23** have a near-miss (sim ≥ 0.85) among the citing paper's unmatched refs — likely OUR resolution misses; the rest are plausibly absent from the .bbl or wrong in OpenAlex.

## A∩B — 10 samples (both indexes agree)

- `W2178314882` **Convergent Learning: Do different neural networks learn the same represe** →
  `W1825675169` **Understanding Neural Networks Through Deep Visualization**
  via `title`, key `yosinski-2015-ICML-DL-understanding-neural-networks`
- `W2964204621` **What you can cram into a single $&amp;!#* vector: Probing sentence embed** →
  `W2964159778` **Visualizing and Understanding Neural Models in NLP**
  via `title`, key `Li:etal:2016`
- `W3152409010` **Exploring the Role of BERT Token Representations to Explain Sentence Pro** →
  `W2626639386` **SmoothGrad: removing noise by adding noise**
  via `eprint`, key `smilkov2017smoothgrad`
- `W4378976798` **Toward Transparent AI: A Survey on Interpreting the Inner Structures of ** →
  `W2948771346` **Visualizing and Measuring the Geometry of BERT**
  via `title`, key `reif2019visualizing`
- `W4385805111` **Disentangling Neuron Representations with Concept Vectors** →
  `W2253993278` **Multifaceted Feature Visualization: Uncovering the Different Types of Fe**
  via `eprint`, key `nguyen2016multifaceted`
- `W4389518433` **Memory Injections: Correcting Multi-Hop Reasoning Failures During Infere** →
  `W4315881234` **Does Localization Inform Editing? Surprising Differences in Causality-Ba**
  via `eprint`, key `hase-DoesLocalizationInformEditing-2023`
- `W4389520370` **Editing Large Language Models: Problems, Methods, and Opportunities** →
  `W4281657280` **Locating and Editing Factual Associations in GPT**
  via `title`, key `meng2022locating`
- `W4393146683` **Truth Forest: Toward Multi-Scale Truthfulness in Large Language Models t** →
  `W4384918448` **Llama 2: Open Foundation and Fine-Tuned Chat Models**
  via `eprint`, key `llama2`
- `W4403577370` **Editing Factual Knowledge and Explanatory Ability of Medical Large Langu** →
  `W4389524330` **DEPN: Detecting and Editing Privacy Neurons in Pretrained Language Model**
  via `title`, key ``
- `W7155038902` **Principled Coarse-Grained Acceptance For Speculative Decoding In Speech** →
  `W4385571791` **Analyzing Transformers in Embedding Space**
  via `title`, key `dar-etal-2023-analyzing`

## A\B — 10 samples (we see it, OpenAlex doesn't — verify the ref is real)

- `W1825675169` **Understanding Neural Networks Through Deep Visualization** →
  `W1899185266` **Object Detectors Emerge in Deep Scene CNNs**
  via `eprint`, key `zhou-2014-arXiv-object-detectors-emerge`
- `W3193068792` **Probing Classifiers: Promises, Shortcomings, and Advances** →
  `W2515741950` **Fine-grained Analysis of Sentence Embeddings Using Auxiliary Prediction **
  via `title`, key `DBLP:journals/corr/AdiKBLG16`
- `W4316116432` **Causal Abstraction: A Theoretical Foundation for Mechanistic Interpretab** →
  `W4389518382` **Emergent Linear Representations in World Models of Self-Supervised Seque**
  via `doi`, key `Nanda2023`
- `W4368304611` **Finding Neurons in a Haystack: Case Studies with Sparse Probing** →
  `W3091782154` **Analyzing Individual Neurons in Pre-trained Language Models**
  via `eprint`, key `durrani2020analyzing`
- `W4385573190` **LM-Debugger: An Interactive Tool for Inspection and Intervention in Tran** →
  `W4281657280` **Locating and Editing Factual Associations in GPT**
  via `eprint`, key `meng2022locating`
- `W4387561538` **The Geometry of Truth: Emergent Linear Structure in Large Language Model** →
  `W4387929831` **Linear Representations of Sentiment in Large Language Models**
  via `title`, key `tigges2023linear`
- `W4391215636` **Talking about Large Language Models** →
  `W4298181573` **Improving alignment of dialogue agents via targeted human judgements**
  via `eprint`, key `glaese2022improving`
- `W4399836657` **Transcoders Find Interpretable LLM Feature Circuits** →
  `W4297412003` **In-context Learning and Induction Heads**
  via `eprint`, key `olsson_-context_2022`
- `W4404783416` **Gemma Scope: Open Sparse Autoencoders Everywhere All At Once on Gemma 2** →
  `W4368304611` **Finding Neurons in a Haystack: Case Studies with Sparse Probing**
  via `title`, key `gurnee2023finding`
- `W7155038902` **Principled Coarse-Grained Acceptance For Speculative Decoding In Speech** →
  `W4322718191` **LLaMA: Open and Efficient Foundation Language Models**
  via `title`, key `touvron2023llamaopenefficientfoundation`

## B\A — 10 samples (OpenAlex sees it, we don't — why?)

- `W2118022153` **Interpretable classifiers using rules and Bayesian analysis: Building a ** →
  `W2026905436` **Comprehensible classification models**
  no similar unmatched ref (best sim=0.0) — absent from .bbl or bad OA edge
- `W2764024122` **Interpretable Convolutional Neural Networks** →
  `W2963374347` **Visual interpretability for deep learning: a survey**
  no similar unmatched ref (best sim=0.66) — absent from .bbl or bad OA edge
- `W2962772482` **A survey of methods for explaining black box models** →
  `W1787224781` **On Pixel-Wise Explanations for Non-Linear Classifier Decisions by Layer-**
  no similar unmatched ref (best sim=0.579) — absent from .bbl or bad OA edge
- `W3018827121` **Syntactic Structure from Deep Learning** →
  `W2906152891` **Analysis Methods in Neural Language Processing: A Survey**
  no similar unmatched ref (best sim=0.0) — absent from .bbl or bad OA edge
- `W3100198908` **From Zero to Hero: On the Limitations of Zero-Shot Language Transfer wit** →
  `W2942810103` **Similarity of Neural Network Representations Revisited**
  no similar unmatched ref (best sim=0.613) — absent from .bbl or bad OA edge
- `W4322616366` **Analyzing And Editing Inner Mechanisms Of Backdoored Language Models** →
  `W4316135772` **Progress measures for grokking via mechanistic interpretability**
  near-miss in unmatched refs (sim=1.0): “Progress measures for grokking via mechanistic interpretability. In booktitleThe”
- `W4391215636` **Talking about Large Language Models** →
  `W4304195432` **ReAct: Synergizing Reasoning and Acting in Language Models**
  no similar unmatched ref (best sim=0.718) — absent from .bbl or bad OA edge
- `W4402351622` **Enhancing Event Causality Identification with Rationale and Structure-Aw** →
  `W4281657280` **Locating and Editing Factual Associations in GPT**
  no similar unmatched ref (best sim=0.0) — absent from .bbl or bad OA edge
- `W4411337774` **Debugging and Runtime Analysis of Neural Networks with VLMs (A Case Stud** →
  `W4386839891` **Sparse Autoencoders Find Highly Interpretable Features in Language Model**
  no similar unmatched ref (best sim=0.0) — absent from .bbl or bad OA edge
- `W7128589046` **A framework for causal concept-based model explanations** →
  `W2493343568` **European Union Regulations on Algorithmic Decision Making and a “Right t**
  no similar unmatched ref (best sim=0.554) — absent from .bbl or bad OA edge
