# dash_app.py
import os, io, base64, json, tempfile
import pandas as pd
from main import extract_and_merge_survey, extract_selected_pages_survey
import requests
import time
import subprocess

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, dash_table, no_update

# ArcGIS integration - Now handled by file-based system  
SHARED_FOLDER = "/mnt/ulmfile_shared"  # Mount point for the watchdog folder
# Network share has been mounted successfully: //ulmfile/Shared/GIS/GIS Data/Summer Intern 2025/Shared file (watchdog) -> /mnt/ulmfile_shared

# FME Workbench configuration
FME_WORKBENCH_PATH = r"\\ulmfile\Shared\GIS\GIS Data\Summer Intern 2025\operator_survey_line.fmw"
FME_ENGINE_PATH = r"C:\Program Files\FME\fme.exe"  # Default FME installation path

# FME will be triggered automatically by Windows watcher when CSV is updated

# Check if shared folder is available
def check_shared_folder_available():
    try:
        # Check if folder exists and is writable
        return os.path.exists(SHARED_FOLDER) and os.access(SHARED_FOLDER, os.W_OK)
    except:
        return False

SHARED_FOLDER_AVAILABLE = check_shared_folder_available()

# Initialize Dash with a Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)
server = app.server

def write_to_geodatabase_via_file(survey_data):
    """Save survey data to shared folder for ArcGIS processing"""
    # Check folder availability dynamically
    if not check_shared_folder_available():
        return {"success": False, "error": "Shared folder not available or not writable. Please check network connection and permissions."}
    
    try:
        # Generate unique filename with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        uwi = survey_data.get("uwi", "unknown").replace("/", "_").replace("\\", "_").replace(" ", "_")
        filename = f"survey_{uwi}_{timestamp}.json"
        filepath = os.path.join(SHARED_FOLDER, filename)
        
        # Prepare data in the format your watcher expects
        # Your watcher is very flexible and can handle the survey_data format
        export_data = {
            "metadata": {
                "exported_at": datetime.datetime.now().isoformat(),
                "exported_from": "dash_ui",
                "filename": filename,
                "status": "pending_processing",
                "well_name": survey_data.get("uwi", "Unknown Well"),
                "operator": survey_data.get("operator", "Unknown"),
                "vendor": survey_data.get("vendor", "Unknown"),
                "contact_info": survey_data.get("contact_info", ""),
                "county": survey_data.get("county", ""),
                "surfacelocX": survey_data.get("shl_x", ""),
                "surfacelocY": survey_data.get("shl_y", ""),
                "lease_location": survey_data.get("lease_location", ""),
                "coordinate_system": survey_data.get("map_zone", ""),
                "map_system": survey_data.get("map_system", ""),
                "geo_datum": survey_data.get("geo_datum", ""),
                "system_datum": survey_data.get("system_datum", ""),
                "ground_level_elevation": survey_data.get("ground_level_elevation", ""),
                "datum_elevation": survey_data.get("datum_elevation", ""),
                "job_number": survey_data.get("job_number", ""),
                "date_created": survey_data.get("date_created", ""),

            },
            "survey_data": survey_data.get("survey_points", []),
            "exported_at": datetime.datetime.now().isoformat()
        }
        
        # Write to shared folder
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return {"success": True, "message": f"✅ Survey data saved to {filename}! Windows watcher will process it automatically. Check the shared folder for the file.", "filename": filename}
        
    except Exception as e:
        return {"success": False, "error": f"Error saving to shared folder: {str(e)}"}

# --- LAYOUT ---------------------------------------------------------------

# --- NAVBAR ---
navbar = dbc.Navbar(
    dbc.Container([
        html.Div([
            dbc.NavbarBrand("University Lands", className="fw-bold fs-4 text-light mb-0"),
            dbc.DropdownMenu(
                [
                    dbc.DropdownMenuItem("PDF Extraction", href="/", active="exact"),
                    dbc.DropdownMenuItem("Analytics", href="/analytics", active="exact"),
                ],
                label="Menu",
                color="primary",
                className="me-3",
                align_end=True,
                nav=True,
            ),
        ], className="d-flex justify-content-between align-items-center w-100", style={"width": "100%"}),
        dbc.NavbarToggler(id="navbar-toggler"),
        dbc.Collapse(
            [],
            id="navbar-collapse",
            navbar=True,
        ),
    ], fluid=True),
    color="dark",
    dark=True,
    className="mb-4 border-bottom shadow-sm"
)

