# Thesis Replication Package

This repository contains the replication materials associated with the research contributions presented in the thesis.

The repository is organized into five replication packages corresponding to the main empirical and technical contributions of the thesis. Each package contains its own `README.md` with detailed information about the included artifacts, dependencies, execution instructions, and reproducibility considerations.

## Repository Structure

```text
thesis-replication-package/
├── 1-requirements-analysis/
├── 2-conceptual-modeling/
├── 3-privacy-coordination-patterns/
├── 4-behavior-assessment/
├── 5-privacy-testing/
├── .gitignore
└── README.md
```

## Replication Packages

### 1. Requirements Analysis

**Thesis:** Chapter 3 — *Understanding Ethical Requirements in Cyber-Physical Systems*

Directory:

```text
1-requirements-analysis/
```

This package contains the artifacts supporting the Grounded Theory Literature Review used to identify and structure ethics-based requirements in Cyber-Physical Systems.

The main materials include:

* literature search and study-selection data;
* qualitative coding matrices;
* hierarchical clustering analysis;
* machine-readable GraphML representations of the resulting catalog;
* corresponding visualizations.

Related publication:

Yelyzaveta Kurkchi and Catia Trubiani. *Ethics-Based Requirements for Engineering Cyber-Physical Systems: A Literature Study*. In *Proceedings of the Software Engineering and Advanced Applications (SEAA)*, volume 16081, pages 254–272. Springer, 2025. DOI: 10.1007/978-3-032-04190-6_16.

---

### 2. Conceptual Modeling

**Thesis:** Chapter 4 — *Modeling Ethical Concerns when Designing Cyber-Physical Systems*
**Section:** *From Ethical Requirements to Design Objectives and Techniques*

Directory:

```text
2-conceptual-modeling/
```

This package contains the artifacts supporting the **DETE4CPES** approach.

The work considers three ethics-based requirements:

* Privacy;
* Security;
* Transparency.

The package includes:

* literature-analysis material;
* Design Objectives (DESO);
* Design Techniques (DEST);
* knowledge graphs representing the relationships among the identified concepts;
* an illustrative patient-monitoring use case;
* prototype simulation material demonstrating selected design techniques.

Related publication:

Yelyzaveta Kurkchi, Ivan Compagnucci, and Catia Trubiani. *Understanding the Concepts behind Ethics in Designing Cyber-Physical Systems*. In *Proceedings of the International Conference on the Quality of Information and Communications Technology (QUATIC)*. Springer, 2026.

---

### 3. Privacy Coordination Patterns

**Thesis:** Chapter 4 — *Modeling Ethical Concerns when Designing Cyber-Physical Systems*
**Section:** *From Privacy Requirements to Design Strategies for Coordination*

Directory:

```text
3-privacy-coordination-patterns/
```

This package investigates how the operationalization of privacy requirements can influence architectural and coordination decisions in Cyber-Physical Systems.

The experimental study compares:

* Centralized coordination;
* Semi-Decentralized coordination;
* Decentralized coordination.

The package contains:

* the simulation implementation;
* experimental configurations;
* literature-analysis material;
* raw simulation logs;
* aggregated experimental results;
* analysis notebooks;
* generated plots and reports.

Related work:

Yelyzaveta Kurkchi, Ivan Compagnucci, and Catia Trubiani. *Designing Cyber-Physical Systems by Privacy-based Coordination Patterns*. Ongoing work; submission venue to be decided.

---

### 4. Behavior Assessment

**Thesis:** Chapter 5 — *Assessing Human Perceptions of Cyber-Physical Systems Behavior*

Directory:

```text
4-behavior-assessment/
```

This package contains the materials supporting an empirical study of human perceptions of ethical behavior in self-driving cars.

The study investigates participants' assessments of simulated self-driving car behavior and the relationship between perceived safety and ethical acceptability.

The replication package includes:

* processed and anonymized participant data;
* analysis and preprocessing notebooks;
* the survey instrument;
* CARLA simulation scripts;
* recorded scenario videos presented to participants.

The raw participant data are not distributed for privacy reasons. The processed and anonymized dataset is provided for reproduction of the reported analyses.

Related work:

Yelyzaveta Kurkchi, Christian Birchler, Sebastiano Panichella, and Catia Trubiani. *Human Perception of Ethics in Self-Driving Cars: An Empirical Study*. Submitted to *ACM Transactions on Software Engineering and Methodology*, August 2026.

---

### 5. Privacy Testing

**Thesis:** Chapter 6 — *Verifying Ethical Concerns when Testing Cyber-Physical Systems*

Directory:

```text
5-privacy-testing/
```

This package contains the implementation and experimental artifacts for simulation-based testing of privacy requirements in robotic systems.

The work introduces **CATER**, a Genetic Algorithm-based search-based testing approach for generating test cases that expose privacy violations. CATER is evaluated against **Random Search (RS)** in robotic navigation scenarios involving human agents and restricted areas.

The package contains:

* the CATER implementation;
* the Random Search baseline;
* privacy-aware simulation configurations;
* restricted-area generation;
* experimental outputs;
* analysis material.

This package extends the RVSG framework and preserves its original ROS 2 workspace structure because the simulation depends on existing package paths and simulation resources.

Related publication:

Yelyzaveta Kurkchi, Hassan Sartaj, Catia Trubiani, and Shaukat Ali. *Search-Based Testing of Privacy Requirements: A Case Study in Robotic Systems*. In *Proceedings of the International Conference on Testing Software and Systems (ICTSS)*, Lecture Notes in Computer Science. Springer, 2026

## Reproducibility

Each replication package provides its own instructions for reproducing or inspecting the corresponding results.

Because the contributions rely on different methodologies and software environments, there is no single execution environment for the entire repository. Depending on the package, reproduction may require:

* Python and Jupyter;
* scientific Python libraries;
* CARLA;
* ROS 2 Humble;
* Gazebo;
* HuNavSim;
* additional simulation-specific dependencies.

Please refer to the `README.md` inside each package before running its artifacts.

Some simulation-based experiments may exhibit small numerical differences across executions or machines because of simulation nondeterminism. Package-specific reproducibility considerations are documented in the corresponding README files.

## Data and Privacy

The repository contains only data that can be distributed as part of the replication package.

In particular, the raw participant responses associated with the human-centered study in `4-behavior-assessment/` are not included for privacy reasons. A processed and anonymized dataset is provided to support reproduction of the reported analyses.

## Citation

When using a specific replication package, please cite the corresponding publication listed in that package's `README.md`.

If the repository as a whole is used, please cite the thesis together with the relevant associated publication(s).
