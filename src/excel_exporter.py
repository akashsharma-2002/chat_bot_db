# src/excel_exporter.py
"""
Excel Export Module for Database Query Results
==============================================

Provides Excel export functionality for query results:
- Automatic Excel generation for results with > 15 rows
- Download and view options in chat interface
- Formatted Excel files with proper styling
- Integration with Smart DBA Bot chat system
"""

import pandas as pd
import io
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import streamlit as st
from dataclasses import dataclass

@dataclass
class ExcelExportData:
    """Represents data ready for Excel export"""
    filename: str
    data: pd.DataFrame
    sheet_name: str
    title: str
    total_rows: int

class ExcelExporter:
    """
    Excel export system for database query results
    """
    
    def __init__(self):
        self.temp_files = {}  # Store temporary Excel files
    
    def should_export_to_excel(self, query_results: List, min_rows: int = 15) -> bool:
        """
        Check if query results should be exported to Excel
        
        """
        total_rows = 0
        successful_results = 0
        
        for result in query_results:
            if result.success and result.data is not None and not result.data.empty:
                total_rows += len(result.data)
                successful_results += 1
        
        print(f"[DEBUG Excel] Total rows: {total_rows}, Successful results: {successful_results}, Min rows: {min_rows}")
        print(f"[DEBUG Excel] Should export: {total_rows > min_rows}")
        
        return total_rows > min_rows
    
    def prepare_excel_data(self, query_results: List, query_text: str = "") -> Optional[ExcelExportData]:
        """
        Prepare data for Excel export from query results
        """
        if not self.should_export_to_excel(query_results):
            return None
        
        # Combine all successful results
        all_data = []
        datacenter_info = []
        
        for result in query_results:
            if result.success and result.data is not None and not result.data.empty:
                df = result.data.copy()
                # Add source information
                df['Source_Datacenter'] = result.server_name
                df['Database_Type'] = result.table_name.replace('_tb', '').upper()
                df['Query_Execution_Time'] = f"{result.execution_time:.2f}s"
                
                all_data.append(df)
                datacenter_info.append({
                    'Datacenter': result.server_name,
                    'Database_Type': result.table_name.replace('_tb', '').upper(),
                    'Record_Count': len(df),
                    'Execution_Time': f"{result.execution_time:.2f}s"
                })
        
        if not all_data:
            return None
        
        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True, sort=False)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"database_query_results_{timestamp}.xlsx"
        
        # Prepare title
        title = f"Database Query Results - {len(combined_df)} records"
        if query_text:
            title += f" | Query: {query_text[:50]}..."
        
        return ExcelExportData(
            filename=filename,
            data=combined_df,
            sheet_name="Query_Results",
            title=title,
            total_rows=len(combined_df)
        )
    
    def create_excel_file(self, export_data: ExcelExportData) -> bytes:
        """
        Create formatted Excel file from export data
        
        """
        buffer = io.BytesIO()
        
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Write main data
            export_data.data.to_excel(
                writer, 
                sheet_name=export_data.sheet_name,
                index=False,
                startrow=2  # Leave space for title
            )
            
            # Get the worksheet to add formatting
            worksheet = writer.sheets[export_data.sheet_name]
            
            # Add title
            worksheet['A1'] = export_data.title
            worksheet['A1'].font = worksheet['A1'].font.copy(bold=True, size=14)
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                # Set column width (max 50 characters)
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Add summary sheet if multiple datacenters
            datacenters = export_data.data['Source_Datacenter'].nunique()
            if datacenters > 1:
                summary_data = []
                for dc in export_data.data['Source_Datacenter'].unique():
                    dc_data = export_data.data[export_data.data['Source_Datacenter'] == dc]
                    for db_type in dc_data['Database_Type'].unique():
                        db_data = dc_data[dc_data['Database_Type'] == db_type]
                        summary_data.append({
                            'Datacenter': dc,
                            'Database_Type': db_type,
                            'Record_Count': len(db_data),
                            'Unique_Servers': db_data['hostname'].nunique() if 'hostname' in db_data.columns else 'N/A'
                        })
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False, startrow=1)
                
                # Format summary sheet
                summary_ws = writer.sheets['Summary']
                summary_ws['A1'] = 'Query Results Summary'
                summary_ws['A1'].font = summary_ws['A1'].font.copy(bold=True, size=14)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def create_streamlit_export_component(self, export_data: ExcelExportData, excel_bytes: bytes) -> str:
        """
        Create Streamlit-native Excel export component that works entirely in memory

        """
        # Store data in Streamlit session state for in-memory handling
        component_id = f"excel_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize session state if needed
        try:
            if 'excel_exports' not in st.session_state:
                st.session_state.excel_exports = {}
            
            st.session_state.excel_exports[component_id] = {
                'data': excel_bytes,
                'filename': export_data.filename,
                'total_rows': export_data.total_rows,
                'file_size': len(excel_bytes)
            }
            
            print(f"[DEBUG Excel] Stored export data with component_id: {component_id}")
            print(f"[DEBUG Excel] Session state keys: {list(st.session_state.excel_exports.keys()) if hasattr(st.session_state, 'excel_exports') else 'No excel_exports'}")
            
        except Exception as e:
            print(f"[DEBUG Excel] Session state storage failed: {e}")
            # Fallback to instance storage
            self.temp_files[component_id] = {
                'data': excel_bytes,
                'filename': export_data.filename,
                'total_rows': export_data.total_rows,
                'file_size': len(excel_bytes)
            }
            print(f"[DEBUG Excel] Used fallback temp_files storage")
        
        return component_id
    
    def render_excel_export_ui(self, component_id: str) -> None:
        """
        Render Excel export UI using Streamlit components (Download only)
        
        Args:
            component_id: Component ID from create_streamlit_export_component
        """
        export_info = None
        
        # Try session state first
        if hasattr(st.session_state, 'excel_exports') and component_id in st.session_state.excel_exports:
            export_info = st.session_state.excel_exports[component_id]
            print(f"[DEBUG Excel UI] Found export in session state: {component_id}")
        # Fallback to instance storage
        elif component_id in self.temp_files:
            export_info = self.temp_files[component_id]
            print(f"[DEBUG Excel UI] Found export in temp_files: {component_id}")
        else:
            print(f"[DEBUG Excel UI] Export data not found for: {component_id}")
            print(f"[DEBUG Excel UI] Available session keys: {list(st.session_state.excel_exports.keys()) if hasattr(st.session_state, 'excel_exports') else 'None'}")
            print(f"[DEBUG Excel UI] Available temp_files keys: {list(self.temp_files.keys())}")
            st.error(f"Excel export data not found for {component_id}")
            return
        
        # Create a container for the export UI with enhanced styling
        with st.container():
            # Calculate database types count safely
            db_types_count = 'multiple'
            try:
                if hasattr(st.session_state, 'last_query_results') and st.session_state.last_query_results:
                    db_types = set([r.table_name.replace('_tb', '').upper() for r in st.session_state.last_query_results if r.success and r.data is not None and not r.data.empty])
                    db_types_count = len(db_types)
            except:
                db_types_count = 'multiple'
            
            # Simple text info without styling box
            st.markdown(f"📊 **Excel Export Ready**: {export_info['total_rows']} rows across {db_types_count} database types")
            
            # Compact download button and plain text file info
            col1, col2 = st.columns([1, 3])
            with col1:
                st.download_button(
                    label="📥 Download",
                    data=export_info['data'],
                    file_name=export_info['filename'],
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    help=f"Download Excel file with {export_info['total_rows']} rows ({export_info['file_size']/1024:.1f} KB)"
                )
            
            with col2:
                st.markdown(f"**{export_info['total_rows']}** rows • **{export_info['file_size']/1024:.1f}** KB")
    
    def process_query_results_for_export(self, query_results: List, query_text: str = "") -> Optional[str]:
        """
        Process query results and create in-memory Excel export if needed
        """
        print(f"[DEBUG Excel Process] Starting export process with {len(query_results)} results")
        
        # Check if export is needed
        if not self.should_export_to_excel(query_results):
            print(f"[DEBUG Excel Process] Export not needed - threshold not met")
            return None
        
        try:
            print(f"[DEBUG Excel Process] Preparing Excel data...")
            # Prepare data for Excel
            export_data = self.prepare_excel_data(query_results, query_text)
            if not export_data:
                print(f"[DEBUG Excel Process] Export data preparation failed")
                return None
            
            print(f"[DEBUG Excel Process] Export data prepared: {export_data.total_rows} rows")
            
            # Create Excel file in memory
            print(f"[DEBUG Excel Process] Creating Excel file...")
            excel_bytes = self.create_excel_file(export_data)
            print(f"[DEBUG Excel Process] Excel file created: {len(excel_bytes)} bytes")
            
            # Create Streamlit component
            print(f"[DEBUG Excel Process] Creating Streamlit component...")
            component_id = self.create_streamlit_export_component(export_data, excel_bytes)
            print(f"[DEBUG Excel Process] Component created: {component_id}")
            
            return component_id
            
        except Exception as e:
            print(f"[DEBUG Excel Process] Exception in process_query_results_for_export: {str(e)}")
            import traceback
            print(f"[DEBUG Excel Process] Traceback: {traceback.format_exc()}")
            try:
                st.error(f"❌ Excel export failed: {str(e)}")
            except:
                pass  # Don't fail if st.error fails
            return None
    
    def render_in_chat_export(self, query_results: List, query_text: str = "") -> bool:
        """
        Render Excel export directly in chat message (in-memory only)

        """
        component_id = self.process_query_results_for_export(query_results, query_text)
        if not component_id:
            return False
        
        # Render the export UI
        self.render_excel_export_ui(component_id)
        return True

# Integration functions for the main application
def create_in_memory_excel_export(query_results: List, query_text: str = "") -> bool:
    """
    Create in-memory Excel export for chat integration
    
    """
    exporter = ExcelExporter()
    return exporter.render_in_chat_export(query_results, query_text)

def should_show_excel_export(query_results: List) -> bool:
    """
    Check if Excel export should be shown for given query results

    """
    exporter = ExcelExporter()
    return exporter.should_export_to_excel(query_results)
