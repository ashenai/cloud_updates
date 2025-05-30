from sqlalchemy import text

# Attempt to import db, but handle failure for direct script execution
try:
    from app import db
except ImportError as e:
    # This allows the script to be parsed and __main__ to run for basic checks,
    # but execute_query will fail if db is not available.
    db = None
    # print(f"Warning: Failed to import 'db' from 'app' ({e}). 'execute_query' will not be functional without app context.")

def execute_query(sql_query: str, params: list = None) -> dict:
    """
    Executes a given SQL query with parameters and returns the results.

    Args:
        sql_query (str): The SQL query string (should use placeholders like :param_name or ?).
        params (list, optional): A list of parameters for the SQL query.
                                    If using named parameters in SQL (e.g., :name),
                                    this should be a dict. For '?' or '%s' style, a list/tuple.
                                    SQLAlchemy typically uses named parameters or ? directly.
                                    The SQLGenerator currently produces '?' placeholders.

    Returns:
        dict: A dictionary with 'success' (bool), 'data' (list of dicts if successful, else None),
                and 'error' (str if failed, else None).
    """
    results = []
    try:
        if db is None:
            raise RuntimeError("Database (db) is not initialized. This function requires a Flask app context.")

        # For '?' placeholders, SQLAlchemy expects a list/tuple of parameters.
        # If SQLGenerator produced named parameters (e.g., :foo), params would be a dict.
        # Our current SQLGenerator produces '?' which works with a list for params.

        # The SQLAlchemy Core way (which Flask-SQLAlchemy wraps)
        # For SELECT statements, result is a CursorResult object
        # For DML (INSERT, UPDATE, DELETE) without RETURNING, it's a CursorResult without rows.

        # Ensure the parameters are passed as a dictionary if they are named in the query string,
        # or as a list/tuple if positional placeholders like '?' are used.
        # The current sql_generator.py produces '?' placeholders, so params should be a list.

        # Convert '?' to named parameters for broader compatibility and explicitness with SQLAlchemy text()
        # e.g. "WHERE col = ?" with params ['value'] becomes "WHERE col = :p1" with params {"p1": "value"}
        # This also helps prevent issues if a '?' is in a string literal within the query itself.

        # However, for simplicity with current SQLGenerator, we'll assume direct '?' support if db.session.execute handles it,
        # or we might need to adapt the SQLGenerator or this function.
        # Let's try with direct parameters first.

        # Flask-SQLAlchemy's db.session.execute expects a statement (often text()) and params.
        # To make it work with '?', we need to ensure the SQL string is compatible.
        # A common way for raw SQL with '?' is to use the DBAPI connection directly,
        # but with SQLAlchemy, text() with bindparam is preferred.

        # Let's refine the SQL from '?' to named parameters before execution for robustness with text().
        # e.g., "SELECT * FROM foo WHERE bar = ? AND baz = ?"
        # becomes "SELECT * FROM foo WHERE bar = :p1 AND baz = :p2"
        # and params ["a", "b"] becomes {"p1": "a", "p2": "b"}

        param_dict = {}
        formatted_sql_query = sql_query
        # No '?' to named param conversion will be done for now.
        # We will rely on SQLAlchemy's ability to handle '?' with a list of parameters.
        # If this causes issues, SQLGenerator should be updated to produce named parameters.


        # Execute the query
        # For Flask-SQLAlchemy, db.session.execute(text(sql_query), params_dict_or_list)
        # If sql_query uses '?', params should be a list/tuple.
        # If sql_query uses :name, params should be a dict.
        # Our generator uses '?', so params is a list.

        # The `text()` construct is important to declare that this is a SQL string.
        compiled_statement = text(sql_query)

        # db.session.execute can take parameters as a dictionary or a list/tuple
        # depending on how parameters are specified in the query text.
        # For '?' (qmark style), it expects a list/tuple.
        result_proxy = db.session.execute(compiled_statement, params if params else [])

        # For SELECT queries, we want to fetch results.
        # .fetchall() returns a list of Row objects.
        # We convert these to a list of dicts for easier JSON serialization.
        if result_proxy.returns_rows:
            rows = result_proxy.fetchall()
            # Get column names from the ResultProxy's keys()
            column_names = list(result_proxy.keys())
            for row in rows:
                results.append(dict(zip(column_names, row)))

        # For writes that don't return rows (INSERT, UPDATE, DELETE without RETURNING),
        # we might want to commit. For SELECTs, it's not necessary.
        # db.session.commit() # Uncomment if performing writes

        return {"success": True, "data": results, "error": None}

    except Exception as e:
        # db.session.rollback() # Rollback in case of error during a transaction
        # print(f"Database execution error: {e}") # For logging
        return {"success": False, "data": None, "error": str(e)}

if __name__ == '__main__':
    # This block is for basic testing.
    # It requires a running Flask app context with SQLAlchemy initialized,
    # or significant mocking, which is complex for a subtask.
    # We will rely on integration testing via an API endpoint later.
    # For now, just ensure the file is syntactically correct.

    print("db_executor.py created.")
    if db is None:
        print("Note: Flask-SQLAlchemy 'db' object was not imported. 'execute_query' needs a proper app context to run.")
    else:
        print("'db' object imported (though it might not be fully initialized without app context).")
    print("Manual or integration testing required for full 'execute_query' functionality.")

    # Example of how it might be called (conceptual):
    # mock_sql = "SELECT product_name, COUNT(id) AS update_count FROM \"update\" WHERE provider = ? GROUP BY product_name ORDER BY update_count DESC LIMIT ?;"
    # mock_params = ["aws", 1]
    # To run this, we'd need app context.
    # from flask import Flask
    # app = Flask(__name__)
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' # Example config
    # from flask_sqlalchemy import SQLAlchemy
    # db_instance = SQLAlchemy() # In a real app, this is often 'db' from app/__init__.py
    # db_instance.init_app(app) # Initialize db_instance with app
    # with app.app_context():
    #     # In app/__init__.py, 'db' would be the initialized SQLAlchemy object.
    #     # For this test, we'd need to ensure 'db' used by execute_query is this db_instance.
    #     # This usually means 'from app import db' works because db is globally available after app init.
    #     # Potentially create tables if using in-memory for test: db_instance.create_all()
    #     # response = execute_query(mock_sql, mock_params) # This would call the global 'db'
    #     # print(response)
    print("Conceptual test: To run execute_query, a Flask app context with db initialized is needed.")