# --- PAGE LAYOUTS ---
pdf_extraction_layout = dbc.Container(fluid=True, children=[
    html.H2("Directional Survey Extractor", className="my-3"),
    dcc.Store(id="survey-store"),
    dcc.Store(id="pdf-pages-store"),  # Store for individual PDF pages
    dcc.Store(id="selected-pages-store", data=[]),  # Store for selected page indices
    dcc.Store(id="current-page-store", data=0),  # Store for currently viewed page
    dbc.Row([
        dbc.Col([
            html.H5("Upload PDF"),
            dcc.Upload(
                id="upload-pdf",
                children=html.Div("📂 Drag & drop or click to select a PDF file"),
                style={
                    "border": "2px dashed #888",
                    "padding": "20px",
                    "textAlign": "center",
                    "cursor": "pointer",
                },
                accept=".pdf",
                multiple=False,
            ),
            dcc.Loading(
                id="pdf-loading",
                type="circle",
                fullscreen=False,
                children=html.Div(id="pdf-preview", className="mt-3")
            )
        ], width=6),
        dbc.Col([
            html.H5("Confirm Survey Form"),
            dcc.Loading(
                id="process-loading",
                type="default",
                children=[
                    dbc.Button(
                        "Process", 
                        id="process-selected-btn", 
                        color="success", 
                        size="md",
                        className="mb-3",
                        style={"width": "150px"}
                    )
                ]
            ),
            dbc.Form([
                dbc.Row([
                    dbc.Label("UWI", width=4),
                    dbc.Col(dbc.Input(id="uwi"), width=8)
                ], className="mb-2"),
                dbc.Row([
                    dbc.Label("Operator", width=4),
                    dbc.Col(dbc.Input(id="operator"), width=8)
                ], className="mb-2"),
                dbc.Row([
                    dbc.Label("Vendor", width=4),
                    dbc.Col(dbc.Input(id="vendor"), width=8)
                ], className="mb-2"),
                dbc.Row([
                    dbc.Label("Lease/Site Location", width=4),
                    dbc.Col(dbc.Input(id="lease_location"), width=8)
                ], className="mb-2"),
                dbc.Row([
                    dbc.Label("County", width=4),
                    dbc.Col(dbc.Input(id="county"), width=8)
                ], className="mb-2"),
                dbc.Row([
                    dbc.Label("Contact Info.", width=4),
                    dbc.Col(dbc.Input(id="contact_info"), width=8)
                ], className="mb-2"),
                dbc.Row([
                    dbc.Label("Coordinate Reference System", width=4),
                    dbc.Col(dbc.Input(id="map_zone"), width=8)
                ], className="mb-2"),
                dbc.Row([
                    dbc.Label("Map System", width=4),
                    dbc.Col(dbc.Input(id="map_system"), width=8)
                ], className="mb-2"),
                dbc.Row([
                    dbc.Label("Geodetic Datum", width=4),
                    dbc.Col(dbc.Input(id="geo_datum"), width=8)
                ], className="mb-2"),
                dbc.Row([
                    dbc.Label("System Datum", width=4),
                    dbc.Col(dbc.Input(id="system_datum"), width=8)
                ], className="mb-2"),
                dbc.Row([
                    dbc.Label("SHL X", width=4),
                    dbc.Col(dbc.Input(id="shl_x"), width=8)
                ], className="mb-2"),
                dbc.Row([
                    dbc.Label("SHL Y", width=4),
                    dbc.Col(dbc.Input(id="shl_y"), width=8)
                ], className="mb-2"),
                dbc.Row([
                    dbc.Label("Datum Elevation", width=4),
                    dbc.Col(dbc.Input(id="datum_elevation"), width=8)
                ], className="mb-2"),
                dbc.Row([
                    dbc.Label("Ground Level Elevation", width=4),
                    dbc.Col(dbc.Input(id="ground_level_elevation"), width=8)
                ], className="mb-2"),
                dbc.Row([
                    dbc.Label("Job Number", width=4),
                    dbc.Col(dbc.Input(id="job_number"), width=8)
                ], className="mb-2"),
                dbc.Row([
                    dbc.Label("Date Created", width=4),
                    dbc.Col(dbc.Input(id="date_created"), width=8)
                ], className="mb-2"),
                dcc.Loading(
                    id="update-form-loading",
                    type="default",
                    children=[
                        dbc.Button("Submit Form", id="update-meta", color="primary", className="mt-2")
                    ]
                )
            ])
        ], width=6)
    ]),
    html.Hr(),
    html.H5("Directional Survey Points"),
    dash_table.DataTable(
        id="survey-table",
        columns=[],
        data=[],
        editable=True,
        row_deletable=True,
        page_size=10,
        style_table={"overflowX": "auto", "overflowY": "auto", "maxHeight": "400px"},
        sort_action="native",
        virtualization=True,
        fixed_rows={"headers": True},
        page_action='none'
    ),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            dbc.Button("Download JSON", id="download-btn", color="success", className="me-2")
        ], width="auto"),
        dbc.Col([
            dbc.Button("Load FME Workbench", id="download-csv-btn", color="warning", className="me-2")
        ], width="auto"),
        dbc.Col([
            dcc.Loading(
                id="arcgis-loading",
                type="default",
                children=[
                    dbc.Button("Write to ArcGIS GDB", id="arcgis-btn", color="info", disabled=not SHARED_FOLDER_AVAILABLE)
                ]
            )
        ], width="auto"),
    ]),
    dcc.Download(id="download-json"),
    dcc.Download(id="download-csv"),
    html.Div(id="arcgis-status", className="mt-3"),
    # Toast notifications
    html.Div(id="toast-container", style={"position": "fixed", "top": 20, "right": 20, "z-index": 9999})
])

