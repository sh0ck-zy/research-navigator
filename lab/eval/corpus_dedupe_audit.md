# corpus dedupe audit — title+year (pre-re-cluster mandate)

Source: v3 (683 records, frozen). Candidates: 8 (2 accepted, 6 rejected by author gate). Merge groups: 2.

## Accepted merges

### W2282821441 + W2516809705 -> keep `W2516809705`
- `W2282821441` (2016, cited_by=15548, edges=2) "Why Should I Trust You?"
- `W2516809705` (2016, cited_by=5259, edges=1) “Why Should I Trust You?”: Explaining the Predictions of Any Classifier **<- canonical**
  - via `title_fuzzy` {'title_set': 1.0, 'title_sort': 0.4944, 'subset': True} author_gate: jaccard=1.00 overlap=['guestrin', 'ribeiro', 'singh']

### W2799124508 + W2964204621 -> keep `W2964204621`
- `W2799124508` (2018, cited_by=279, edges=2) What you can cram into a single vector: Probing sentence embeddings for linguistic propert
- `W2964204621` (2018, cited_by=595, edges=4) What you can cram into a single $&amp;!#* vector: Probing sentence embeddings for linguist **<- canonical**
  - via `title_fuzzy` {'title_set': 1.0, 'title_sort': 0.9787, 'subset': True} author_gate: overlap=['baroni', 'barrault', 'conneau']

## Rejected candidates (gate failed — kept separate, review these)

- `W2786672974` vs `W2889326414` via `title_fuzzy` author_gate: jaccard=0.40 overlap=['healy', 'mcinnes']
  - “UMAP: Uniform Manifold Approximation and Projection for Dimension Reduction” (2018) vs “UMAP: Uniform Manifold Approximation and Projection” (2018)
- `W2809925683` vs `W2891503716` via `title_fuzzy` author_gate: jaccard=0.00 overlap=[]
  - “Explainable artificial intelligence: A survey” (2018) vs “Peeking Inside the Black-Box: A Survey on Explainable Artificial Intelligence (X” (2018)
- `W4321177655` vs `W4389984066` via `title_fuzzy` author_gate: REJECT: distinct arXiv ids (different works)
  - “Augmented Language Models: a Survey” (2023) vs “Retrieval-Augmented Generation for Large Language Models: A Survey” (2023)
- `W4385849354` vs `W4395101889` via `title_fuzzy` author_gate: jaccard=0.15 overlap=['yao', 'zhang']
  - “EasyEdit: An Easy-to-use Knowledge Editing Framework for Large Language Models” (2023) vs “Editing Large Language Models” (2023)
- `W4388585315` vs `W4395101889` via `title_fuzzy` author_gate: jaccard=0.20 overlap=['zhang']
  - “Massive Editing for Large Language Models via Meta Learning” (2023) vs “Editing Large Language Models” (2023)
- `W4389520370` vs `W4395101889` via `title_fuzzy` author_gate: jaccard=0.38 overlap=['deng', 'yao', 'zhang']
  - “Editing Large Language Models: Problems, Methods, and Opportunities” (2023) vs “Editing Large Language Models” (2023)
