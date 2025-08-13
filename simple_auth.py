import streamlit as st
import yaml
import hashlib
import datetime
import jwt
import hmac


class SimpleAuth:
    def __init__(self, config_file='config.yaml'):
        """Initialize the authentication system with config file."""
        self.config_file = config_file
        self.config = self._load_config()
        
    def _load_config(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config_file, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            st.error(f"Configuration file {self.config_file} not found!")
            return None
        except yaml.YAMLError as e:
            st.error(f"Error parsing configuration file: {e}")
            return None
    
    def _hash_password(self, password):
        """Hash password using SHA256."""
        return hashlib.sha256(str.encode(password)).hexdigest()
    
    def _verify_password(self, stored_password, provided_password):
        """Verify if provided password matches stored password."""
        # If stored password is already hashed, compare with hashed provided password
        if len(stored_password) == 64:  # SHA256 hash length
            return stored_password == self._hash_password(provided_password)
        else:
            # If stored password is plain text, compare directly
            return stored_password == provided_password
    
    def authenticate_user(self, username, password):
        """Authenticate user with username and password."""
        if not self.config:
            return False
            
        users = self.config.get('credentials', {}).get('usernames', {})
        
        # Debug prints
        print(f"Debug - Username: {repr(username)}")
        print(f"Debug - Password: {repr(password)}")
        print(f"Debug - Available users: {list(users.keys())}")
        
        if username in users:
            stored_password = users[username]['password']
            print(f"Debug - Stored password: {repr(stored_password)}")
            
            is_match = self._verify_password(stored_password, password)
            print(f"Debug - Password match: {is_match}")
            
            if is_match:
                return True
        
        return False
    
    def is_preauthorized(self, email):
        """Check if email is preauthorized."""
        if not self.config:
            return False
            
        preauthorized = self.config.get('preauthorized', {}).get('emails', [])
        return email in preauthorized
    
    def create_jwt_token(self, username):
        """Create JWT token for authenticated user."""
        if not self.config:
            return None
            
        cookie_config = self.config.get('cookie', {})
        secret_key = cookie_config.get('key', 'default_secret_key')
        expiry_days = cookie_config.get('expiry_days', 30)
        
        payload = {
            'username': username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=expiry_days)
        }
        
        return jwt.encode(payload, secret_key, algorithm='HS256')
    
    def verify_jwt_token(self, token):
        """Verify JWT token and return username if valid."""
        if not self.config:
            return None
            
        try:
            cookie_config = self.config.get('cookie', {})
            secret_key = cookie_config.get('key', 'default_secret_key')
            
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            return payload.get('username')
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def login_form(self):
        """Display enhanced login form with branding and better UI."""
        # Custom CSS for login page
        st.markdown("""
        <style>
            /* Login page specific styling */
            .login-header {
                text-align: center;
                padding: 3rem 0 2rem 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 15px;
                margin-bottom: 3rem;
                color: white;
                box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
            }
            
            
            .login-title {
                text-align: center;
                color: #333;
                margin-bottom: 2rem;
                font-weight: 600;
            }
            
            /* Custom input styling */
            .stTextInput > div > div > input {
                border-radius: 8px;
                border: 2px solid #e0e0e0;
                padding: 12px 16px;
                font-size: 16px;
                transition: all 0.3s ease;
            }
            
            .stTextInput > div > div > input:focus {
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            
            /* Custom button styling */
            .stButton > button {
                width: 100%;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                font-weight: 600;
                color: white;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }
            
            .stButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
                background: linear-gradient(135deg, #5a6fd8 0%, #6a4c93 100%);
            }
            
            /* Hide main menu and footer for login */
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
        </style>
        """, unsafe_allow_html=True)
        
        # Main header with branding
        st.markdown("""
        <div class="login-header">
            <h1 style="margin: 0; font-size: 3rem; font-weight: 700;">Smart DBA Bot</h1>
            <p style="margin: 1rem 0 0 0; font-size: 1.3rem; opacity: 0.9;">Ask questions about your database!</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Center the login form
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown('<h3 style="text-align: center; color: #667eea; margin: 2rem 0; font-weight: 600;">Login</h3>', unsafe_allow_html=True)
            
            with st.form("login_form", clear_on_submit=False):
                st.markdown("<br>", unsafe_allow_html=True)
                username = st.text_input("Username", placeholder="Enter your username")
                st.markdown("<br>", unsafe_allow_html=True)
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                st.markdown("<br>", unsafe_allow_html=True)
                
                submit = st.form_submit_button("Login")
                
                if submit:
                    if username.strip() and password.strip():
                        if self.authenticate_user(username, password):
                            # Set session state
                            st.session_state['authenticated'] = True
                            st.session_state['username'] = username
                            
                            # Create and store JWT token
                            token = self.create_jwt_token(username)
                            if token:
                                st.session_state['token'] = token
                            
                            st.success("✅ Login successful! Redirecting...")
                            st.rerun()
                        else:
                            st.error("❌ Invalid username or password")
                    else:
                        st.warning("⚠️ Please enter both username and password")
    
    def logout(self):
        """Handle user logout."""
        # Clear session state
        for key in ['authenticated', 'username', 'token']:
            if key in st.session_state:
                del st.session_state[key]
        
        st.success("Logged out successfully!")
        st.rerun()
    
    def is_authenticated(self):
        """Check if user is authenticated."""
        # Check session state first
        if st.session_state.get('authenticated', False):
            return True
        
        # Check JWT token if available
        token = st.session_state.get('token')
        if token:
            username = self.verify_jwt_token(token)
            if username:
                st.session_state['authenticated'] = True
                st.session_state['username'] = username
                return True
        
        return False
    
    def get_username(self):
        """Get current authenticated username."""
        return st.session_state.get('username', 'Unknown')
    
    def require_auth(self):
        """Decorator-like function to require authentication."""
        if not self.is_authenticated():
            self.login_form()
            st.stop()