analytics_layout = dbc.Container(fluid=True, children=[
    html.H2("Analytics (Coming Soon)", className="my-3"),
    html.P("This page will provide analytics and visualizations of extracted survey data.")
])

# --- MULTIPAGE APP ---
from dash import dcc as dash_dcc
app.layout = html.Div([
    dcc.Location(id="url"),
    navbar,
    html.Div(id="page-content")
])

@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    if pathname == "/analytics":
        return analytics_layout
    return pdf_extraction_layout


# --- CALLBACKS -----------------------------------------------------------

# 1) Handle PDF upload and show enhanced page viewer
@app.callback(
    [Output("pdf-preview", "children"),
     Output("pdf-pages-store", "data"),
     Output("selected-pages-store", "data"),
     Output("current-page-store", "data")],
    Input("upload-pdf", "contents"),
    State("upload-pdf", "filename"),
    prevent_initial_call=True
)
def handle_pdf_upload(contents, filename):
    if not contents:
        return "", None, [], 0
    
    content_type, content_string = contents.split(",")
    pdf_bytes = base64.b64decode(content_string)
    
    # Save PDF temporarily to extract pages
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(pdf_bytes)
    tmp.close()
    
    try:
        # Convert PDF to images at same DPI as main.py for consistency
        from pdf2image import convert_from_path
        images = convert_from_path(tmp.name, dpi=300)  # Same DPI as main.py for consistency
        
        # Store base64 encoded images for later processing
        pages_data = []
        
        for idx, img_pil in enumerate(images):
            # Convert to base64 for storage and display
            img_buffer = io.BytesIO()
            img_pil.save(img_buffer, format='PNG')
            img_b64 = base64.b64encode(img_buffer.getvalue()).decode()
            
            pages_data.append({
                'index': idx,
                'base64': img_b64,
                'filename': f"{filename}_page_{idx+1}.png" if filename else f"page_{idx+1}.png"
            })
        
        # Create scrollable PDF preview
        pdf_viewer = create_pdf_viewer(pages_data, 0, filename)  # current_page parameter kept for compatibility
        
        # Default: all pages selected
        default_selected = list(range(len(images)))
        
        return pdf_viewer, pages_data, default_selected, 0
        
    except Exception as e:
        error_msg = html.Div([
            dbc.Alert(f"Error processing PDF: {str(e)}", color="danger")
        ])
        return error_msg, None, [], 0
    finally:
        os.unlink(tmp.name)

