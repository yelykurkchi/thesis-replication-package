# Conceptual Modeling

This directory contains the replication materials for **Chapter 4 — Modeling Ethical Concerns when Designing Cyber-Physical Systems**, specifically the section **From Ethical Requirements to Design Objectives and Techniques**.

The section investigates how ethics-based requirements can be refined into design objectives and corresponding design techniques that support the engineering of Cyber-Physical Systems (CPS). In this work, we specifically consider three ethics-based requirements: **Privacy, Security, and Transparency**.

The replication package includes the artifacts supporting the DETE4CPES approach, the illustrative patient-monitoring use case, and a prototype simulator used to demonstrate selected design techniques.

The study presented in this section is based on the work:

*Understanding the Concepts behind Ethics in Designing Cyber-Physical Systems*

**Authors:** Yelyzaveta Kurkchi, Ivan Compagnucci, and Catia Trubiani

## Repository Structure

```text
2-conceptual-modeling/
├── dete4cpes/
├── simulator/
├── use-case/
└── README.md
```

## DETE4CPES

The `dete4cpes/` directory contains the artifacts supporting the identification and organization of design objectives and design techniques for the ethics-based requirements considered in this work: **Privacy, Security, and Transparency**.

The approach distinguishes between:

* **Design Objectives (DESO)**, which represent design-oriented objectives to realize the ethics-based requirements;
* **Design Techniques (DEST)**, which represent concrete techniques that can support the corresponding design objectives.

The directory contains the literature-analysis material, the resulting knowledge graphs for Privacy, Security, and Transparency, and supplementary documentation.

## Illustrative Use Case

The `use-case/` directory contains the BPMN model of the patient-monitoring scenario used to illustrate the application of the proposed approach.

The use case demonstrates how ethics-based requirements can be related to design objectives and techniques and subsequently connected to concrete design decisions within a CPS.

## Prototype Simulator

The `simulator/` directory contains a Python prototype implementing a patient-monitoring scenario.

The prototype is used to illustrate selected design techniques identified through the conceptual modeling approach.

The directory contains the implementation, experiment scripts, dependencies, generated results, and additional instructions for executing the prototype.

## Main Replication Artifacts

The package provides three main types of artifacts:

* **DETE4CPES artifacts**, including the literature-analysis material and knowledge graphs representing design objectives and techniques for Privacy, Security, and Transparency;
* **Use-case artifacts**, providing the BPMN representation of the patient-monitoring scenario;
* **Prototype implementation**, providing an executable example illustrating selected design techniques.

Together, these artifacts provide traceability from the considered ethics-based requirements to design objectives and techniques and demonstrate their application within a CPS design scenario.

## Related Publication

The work presented in this section is based on:

*Understanding the Concepts behind Ethics in Designing Cyber-Physical Systems*

Yelyzaveta Kurkchi, Ivan Compagnucci, and Catia Trubiani.