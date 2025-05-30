import spacy
import yaml
import os

class QueryParser:
    def __init__(self, schema_path="app/db_schema_representation.yaml"):
        # Construct the absolute path to the schema file
        # Assumes this script (query_parser.py) is in the 'app' directory
        # and schema_path is relative to the project root (ashenai/cloud_updates)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # This should point to ashenai/cloud_updates
        absolute_schema_path = os.path.join(base_dir, schema_path)

        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            # This can happen if the model isn't downloaded directly
            # The subtask for spaCy setup should have handled this, but as a fallback:
            print("Downloading en_core_web_sm model...")
            spacy.cli.download("en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")

        try:
            with open(absolute_schema_path, 'r') as f:
                self.db_schema = yaml.safe_load(f)
            if not self.db_schema or 'tables' not in self.db_schema:
                raise ValueError("Schema is empty or not structured correctly.")
            # For now, we assume a single table 'update' as per our schema file
            self.target_table_schema = next((t for t in self.db_schema['tables'] if t['name'] == 'update'), None)
            if not self.target_table_schema:
                raise ValueError("Table 'update' not found in schema representation.")
        except FileNotFoundError:
            print(f"Error: Schema file not found at {absolute_schema_path}")
            self.db_schema = None
            self.target_table_schema = None
        except Exception as e:
            print(f"Error loading or parsing schema: {e}")
            self.db_schema = None
            self.target_table_schema = None

    def parse_query(self, query_text: str) -> dict:
        if not self.target_table_schema:
            return {"error": "Database schema not loaded correctly."}

        doc = self.nlp(query_text.lower()) # Process query in lowercase for easier matching
        parsed_query = {
            "intent": "find_data",  # Default intent
            "select_columns": ["title", "provider", "product_name", "published_date"], # Default columns to select
            "filters": [],
            "aggregations": [],
            "order_by": None,
            "limit": None,
            "target_table": self.target_table_schema['name']
        }

        # Very basic keyword and entity matching
        # This will be significantly improved with more sophisticated NLP techniques

        # Identify keywords for intent
        if "count" in query_text.lower() or "how many" in query_text.lower():
            parsed_query["intent"] = "count"
            # For a count, we typically count primary keys or a distinct column
            parsed_query["select_columns"] = [] # Clear default select for count
            parsed_query["aggregations"] = [{"type": "COUNT", "column": self.target_table_schema['columns'][0]['name'], "alias": "total_count"}]


        if "most" in query_text.lower() and "updates" in query_text.lower() and not "service with the most updates" in query_text.lower(): # e.g., "service with most updates" but not the specific phrase
            parsed_query["intent"] = "find_most_frequent"
            # Default to 'product_name' if not specified, can be refined
            parsed_query["group_by_column"] = "product_name"
            parsed_query["aggregations"] = [
                {"type": "COUNT", "column": self.target_table_schema['columns'][0]['name'], "alias": "update_count"}
            ]
            parsed_query["order_by"] = {"column": "update_count", "direction": "DESC"}
            parsed_query["limit"] = 5 # Default to top 5
            parsed_query["select_columns"] = [parsed_query["group_by_column"]] # Select the grouped column


        # Identify known column names and potential values from the query
        # valid_column_names = {col['name']: col for col in self.target_table_schema['columns']}

        # for token in doc:
            # Direct match for column names (very simplistic)
            # if token.text in valid_column_names:
                # This needs more context. Is it a filter, a select target, or part of an aggregation?
                # For now, let's assume if a column name is mentioned, it might be a filter candidate.
                # pass # Placeholder for more advanced logic

        # Example: "updates for aws" or "aws updates"
        # Example: "updates about EC2"
        # This requires NER and linking entities to schema columns.
        # For now, a very naive check for provider or product_name examples
        for entity in doc.ents: # spaCy's NER
            # This is very basic, actual entity linking is more complex
            if entity.label_ in ["ORG", "PRODUCT", "GPE"]: # Common labels for providers/services (GPE for geo-political entity like AWS)
                # Check if entity text matches any example in schema
                for col_schema in self.target_table_schema['columns']:
                    if 'examples' in col_schema and col_schema.get('data_type') == 'TEXT': # Only match text columns for now
                        if entity.text.lower() in [ex.lower() for ex in col_schema['examples']]:
                            # Found a potential filter
                            # Avoid duplicate filters for the same column and value
                            if not any(f['column'] == col_schema['name'] and f['value'].lower() == entity.text.lower() for f in parsed_query["filters"]):
                                parsed_query["filters"].append({
                                    "column": col_schema['name'],
                                    "operator": "EQUALS", # Default operator
                                    "value": entity.text # Use original casing from entity if possible, or schema example
                                })
                                break # Stop after first match for this entity

        # Simple check for provider without relying on NER (if NER misses it)
        if not any(f['column'] == 'provider' for f in parsed_query["filters"]):
            if "aws" in query_text.lower():
                parsed_query["filters"].append({"column": "provider", "operator": "EQUALS", "value": "aws"})
            elif "azure" in query_text.lower():
                parsed_query["filters"].append({"column": "provider", "operator": "EQUALS", "value": "azure"})

        # Check for specific product names if not caught by NER as ORG/PRODUCT
        # This is a fallback, ideally NER should be customized or fine-tuned.
        if not any(f['column'] == 'product_name' for f in parsed_query["filters"]):
            for col_schema in self.target_table_schema['columns']:
                if col_schema['name'] == 'product_name' and 'examples' in col_schema:
                    for example_product in col_schema['examples']:
                        if example_product.lower() in query_text.lower():
                            if not any(f['column'] == 'product_name' and f['value'].lower() == example_product.lower() for f in parsed_query["filters"]):
                                 parsed_query["filters"].append({
                                    "column": "product_name",
                                    "operator": "EQUALS",
                                    "value": example_product # Use the example from schema for consistent casing
                                })
                            break # Found one, move to next part of query

        # Handle "which is the AWS service with the most updates"
        # "which is the" -> implies finding a specific entity
        # "AWS service" -> provider = AWS, entity = product_name (service)
        # "most updates" -> intent = find_most_frequent, aggregate by product_name, order by count desc, limit 1
        if "service with the most updates" in query_text.lower():
            parsed_query["intent"] = "find_most_frequent_entity" # More specific intent
            parsed_query["group_by_column"] = "product_name"
            # Ensure id is a valid column for counting, or use the first primary key column
            pk_col = next((col['name'] for col in self.target_table_schema['columns'] if col.get('is_primary_key')), 'id')
            parsed_query["aggregations"] = [{"type": "COUNT", "column": pk_col, "alias": "update_count"}]
            parsed_query["order_by"] = {"column": "update_count", "direction": "DESC"}
            parsed_query["limit"] = 1
            parsed_query["select_columns"] = ["product_name"] # Only select the product name

            # Check for provider context like "AWS service"
            # Ensure provider filter is not duplicated if already added by NER
            if "aws service" in query_text.lower() and not any(f['column'] == 'provider' and f['value'] == 'aws' for f in parsed_query["filters"]):
                # Remove any other provider filter if it exists
                parsed_query["filters"] = [f for f in parsed_query["filters"] if f['column'] != 'provider']
                parsed_query["filters"].append({"column": "provider", "operator": "EQUALS", "value": "aws"})
            elif "azure service" in query_text.lower() and not any(f['column'] == 'provider' and f['value'] == 'azure' for f in parsed_query["filters"]):
                parsed_query["filters"] = [f for f in parsed_query["filters"] if f['column'] != 'provider']
                parsed_query["filters"].append({"column": "provider", "operator": "EQUALS", "value": "azure"})

        # Remove duplicate filters (simple approach based on column and value)
        unique_filters = []
        seen_filters = set()
        for f in parsed_query["filters"]:
            filter_tuple = (f["column"], f.get("operator", "EQUALS"), f["value"].lower() if isinstance(f["value"], str) else f["value"])
            if filter_tuple not in seen_filters:
                unique_filters.append(f)
                seen_filters.add(filter_tuple)
        parsed_query["filters"] = unique_filters

        return parsed_query