def create_pdf_viewer(pages_data, current_page, filename):
    """Create a scrollable PDF viewer with all pages displayed vertically"""
    if not pages_data:
        return ""
    
    total_pages = len(pages_data)
    
    # Header with selection controls
    header_controls = dbc.Row([
        dbc.Col([
            html.H6(f"📄 PDF Preview ({total_pages} pages)", className="mb-2")
        ], width="auto"),
        dbc.Col([
            dbc.ButtonGroup([
                dbc.Button("✅ Select All", id="select-all-btn", size="sm", color="success", outline=True),
                dbc.Button("❌ Deselect All", id="deselect-all-btn", size="sm", color="danger", outline=True)
            ])
        ], width="auto"),
    ], justify="between", align="center", className="mb-3")
    
    # Create scrollable pages container
    pages_container = []
    for idx, page_data in enumerate(pages_data):
        page_card = dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col([
                        html.H6(f"Page {idx + 1}", className="mb-0 text-primary")
                    ], width="auto"),
                    dbc.Col([
                        dbc.Checkbox(
                            id={"type": "page-checkbox", "index": idx},
                            value=True,  # Default selected
                            label="Include",
                            className="fw-bold text-success"
                        )
                    ], width="auto"),
                ], justify="between", align="center")
            ], className="py-2"),
            dbc.CardBody([
                html.Img(
                    src=f"data:image/png;base64,{page_data['base64']}",
                    style={
                        "width": "100%", 
                        "height": "auto",
                        "border": "1px solid #ddd",
                        "borderRadius": "4px"
                    }
                )
            ], className="p-2")
        ], className="mb-3")
        pages_container.append(page_card)
    
    # Scrollable pages display
    scrollable_pages = html.Div(
        pages_container,
        style={
            "maxHeight": "700px", 
            "overflowY": "auto",
            "overflowX": "hidden",
            "border": "1px solid #e0e0e0",
            "borderRadius": "8px",
            "padding": "15px",
            "backgroundColor": "#f8f9fa"
        }
    )
    
    # File info
    file_info = html.Div([
        html.Small(f"File: {filename}", style={"color": "#555"}) if filename else ""
    ], className="mt-2")
    
    return html.Div([
        header_controls,
        scrollable_pages,
        file_info
    ])

# Select/Deselect all pages callbacks
@app.callback(
    [Output({"type": "page-checkbox", "index": dash.ALL}, "value"),
     Output("selected-pages-store", "data", allow_duplicate=True)],
    [Input("select-all-btn", "n_clicks"),
     Input("deselect-all-btn", "n_clicks")],
    [State("pdf-pages-store", "data")],
    prevent_initial_call=True
)
def select_deselect_all(select_clicks, deselect_clicks, pages_data):
    if not pages_data:
        return [], []
    
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update, no_update
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    total_pages = len(pages_data)
    
    if button_id == "select-all-btn":
        # Select all pages
        checkbox_values = [True] * total_pages
        selected_pages = list(range(total_pages))
    else:  # deselect-all-btn
        # Deselect all pages
        checkbox_values = [False] * total_pages
        selected_pages = []
    
    return checkbox_values, selected_pages

# Update selected pages when individual checkboxes change
@app.callback(
    Output("selected-pages-store", "data", allow_duplicate=True),
    Input({"type": "page-checkbox", "index": dash.ALL}, "value"),
    [State({"type": "page-checkbox", "index": dash.ALL}, "id"),
     State("pdf-pages-store", "data")],
    prevent_initial_call=True
)
def update_page_selection_from_checkboxes(checkbox_values, checkbox_ids, pages_data):
    if not pages_data:
        return []
    
    # Get selected page indices
    selected_pages = []
    for i, is_checked in enumerate(checkbox_values):
        if is_checked and i < len(checkbox_ids):
            page_index = checkbox_ids[i]["index"]
            selected_pages.append(page_index)
    
    selected_pages = sorted(selected_pages)
    
    return selected_pages

