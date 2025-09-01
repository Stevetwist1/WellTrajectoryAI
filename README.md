# WellTrajectoryAI

A sophisticated OCR and AI-powered directional survey processing system for extracting structured data from petroleum industry survey documents. WellTrajectoryAI combines advanced computer vision (PaddleOCR) with large language models to automatically extract directional survey data from PDF documents and generate well trajectory visualizations through automated FME integration.

## 🌟 Features

- **Interactive Web Interface**: Modern Dash-based web application with Bootstrap UI for document processing and data validation
- **Advanced OCR Processing**: Uses PaddleOCR with GPU acceleration for high-accuracy text detection and recognition from survey documents
- **AI-Powered Data Extraction**: Leverages OpenAI GPT models to extract structured directional survey data from OCR results
- **Multi-Page PDF Support**: Visual page selection and processing with drag-and-drop interface
- **Real-Time Processing**: Live PDF upload, page selection, and immediate data extraction
- **Multi-Format Export**: Generates JSON and CSV outputs for downstream processing and analysis
- **FME Integration**: Automatic minimum curvature calculations and well trajectory generation through FME workbench automation
- **ArcGIS Integration**: Direct export to ArcGIS geodatabase for spatial analysis and visualization
- **Cross-Platform Workflow**: Linux-based processing with Windows FME integration via network shared folders

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- CUDA-compatible GPU (optional, for faster OCR processing)
- OpenAI API access
- Network access to Windows shared folder (for FME integration)
- FME Desktop/Server (for trajectory calculations)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd WellTrajectoryAI
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install system dependencies:
```bash
# For PDF processing
sudo apt install poppler-utils

# For network share mounting
sudo apt install cifs-utils

# For GPU acceleration (optional)
sudo apt install nvidia-utils-535
```

5. Set up environment variables:
Create a `.env` file in the project root:
```env
OPENAI_API_KEY=your_openai_api_key_here
SHARED_FOLDER=/mnt/ulmfile_shared
FME_WORKBENCH_PATH=\\ulmfile\Shared\GIS\operator_survey_line.fmw
```

### Network Share Setup

1. Create mount point and credentials:
```bash
sudo mkdir -p /mnt/ulmfile_shared
sudo nano /etc/cifs-credentials
# Add your credentials:
# username=your_username
# password=your_password
# domain=your_domain

sudo chmod 600 /etc/cifs-credentials
```

2. Mount the shared folder:
```bash
sudo mount -t cifs "//server/share/path" /mnt/ulmfile_shared -o credentials=/etc/cifs-credentials,uid=$USER,gid=$USER
```

### Usage

1. Start the web application:
```bash
python app.py
```

2. Open your browser to `http://localhost:8050`

3. Upload a PDF survey document using the drag-and-drop interface

4. Select pages containing survey data

5. Click "Process" to extract data using OCR and AI

6. Review and edit the extracted metadata in the form

7. Verify survey points in the interactive data table

8. Export data:
   - **Download JSON**: Raw structured data
   - **Download CSV**: CSV export with automatic FME processing
   - **Write to ArcGIS GDB**: Direct geodatabase integration

## 📊 Data Extraction

WellTrajectoryAI extracts comprehensive directional survey data:

### Survey Metadata
- **UWI (Unique Well Identifier)**
- **Operator and Vendor Information**
- **Location Details** (Lease, County, Contact Info)
- **Coordinate Systems** (Map Zone, Geodetic Datum)
- **Surface Coordinates** (SHL X, SHL Y)
- **Elevation Data** (Datum, Ground Level)

### Directional Survey Points
- **Measured Depth (MD)**
- **Inclination (INC)**
- **Azimuth (AZI)**
- **True Vertical Depth (TVD)**
- **North-South Displacement (NS)**
- **East-West Displacement (EW)**

### Sample Output
```json
{
  "uwi": "42-475-3847300",
  "operator": "University Lands",
  "vendor": "Survey Company Name",
  "lease_location": "Lease ABC-123",
  "county": "Harris",
  "shl_x": "1234567.89",
  "shl_y": "9876543.21",
  "datum_elevation": "1500.0",
  "survey_points": [
    {
      "md": 0,
      "inc": 0,
      "azi": 0,
      "tvd": 0,
      "ns": 0,
      "ew": 0
    },
    {
      "md": 100,
      "inc": 2.5,
      "azi": 45.2,
      "tvd": 99.8,
      "ns": 10.2,
      "ew": 15.3
    }
  ]
}
```

## 🔧 Technical Architecture

### Web Application Stack
- **Frontend**: Dash with Bootstrap Components
- **Backend**: Python Flask server
- **UI Components**: Interactive data tables, file upload, form validation
- **Real-time Processing**: Live feedback and progress indicators

### Data Processing Pipeline
1. **PDF Upload**: Drag-and-drop interface with preview
2. **Page Selection**: Visual page thumbnails with selection controls
3. **OCR Processing**: PaddleOCR with GPU acceleration
4. **AI Extraction**: Structured data extraction using OpenAI
5. **Data Validation**: Interactive form editing and validation
6. **Export Processing**: Multiple output formats and integrations

### Integration Components
- **FME Automation**: File-based trigger system for minimum curvature calculations
- **ArcGIS Integration**: JSON export for geodatabase import
- **Network Share**: Cross-platform file exchange for Windows integration

