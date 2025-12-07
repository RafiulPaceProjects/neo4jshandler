# Neo4j GraphBot

<div align="center">

![Neo4j GraphBot](https://via.placeholder.com/800x200.png?text=Neo4j+GraphBot+Banner)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()

**Chat with your Graph. Zero Cypher required.**

</div>

---

## 🚀 Elevator Pitch

**Neo4j GraphBot** transforms the way you interact with graph databases by turning natural language questions into optimized Cypher queries. It acts as an intelligent bridge, allowing developers and analysts to explore complex datasets instantly without writing a single line of query code.

## ✨ Features

| 🧠 Intelligent Querying | 🔍 Deep Inspection | 🛡️ Safe & Secure |
|-------------------------|--------------------|-------------------|
| Translates natural language (e.g., "Find friends of friends") into precise Cypher. | Automatic schema analysis maps your database structure in the background. | Validates queries and requires confirmation for write/delete operations. |
| **Rich CLI Interface** | **Multi-Model Support** | **Explainability** |
| Beautiful, interactive terminal UI with syntax highlighting and tables. | Switch between Gemini, OpenAI, or other LLM providers easily. | Explains the *why* behind query results in plain English. |

## 🏁 Quick Start

Get up and running in seconds.

```bash
# 1. Clone and Install
git clone https://github.com/yourusername/neo4j-graphbot.git
cd neo4j-graphbot
pip install -e .

# 2. Configure (Edit .env with your keys)
cp config/config.env.template config/config.env

# 3. Launch
graphbot
```

## 🗺️ Project Structure

```text
neo4j-graphbot/
├── config/                 # Configuration files (.env, providers.yaml)
├── docs/                   # Documentation
│   ├── architecture.md     # System design & diagrams
│   ├── setup-guide.md      # Detailed installation steps
│   └── api-reference.md    # Code documentation
├── src/
│   └── graphbot/
│       ├── core/           # Core logic (Schema Context)
│       ├── handlers/       # Neo4j Database handlers
│       ├── services/       # LLM & Agent Services
│       └── utils/          # Helpers & Query Builders
├── tests/                  # Integration & Unit tests
├── Dockerfile              # Container definition
└── README.md               # You are here
```

## 📚 Documentation

For detailed instructions, please refer to the documentation:

*   📖 [**Architecture Overview**](docs/architecture.md) - How it works under the hood.
*   🛠️ [**Setup Guide**](docs/setup-guide.md) - Deep dive into configuration and environment.
*   💻 [**API Reference**](docs/api-reference.md) - For developers extending the bot.
*   🚀 [**Deployment**](docs/deployment.md) - Building and running in production.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 👥 Authors

<table>
  <tr>
    <td align="center"><strong>📚 Academic Context</strong></td>
  </tr>
  <tr>
    <td>
      <strong>Course:</strong> CS 673 — Scalable Databases (Fall 2025)<br>
      <strong>Institution:</strong> Pace University
    </td>
  </tr>
</table>

### Development Team

| Name | Role |
|------|------|
| **Rafiul Haider** (UID: U0200293) | Lead Developer |
| **Ali Khan** | Developer |
| **Yogesh** | Developer |

> *This application was developed as a Final Project submission to demonstrate the modeling, cleansing, and querying capabilities of a Graph Database architecture.*

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