# 3) Process selected pages and extract survey data
@app.callback(
    [Output("survey-store", "data"),
     Output("survey-table", "columns"),
     Output("survey-table", "data"),
     Output("uwi", "value"),
     Output("operator", "value"),
     Output("vendor", "value"),
     Output("lease_location", "value"),
     Output("county", "value"),
     Output("contact_info", "value"),
     Output("map_zone", "value"),
     Output("map_system", "value"),
     Output("geo_datum", "value"),
     Output("system_datum", "value"),
     Output("shl_x", "value"),
     Output("shl_y", "value"),
     Output("datum_elevation", "value"),
     Output("ground_level_elevation", "value"),
     Output("job_number", "value"),
     Output("date_created", "value"),
     Output("process-selected-btn", "disabled"),
     Output("process-selected-btn", "children")],
    Input("process-selected-btn", "n_clicks"),
    [State("pdf-pages-store", "data"),
     State("selected-pages-store", "data")],
     prevent_initial_call=True
)
def process_selected_pages(n_clicks, pages_data, selected_pages):
    if not n_clicks or not pages_data or not selected_pages:
        return [no_update] * 21
    
    try:
        # Process only selected pages using the function from main.py
        survey = extract_selected_pages_survey(pages_data, selected_pages)
        
        # Prepare table columns and data for survey points
        table_columns = []
        table_data = []
        if survey and isinstance(survey, dict) and "survey_points" in survey:
            points = survey["survey_points"]
            if points:
                # Sort points by 'md' ascending if present
                try:
                    table_data = sorted(points, key=lambda x: float(x.get("md", 0)))
                except Exception:
                    table_data = points
                table_columns = [{"name": k, "id": k} for k in points[0].keys()]
        
        # Populate form fields from metadata
        meta_keys = [
            "uwi", "operator", "vendor", "lease_location", "county", "contact_info",
            "map_zone", "map_system", "geo_datum", "system_datum",
            "shl_x", "shl_y", "datum_elevation", "ground_level_elevation", "job_number", "date_created"
        ]
        form_values = [survey.get(k, "") if survey else "" for k in meta_keys]
        
        # Return all outputs in order: survey data + form values + button state
        return [survey, table_columns, table_data] + form_values + [False, "Process"]
        
    except Exception as e:
        error_survey = {"error": str(e)}
        return [error_survey] + [no_update] * 18 + [False, "Process"]

# 4) Callback to update survey store when table data is modified
@app.callback(
    Output("survey-store", "data", allow_duplicate=True),
    Input("survey-table", "data"),
    State("survey-store", "data"),
    prevent_initial_call=True
)
def update_survey_from_table(table_data, survey):
    if survey and table_data is not None:
        # Update the survey_points in the survey store
        survey["survey_points"] = table_data
    return survey

# 5) Metadata update callback
@app.callback(
    [Output("survey-store", "data", allow_duplicate=True),
     Output("survey-table", "columns", allow_duplicate=True),
     Output("survey-table", "data", allow_duplicate=True),
     Output("update-meta", "color")],
    Input("update-meta", "n_clicks"),
    [State("survey-store", "data"),
     State("uwi", "value"),
     State("operator", "value"),
     State("vendor", "value"),
     State("lease_location", "value"),
     State("county", "value"),
     State("contact_info", "value"),
     State("map_zone", "value"),
     State("map_system", "value"),
     State("geo_datum", "value"),
     State("system_datum", "value"),
     State("shl_x", "value"),
     State("shl_y", "value"),
     State("datum_elevation", "value"),
     State("ground_level_elevation", "value"),
     State("job_number", "value"),
     State("date_created", "value")],
    prevent_initial_call=True
)
def update_metadata(n_clicks, survey, *form_values):
    if not n_clicks or not survey:
        return [no_update] * 4
    
    # Add a small delay to make the color change visible
    import time
    time.sleep(0.3)
    
    # Update metadata
    keys = [
        "uwi", "operator", "vendor", "lease_location", "county", "contact_info",
        "map_zone", "map_system", "geo_datum", "system_datum",
        "shl_x", "shl_y", "datum_elevation", "ground_level_elevation", "job_number", "date_created"
    ]
    
    for k, v in zip(keys, form_values):
        survey[k] = v
    
    # Also refresh the survey table data
    table_columns = []
    table_data = []
    if survey and isinstance(survey, dict) and "survey_points" in survey:
        points = survey["survey_points"]
        if points:
            # Sort points by 'md' ascending if present
            try:
                table_data = sorted(points, key=lambda x: float(x.get("md", 0)))
            except Exception:
                table_data = points
            table_columns = [{"name": k, "id": k} for k in points[0].keys()]
    
    return survey, table_columns, table_data, "info"

