# src/intelligent_live_query.py
"""
Intelligent Live Query System with Graph Visualization
=====================================================

LLM dynamically generates SQL queries based on user questions,
executes them across 4 inventory databases, and provides intelligent analysis
with interactive graph visualizations.

Flow:
1. User asks question in natural language
2. LLM analyzes question and generates appropriate SQL queries
3. System executes queries across all 4 datacenter databases
4. LLM analyzes results and provides intelligent response
5. If graph requested, generates interactive visualization
"""

import os
import json
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from openai import OpenAI
import pandas as pd
import concurrent.futures
from threading import Lock

# Handle environment variables for both local and cloud deployment
try:
    import streamlit as st
    # Try to get from Streamlit secrets first (for cloud deployment)
    def get_env_var(key, default=None):
        try:
            return st.secrets[key]
        except:
            return os.getenv(key, default)
except ImportError:
    # Fallback for non-Streamlit environments
    from dotenv import load_dotenv
    load_dotenv()
    def get_env_var(key, default=None):
        return os.getenv(key, default)

# Import graph visualization module
try:
    from graph_visualizer import GraphVisualizer, enhance_chat_response_with_graphs
except ImportError:
    GraphVisualizer = None
    enhance_chat_response_with_graphs = None
    print("[WARNING] Graph visualization module not available")

@dataclass
class QueryRequest:
    """Represents a query request from the LLM"""
    sql: str
    target_tables: List[str]  # Which tables to query
    target_servers: List[str]  # Which servers to query (or 'all')
    reason: str  # Why this query is needed
    expected_result: str  # What we expect to find

@dataclass
class QueryResult:
    """Result from executing queries"""
    server_name: str
    table_name: str
    sql: str
    success: bool
    data: Optional[pd.DataFrame]
    row_count: int
    execution_time: float
    error: Optional[str] = None

