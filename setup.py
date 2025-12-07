"""Setup configuration for Neo4j GraphBot."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    with open(readme_file, "r", encoding="utf-8") as fh:
        long_description = fh.read()

setup(
    name="neo4j-graphbot",
    version="1.0.0",
    author="Rafiul Haider",
    description="A CLI interface for interacting with Neo4j using natural language via Gemini API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/neo4j-graphbot",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Database",
    ],
    python_requires=">=3.8",
    install_requires=[
        "neo4j>=5.15.0",
        "google-generativeai>=0.3.2",
        "python-dotenv>=1.0.0",
        "rich>=13.7.0",
    ],
    entry_points={
        "console_scripts": [
            "graphbot=graphbot.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)