# Reset update form button color back to primary after brief delay
app.clientside_callback(
    """
    function(color) {
        if (color === 'info') {
            setTimeout(function() {
                window.dash_clientside.set_props("update-meta", {"color": "primary"});
            }, 800);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("update-meta", "style"),  # Dummy output
    Input("update-meta", "color"),
    prevent_initial_call=True
)


# 6) Download JSON
@app.callback(
    Output("download-json", "data"),
    Input("download-btn", "n_clicks"),
    State("survey-store", "data"),
    prevent_initial_call=True,
    allow_duplicate=True
)
def download_json(n, survey):
    return dict(
      content=json.dumps(survey, indent=2),
      filename="directional_survey.json"
    )

# 6b) Download CSV - Save to shared folder for FME processing
@app.callback(
    [Output("download-csv", "data"),
     Output("arcgis-status", "children", allow_duplicate=True),
     Output("toast-container", "children", allow_duplicate=True)],
    Input("download-csv-btn", "n_clicks"),
    State("survey-store", "data"),
    prevent_initial_call=True
)
def download_csv(n_clicks, survey):
    if not n_clicks or not survey:
        return no_update, no_update, no_update
    
    # Create DataFrame with survey points in specified order
    survey_points = survey.get("survey_points", [])
    if not survey_points:
        # Return empty CSV if no survey points
        error_alert = dbc.Alert("No survey data available for CSV export", color="warning", duration=4000)
        return no_update, error_alert, no_update
    
    # Convert to DataFrame and reorder columns as specified: md, inc, azi, tvd, ns, ew
    df = pd.DataFrame(survey_points)
    
    # Define the desired column order
    desired_columns = ["md", "inc", "azi", "tvd", "ns", "ew"]
    
    # Reorder columns, keeping only the ones that exist
    existing_columns = [col for col in desired_columns if col in df.columns]
    # Add any additional columns not in the desired order
    other_columns = [col for col in df.columns if col not in desired_columns]
    final_columns = existing_columns + other_columns
    
    if existing_columns:
        df = df[final_columns]
    
    # Add UWI as the first column
    uwi_value = survey.get("uwi", "")
    df.insert(0, "uwi", uwi_value)
    
    # Add other metadata columns after survey data
    metadata_fields = [
        "operator", "vendor", "lease_location", "county", "contact_info",
        "map_zone", "map_system", "geo_datum", "system_datum",
        "shl_x", "shl_y", "datum_elevation", "ground_level_elevation", 
        "job_number", "date_created"
    ]
    
    # Add metadata as columns (repeat for each row)
    for field in metadata_fields:
        value = survey.get(field, "")
        df[field] = value
    
    # Convert DataFrame to CSV
    csv_content = df.to_csv(index=False)
    
    # Generate filename - use fixed name for FME automation
    filename = "latest_directional_survey.csv"
    
    # Try to save to shared folder for FME processing
    if check_shared_folder_available():
        try:
            # Save CSV to shared folder with fixed filename for FME
            filepath = os.path.join(SHARED_FOLDER, filename)
            with open(filepath, 'w', newline='') as f:
                f.write(csv_content)
            
            # Simple success feedback - Windows watcher will handle FME automatically
            success_alert = dbc.Alert(
                [
                    html.I(className="fas fa-check-circle me-2"),
                    f"✅ CSV saved as '{filename}'. Windows FME watcher will process automatically."
                ], 
                color="success", 
                dismissable=True,
                duration=8000
            )
            
            # Success toast
            toast = dbc.Toast(
                [html.P(f"CSV exported! Windows will run FME automatically.", className="mb-0")],
                id="csv-success-toast",
                header="📊🚀 CSV Ready for FME!",
                is_open=True,
                dismissable=True,
                icon="success",
                duration=4000,
                style={"position": "fixed", "top": 66, "right": 10, "width": 350},
            )
            
            return no_update, success_alert, toast
            
        except Exception as e:
            # Error saving to shared folder - fallback to browser download
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            uwi = survey.get("uwi", "survey")
            safe_uwi = uwi.replace("/", "_").replace("\\", "_").replace(" ", "_") if uwi else "survey"
            browser_filename = f"directional_survey_{safe_uwi}_{timestamp}.csv"
            
            error_alert = dbc.Alert(
                [
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    f"❌ Error saving to shared folder: {str(e)}. Downloading to browser instead."
                ], 
                color="warning", 
                dismissable=True,
                duration=8000
            )
            
            return dict(content=csv_content, filename=browser_filename), error_alert, no_update
    else:
        # Shared folder not available - fallback to browser download
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        uwi = survey.get("uwi", "survey")
        safe_uwi = uwi.replace("/", "_").replace("\\", "_").replace(" ", "_") if uwi else "survey"
        browser_filename = f"directional_survey_{safe_uwi}_{timestamp}.csv"
        
        warning_alert = dbc.Alert(
            [
                html.I(className="fas fa-exclamation-triangle me-2"),
                "⚠️ Shared folder not available. Downloading CSV to browser instead. Mount the shared folder for automatic FME processing."
            ], 
            color="warning", 
            dismissable=True,
            duration=8000
        )
        
        return dict(content=csv_content, filename=browser_filename), warning_alert, no_update

# 7) Write to ArcGIS Geodatabase
@app.callback(
    [Output("arcgis-status", "children"),
     Output("arcgis-btn", "disabled"),
     Output("toast-container", "children")],
    Input("arcgis-btn", "n_clicks"),
    State("survey-store", "data"),
    prevent_initial_call=True
)
def write_to_arcgis(n_clicks, survey_data):
    if not n_clicks or not survey_data:
        return "", not SHARED_FOLDER_AVAILABLE, ""
    
    # Show immediate feedback
    result = write_to_geodatabase_via_file(survey_data)
    
    if result["success"]:
        alert = dbc.Alert(
            [
                html.I(className="fas fa-check-circle me-2"),
                f"{result['message']}"
            ], 
            color="success", 
            dismissable=True,
            duration=8000
        )
        
        # Add toast notification
        toast = dbc.Toast(
            [html.P(f"File created: {result.get('filename', 'survey file')}", className="mb-0")],
            id="success-toast",
            header="✅ Success!",
            is_open=True,
            dismissable=True,
            icon="success",
            duration=4000,
            style={"position": "fixed", "top": 66, "right": 10, "width": 350},
        )
        
        # Re-enable button after success
        return alert, not SHARED_FOLDER_AVAILABLE, toast
    else:
        alert = dbc.Alert(
            [
                html.I(className="fas fa-exclamation-triangle me-2"),
                f"❌ Error: {result['error']}"
            ], 
            color="danger", 
            dismissable=True,
            duration=10000
        )
        
        # Add error toast
        toast = dbc.Toast(
            [html.P(f"Failed to save file: {result['error']}", className="mb-0")],
            id="error-toast",
            header="❌ Error",
            is_open=True,
            dismissable=True,
            icon="danger",
            duration=6000,
            style={"position": "fixed", "top": 66, "right": 10, "width": 350},
        )
        
        # Re-enable button after error
        return alert, not SHARED_FOLDER_AVAILABLE, toast


if __name__ == "__main__":
    app.run(debug=True, port=8050)
