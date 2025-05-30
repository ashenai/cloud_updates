import yaml
import os

class SQLGenerator:
    def __init__(self, db_schema_representation: dict):
        self.db_schema = db_schema_representation
        if not self.db_schema or 'tables' not in self.db_schema:
            raise ValueError("Database schema representation is missing or malformed.")

    def _get_table_schema(self, table_name: str):
        for table in self.db_schema['tables']:
            if table['name'] == table_name:
                return table
        raise ValueError(f"Table '{table_name}' not found in schema.")

    def _get_column_data_type(self, table_schema: dict, column_name: str) -> str:
        for col in table_schema['columns']:
            if col['name'] == column_name:
                return col.get('data_type', 'TEXT').upper() # Default to TEXT
        # Handle special case for aggregated columns like 'update_count' which might not be in schema directly
        if column_name.endswith("_count"): # A common alias from QueryParser
            return "INTEGER"
        raise ValueError(f"Column '{column_name}' not found in table '{table_schema['name']}'.")

    def generate_sql(self, parsed_query: dict) -> tuple[str, list]:
        if "error" in parsed_query:
            raise ValueError(f"Cannot generate SQL from erroneous parsed query: {parsed_query['error']}")

        table_name = parsed_query.get("target_table")
        if not table_name:
            raise ValueError("Target table not specified in parsed query.")

        table_schema = self._get_table_schema(table_name)
        params = []

        # SELECT clause
        select_columns = parsed_query.get("select_columns", [])
        aggregations = parsed_query.get("aggregations", [])

        if not select_columns and not aggregations:
            # Default to selecting all columns from the table schema if none specified
            # However, QueryParser usually defaults, so this is a fallback.
            # For safety, let's ensure there's at least one primary key or first column if nothing else.
            select_columns = [table_schema['columns'][0]['name']]

        select_parts = []
        if select_columns: # Ensure select_columns is not empty before joining
            select_parts.extend([f'"{col}"' for col in select_columns]) # Quote column names

        for agg in aggregations:
            agg_type = agg.get("type", "COUNT").upper()
            agg_col = agg.get("column", "*")
            agg_alias = agg.get("alias")

            # Quote column name if it's not '*'
            quoted_agg_col = f'"{agg_col}"' if agg_col != "*" else "*"

            if agg_alias:
                select_parts.append(f'{agg_type}({quoted_agg_col}) AS "{agg_alias}"')
            else:
                select_parts.append(f'{agg_type}({quoted_agg_col})')

        if not select_parts: # Should not happen if logic above is correct, but as a failsafe
             select_parts.append(f'"{table_schema["columns"][0]["name"]}"')


        sql = f'SELECT {", ".join(select_parts)} FROM "{table_name}"'

        # WHERE clause
        filters = parsed_query.get("filters", [])
        where_clauses = []
        if filters:
            for f in filters:
                col_name = f["column"]
                operator = f.get("operator", "EQUALS").upper()
                value = f["value"]

                # Basic operator mapping
                # Ensure column names are quoted
                if operator == "EQUALS":
                    where_clauses.append(f'"{col_name}" = ?')
                    params.append(value)
                elif operator == "CONTAINS" or operator == "LIKE": # Assuming 'CONTAINS' means 'LIKE'
                    where_clauses.append(f'"{col_name}" LIKE ?')
                    params.append(f"%{value}%")
                elif operator == "GREATER_THAN":
                    where_clauses.append(f'"{col_name}" > ?')
                    params.append(value)
                elif operator == "LESS_THAN":
                    where_clauses.append(f'"{col_name}" < ?')
                    params.append(value)
                # Add more operators as needed (e.g., IN, BETWEEN, NOT EQUALS)
                else:
                    # Default to equals for unknown operators for now
                    where_clauses.append(f'"{col_name}" = ?')
                    params.append(value)

            sql += " WHERE " + " AND ".join(where_clauses)

        # GROUP BY clause
        group_by_column = parsed_query.get("group_by_column")
        if group_by_column:
            sql += f' GROUP BY "{group_by_column}"' # Quote group by column

        # ORDER BY clause
        order_by = parsed_query.get("order_by")
        if order_by:
            order_col = order_by["column"]
            # Check if order_col is an alias from aggregation or a direct column
            is_alias = any(agg.get("alias") == order_col for agg in aggregations)

            # Quote column name if it's not an alias from aggregation
            quoted_order_col = f'"{order_col}"' if not is_alias else order_col

            direction = order_by.get("direction", "ASC").upper()
            sql += f' ORDER BY {quoted_order_col} {direction}'

        # LIMIT clause
        limit = parsed_query.get("limit")
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        return sql.strip() + ";", params


if __name__ == '__main__':
    # Assuming query_parser.py is in the same directory (app)
    # This needs to be adjusted if the script is run from a different context
    # For the agent, these paths need to be relative to the repo root or use absolute paths if necessary.

    # Try to import QueryParser with error handling for module path issues
    try:
        from query_parser import QueryParser
    except ModuleNotFoundError:
        print("Error: Could not import QueryParser. Ensure it's in the Python path or same directory.")
        print("Attempting to adjust sys.path for local import from 'app' directory...")
        import sys
        # Assuming this script (sql_generator.py) is in 'app/'
        # and query_parser.py is also in 'app/'
        # The project root would be one level up from 'app/'
        current_dir = os.path.dirname(os.path.abspath(__file__)) # Should be /app/app
        # project_root = os.path.dirname(current_dir) # Should be /app
        # sys.path.insert(0, project_root) # Add project root to path
        sys.path.insert(0, current_dir) # Add current 'app' directory to path for direct import

        try:
            from query_parser import QueryParser
            print("Successfully imported QueryParser after path adjustment.")
        except ModuleNotFoundError as e:
            print(f"Failed to import QueryParser even after path adjustment: {e}")
            exit()


    # Construct path to schema YAML
    # Assumes this script (sql_generator.py) is in ashenai/cloud_updates/app
    # and schema is also in ashenai/cloud_updates/app
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # ashenai/cloud_updates (project root)
    schema_file_path = os.path.join(base_dir, "app/db_schema_representation.yaml") # Correct path from project root

    loaded_schema = None
    try:
        with open(schema_file_path, 'r') as f:
            loaded_schema = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading schema for test from {schema_file_path}: {e}")
        exit()

    if not loaded_schema:
        print(f"Schema could not be loaded from {schema_file_path}. Exiting test.")
        exit()

    # Initialize parser and generator
    # QueryParser expects schema_path relative to project root
    query_parser = QueryParser(schema_path="app/db_schema_representation.yaml")
    sql_generator = SQLGenerator(db_schema_representation=loaded_schema)

    if not query_parser.target_table_schema:
        print("QueryParser failed to load target table schema. Check schema path and content.")
        exit()

    queries_to_test = [
        "What are the latest AWS updates?",
        "how many azure updates",
        "which is the AWS service with the most updates",
        "show me updates for EC2",
        "count all aws updates",
        "azure updates for Azure Functions" # Test product with space
    ]

    for q_text in queries_to_test:
        print(f"Natural Language Query: {q_text}")
        parsed_q = query_parser.parse_query(q_text)
        print(f"Parsed Query: {parsed_q}")

        if "error" in parsed_q:
            print(f"Skipping SQL generation due to parsing error: {parsed_q['error']}\n")
            continue

        try:
            sql, params = sql_generator.generate_sql(parsed_q)
            print(f"Generated SQL: {sql}")
            print(f"Parameters: {params}\n")
        except Exception as e:
            print(f"Error generating SQL: {e}\n")
