# DETE4CPES

This directory contains the artifacts supporting the **DETE4CPES** approach for identifying and organizing Design Objectives (DESO) and Design Techniques (DEST) associated with ethics-based requirements in Cyber-Physical Systems.

The artifacts focus on three ethics-based requirements: **Privacy, Security, and Transparency**.

## Repository Structure

```text
dete4cpes/
├── knowledge-graphs/
│   ├── figures/
│   ├── privacy.graphml
│   ├── security.graphml
│   ├── security(2).graphml
│   ├── security(3).graphml
│   └── transparency.graphml
├── literature-analysis/
│   └── literature-search-results.xlsx
├── Appendix.pdf
└── README.md
```

## Literature Analysis

The `literature-analysis/` directory contains the material supporting the identification of Design Objectives (DESO) and Design Techniques (DEST) from the analyzed literature.

### `literature-search-results.xlsx`

This workbook:

* contains the literature search results collected from Scopus, IEEE Xplore, and ACM Digital Library;
* reports the search strings and bibliographic metadata;
* documents the inclusion and exclusion decisions and the corresponding rationale;
* includes the extracted mappings between the selected papers, ethics-based requirements, Design Objectives (DESO), and Design Techniques (DEST).

## Knowledge Graphs

The `knowledge-graphs/` directory contains machine-readable representations of the resulting DETE4CPES knowledge graphs in GraphML format.

The knowledge graphs organize the identified Design Objectives and Design Techniques and represent the relationships among them.

### Privacy

`privacy.graphml` contains the complete knowledge graph for **Privacy**.

### Security

The complete knowledge graph for **Security** is divided into three GraphML files for readability:

* `security.graphml`
* `security(2).graphml`
* `security(3).graphml`

Together, these files represent the complete Security knowledge graph.

### Transparency

`transparency.graphml` contains the complete knowledge graph for **Transparency**.

### `figures/`

The `figures/` directory contains PDF visualizations of the knowledge graphs provided in GraphML format.

These files allow the resulting graphs to be inspected without requiring a GraphML-compatible graph visualization tool.

## Appendix

### `Appendix.pdf`

The appendix provides supplementary information about the literature analysis and the resulting DETE4CPES artifacts. In particular, it:

* lists the selected papers included in the literature analysis;
* maps each selected paper to the ethics-based requirements it addresses: Privacy, Security, and Transparency;
* provides the complete descriptions of the identified Design Objectives (DESO) and Design Techniques (DEST).