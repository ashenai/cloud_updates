# Natural Language Search Feature Documentation

This document provides an overview of the natural language search feature implemented in the Cloud Updates project.

## API Endpoint: `/api/nl_search/`

- **Method:** `POST`
- **Description:** Accepts a natural language query and attempts to translate it into a SQL query to search the cloud updates database.
- **Request Body (JSON):**
  ```json
  {
      "query": "Your natural language query string"
  }
  ```
  Example: `{"query": "which aws service had the most updates last month?"}`

- **Response Body (JSON):**
  - **On Success (HTTP 200):**
    ```json
    {
        "success": true,
        "data": [
            { "column1": "value1", "column2": "value2", ... },
            ...
        ]
    }
    ```
    The `data` array contains objects representing the rows returned from the database.
  - **On Failure (HTTP 400 for bad request, HTTP 500 for server errors):**
    ```json
    {
        "success": false,
        "error": "A description of the error"
    }
    ```

## Database Schema Representation (`app/db_schema_representation.yaml`)

- **Purpose:** This YAML file provides the Natural Language Processing (NLP) components with a structured understanding of the relevant database tables and columns. It's crucial for correctly mapping natural language terms to database entities.
- **Structure:**
  The file contains a list of `tables`. Each table has:
    - `name`: The actual table name in the database (e.g., `update`).
    - `description`: A human-readable description of the table.
    - `columns`: A list of column definitions. Each column has:
      - `name`: The actual column name (e.g., `provider`, `product_name`).
      - `data_type`: The general data type (e.g., `TEXT`, `DATETIME`, `INTEGER`, `TEXT_ARRAY`). `TEXT_ARRAY` indicates a field that is stored as a JSON string list but queried as if it's an array.
      - `is_primary_key` (optional, boolean): Indicates if the column is a primary key.
      - `description`: A human-readable description of the column.
      - `examples` (optional, list of strings): Example values that might appear in this column, used to aid entity recognition.

## Core Modules

- **`app/query_parser.py` (`QueryParser` class):**
  - Responsible for taking the raw natural language string.
  - Uses spaCy for NLP tasks (tokenization, NER, POS tagging, dependency parsing).
  - Leverages `db_schema_representation.yaml` to identify entities.
  - Outputs a structured dictionary representing the parsed query (intent, filters, selected columns, etc.).

- **`app/sql_generator.py` (`SQLGenerator` class):**
  - Takes the structured dictionary from `QueryParser`.
  - Constructs a parameterized SQL query string and a list of parameters.

- **`app/db_executor.py` (`execute_query` function):**
  - Takes the SQL string and parameters.
  - Executes the query against the database using Flask-SQLAlchemy.
  - Returns the results or error information.

- **`app/routes.py` (within `nl_search_bp` blueprint):**
  - Defines the `/api/nl_search/` POST endpoint that orchestrates the above modules.
  - Defines the `/api/nl_search/page` GET endpoint that serves the HTML frontend.

- **`app/templates/search_nl.html`:**
  - A simple HTML page with JavaScript to provide a UI for the natural language search, interacting with the `/api/nl_search/` endpoint.
