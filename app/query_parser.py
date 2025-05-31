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

        # --- BEGIN NEW LOGIC FOR "top N <entity>" ---
        is_top_n_query = False
        limit_number = None
        group_by_col_for_top_n = None

        for i, token in enumerate(doc):
            if token.lemma_ == "top" and i + 1 < len(doc) and doc[i+1].like_num:
                try:
                    limit_number = int(doc[i+1].text)
                    is_top_n_query = True
                    # Try to identify the entity being ranked (e.g., "services", "products")
                    if i + 2 < len(doc):
                        entity_token = doc[i+2]
                        if entity_token.lemma_ in ["service", "product"]:
                            group_by_col_for_top_n = "product_name"
                        # Can add more mappings, e.g., "categories" -> "categories"
                        # elif entity_token.lemma_ in ["category", "categories"]:
                        #    group_by_col_for_top_n = "categories"

                    # If no specific entity is found right after "top N",
                    # but query generally mentions "service" or "product", infer it.
                    if not group_by_col_for_top_n:
                        if "service" in query_text.lower() or "product" in query_text.lower():
                            group_by_col_for_top_n = "product_name"
                    break # Found "top [number]", process one such phrase
                except ValueError: # Handle cases where doc[i+1].text is not a valid int
                    is_top_n_query = False # Not a valid top N query
                    limit_number = None


        if is_top_n_query and limit_number is not None and group_by_col_for_top_n is not None:
            valid_columns = [col['name'] for col in self.target_table_schema['columns']]
            if group_by_col_for_top_n not in valid_columns:
                # If the guessed group_by column is not valid, invalidate this path
                is_top_n_query = False

        if is_top_n_query and limit_number is not None and group_by_col_for_top_n is not None:
            parsed_query["intent"] = "find_most_frequent_entity" # Specific intent for top N
            parsed_query["group_by_column"] = group_by_col_for_top_n

            pk_col = self.target_table_schema['columns'][0]['name']
            for col_def in self.target_table_schema['columns']:
                if col_def.get('is_primary_key', False):
                    pk_col = col_def['name']
                    break

            parsed_query["aggregations"] = [{"type": "COUNT", "column": pk_col, "alias": "mention_count"}]
            parsed_query["order_by"] = {"column": "mention_count", "direction": "DESC"}
            parsed_query["limit"] = limit_number
            parsed_query["select_columns"] = [group_by_col_for_top_n]
        # --- END NEW LOGIC FOR "top N <entity>" ---


        # Identify keywords for intent (general count)
        # Ensure this doesn't override the more specific "top N" intent if it was set.
        if (parsed_query["intent"] != "find_most_frequent_entity" or not is_top_n_query) and \
           ("count" in query_text.lower() or "how many" in query_text.lower()):
            parsed_query["intent"] = "count"
            parsed_query["select_columns"] = []
            # Ensure pk_col is defined for count, similar to above logic
            pk_col_count = self.target_table_schema['columns'][0]['name']
            for col_def in self.target_table_schema['columns']:
                if col_def.get('is_primary_key', False):
                    pk_col_count = col_def['name']
                    break
            parsed_query["aggregations"] = [{"type": "COUNT", "column": pk_col_count, "alias": "total_count"}]

        # General "most frequent" intent, if not already handled by "top N" or specific "service with most updates"
        if parsed_query["intent"] != "find_most_frequent_entity" and \
           "most" in query_text.lower() and "updates" in query_text.lower() and \
           not "service with the most updates" in query_text.lower():
            parsed_query["intent"] = "find_most_frequent"
            parsed_query["group_by_column"] = "product_name" # Default group by for general "most"
            # Ensure pk_col is defined for aggregation count
            pk_col_agg = self.target_table_schema['columns'][0]['name']
            for col_def in self.target_table_schema['columns']:
                if col_def.get('is_primary_key', False):
                    pk_col_agg = col_def['name']
                    break
            parsed_query["aggregations"] = [
                {"type": "COUNT", "column": pk_col_agg, "alias": "update_count"}
            ]
            parsed_query["order_by"] = {"column": "update_count", "direction": "DESC"}
            parsed_query["limit"] = 5 # Default to top 5 for general "most"
            if "product_name" in [col['name'] for col in self.target_table_schema['columns']]:
                 parsed_query["select_columns"] = ["product_name"]
            else: # Fallback if product_name isn't a column (schema error?)
                 parsed_query["select_columns"] = [self.target_table_schema['columns'][0]['name']]


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
        # This specific phrase should only be processed if not already handled by "top N"
        if not is_top_n_query and "service with the most updates" in query_text.lower():
            parsed_query["intent"] = "find_most_frequent_entity"
            parsed_query["group_by_column"] = "product_name"
            pk_col_specific = next((col['name'] for col in self.target_table_schema['columns'] if col.get('is_primary_key')), self.target_table_schema['columns'][0]['name'])
            parsed_query["aggregations"] = [{"type": "COUNT", "column": pk_col_specific, "alias": "update_count"}]
            parsed_query["order_by"] = {"column": "update_count", "direction": "DESC"}
            parsed_query["limit"] = 1 # "the service" implies top 1
            if "product_name" in [col['name'] for col in self.target_table_schema['columns']]:
                parsed_query["select_columns"] = ["product_name"]
            else:
                parsed_query["select_columns"] = [pk_col_specific]


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
            "Azure updates for Blob Storage", # Test multi-word product
            "which are the top 3 AWS services mentioned in the updates" # New test query
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
