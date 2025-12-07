# API Reference & Core Logic

This document outlines the key classes and methods that drive the Neo4j GraphBot.

## Core Services

### `UnifiedLLMService`
**Path**: `src/graphbot/services/unified_llm_service.py`

Handles all interactions with Language Model providers.

#### `__init__(config_path: str)`
Initializes the service by loading the provider configuration.

#### `generate_cypher_query_async(user_input: str, context: Optional[str]) -> str`
Translates natural language into a Cypher query.
*   **user_input**: The user's question.
*   **context**: The schema definition string to guide the LLM.
*   **Returns**: A raw Cypher query string.

#### `explain_result_async(query: str, results: list, user_input: str) -> str`
Generates a human-readable summary of the database results.

---

### `Neo4jHandler`
**Path**: `src/graphbot/handlers/neo4j_handler.py`

Manages the connection lifecycle and query execution against Neo4j.

#### `connect_async(uri, user, password, database)`
Establishes an asynchronous connection to the Neo4j Bolt driver.

#### `execute_query_async(query: str, parameters: dict = None) -> List[Record]`
Executes a Cypher query and returns the results.
*   **query**: The Cypher query string.
*   **parameters**: Optional dictionary of query parameters.
*   **Returns**: A list of Neo4j Records.

---

### `InsightAgent`
**Path**: `src/graphbot/services/insight_agent.py`

A background worker that analyzes the database to build a semantic map.

#### `analyze_database_async(neo4j_handler) -> Dict`
Performs a deep scan of the database structure.
1.  Fetches all Node Labels and Relationship Types.
2.  Samples properties for each label.
3.  Uses a "Worker" LLM model to generate a summary of the domain.
4.  Suggests relevant questions based on the data.

---

### `QueryBuilder`
**Path**: `src/graphbot/utils/query_builder.py`

Utilities for validating and sanitizing Cypher queries.

#### `validate_query(query: str) -> Tuple[bool, str]`
Checks for syntax errors or unsafe operations.
*   **Returns**: `(is_valid, error_message)`

#### `is_read_only(query: str) -> bool`
Determines if a query performs write operations (e.g., `CREATE`, `MERGE`, `DELETE`). Used to prompt the user for confirmation before execution.

