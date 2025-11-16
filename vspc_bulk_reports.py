#!/usr/bin/env python3
"""
VSPC Automated Report Creator - Bulk mode (No confirmation)
Creates reports for all companies that don't have one
"""

import asyncio
import json
import sys
import argparse
from datetime import datetime

try:
    from playwright.async_api import async_playwright
    import requests
    import urllib3
except ImportError:
    print("ERROR: Required packages not installed")
    print("Install with: pip install playwright requests urllib3")
    sys.exit(1)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

async def get_token_and_cookie(vspc_url, username, password):
    """Use Playwright to login and capture token + cookie"""
    print("[*] Starting headless browser...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        captured_token = {'token': None}

        async def handle_response(response):
            if '/api/v3/token' in response.url and response.status == 200:
                try:
                    data = await response.json()
                    captured_token['token'] = data.get('access_token')
                except:
                    pass

        page.on('response', handle_response)

        print(f"[*] Navigating to {vspc_url}/login...")
        await page.goto(f"{vspc_url}/login", wait_until="networkidle", timeout=30000)

        print(f"[*] Logging in as {username}...")
        await page.fill('input[type="text"], input[name="username"]', username)
        await page.fill('input[type="password"], input[name="password"]', password)

        try:
            await page.click('button:has-text("Log in")', timeout=5000)
        except:
            try:
                await page.click('button[type="submit"]', timeout=5000)
            except:
                await page.click('button', timeout=5000)

        try:
            await page.wait_for_url(f"{vspc_url}/home/**", timeout=10000)
        except:
            await page.wait_for_timeout(5000)

        print("[+] Login successful")

        token = captured_token['token']
        cookies = await context.cookies()
        x_auth_cookie = None
        for cookie in cookies:
            if cookie['name'] == 'x-authorization':
                x_auth_cookie = cookie['value']
                break

        await browser.close()

        if token and x_auth_cookie:
            print(f"[+] Authentication credentials captured")

        return token, x_auth_cookie

class VSPCReportManager:
    def __init__(self, vspc_url, token, cookie):
        self.vspc_url = vspc_url
        self.token = token
        self.cookie = cookie
        self.session = requests.Session()
        self.session.verify = False

    def _make_request(self, endpoint, payload=None):
        """Make authenticated request to VSPC"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-ui-request": "true",
            "Origin": self.vspc_url
        }
        cookies = {"x-authorization": self.cookie}

        response = self.session.post(
            f"{self.vspc_url}{endpoint}",
            headers=headers,
            cookies=cookies,
            json=payload or {}
        )
        response.raise_for_status()
        return response.json()

    def get_companies(self):
        """Get all companies"""
        print("\n[*] Retrieving all companies...")
        result = self._make_request("/uiapi/Company/GetCompanyList")
        companies = result.get("data", [])
        print(f"[+] Found {len(companies)} companies")
        return companies

    def get_existing_reports(self):
        """Get all existing reports"""
        print("[*] Retrieving existing reports...")
        result = self._make_request("/uiapi/Report/GetReports")
        reports = result.get("data", [])
        print(f"[+] Found {len(reports)} existing reports")
        return reports

    def get_locations_for_company(self, company_id):
        """Get locations for a company"""
        result = self._make_request("/uiapi/Location/GetLocations", {"companyId": company_id})
        locations = result.get("data", [])
        return locations

    def create_report(self, company_name, company_id, location_ids=None):
        """Create a report for a company"""
        report_name = f"Protected Computers - {company_name} - {datetime.now().strftime('%Y%m%d')}"

        payload = {
            "type": "protectedComputers",
            "name": report_name,
            "description": f"Auto-created for {company_name} at {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "parameters": {
                "accessMode": "public",
                "aggregationMode": "singleCompany",
                "companies": [company_id],
                "locations": location_ids or [],
                "rpoInterval": {"number": 1, "period": "day"},
                "excludeMask": "",
                "groupBy": 1,
                "includeCompaniesDetails": False,
                "allCompaniesAndNewlyAdded": False,
                "includeResellerCompanies": False,
                "emailOptions": "%Company Owner%",
                "operationModeFilter": [-1],
                "managementTypeFilter": [-1],
                "guestOsFilter": [0, 1, 2]
            },
            "schedule": {
                "type": "daily",
                "daily": {
                    "time": "08:00",
                    "kind": "everyDay",
                    "days": ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
                },
                "monthly": {
                    "time": "07:00",
                    "week": "first",
                    "day": "sunday",
                    "dayNumber": 1,
                    "months": ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
                },
                "timeZoneId": "Romance Standard Time"
            }
        }

        result = self._make_request("/uiapi/Report/Save", payload)

        if result.get("data", {}).get("status") == "success":
            return True, report_name
        return False, None

    def find_companies_without_reports(self, companies, reports, verbose=False):
        """Find companies that don't have reports"""
        print("\n[*] Analyzing companies and reports...")

        # Build a map of company ID -> company info
        company_map = {}
        for company in companies:
            company_id = company.get("companyId") or company.get("id") or company.get("instanceUid")
            company_name = company.get("name", "Unknown")
            if company_id:
                company_map[company_id] = {
                    "id": company_id,
                    "name": company_name
                }

        if verbose:
            print(f"\n[DEBUG] Company IDs found:")
            for cid, info in company_map.items():
                print(f"  ID {cid}: {info['name']}")

        # Extract company IDs from existing reports
        companies_with_reports = {}

        for report in reports:
            report_name = report.get("name", "Unnamed")
            company_id = report.get("companyID")

            if verbose:
                print(f"\n[DEBUG] Report '{report_name}' -> Company ID: {company_id} ({report.get('companyName', 'Unknown')})")

            if company_id:
                if company_id not in companies_with_reports:
                    companies_with_reports[company_id] = []
                companies_with_reports[company_id].append(report_name)

        if verbose:
            print(f"\n[DEBUG] Companies with reports:")
            for cid, report_names in companies_with_reports.items():
                company_name = company_map.get(cid, {}).get("name", "Unknown")
                print(f"  ID {cid} ({company_name}): {len(report_names)} report(s)")
                for rname in report_names:
                    print(f"    - {rname}")

        # Find companies without reports
        companies_without_reports = []

        for company_id, company_info in company_map.items():
            if company_id not in companies_with_reports:
                companies_without_reports.append(company_info)
                if verbose:
                    print(f"\n[DEBUG] Company {company_id} ({company_info['name']}) has NO reports")

        print(f"\n[+] Companies WITH reports: {len(companies_with_reports)}")
        print(f"[+] Companies WITHOUT reports: {len(companies_without_reports)}")

        return companies_without_reports

    def create_reports_for_companies(self, companies, dry_run=False):
        """Create reports for multiple companies"""
        print(f"\n{'=' * 60}")
        print(f"{'DRY RUN - ' if dry_run else ''}Creating Reports")
        print(f"{'=' * 60}")

        results = {
            "success": [],
            "failed": []
        }

        for i, company in enumerate(companies, 1):
            company_id = company["id"]
            company_name = company["name"]

            print(f"\n[{i}/{len(companies)}] Processing: {company_name} (ID: {company_id})")

            if dry_run:
                print(f"    [DRY RUN] Would create report for {company_name}")
                results["success"].append(company_name)
                continue

            try:
                # Get locations
                locations = self.get_locations_for_company(company_id)
                location_ids = []
                if locations:
                    location_ids = [loc.get("locationId") or loc.get("id") for loc in locations]
                    location_names = [loc.get("name") for loc in locations]
                    print(f"    [*] Locations: {', '.join(location_names)}")

                # Create report
                success, report_name = self.create_report(company_name, company_id, location_ids)

                if success:
                    print(f"    [+] SUCCESS: {report_name}")
                    results["success"].append(company_name)
                else:
                    print(f"    [!] FAILED: Could not create report")
                    results["failed"].append(company_name)

            except Exception as e:
                print(f"    [!] ERROR: {e}")
                results["failed"].append(company_name)

        return results

async def main():
    parser = argparse.ArgumentParser(
        description="Create VSPC reports for all companies without one"
    )
    parser.add_argument("--url", required=True, help="VSPC URL")
    parser.add_argument("--login", required=True, help="Username")
    parser.add_argument("--password", required=True, help="Password")
    parser.add_argument("--company", help="Create report for specific company only")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be created")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed debug output")

    args = parser.parse_args()

    print("=" * 60)
    print("VSPC Bulk Report Creator")
    print("=" * 60)

    # Authenticate
    token, cookie = await get_token_and_cookie(args.url, args.login, args.password)

    if not token or not cookie:
        print("[!] Authentication failed")
        sys.exit(1)

    # Initialize manager
    manager = VSPCReportManager(args.url, token, cookie)

    try:
        # Get companies and reports
        all_companies = manager.get_companies()
        existing_reports = manager.get_existing_reports()

        if args.company:
            # Single company mode
            target_companies = [c for c in all_companies if c.get("name", "").lower() == args.company.lower()]
            if not target_companies:
                print(f"[!] Company '{args.company}' not found")
                print(f"[*] Available: {[c.get('name') for c in all_companies]}")
                sys.exit(1)

            companies_to_process = [{
                "id": target_companies[0].get("companyId") or target_companies[0].get("id"),
                "name": target_companies[0].get("name")
            }]
        else:
            # Bulk mode - find companies without reports
            companies_to_process = manager.find_companies_without_reports(
                all_companies, 
                existing_reports,
                verbose=args.verbose
            )

        if not companies_to_process:
            print("\n[+] All companies already have reports!")
            sys.exit(0)

        print(f"\n[*] Companies {'to process' if args.dry_run else 'needing reports'}: {len(companies_to_process)}")
        for company in companies_to_process:
            print(f"    - {company['name']} (ID: {company['id']})")

        # Create reports (NO CONFIRMATION PROMPT)
        results = manager.create_reports_for_companies(companies_to_process, args.dry_run)

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"{'Would create' if args.dry_run else 'Successfully created'}: {len(results['success'])}")
        if results["failed"]:
            print(f"Failed: {len(results['failed'])}")
            for name in results["failed"]:
                print(f"  - {name}")

        if args.dry_run:
            print("\n[*] This was a dry run. Use without --dry-run to actually create reports.")

        sys.exit(0 if not results["failed"] else 1)

    except Exception as e:
        print(f"\n[!] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
