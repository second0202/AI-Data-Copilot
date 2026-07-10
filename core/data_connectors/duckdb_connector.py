import duckdb
import pandas as pd
import re
from config.settings import settings

class DuckDBConnector:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.DUCKDB_PATH
        self.conn = duckdb.connect(self.db_path)

    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute a SQL query and return a pandas DataFrame."""
        try:
            return self.conn.execute(query).df()
        except Exception as e:
            raise Exception(f"Error executing DuckDB query: {str(e)}")

    def load_csv(self, table_name: str, file_path: str):
        """Load a CSV file into a DuckDB table."""
        query = f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM read_csv_auto('{file_path}')"
        self.conn.execute(query)

    def load_dataframe(self, table_name: str, dataframe: pd.DataFrame):
        """Load a pandas DataFrame into a DuckDB table, replacing the table if it exists."""
        self.conn.register("temp_upload_df", dataframe)
        self.conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM temp_upload_df")
        self.conn.unregister("temp_upload_df")

    def load_file(self, table_name: str, file_path: str) -> int:
        """Load a CSV or XLSX file into DuckDB and return row count."""
        sanitized_table_name = self.sanitize_table_name(table_name)
        lower_path = file_path.lower()
        if lower_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        elif lower_path.endswith(".xlsx"):
            df = pd.read_excel(file_path)
        else:
            raise ValueError("Only CSV and XLSX files are supported.")

        self.load_dataframe(sanitized_table_name, df)
        return len(df)

    def list_tables(self) -> list[str]:
        tables = self.conn.execute("SHOW TABLES").df()
        return tables["name"].tolist() if not tables.empty else []

    def get_table_preview(self, table_name: str, limit: int = 10) -> list[dict]:
        sanitized_table_name = self.sanitize_table_name(table_name)
        df = self.conn.execute(f"SELECT * FROM {sanitized_table_name} LIMIT {limit}").df()
        return df.to_dict(orient="records")

    @staticmethod
    def sanitize_table_name(table_name: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", table_name.strip())
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")
        if not cleaned:
            cleaned = "uploaded_table"
        if cleaned[0].isdigit():
            cleaned = f"t_{cleaned}"
        return cleaned.lower()

    def get_schema(self) -> str:
        """Get the database schema for LLM context."""
        tables = self.conn.execute("SHOW TABLES").df()
        schema_info = []
        
        for _, row in tables.iterrows():
            table_name = row['name']
            columns = self.conn.execute(f"DESCRIBE {table_name}").df()
            col_info = [f"{c['column_name']} ({c['column_type']})" for _, c in columns.iterrows()]
            schema_info.append(f"Table: {table_name}\nColumns: {', '.join(col_info)}")
            
        return "\n\n".join(schema_info)

    def close(self):
        self.conn.close()

# Singleton instance for the app
duckdb_connector = DuckDBConnector()
