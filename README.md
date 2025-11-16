# VSPC Automated Report Creator

Automate the creation of scheduled reports in Veeam Service Provider Console (VSPC) v9.1. This toolkit provides multiple solutions for creating "Protected Computers (RPO)" reports programmatically.

TL;DR it replicates this wizard : https://helpcenter.veeam.com/docs/vac/provider_admin/configure_computers_report.html?ver=9.1 using webui until we have proper RestAPI


[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 🚀 Features

- **Fully Automated**: Uses headless browser to handle authentication automatically
- **Bulk Operations**: Create reports for all companies that don't have one
- **Smart Detection**: Identifies which companies already have reports to avoid duplicates
- **Flexible Options**: Single company or bulk mode
- **Dry-run Support**: Preview changes before executing
- **Verbose Debugging**: Detailed output for troubleshooting

## 📋 Requirements

### System Requirements
- Python 3.7+
- Linux/WSL/macOS (for bash scripts)
- Network access to VSPC server
- VSPC v9.1

### Python Dependencies
`pip install playwright requests urllib3`

## 🛠️ Installation

1. **Clone the repository:**
`git clone https://github.com/yourusername/vspc-report-automation.git`
`cd vspc-report-automation`
2. **Install Python dependencies:**
`pip install playwright requests urllib3`
`python3 -m playwright install chromium`

### 1. vspc_bulk_reports.py ⭐ Recommended
**Fully automated bulk report creator** - Creates reports for all companies without one.
#### Usage

- Dry run (preview only)

```
python3 vspc_bulk_reports.py
--url https://your-vspc-server:1280
--login administrator
--password 'YourPassword'
--dry-run
```

- Create reports for all companies without one

```
python3 vspc_bulk_reports.py
--url https://your-vspc-server:1280
--login administrator
--password 'YourPassword'
Create report for specific company
```
- Create report for specific company
```
python3 vspc_bulk_reports.py
--url https://your-vspc-server:1280
--login administrator
--password 'YourPassword'
--company 'CompanyName'
```
- Verbose debug mode

```
python3 vspc_bulk_reports.py
--url https://your-vspc-server:1280
--login administrator
--password 'YourPassword'
--verbose
```


#### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--url` | ✅ Yes | VSPC server URL (e.g., https://192.168.1.100:1280) |
| `--login` | ✅ Yes | Username for VSPC |
| `--password` | ✅ Yes | Password for VSPC |
| `--company` | ❌ No | Target specific company by name |
| `--dry-run` | ❌ No | Preview what would be created without creating |
| `--verbose` or `-v` | ❌ No | Show detailed debug information |

---

**Output:**

<img width="551" height="618" alt="image" src="https://github.com/user-attachments/assets/a87a981e-f03a-4e76-9703-3f60fc9752f2" />

## 📊 Report Configuration

All reports are created with these settings:

| Setting | Value |
|---------|-------|
| **Type** | Protected Computers (RPO) |
| **Schedule** | Daily at 08:00 (Romance Standard Time / UTC+1) |
| **Access Mode** | Public |
| **Aggregation** | Single Company |
| **RPO Interval** | 1 day |
| **Guest OS Filter** | All (Windows, Linux, Mac) |
| **Email** | Send to Company Owner |

## 🔍 How It Works
### Detailed Process

1. **Authentication**: Opens headless Chromium browser and logs into VSPC
2. **Token Capture**: Intercepts `/api/v3/token` API call to capture access token
3. **Cookie Extraction**: Captures `x-authorization` cookie from browser session
4. **Company Analysis**: Retrieves all companies via `/uiapi/Company/GetCompanyList`
5. **Report Analysis**: Retrieves existing reports via `/uiapi/Report/GetReports`
6. **Smart Detection**: Compares companies against reports using `companyID` field
7. **Report Creation**: Creates reports only for companies without existing ones
8. **Location Mapping**: Automatically includes all locations for each company

## 🐛 Troubleshooting

### Issue: "Authentication failed"
**Solution**: 
- Verify credentials are correct
- Ensure VSPC URL is accessible
- Check if VSPC service is running
- Verify firewall rules allow connection

### Issue: "Certificate verification failed"
**Solution**: Scripts disable SSL verification by default for self-signed certificates. This is normal for VSPC deployments.

### Issue: "Playwright not found"
**Solution**: 
`python3 -m playwright install chromium`

### Issue: "All companies show as needing reports"
**Solution**: 
- Use `--verbose` flag to see debug output
- The script looks for `companyID` field in existing reports
- Verify reports were created through this script or VSPC UI

### Issue: Script creates duplicate reports
**Solution**: This was fixed in latest version. The script now correctly reads `report.companyID` field to detect existing reports.

### Issue: "Login button not found"
**Solution**: The script tries multiple selectors. If it fails, the login page structure may have changed. Check VSPC version compatibility.

## 🔒 Security Notes

- ⚠️ Passwords are passed as command-line arguments (consider using environment variables)
- ✅ SSL certificate verification is disabled for self-signed certificates
- ✅ Token and cookies are captured in memory only, not persisted
- ✅ Scripts use HTTPS for all API communication
- ⚠️ Command-line history may contain passwords (use `history -c` to clear)

## 📝 License

MIT License - Feel free to modify and distribute.

## 🤝 Contributing

Contributions welcome! 

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📧 Support

- For VSPC API issues: Consult [Veeam documentation](https://helpcenter.veeam.com/)
- For script issues: Open an issue in this repository