if __name__ == '__main__':
    # Basic test cases
    # When running this script directly, schema_path needs to be relative to this file's location
    # Assuming query_parser.py is in 'app/' and db_schema_representation.yaml is also in 'app/'
    # The constructor expects schema_path to be relative to project root.
    # So, "app/db_schema_representation.yaml" should work if project root is parent of "app"

    # Correct path for __main__ execution:
    # The QueryParser class expects schema_path to be from the project root.
    # If this script is app/query_parser.py, and schema is app/db_schema_representation.yaml
    # then the path "app/db_schema_representation.yaml" is correct.
    # The os.path.abspath(__file__) will be /app/app/query_parser.py
    # os.path.dirname(os.path.abspath(__file__)) is /app/app
    # os.path.dirname(os.path.dirname(os.path.abspath(__file__))) is /app (project root)
    # So, os.path.join(base_dir, schema_path) becomes /app/app/db_schema_representation.yaml which is correct.

    parser = QueryParser(schema_path="app/db_schema_representation.yaml")

    if parser.db_schema and parser.target_table_schema: # Proceed only if schema loaded correctly
        queries_to_test = [
            "What are the latest AWS updates?",
            "how many azure updates last week", # Date parsing not yet implemented
            "which is the AWS service with the most updates",
            "show me updates for EC2",
            "count all aws updates",
            "updates about Azure Functions",
            "Azure updates for Blob Storage" # Test multi-word product
        ]
        for q in queries_to_test:
            print(f"Query: {q}")
            parsed = parser.parse_query(q)
            print(f"Parsed: {parsed}\n")
    else:
        print("Could not run tests as DB schema failed to load.")
        if not parser.db_schema:
            print("Reason: parser.db_schema is None.")
        if parser.db_schema and not parser.target_table_schema:
             print("Reason: parser.target_table_schema is None (table 'update' not found or schema malformed).")
