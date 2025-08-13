import streamlit as st
import psycopg2
import socket
import ssl
from datetime import datetime
import time

st.title("🔧 Database Connection Debug Tool")

# Function to get environment variable with fallback
def get_env_var(key, default=None):
    try:
        return st.secrets[key]
    except:
        return default

# Test environment variables
st.subheader("1. Environment Variables Check")
try:
    host1 = get_env_var("HEALTH_CHECK_HOST_1")
    db = get_env_var("HEALTH_CHECK_DB") 
    user = get_env_var("HEALTH_CHECK_USER")
    port = get_env_var("HEALTH_CHECK_PORT")
    password = get_env_var("HEALTH_CHECK_PASSWORD")
    
    if host1:
        st.success(f"✅ Host: {host1}")
    else:
        st.error("❌ HEALTH_CHECK_HOST_1 not found")
        
    if db:
        st.success(f"✅ Database: {db}")
    else:
        st.error("❌ HEALTH_CHECK_DB not found")
        
    if user:
        st.success(f"✅ User: {user}")
    else:
        st.error("❌ HEALTH_CHECK_USER not found")
        
    if port:
        st.success(f"✅ Port: {port}")
    else:
        st.error("❌ HEALTH_CHECK_PORT not found")
        
    if password:
        st.success("✅ Password: [HIDDEN]")
    else:
        st.error("❌ HEALTH_CHECK_PASSWORD not found")
        
except Exception as e:
    st.error(f"❌ Secrets error: {e}")

# Test DNS resolution
st.subheader("2. DNS Resolution Test")
if host1:
    try:
        start_time = time.time()
        ip_address = socket.gethostbyname(host1)
        dns_time = (time.time() - start_time) * 1000
        st.success(f"✅ DNS resolved {host1} to {ip_address} ({dns_time:.1f}ms)")
    except Exception as e:
        st.error(f"❌ DNS resolution failed: {e}")
else:
    st.warning("⚠️ Skipping DNS test - no host configured")

# Test network connectivity (telnet-like)
st.subheader("3. Network Connectivity Test")
if host1 and port:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)
        start_time = time.time()
        result = sock.connect_ex((host1, int(port)))
        connect_time = (time.time() - start_time) * 1000
        sock.close()
        
        if result == 0:
            st.success(f"✅ Network connection to {host1}:{port} successful ({connect_time:.1f}ms)")
        else:
            st.error(f"❌ Cannot connect to {host1}:{port} (error code: {result})")
            st.info("This usually indicates:")
            st.info("• Firewall blocking connection from Streamlit Cloud")
            st.info("• Database server not accessible from internet")
            st.info("• Port filtering or VPN restrictions")
    except Exception as e:
        st.error(f"❌ Network test failed: {e}")
else:
    st.warning("⚠️ Skipping network test - missing host/port configuration")

# Test SSL capabilities
st.subheader("4. SSL/TLS Test")
if host1 and port:
    try:
        # Test SSL connection
        context = ssl.create_default_context()
        with socket.create_connection((host1, int(port)), timeout=15) as sock:
            with context.wrap_socket(sock, server_hostname=host1) as ssock:
                st.success(f"✅ SSL/TLS connection successful")
                st.info(f"SSL version: {ssock.version()}")
    except Exception as e:
        st.warning(f"⚠️ SSL connection failed: {e}")
        st.info("Will try non-SSL PostgreSQL connection")

# Test PostgreSQL connection with multiple strategies
st.subheader("5. PostgreSQL Connection Test")

if st.button("Test Database Connection"):
    if not all([host1, port, db, user, password]):
        st.error("❌ Missing required connection parameters")
    else:
        # Strategy 1: Try with SSL preferred
        st.write("**Strategy 1: SSL Preferred**")
        try:
            with st.spinner("Connecting with SSL preferred..."):
                conn_params = {
                    'host': host1,
                    'port': int(port),
                    'dbname': db,
                    'user': user,
                    'password': password,
                    'connect_timeout': 30,
                    'sslmode': 'prefer',
                    'application_name': 'debug_connection_test'
                }
                
                conn = psycopg2.connect(**conn_params)
                cursor = conn.cursor()
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                cursor.close()
                conn.close()
                
                st.success(f"✅ PostgreSQL connection successful (SSL preferred)!")
                st.info(f"Database version: {version}")
                
        except psycopg2.OperationalError as e:
            st.error(f"❌ SSL preferred connection failed: {e}")
            
            # Strategy 2: Try without SSL
            st.write("**Strategy 2: No SSL**")
            try:
                with st.spinner("Connecting without SSL..."):
                    conn_params['sslmode'] = 'disable'
                    
                    conn = psycopg2.connect(**conn_params)
                    cursor = conn.cursor()
                    cursor.execute("SELECT version();")
                    version = cursor.fetchone()[0]
                    cursor.close()
                    conn.close()
                    
                    st.success(f"✅ PostgreSQL connection successful (no SSL)!")
                    st.info(f"Database version: {version}")
                    
            except psycopg2.OperationalError as e2:
                st.error(f"❌ Non-SSL connection also failed: {e2}")
                
                # Strategy 3: Try with require SSL
                st.write("**Strategy 3: SSL Required**")
                try:
                    with st.spinner("Connecting with SSL required..."):
                        conn_params['sslmode'] = 'require'
                        
                        conn = psycopg2.connect(**conn_params)
                        cursor = conn.cursor()
                        cursor.execute("SELECT version();")
                        version = cursor.fetchone()[0]
                        cursor.close()
                        conn.close()
                        
                        st.success(f"✅ PostgreSQL connection successful (SSL required)!")
                        st.info(f"Database version: {version}")
                        
                except psycopg2.OperationalError as e3:
                    st.error(f"❌ SSL required connection failed: {e3}")
                    st.error("**All connection strategies failed!**")
                    
                    st.info("**Common issues:**")
                    st.info("• Database firewall blocking Streamlit Cloud IPs")
                    st.info("• Incorrect credentials")
                    st.info("• Database server behind VPN/private network")
                    st.info("• Connection limits reached")
                    st.info("• Specific SSL certificate requirements")
                    
        except Exception as e:
            st.error(f"❌ Unexpected connection error: {e}")

