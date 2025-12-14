# Model Hub CLI

Model Hub CLI is a prototype command-line application developed as an infrastructure solution for ACME Corporation. This tool is designed to help ACME’s software architecture teams easily browse, discover, and integrate AI/ML models—especially those from the Hugging Face ecosystem—into their services.


## Project Motivation

ACME Corporation operates the ACME Web Service and is expanding its developer offerings by building internal AI/ML services using Python and PyTorch. Early prototypes have shown promising results, and ACME plans to introduce both hardware products with embedded AI and large-scale cloud AI services.

To accelerate adoption and integration, service teams requested an accessible catalogue of available AI/ML models, complete with information about training datasets, performance benchmarks, and codebases. Our team provides infrastructure for ACME and is tasked with making it easy for these teams to get started with state-of-the-art machine learning models.


## Features

- **Model Catalogue Browsing**: Search and list available AI/ML models from Hugging Face.
- **Model Evaluation**: View detailed metrics evaluating the suitability of models for ACME products and services.
- **Easy Integration**: Retrieve package information to quickly plug models into ACME’s ecosystem.
- **Command-Line Simplicity**: Intuitive CLI commands for fast access and automation.
- **Extensible Architecture**: Designed to support additional model hubs in the future.


## Installation

Clone the repository:

```sh
git clone https://github.com/rcaustin/model-hub-cli.git
cd model-hub-cli
```


Install Python dependencies:

Linux:
```sh
./run.py install
```

Windows:
```batch
run.bat install
```

## Usage

Basic command structure:

```sh
./run.py <argument>
```

### Supported Arguments

- `install`: Create a virtual environment and install project dependencies
- `test`: Run the pytest suite and print the results to stdout
- `<absolute filepath>`: Read URLs from the file; catalogue models, code, and datasets found


## Contributing

External contributions are not being accepted at this time.


# API Endpoints

The following REST API endpoints are implemented in this repository (see `src/api/`):

## Artifact Endpoints (`artifact_routes.py`)
- `POST /artifacts` — List artifacts by query
- `GET /artifact/byName/{name}` — Get artifacts by exact name
- `POST /artifact/byRegEx` — Get artifacts by regex pattern
- `POST /artifact/{artifact_type}` — Create a new artifact
- `GET /artifacts/{artifact_type}/{id}` — Get a single artifact by type and id
- `DELETE /artifacts/{artifact_type}/{id}` — Delete an artifact
- `GET /artifact/{artifact_type}/{id}/cost` — Get storage cost for an artifact

## Authentication (`auth.py`)
- `PUT /authenticate` — Authenticate a user and get an access token

## Health & Tracks (`health.py`)
- `GET /health` — Liveness probe
- `GET /tracks` — Get planned tracks

## Model Endpoints (`model.py`)
- `GET /artifact/model/{id}/rate` — Get ratings for a model artifact
- `GET /artifact/model/{id}/lineage` — Get lineage graph for a model artifact
- `POST /artifact/model/{id}/license-check` — License check for a model artifact

## Registry Reset (`reset.py`)
- `DELETE /reset` — Reset registry state (clears all artifacts)


## License

This project is licensed under the GNU Lesser General Public License v2.1. See the [LICENSE](LICENSE) file for details.


## Contact

For questions or support, please open an issue or contact ACME Corporation.

---