class IntelligentLiveQuerySystem:
    """
    Intelligent system that generates and executes live queries based on user questions
    """
    
    def __init__(self):
        self.servers = self._load_server_configs()
        self.llm_client = self._init_llm_client()
        self.query_lock = Lock()
        
        # Database schema information (cached for query generation)
        self.schema_cache = {}
        self._load_schema_cache()
    
    def _load_server_configs(self) -> List[Dict[str, str]]:
        """Load server configurations from environment with proper datacenter mappings"""
        servers = []
        # Enhanced datacenter mapping with multiple naming options
        datacenter_configs = [
            {"name": "DC4", "aliases": ["dc4", "datacenter-4", "datacenter 4"], "host_key": "HEALTH_CHECK_HOST_1"},
            {"name": "GB00", "aliases": ["gb00", "datacenter-2", "datacenter 2"], "host_key": "HEALTH_CHECK_HOST_2"},
            {"name": "CH00", "aliases": ["ch00", "datacenter-3", "datacenter 3"], "host_key": "HEALTH_CHECK_HOST_3"},
            {"name": "SG00", "aliases": ["sg00", "datacenter-1", "datacenter 1"], "host_key": "HEALTH_CHECK_HOST_4"}
        ]
        
        for dc_config in datacenter_configs:
            host_address = get_env_var(dc_config["host_key"])
            if host_address:
                servers.append({
                    'name': dc_config["name"],
                    'aliases': dc_config["aliases"],
                    'host': host_address,
                    'port': int(get_env_var("HEALTH_CHECK_PORT", "5432")),
                    'database': get_env_var("HEALTH_CHECK_DB", "inventory"),
                    'username': get_env_var("HEALTH_CHECK_USER", "app_user_pg"),
                    'password': get_env_var("HEALTH_CHECK_PASSWORD", "Str0ngPg#2025")
                })
        return servers
    
    def _init_llm_client(self) -> OpenAI:
        """Initialize LLM client"""
        github_token = get_env_var("GITHUB_TOKEN")
        if not github_token:
            raise ValueError("GITHUB_TOKEN environment variable is not set. Please set it with a valid GitHub token.")
        
        try:
            return OpenAI(
                base_url="https://models.github.ai/inference",
                api_key=github_token,
            )
        except Exception as e:
            raise Exception(f"Failed to initialize OpenAI client: {str(e)}. Make sure GITHUB_TOKEN is valid and you have access to GitHub Models.")
    
    def _load_schema_cache(self):
        """Load database schema information for intelligent query generation"""
        # Actual schema from the inventory database
        actual_schema = {
            'oracle_tb': [
                'id', 'data_extracted_on', 'database_type', 'hostname', 'database_status', 
                'database_name', 'database_size', 'database_version', 'database_role',
                'database_uptime', 'is_it_pdb', 'cluster_type', 'os_type', 'cpu_count',
                'encryption_status', 'server_uptime', 'ram', 'last_backup', 'backup_type',
                'collection_status', 'data_centre'
            ],
            'postgres_tb': [
                'id', 'data_extracted_on', 'database_type', 'hostname', 'database_status', 
                'database_name', 'database_size', 'database_version', 'database_role',
                'database_uptime', 'is_it_pdb', 'cluster_type', 'os_type', 'cpu_count',
                'encryption_status', 'server_uptime', 'ram', 'last_backup', 'backup_type',
                'collection_status', 'data_centre'
            ],
            'mysql_tb': [
                'id', 'data_extracted_on', 'database_type', 'hostname', 'database_status', 
                'database_name', 'database_size', 'database_version', 'database_role',
                'database_uptime', 'is_it_pdb', 'cluster_type', 'os_type', 'cpu_count',
                'encryption_status', 'server_uptime', 'ram', 'last_backup', 'backup_type',
                'collection_status', 'data_centre'
            ],
            'mssql_tb': [
                'id', 'data_extracted_on', 'database_type', 'hostname', 'database_status', 
                'database_name', 'database_size', 'database_version', 'database_role',
                'database_uptime', 'is_it_pdb', 'cluster_type', 'os_type', 'cpu_count',
                'encryption_status', 'server_uptime', 'ram', 'last_backup', 'backup_type',
                'collection_status', 'data_centre'
            ]
        }
        self.schema_cache = actual_schema
    
    async def answer_question(self, user_question: str) -> str:
        """
        Main method: Answer user question by generating and executing live queries
        """
        try:
            print(f"[DEBUG] Processing question: {user_question}")
            
            # Step 1: LLM analyzes question and generates query plan
            query_plan = await self._generate_query_plan(user_question)
            
            if not query_plan:
                return "❌ I couldn't understand your question. Please try rephrasing it."
            
            print(f"[DEBUG] Generated {len(query_plan)} queries")
            
            # Step 2: Execute queries across all relevant servers
            query_results = await self._execute_queries(query_plan)
            
            print(f"[DEBUG] Executed queries, got {len(query_results)} results")
            
            # Store query results for potential graph generation
            self._last_query_results = query_results
            
            # Step 3: LLM analyzes results and provides intelligent response
            final_response = await self._analyze_and_respond(
                user_question, query_plan, query_results
            )
            
            return final_response
            
        except Exception as e:
            return f"❌ Error processing your question: {str(e)}"
    
    async def _generate_query_plan(self, user_question: str) -> List[QueryRequest]:
        """
        LLM generates SQL queries based on user question
        """
        schema_info = json.dumps(self.schema_cache, indent=2)
        
        system_prompt = f"""
You are an expert SQL query generator for database health monitoring systems.

AVAILABLE DATABASES AND TABLES:
{schema_info}

AVAILABLE DATACENTERS:
- DC4 (us01vlpgdd.saas-n.com) = HEALTH_CHECK_HOST_1 [PRIMARY - Most Active]
- GB00 (host2.example.com) = HEALTH_CHECK_HOST_2
- CH00 (host3.example.com) = HEALTH_CHECK_HOST_3  
- SG00 (host4.example.com) = HEALTH_CHECK_HOST_4

Each datacenter has inventory database with tables: oracle_tb, postgres_tb, mysql_tb, mssql_tb

YOUR TASK:
1. Analyze the user's question to identify which datacenter(s) and database type(s)
2. Generate appropriate SQL queries with CORRECT syntax
3. Map datacenter names correctly (DC4, GB00, CH00, SG00)
4. Return JSON array of query requests

CRITICAL SQL RULES:
- Use standard PostgreSQL SQL syntax ONLY
- ORDER BY clause MUST reference columns that exist in the SELECT clause
- For DISTINCT queries: SELECT DISTINCT hostname, database_name FROM table_name ORDER BY hostname
- For server lists with details: SELECT hostname, database_name, status, data_extracted_on FROM table_name ORDER BY data_extracted_on DESC
- Use ILIKE for case-insensitive matching
- NEVER use ORDER BY with columns not in SELECT when using DISTINCT
- For uptime queries: database_uptime contains TIMESTAMP values (e.g., '2025-07-21 19:08:48')
- To filter by uptime days: 
  * For "uptime > X days" (longer uptime): Use "NOW() - database_uptime::timestamp > INTERVAL 'X days'"
  * For "uptime < X days" (shorter uptime): Use "NOW() - database_uptime::timestamp < INTERVAL 'X days'"
- When user asks for uptime info, include server_uptime column in SELECT
- For vague numbers like "days" without specific number, assume 7 days as default

DATACENTER SELECTION LOGIC:
- Datacenter filtering is handled by selecting which physical servers to query
- NEVER use data_centre column in WHERE clauses - it's for reference only
- No datacenter mentioned → Query ALL datacenters ["all"]
- "DC4", "dc4", "datacenter-4", "from DC4" → Query DC4 only ["DC4"]
- "GB00", "gb00", "datacenter-2", "from GB00" → Query GB00 only ["GB00"]
- "CH00", "ch00", "datacenter-3", "from CH00" → Query CH00 only ["CH00"]
- "SG00", "sg00", "datacenter-1", "from SG00" → Query SG00 only ["SG00"]

CORRECT SQL EXAMPLES using ACTUAL column names:
✅ GOOD for server lists: "SELECT DISTINCT hostname FROM oracle_tb ORDER BY hostname"
✅ GOOD with details: "SELECT DISTINCT hostname, database_name, database_status FROM oracle_tb ORDER BY hostname"
✅ GOOD with filtering: "SELECT DISTINCT hostname FROM oracle_tb WHERE database_status ILIKE '%down%' ORDER BY hostname"
✅ GOOD for all details: "SELECT hostname, database_name, database_status, data_extracted_on FROM oracle_tb ORDER BY data_extracted_on DESC"
✅ GOOD for uptime queries: "SELECT DISTINCT hostname, database_name, database_status, server_uptime FROM oracle_tb WHERE NOW() - database_uptime::timestamp > INTERVAL '10 days' ORDER BY hostname"
✅ GOOD for DC4 uptime: "SELECT DISTINCT hostname, database_name, database_status, server_uptime FROM oracle_tb WHERE NOW() - database_uptime::timestamp > INTERVAL '7 days' ORDER BY hostname"
❌ BAD: "SELECT DISTINCT hostname FROM oracle_tb ORDER BY data_extracted_on" (ORDER BY column not in SELECT)
❌ BAD: "SELECT hostname, status FROM oracle_tb" (column 'status' doesn't exist, use 'database_status')
❌ BAD: "WHERE database_uptime > days" (invalid syntax, use proper INTERVAL)

IMPORTANT: For server listings, always use DISTINCT hostname to avoid duplicates!

DATABASE TYPE SELECTION:
- "Oracle", "oracle" → target_tables: ["oracle_tb"]
- "PostgreSQL", "postgres", "pg" → target_tables: ["postgres_tb"]
- "MySQL", "mysql" → target_tables: ["mysql_tb"]
- "SQL Server", "mssql", "sqlserver" → target_tables: ["mssql_tb"]
- No specific type mentioned → target_tables: ["oracle_tb", "postgres_tb", "mysql_tb", "mssql_tb"]

RESPONSE FORMAT (JSON):
[
  {{
    "sql": "SELECT hostname, database_name, database_status, data_extracted_on FROM oracle_tb ORDER BY data_extracted_on DESC",
    "target_tables": ["oracle_tb"],
    "target_servers": ["DC4"],
    "reason": "Get Oracle server list from DC4 datacenter with latest data first",
    "expected_result": "List of Oracle servers in DC4 ordered by extraction date"
  }}
]
"""

        user_prompt = f"""
Generate SQL queries to answer this question:
"{user_question}"

Return only the JSON array, no other text.
"""

        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent SQL generation
                max_tokens=2000
            )
            
            response_text = response.choices[0].message.content.strip()
            print(f"[DEBUG] Full LLM response: {response_text}")  # Debug output
            
            # Extract JSON from response - more robust parsing
            if response_text.startswith('```json'):
                response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
            elif response_text.startswith('```'):
                response_text = response_text[3:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
            
            # Clean up the response text
            response_text = response_text.strip()
            
            # Try to find JSON array if it's embedded in other text
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            
            print(f"[DEBUG] Cleaned JSON: {response_text[:200]}...")  # Debug output
            
            query_data = json.loads(response_text)
            
            # Convert to QueryRequest objects
            query_requests = []
            for q in query_data:
                query_requests.append(QueryRequest(
                    sql=q['sql'],
                    target_tables=q['target_tables'],
                    target_servers=q['target_servers'],
                    reason=q['reason'],
                    expected_result=q['expected_result']
                ))
            
            print(f"[DEBUG] Successfully generated {len(query_requests)} query requests")
            return query_requests
            
        except Exception as e:
            print(f"[ERROR] Query generation failed: {e}")
            print(f"[ERROR] Response text: {response_text if 'response_text' in locals() else 'No response text'}")
            return []
    
    async def _execute_queries(self, query_plan: List[QueryRequest]) -> List[QueryResult]:
        """
        Execute queries across all relevant servers and tables
        """
        all_results = []
        
        # Use thread pool for concurrent execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            
            for query_request in query_plan:
                # Determine which servers to query
                if query_request.target_servers == ["all"]:
                    target_servers = self.servers
                else:
                    # Map datacenter names properly
                    target_servers = []
                    for target_name in query_request.target_servers:
                        for server in self.servers:
                            if server['name'] == target_name:
                                target_servers.append(server)
                                break
                
                # Create execution tasks
                for server in target_servers:
                    for table_name in query_request.target_tables:
                        future = executor.submit(
                            self._execute_single_query,
                            server, table_name, query_request.sql
                        )
                        futures.append(future)
            
            # Collect results
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=30)  # 30 second timeout
                    all_results.append(result)
                except Exception as e:
                    print(f"[ERROR] Query execution failed: {e}")
        
        return all_results
    
    def _execute_single_query(self, server: Dict, table_name: str, sql: str) -> QueryResult:
        """
        Execute a single query on a specific server and table
        """
        start_time = datetime.now()
        
        print(f"[DEBUG Query] Executing on {server['name']} ({server['host']}) - Table: {table_name}")
        
        try:
            # Modify SQL to target specific table
            modified_sql = sql.replace('{table}', table_name)
            if 'FROM ' not in modified_sql.upper():
                modified_sql = f"SELECT * FROM {table_name} WHERE " + modified_sql
            
            print(f"[DEBUG Query] SQL: {modified_sql[:100]}...")
            
            # Connect and execute with enhanced connection parameters
            print(f"[DEBUG Query] Connecting to {server['host']}:{server['port']} as {server['username']}")
            
            # Enhanced connection parameters for cloud deployment
            conn_params = {
                'host': server['host'],
                'port': server['port'],
                'dbname': server['database'],
                'user': server['username'],
                'password': server['password'],
                'connect_timeout': 30,  # Increased timeout for cloud connections
                'sslmode': 'prefer',    # Try SSL first, fallback to non-SSL
                'application_name': 'smart_dba_bot',
                'options': '-c statement_timeout=30000'  # 30 second query timeout
            }
            
            try:
                conn = psycopg2.connect(**conn_params)
            except psycopg2.OperationalError as e:
                # If SSL connection fails, try without SSL
                if 'SSL' in str(e) or 'ssl' in str(e).lower():
                    print(f"[DEBUG Query] SSL connection failed, retrying without SSL: {e}")
                    conn_params['sslmode'] = 'disable'
                    conn = psycopg2.connect(**conn_params)
                else:
                    raise
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(modified_sql)
                rows = cursor.fetchall()
                
                # Convert to DataFrame
                df = pd.DataFrame(rows) if rows else pd.DataFrame()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                conn.close()
                
                return QueryResult(
                    server_name=server['name'],
                    table_name=table_name,
                    sql=modified_sql,
                    success=True,
                    data=df,
                    row_count=len(df),
                    execution_time=execution_time
                )
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return QueryResult(
                server_name=server['name'],
                table_name=table_name,
                sql=sql,
                success=False,
                data=None,
                row_count=0,
                execution_time=execution_time,
                error=str(e)
            )
    
    async def _analyze_and_respond(self, user_question: str, 
                                   query_plan: List[QueryRequest], 
                                   query_results: List[QueryResult]) -> str:
        """
        LLM analyzes query results and provides intelligent response
        """
        
        # Prepare results summary for LLM
        results_summary = self._prepare_results_summary(query_results)
        
        system_prompt = """
You are an expert Database Administrator providing crisp, focused analysis.

DATACENTER MAPPING:
- DC4 = First datacenter
- GB00 = Second datacenter
- CH00 = Third datacenter  
- SG00 = Fourth datacenter

Your task:
1. Analyze the query results from datacenters (DC4, GB00, CH00, SG00)
2. Provide CRISP, FOCUSED responses - NO unnecessary suggestions unless asked
3. For server lists, format as a table with proper headers and alignment
4. Use unique hostnames only, no duplicates
5. Number rows sequentially starting from 1
6. IMPORTANT: When user asks for "all servers" or "all database types" but some database types return no data or errors:
   - Show available data from successful queries
   - Add a brief note explaining missing database types
   - all database means oracle, postgres , mysql and mssql everything if any csv is not found it shall say in the output saying "example: no data found for mysql database" 

Response guidelines:
- Be direct and to the point
- Format server listings as a perfectly aligned table INSIDE <div> blocks
- CRITICAL: Wrap the entire table in <div style="font-family: monospace; white-space: pre;"> to preserve spacing
- DYNAMICALLY adjust columns based on the user's specific request AND query criteria
- If user asks for specific columns (e.g., "only host details and server uptime"), show ONLY those columns
- If user asks for "unique" data, ensure no duplicate rows
- AUTOMATIC COLUMN INCLUSION based on query criteria:
  * If query involves uptime filtering → automatically include "server uptime" column
  * If query involves size filtering → automatically include "database size" column
  * If query involves status filtering → automatically include "database status" column
  * If query involves backup filtering → automatically include "last backup" column
  * If query involves RAM filtering → automatically include "ram" column
- For general queries without column specification, use standard format: sno, host details, data centre, Database
- Always include sno column for numbering unless user specifically excludes it

EXAMPLE FORMATS:

Basic server list:
<div style="font-family: monospace; white-space: pre;">
sno    host details                     data centre   Database
---    -------------------------------- -----------   --------
  1    us01vldgbdbv05.auto.saas-n.com       DC4       oracle
  2    us01vlpgdd.saas-n.com                DC4       postgres
</div>

Uptime query (when user asks about uptime):
<div style="font-family: monospace; white-space: pre;">
sno    host details                     data centre   Database   server uptime
---    -------------------------------- -----------   --------   -------------
  1    us01vldgbdbv05.auto.saas-n.com       DC4       oracle     2025-07-21 19:08:48
  2    us01vlpgdd.saas-n.com                DC4       postgres   2025-07-22 10:01:27
</div>

Custom columns (when user asks for "only host details and server uptime"):
<div style="font-family: monospace; white-space: pre;">
sno    host details                     server uptime
---    -------------------------------- -------------
  1    us01vldgbdbv05.auto.saas-n.com   2025-07-21 19:08:48
  2    us01vlpgdd.saas-n.com            2025-07-22 10:01:27
</div>

When user asks for unique values only (no sno needed for unique data):
<div style="font-family: monospace; white-space: pre;">
host details                     server uptime
-------------------------------- -------------
us01vlpgdd.saas-n.com            2025-07-10 10:05:24
</div>

- MANDATORY formatting rules:
  * Wrap entire table in <div style="font-family: monospace; white-space: pre;"> blocks
  * CRITICAL: Each row MUST be on a separate line with actual line breaks (\n)
  * Use actual newline characters between each row - DO NOT put all on one line
  * sno column: 3 digits right-aligned, 6 total chars
  * host details column: 32 chars left-aligned, pad with spaces
  * data centre column: 11 chars left-aligned, pad with spaces  
  * Database column: left-aligned
  * Use spaces for ALL alignment, never tabs
  * Include separator line with dashes for clarity
  * EXAMPLE - each line below is a separate line:
    Line 1: sno    host details                     data centre   Database
    Line 2: ---    -------------------------------- -----------   --------
    Line 3:   1    us01vldgbdbv05.auto.saas-n.com       DC4       oracle
    Line 4:   2    us01vlpgdd.saas-n.com                DC4       postgres
- Include datacenter names (DC4, GB00, CH00, SG00) in results
- Show database type based on which table the server appears in
- Don't add tips/suggestions unless specifically asked
- Focus only on answering the exact question asked
- Use 🚨 only for actual critical issues, not general advice
"""

        user_prompt = f"""
ORIGINAL QUESTION: {user_question}

QUERY EXECUTION SUMMARY:
- Total queries executed: {len(query_results)}
- Successful queries: {sum(1 for r in query_results if r.success)}
- Failed queries: {sum(1 for r in query_results if not r.success)}

RESULTS DATA:
{results_summary}

Please analyze these results and provide a comprehensive answer to the user's question.
"""

        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=3000
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"❌ Error analyzing results: {str(e)}"
    
    def _prepare_results_summary(self, query_results: List[QueryResult]) -> str:
        """
        Prepare a summary of query results for LLM analysis
        """
        summary = ""
        
        # Group results by server and table
        results_by_server = {}
        for result in query_results:
            if result.server_name not in results_by_server:
                results_by_server[result.server_name] = {}
            if result.table_name not in results_by_server[result.server_name]:
                results_by_server[result.server_name][result.table_name] = []
            results_by_server[result.server_name][result.table_name].append(result)
        
        for server_name, tables in results_by_server.items():
            summary += f"\n=== {server_name} ===\n"
            
            for table_name, results in tables.items():
                summary += f"\n{table_name}:\n"
                
                for result in results:
                    if result.success and result.data is not None and not result.data.empty:
                        # Include key statistics
                        df = result.data
                        summary += f"  - Records: {len(df)}\n"
                        
                        # Include sample of actual data (first few rows)
                        if len(df) > 0:
                            summary += f"  - Sample data:\n"
                            sample_df = df.head(5)
                            for _, row in sample_df.iterrows():
                                row_str = ", ".join([f"{k}={v}" for k, v in row.items() if pd.notna(v)])
                                summary += f"    {row_str}\n"
                        
                        # Include key aggregations if relevant columns exist
                        if 'database_status' in df.columns:
                            status_counts = df['database_status'].value_counts()
                            summary += f"  - Status distribution: {status_counts.to_dict()}\n"
                        
                        if 'database_size' in df.columns:
                            # Handle database_size which might be in different formats
                            try:
                                df['size_numeric'] = pd.to_numeric(df['database_size'], errors='coerce')
                                valid_sizes = df['size_numeric'].dropna()
                                if len(valid_sizes) > 0:
                                    total_size = valid_sizes.sum()
                                    avg_size = valid_sizes.mean()
                                    summary += f"  - Total size: {total_size:.2f} GB, Average: {avg_size:.2f} GB\n"
                            except:
                                summary += f"  - Database sizes available but format varies\n"
                        
                        if 'ram' in df.columns:
                            try:
                                df['ram_numeric'] = pd.to_numeric(df['ram'], errors='coerce')
                                valid_ram = df['ram_numeric'].dropna()
                                if len(valid_ram) > 0:
                                    avg_ram = valid_ram.mean()
                                    summary += f"  - Average RAM: {avg_ram:.2f} GB\n"
                            except:
                                pass
                    
                    elif not result.success:
                        summary += f"  - ERROR: {result.error}\n"
                    else:
                        summary += f"  - No data returned (empty table)\n"
        
        return summary