# Test simple query if connection works
st.subheader("6. Database Query Test")
if st.button("Test Database Query"):
    if not all([host1, port, db, user, password]):
        st.error("❌ Missing required connection parameters")
    else:
        try:
            with st.spinner("Testing database query..."):
                # Use the most permissive connection first
                conn_params = {
                    'host': host1,
                    'port': int(port),
                    'dbname': db,
                    'user': user,
                    'password': password,
                    'connect_timeout': 30,
                    'sslmode': 'prefer',
                    'application_name': 'debug_query_test'
                }
                
                conn = psycopg2.connect(**conn_params)
                cursor = conn.cursor()
                
                # Test query on oracle_tb table
                cursor.execute("""
                    SELECT COUNT(*) as total_records 
                    FROM oracle_tb 
                    LIMIT 1;
                """)
                count = cursor.fetchone()[0]
                
                # Test basic data retrieval
                cursor.execute("""
                    SELECT hostname, database_name, database_status 
                    FROM oracle_tb 
                    ORDER BY data_extracted_on DESC
                    LIMIT 3;
                """)
                
                sample_data = cursor.fetchall()
                
                cursor.close()
                conn.close()
                
                st.success(f"✅ Database query successful!")
                st.info(f"Total records in oracle_tb: {count}")
                st.info("Sample data:")
                for row in sample_data:
                    st.text(f"  {row[0]} | {row[1]} | {row[2]}")
                    
        except Exception as e:
            st.error(f"❌ Database query failed: {e}")

# Environment information
st.subheader("7. Environment Information")
st.info(f"**Current time:** {datetime.now()}")
st.info("**Streamlit Cloud IP ranges to whitelist:**")
st.code("""
# Common Streamlit Cloud IP ranges (check Streamlit docs for latest)
# These should be whitelisted in your database firewall
18.216.0.0/12
18.208.0.0/13
3.208.0.0/12
""")

st.subheader("8. Troubleshooting Steps")
with st.expander("🔧 If connections fail, try these steps:"):
    st.markdown("""
    **1. Network/Firewall Issues:**
    - Ensure your database server accepts connections from Streamlit Cloud IP ranges
    - Check if your database is behind a corporate firewall or VPN
    - Verify the database server is accessible from the internet
    
    **2. Database Configuration:**
    - Confirm PostgreSQL is configured to accept external connections
    - Check `pg_hba.conf` and `postgresql.conf` settings
    - Verify the database user has proper permissions
    
    **3. SSL/TLS Issues:**
    - Try different SSL modes: `prefer`, `require`, `disable`
    - Check if your database requires specific SSL certificates
    - Verify SSL configuration on your PostgreSQL server
    
    **4. Credentials:**
    - Double-check username, password, database name, and host
    - Ensure credentials are correctly set in Streamlit Cloud secrets
    - Test credentials from a different client if possible
    
    **5. Connection Limits:**
    - Check if database has reached maximum connection limits
    - Monitor active connections on your database server
    """)

# Show current secrets (masked)
with st.expander("🔍 Current Configuration (Secrets Masked)"):
    st.json({
        "HEALTH_CHECK_HOST_1": host1 if host1 else "NOT SET",
        "HEALTH_CHECK_HOST_2": get_env_var("HEALTH_CHECK_HOST_2", "NOT SET"),
        "HEALTH_CHECK_HOST_3": get_env_var("HEALTH_CHECK_HOST_3", "NOT SET"),
        "HEALTH_CHECK_HOST_4": get_env_var("HEALTH_CHECK_HOST_4", "NOT SET"),
        "HEALTH_CHECK_PORT": port if port else "NOT SET",
        "HEALTH_CHECK_DB": db if db else "NOT SET",
        "HEALTH_CHECK_USER": user if user else "NOT SET",
        "HEALTH_CHECK_PASSWORD": "[HIDDEN]" if password else "NOT SET",
        "GITHUB_TOKEN": "[HIDDEN]" if get_env_var("GITHUB_TOKEN") else "NOT SET"
    })