### OCR Configuration
```python
OCR_MODEL = PaddleOCR(
    device="gpu" if os.path.exists("/usr/bin/nvidia-smi") else "cpu",
    lang="en",
    use_textline_orientation=False,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False
)
```

## 🎯 Workflow Integration

### Automated FME Processing
1. **CSV Export**: Survey data saved as `latest_directional_survey.csv`
2. **File Monitoring**: Windows batch script monitors for file changes
3. **FME Execution**: Automatic workbench execution for minimum curvature calculations
4. **Trajectory Generation**: 3D well path creation with spatial coordinates

### FME Watcher Script
```batch
# fme_csv_watcher.bat - monitors CSV file for changes
set "CSV_FILE=\\server\share\latest_directional_survey.csv"
set "FME_WORKBENCH=\\server\share\operator_survey_line.fmw"
"%FME_ENGINE%" "%FME_WORKBENCH%" --LOG_STANDARDOUT
```

### ArcGIS Geodatabase Integration
- **Metadata Export**: Well information and coordinates
- **Survey Data**: Directional survey points
- **Spatial Integration**: Coordinate system handling and projection
- **Visualization Ready**: Compatible with ArcGIS Pro and Portal

## 📁 Project Structure

```
WellTrajectoryAI/
├── app.py                    # Main Dash web application
├── main.py                   # Command-line processing pipeline
├── models/
│   ├── directionalsurvey.py  # Pydantic data models for surveys
│   └── plat.py              # Pydantic data models for plats
├── services/
│   └── llm.py               # OpenAI integration
├── static/                  # Web application assets
├── plats/                   # Input PDF documents
├── output/                  # Processing results
├── requirements.txt         # Python dependencies
├── fme_csv_watcher.bat     # Windows FME monitoring script
├── .env                    # Environment variables
└── README.md               # This documentation
```

## 🖥️ User Interface

### Main Features
- **📂 PDF Upload**: Drag-and-drop interface with file validation
- **🖼️ Page Preview**: Visual thumbnails with selection controls
- **⚙️ Processing Controls**: Real-time OCR and AI processing
- **📝 Data Forms**: Interactive metadata editing and validation
- **📊 Data Tables**: Editable survey point tables with sorting
- **💾 Export Options**: Multiple format downloads and integrations
- **🔄 Real-time Feedback**: Progress indicators and status messages

### Responsive Design
- **Bootstrap Components**: Modern, mobile-friendly interface
- **Interactive Elements**: Hover effects, loading spinners, toast notifications
- **Data Visualization**: Sortable tables with pagination
- **Form Validation**: Real-time input validation and error handling

## 🔍 Debugging and Troubleshooting

### Common Issues

1. **Shared Folder Access**:
```bash
# Check mount status
mount | grep ulmfile_shared
# Test write permissions
touch /mnt/ulmfile_shared/test_file.txt
# Remount if needed
sudo umount /mnt/ulmfile_shared
sudo mount /mnt/ulmfile_shared
```

2. **OCR Performance**:
```bash
# Check GPU availability
nvidia-smi
# Monitor memory usage
htop
# Adjust DPI for better accuracy vs speed
```

3. **FME Integration**:
```bash
# Verify CSV file creation
ls -la /mnt/ulmfile_shared/latest_directional_survey.csv
# Check FME logs on Windows
```

### Logging and Monitoring
- **Application Logs**: Real-time processing feedback in web interface
- **OCR Statistics**: Text detection confidence scores and processing times
- **API Monitoring**: OpenAI request/response logging with token usage
- **File System**: Shared folder access and permissions monitoring
- **Export Status**: CSV and JSON generation with success/failure tracking

### Visual Debugging
The system generates:
- **PDF Page Previews**: Visual thumbnails for page selection
- **Processing Status**: Real-time feedback during OCR and AI processing
- **Data Validation**: Interactive forms with error highlighting
- **Export Confirmation**: Success/failure notifications with detailed messages

## 🚀 Deployment

### Production Setup
1. **Server Configuration**: Linux server with GPU support
2. **Network Access**: Reliable connection to Windows shared folder
3. **Service Management**: Systemd service for automatic startup
4. **Monitoring**: Log rotation and performance monitoring

### Security Considerations
- **Credential Management**: Secure API key and network credential storage
- **File Permissions**: Proper shared folder access controls
- **Network Security**: VPN access for remote operations
- **Data Protection**: Regular backups and secure file handling

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Commit your changes: `git commit -am 'Add feature'`
5. Push to the branch: `git push origin feature-name`
6. Submit a pull request

## 📄 License

This project is licensed under the GNU General Public License (GPL) - see the LICENSE file for details.

## 🙏 Acknowledgments

- **PaddleOCR**: High-performance OCR engine for document processing
- **OpenAI**: Advanced language model capabilities for data extraction
- **Dash & Plotly**: Interactive web application framework
- **FME (Safe Software)**: Spatial data processing and minimum curvature calculations
- **ArcGIS (Esri)**: GIS platform integration for spatial analysis

## 📞 Support

For questions, issues, or contributions, please open an issue on the GitHub repository.

---

**WellTrajectoryAI** - Transforming directional survey documents into actionable spatial data for the petroleum industry 🛢️⚡