# Usage example and integration
class LiveQueryChatbot:
    """
    Chatbot that uses live queries to answer questions
    """
    
    def __init__(self):
        self.query_system = IntelligentLiveQuerySystem()
    
    async def chat(self, question: str) -> str:
        """
        Main chat interface with progress tracking
        """
        print(f"🤖 Step 1/4: Analyzing your question...")
        print(f"🤖 Step 2/4: Generating SQL queries...")
        print(f"🤖 Step 3/4: Querying live databases...")
        print(f"🤖 Step 4/4: Analyzing results and generating response...")
        
        response = await self.query_system.answer_question(question)
        
        return response

# Integration with existing Streamlit app
def create_live_query_interface():
    """
    Create Streamlit interface for live queries
    """
    import streamlit as st
    import asyncio
    
    st.title("🔍 Live Database Query Assistant")
    st.markdown("Ask questions and I'll query the live databases for you!")
    
    if "live_chatbot" not in st.session_state:
        st.session_state.live_chatbot = LiveQueryChatbot()
    
    # Quick action buttons
    st.markdown("### 🚀 Quick Questions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Overall Health Status"):
            question = "Show me the overall health status of all databases across all datacenters"
            with st.spinner("Querying live databases..."):
                response = asyncio.run(st.session_state.live_chatbot.chat(question))
            st.markdown(response)
    
    with col2:
        if st.button("🚨 Critical Issues"):
            question = "Show me all databases with critical issues like low disk space or backup failures"
            with st.spinner("Querying live databases..."):
                response = asyncio.run(st.session_state.live_chatbot.chat(question))
            st.markdown(response)
    
    with col3:
        if st.button("💾 Storage Analysis"):
            question = "Analyze database storage usage and show the largest databases"
            with st.spinner("Querying live databases..."):
                response = asyncio.run(st.session_state.live_chatbot.chat(question))
            st.markdown(response)
    
    # Custom question input
    st.markdown("### 💬 Ask Your Question")
    user_question = st.text_area(
        "What would you like to know about your databases?",
        placeholder="e.g., 'Show me all Oracle databases that are down in Datacenter-1'"
    )
    
    if st.button("🔍 Query Databases", type="primary"):
        if user_question.strip():
            with st.spinner("Analyzing question and querying live databases..."):
                response = asyncio.run(st.session_state.live_chatbot.chat(user_question))
            
            st.markdown("### 📊 Results")
            st.markdown(response)
        else:
            st.warning("Please enter a question first!")

if __name__ == "__main__":
    # Test the system
    async def test_system():
        chatbot = LiveQueryChatbot()
        
        test_questions = [
            "Show me all databases that are currently down",
            "What are the largest Oracle databases across all datacenters?",
            "Show me backup failures in the last 24 hours",
            "Which servers have less than 10% free disk space?"
        ]
        
        for question in test_questions:
            print(f"\n{'='*60}")
            print(f"Q: {question}")
            print('='*60)
            
            response = await chatbot.chat(question)
            print(response)
    
    # Run test
    asyncio.run(test_system())
