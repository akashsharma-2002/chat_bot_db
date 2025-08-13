# app.py - Main application file with Authentication
import streamlit as st
from datetime import datetime
import sys
from pathlib import Path
import asyncio
from simple_auth import SimpleAuth

# Add src directory to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from intelligent_live_query import LiveQueryChatbot
except ImportError as e:
    st.error(f"Could not import live query system: {e}")
    st.stop()

# ── BASIC PAGE CONFIG ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DBA BOT",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CUSTOM CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    /* Feature cards styling */
    .feature-card {
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        margin: 1rem 0;
        background: #f8f9fa;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .feature-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
        border-color: #667eea;
    }
    
    /* Sidebar navigation styling */
    .sidebar-nav {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    
    .nav-link {
        display: block;
        padding: 12px 16px;
        margin: 8px 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 600;
        font-size: 14px;
        transition: all 0.3s ease;
        border: none;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
    }
    
    .nav-link:hover {
        background: linear-gradient(135deg, #5a6fd8 0%, #6a4c93 100%);
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        color: white !important;
    }
    
    /* Status indicators */
    .status-container {
        background: #e8f5e8;
        border: 1px solid #c3e6c3;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .status-online {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
        color: #2d6a2d;
    }
    
    /* Override default streamlit sidebar styling */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* Main content area styling */
    .main-content {
        padding: 0 1rem;
    }
    
    /* Welcome section styling */
    .welcome-section {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        margin-bottom: 2rem;
    }
    
    /* Chat container styling */
    .chat-container {
        max-height: 500px;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        margin-bottom: 1rem;
        background: #fafafa;
    }
    .user-message {
        background: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        margin-left: 2rem;
        color: black;
    }
    .assistant-message {
        background: #f1f8e9;
        border-left: 4px solid #4caf50;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        margin-right: 2rem;
        color: black;
    }
    
    /* Enhanced styling for messages with embedded graphs */
    .message-with-graph {
        background: #f1f8e9;
        border-left: 4px solid #4caf50;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        margin-right: 2rem;
        color: black;
    }
    
    /* Graph container inside message */
    .graph-container {
        margin-top: 1rem;
        padding: 0.5rem;
        background: rgba(255, 255, 255, 0.3);
        border-radius: 6px;
        border: 1px solid rgba(76, 175, 80, 0.3);
    }
    
    .input-disabled {
        pointer-events: none;
        opacity: 0.6;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state variables
if "live_processing_query" not in st.session_state:
    st.session_state.live_processing_query = False
if "live_pending_question" not in st.session_state:
    st.session_state.live_pending_question = None

# Handle pending questions that need processing
if st.session_state.live_processing_query and st.session_state.live_pending_question:
    # Initialize chatbot and get response with spinner
    if "live_chatbot" not in st.session_state:
        try:
            with st.spinner("🔧 Initializing live query system..."):
                st.session_state.live_chatbot = LiveQueryChatbot()
        except Exception as e:
            st.session_state.live_chat_history.append({
                'role': 'assistant',
                'content': f"❌ Error initializing live query system: {str(e)}",
                'graph': None
            })
            st.session_state.live_processing_query = False
            st.session_state.live_pending_question = None
            st.rerun()
    
    # Get with spinner
    try:
        with st.spinner("processing..."):
            response = asyncio.run(st.session_state.live_chatbot.chat(st.session_state.live_pending_question))
        
        # Check for graph requests and Excel export
        graph_fig = None
        excel_html = None
        
        try:
            # Get query results from the chatbot's last execution
            query_results = None
            if hasattr(st.session_state.live_chatbot.query_system, '_last_query_results'):
                query_results = st.session_state.live_chatbot.query_system._last_query_results
            
            # Handle graph visualization
            try:
                from src.graph_visualizer import GraphVisualizer
                visualizer = GraphVisualizer()
                
                # Check if user requested a graph - enhanced detection
                user_question = st.session_state.live_pending_question.lower()
                graph_keywords = [
                    'graph', 'chart', 'plot', 'visualize', 'visualization',
                    'bar graph', 'pie chart', 'histogram', 'bar chart'
                ]
                
                if any(keyword in user_question for keyword in graph_keywords) and query_results:
                    # Determine chart type and datacenter filter
                    datacenter = None
                    for dc in ['dc4', 'gb00', 'ch00', 'sg00']:
                        if dc in user_question:
                            datacenter = dc.upper()
                            break
                    
                    # Enhanced chart type detection with defaults
                    chart_type = 'bar'  # Default for 'graph', 'chart', 'histogram'
                    
                    if any(keyword in user_question for keyword in ['pie', 'pie chart', 'donut']):
                        chart_type = 'pie'
                    elif any(keyword in user_question for keyword in ['horizontal', 'horizontal bar']):
                        chart_type = 'horizontal_bar'
                    elif any(keyword in user_question for keyword in ['heatmap', 'heat map']):
                        graph_fig = visualizer.create_database_status_heatmap(query_results)
                    elif any(keyword in user_question for keyword in ['comparison', 'compare']):
                        graph_fig = visualizer.create_datacenter_comparison_graph(query_results)
                    elif any(keyword in user_question for keyword in ['resource', 'ram', 'cpu']):
                        graph_fig = visualizer.create_resource_utilization_chart(query_results)
                    else:
                        # Default case: create server count graph with detected type
                        graph_fig = visualizer.create_server_count_graph(query_results, datacenter, chart_type)
                    
                    # Handle remaining cases for specific chart types
                    if graph_fig is None:
                        graph_fig = visualizer.create_server_count_graph(query_results, datacenter, chart_type)
                        
                    if graph_fig:
                        response += "\n\n ***Interactive visualization generated below:***"
            except ImportError:
                pass  # Graph visualization not available
            except Exception as e:
                print(f"[DEBUG] Graph generation failed: {e}")
            
            # Handle Excel export for results with > 2 rows (in-memory)
            excel_component_id = None
            try:
                from src.excel_exporter import should_show_excel_export, ExcelExporter
                
                print(f"[DEBUG Main] Query results count: {len(query_results) if query_results else 0}")
                if query_results:
                    successful_count = sum(1 for r in query_results if r.success and r.data is not None and not r.data.empty)
                    total_rows = sum(len(r.data) for r in query_results if r.success and r.data is not None and not r.data.empty)
                    print(f"[DEBUG Main] Successful queries: {successful_count}, Total rows: {total_rows}")
                    
                    for i, result in enumerate(query_results):
                        print(f"[DEBUG Main] Result {i}: Server={result.server_name}, Table={result.table_name}, Success={result.success}, Rows={len(result.data) if result.data is not None else 0}, Error={result.error}")
                
                if query_results and should_show_excel_export(query_results):
                    # Store query results in session state for Excel export reference
                    st.session_state.last_query_results = query_results
                    
                    # Use session state to maintain exporter instance consistency
                    if 'excel_exporter' not in st.session_state:
                        st.session_state.excel_exporter = ExcelExporter()
                    excel_component_id = st.session_state.excel_exporter.process_query_results_for_export(
                        query_results, st.session_state.live_pending_question
                    )
                    if excel_component_id:
                        # Get database types that were successfully queried
                        db_types = [r.table_name.replace('_tb', '').upper() for r in query_results if r.success and r.data is not None and not r.data.empty]
                        response += f"\n\n\n ****✅ Excel export generated with data from {', '.join(set(db_types))} databases ({total_rows} total records)****"
                        print(f"[DEBUG Main] Excel export component created: {excel_component_id}")
                    else:
                        print(f"[DEBUG Main] Excel export component creation failed")
                else:
                    print(f"[DEBUG Main] Excel export not triggered - insufficient data or criteria not met")
            except ImportError:
                pass  # Excel export not available
            except Exception as e:
                print(f"[DEBUG Main] Excel export failed: {e}")
                
        except Exception as e:
            print(f"[DEBUG] Processing failed: {e}")
        
        # Add assistant response
        st.session_state.live_chat_history.append({
            'role': 'assistant',
            'content': response,
            'graph': graph_fig,
            'excel_component_id': excel_component_id
        })
    except Exception as e:
        # Add error response if query failed
        st.session_state.live_chat_history.append({
            'role': 'assistant',
            'content': f"❌ Error processing your query: {str(e)}",
            'graph': None
        })
    
    # Clear processing state
    st.session_state.live_processing_query = False
    st.session_state.live_pending_question = None
    st.rerun()

def initialize_live_chatbot():
    """Initialize the live query chatbot"""
    if "live_chatbot" not in st.session_state:
        try:
            st.session_state.live_chatbot = LiveQueryChatbot()
            return True
        except Exception as e:
            st.error(f"❌ Could not initialize live query system: {str(e)}")
            return False
    return True

def handle_live_chat_question(question):
    """Handle a question in the live chat interface with conversation history"""
    # Add user message to chat history
    st.session_state.live_chat_history.append({
        'role': 'user',
        'content': question
    })
    
    # Set processing state and trigger rerun to show user message
    st.session_state.live_processing_query = True
    st.session_state.live_pending_question = question
    st.rerun()

def render_live_query_interface():
    """Render the live query chatbot interface with conversation format"""
    
    # Page header
    st.markdown("""
    <div class="main-header">
        <h1 style="margin: 0; font-size: 2.5rem;">Smart DBA Bot</h1>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem;">Ask questions about your database!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize chatbot if not already done
    initialize_live_chatbot()
    
    # Initialize chat history in session state
    if "live_chat_history" not in st.session_state:
        st.session_state.live_chat_history = [
            {
                'role': 'assistant',
                'content': "Hi there, ask me anything!"
            }
        ]
    
    # Display chat conversation
    for message in st.session_state.live_chat_history:
        if message['role'] == 'user':
            st.markdown(f"""
            <div class="user-message">
                <strong> You:</strong><br>
                {message['content']}
            </div>
            """, unsafe_allow_html=True)
        else:
            # Check if message has graph to style appropriately
            has_graph = message.get('graph') is not None
            
            if has_graph:
                # Message with embedded graph
                st.markdown(f"""
                <div class="message-with-graph">
                    <strong>DBA Chatbot:</strong><br>
                    {message['content']}
                    <div class="graph-container">
                        <small>Interactive chart (click fullscreen icon for better view)</small>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Display graph with fullscreen capability
                st.plotly_chart(
                    message['graph'], 
                    use_container_width=True,  # Allow fullscreen
                    config={
                        'displayModeBar': True,  # Show toolbar with fullscreen option
                        'displaylogo': False,
                        'modeBarButtonsToRemove': [
                            'pan2d', 'lasso2d', 'select2d', 'autoScale2d'
                        ]
                    }
                )
                
                # Display Excel export component if available
                if message.get('excel_component_id'):
                    try:
                        from src.excel_exporter import ExcelExporter
                        # Use session state to maintain exporter instance
                        if 'excel_exporter' not in st.session_state:
                            st.session_state.excel_exporter = ExcelExporter()
                        st.session_state.excel_exporter.render_excel_export_ui(message['excel_component_id'])
                    except Exception as e:
                        st.error(f"Excel export error: {e}")
                        import traceback
                        print(f"[DEBUG] Excel export error traceback: {traceback.format_exc()}")
                    
            else:
                # Regular message without graph
                st.markdown(f"""
                <div class="assistant-message">
                    <strong>Smart DBA Bot:</strong><br>
                    {message['content']}
                </div>
                """, unsafe_allow_html=True)
                
                # Display Excel export component if available
                if message.get('excel_component_id'):
                    try:
                        from src.excel_exporter import ExcelExporter
                        # Use session state to maintain exporter instance
                        if 'excel_exporter' not in st.session_state:
                            st.session_state.excel_exporter = ExcelExporter()
                        st.session_state.excel_exporter.render_excel_export_ui(message['excel_component_id'])
                    except Exception as e:
                        st.error(f"Excel export error: {e}")
                        import traceback
                        print(f"[DEBUG] Excel export error traceback: {traceback.format_exc()}")
    
    # User input area
    st.markdown("### Ask Your Question")
    
    # Use form to enable Enter key submission
    with st.form(key="query_form", clear_on_submit=True):
        user_question = st.text_input(
            "Type your question here (Press enter to ask):",
            placeholder="show me all server in dc4?",
            #height=100,
            disabled=st.session_state.live_processing_query
        )
        
        # Query Live Database button 
        col1, col2, col3 = st.columns([1, 2, 2])
        
        with col1:
            button_disabled = st.session_state.live_processing_query
            button_text = "***Ask***" if not button_disabled else "⏳ ***Processing...***"
            
            submitted = st.form_submit_button(
                button_text, 
                type="primary", 
                disabled=button_disabled
            )
        
        # Handle form submission
        if submitted:
            if user_question and user_question.strip():
                handle_live_chat_question(user_question.strip())
            else:
                st.warning("⚠️ Please enter a question before submitting.")
    
    
    # Help section
    st.markdown("---")
    with st.expander("💡 **Need Help? See Example Questions**", expanded=False):
        st.markdown("""
        ## Example Questions You Can Ask:
        
        **📋 Server Details**
        - "show me all server in DC4"
        - "show me server from dc4 whose uptime is more than 10 days from now?"
        """)

def main():
    """Main application with simple authentication"""
    # Initialize simple authentication
    auth = SimpleAuth()
    
    # Check if user is authenticated
    if not auth.is_authenticated():
        # Show login page
        auth.login_form()
    else:
        # User is authenticated - show main application
        st.sidebar.markdown(
            f'<h2 style="color: #667eea; font-weight: 600; margin-bottom: 1rem;">Welcome, {auth.get_username()}!</h2>',
            unsafe_allow_html=True
        )
        
        # Custom CSS for purple logout button
        st.markdown("""
        <style>
            /* Sidebar logout button styling */
            .stButton[data-testid="baseButton-secondary"] > button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
                color: white !important;
                border: none !important;
                border-radius: 8px !important;
                padding: 8px 16px !important;
                font-weight: 600 !important;
                transition: all 0.3s ease !important;
                width: 100% !important;
                box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3) !important;
            }
            
            .stButton[data-testid="baseButton-secondary"] > button:hover {
                transform: translateY(-1px) !important;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5) !important;
                background: linear-gradient(135deg, #5a6fd8 0%, #6a4c93 100%) !important;
            }
            
            /* Alternative selector for sidebar buttons */
            div[data-testid="stSidebar"] .stButton > button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
                color: white !important;
                border: none !important;
                border-radius: 8px !important;
                padding: 8px 16px !important;
                font-weight: 600 !important;
                transition: all 0.3s ease !important;
                width: 100% !important;
                box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3) !important;
            }
            
            div[data-testid="stSidebar"] .stButton > button:hover {
                transform: translateY(-1px) !important;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5) !important;
                background: linear-gradient(135deg, #5a6fd8 0%, #6a4c93 100%) !important;
            }
        </style>
        """, unsafe_allow_html=True)
        
        if st.sidebar.button("Logout", key="logout_btn"):
            auth.logout()
        render_live_query_interface()

# Main execution
if __name__ == "__main__":
    main()
else:
    main()
