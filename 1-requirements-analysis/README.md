# Requirements Analysis

This directory contains the replication materials for **Chapter 3 — Understanding Ethical Requirements in Cyber-Physical Systems** of the thesis.

The chapter investigates ethics-based requirements in Cyber-Physical Systems (CPS) through a Grounded Theory Literature Review Method. The replication package provides the materials used for literature selection, qualitative coding, hierarchical clustering, and construction of the resulting catalog of ethics-based requirements and their interdependencies.

The study presented in this chapter was originally published as:

> Yelyzaveta Kurkchi and Catia Trubiani. *Ethics-Based Requirements for Engineering Cyber-Physical Systems: A Literature Study*. In *Proceedings of the Software Engineering and Advanced Applications (SEAA)*, volume 16081, pages 254–272. Springer, 2025. DOI: [10.1007/978-3-032-04190-6_16](https://doi.org/10.1007/978-3-032-04190-6_16).

## Repository Structure

```text
1-requirements-analysis/
├── analysis/
│   ├── hierarchical-clustering.ipynb
│   └── requirements.txt
├── coding/
│   └── coding-matrices.xlsx
├── results/
│   ├── graphs/
│   └── figures/
├── study-selection/
│   └── literature-search-screening.xlsx
└── README.md
```

## Study Selection

The `study-selection/` directory contains the material documenting the identification and selection of the studies included in the literature analysis.

### `literature-search-screening.xlsx`

This workbook documents the literature study process, including:

* the initial set of identified studies;
* the screening and selection process;
* the final set of studies included in the qualitative analysis.

These data provide traceability between the literature search and the set of studies used in the subsequent coding process.

## Qualitative Coding

The `coding/` directory contains the results of the Grounded Theory coding process.

### `coding-matrices.xlsx`

This workbook contains the coding matrices derived from the selected literature.

The open-coding matrix records the occurrence of the identified concepts across the analyzed studies. Each row corresponds to a selected study, while the concept columns indicate whether a given concept was identified in that study.

The workbook also contains the results of the axial and selective coding activities used to identify and organize relationships among the extracted concepts.

These coding results form the basis for the construction of the ethics-based requirements catalog and for the hierarchical clustering analysis.

## Hierarchical Clustering Analysis

The `analysis/` directory contains the computational analysis used to investigate how the identified ethics-based requirements group together based on their occurrence across the selected studies.

### `hierarchical-clustering.ipynb`

The Jupyter Notebook performs hierarchical clustering over the open-coding results.

The analysis follows these main steps:

1. loads the open-coding matrix from `coding/coding-matrices.xlsx`;
2. extracts the ethics-based requirements from the coding matrix;
3. converts their occurrence across the selected studies into a binary matrix;
4. computes the frequency of each requirement;
5. computes the requirement co-occurrence matrix;
6. applies average-linkage hierarchical clustering;
7. assigns the requirements to four clusters;
8. generates the corresponding clustering results and visualizations.

The general category `Ethics` is excluded from the analysis because it serves as an umbrella concept rather than an individual ethics-based requirement.

The notebook reads the coding workbook using the relative path:

```text
../coding/coding-matrices.xlsx
```

and stores generated outputs under the `results/` directory.

### `requirements.txt`

This file contains the Python dependencies required to execute the notebook.

Install the dependencies from the `analysis/` directory with:

```bash
pip install -r requirements.txt
```

The current analysis requires:

* `pandas` for data processing;
* `matplotlib` for visualization;
* `scipy` for hierarchical clustering;
* `openpyxl` for reading Excel workbooks;
* `jupyter` for executing the notebook.

## Results

The `results/` directory contains the resulting catalog in both machine-readable and visual formats.

### `results/graphs/`

This directory contains GraphML representations of the resulting ethics-based requirements catalog and its main groups.

The GraphML files preserve the graph structure of the catalog and can be opened with software supporting the GraphML format, such as graph analysis or visualization tools.

The directory contains graphs corresponding to the main groups identified in the study, including:

* Privacy and Security;
* Regulation, Safety, and Responsibility;
* Sustainability, Dignity, Equality, Autonomy, Reliability, Accountability, Awareness, and Beneficence;
* the high-level catalog.

Each GraphML file represents ethics-based requirements as nodes and the identified interdependencies among them as edges.

### `results/figures/`

This directory contains PDF visualizations corresponding to the GraphML files in `results/graphs/`.

The figures provide rendered representations of the requirement groups and the overall catalog for inspection without requiring graph-analysis software.

The basename of each PDF corresponds to the basename of the related GraphML file.

## Reproducing the Hierarchical Clustering

To reproduce the clustering analysis, navigate to the `analysis/` directory:

```bash
cd 1-requirements-analysis/analysis
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Then start Jupyter:

```bash
jupyter notebook
```

and open:

```text
hierarchical-clustering.ipynb
```

Run the notebook cells sequentially.

The notebook loads the coding matrix, constructs the binary requirement matrix, computes requirement frequencies and co-occurrences, performs hierarchical clustering, and generates the corresponding results.

## Main Replication Artifacts

The package provides four main types of artifacts:

* **Study-selection data**, documenting the identification, screening, and final selection of the literature included in the study;
* **Qualitative coding data**, documenting the concepts identified across the selected studies and their relationships;
* **Analysis code**, reproducing the hierarchical clustering of the identified ethics-based requirements;
* **Catalog results**, providing the resulting requirement structures in GraphML and PDF formats.

Together, these artifacts provide traceability from the selected literature to the identified ethics-based requirements, their relationships, and the resulting catalog.

## Related Publication

Yelyzaveta Kurkchi and Catia Trubiani. *Ethics-Based Requirements for Engineering Cyber-Physical Systems: A Literature Study*. In *Proceedings of the Software Engineering and Advanced Applications (SEAA)*, volume 16081, pages 254–272. Springer, 2025. DOI: [10.1007/978-3-032-04190-6_16](https://doi.org/10.1007/978-3-032-04190-6_16).