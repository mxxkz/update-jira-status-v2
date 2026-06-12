from robot.api.deco import keyword
from urllib.parse import urlencode, urlparse, parse_qsl
from jsonpath_ng.ext import parse as jsonpath_parse
from jsonpath_ng import parse
import sys
import time
import jwt
import json
import hashlib
import requests
import os

class ZephyrLibraryUat():
    def __init__(self):
        self.zephyr_base_url = 'https://prod-api.zephyr4jiracloud.com/connect'
        self.access_key = os.environ.get("ZEPHYR_ACCESS_KEY")
        self.secret_key = os.environ.get("ZEPHYR_SECRET_KEY")
        self.account_id = os.environ.get("ZEPHYR_ACCOUNT_ID")

    def create_query_string_hash(self, method: str, endpoint: str) -> str:
        parsed_url = urlparse(endpoint)
        canonical_method = method.upper()
        canonical_uri = parsed_url.path
        query_params = parse_qsl(parsed_url.query, keep_blank_values=True)
        sorted_query_params = sorted(query_params)
        canonical_query = urlencode(sorted_query_params)

        canonical_request = '&'.join([canonical_method, canonical_uri, canonical_query])
        return hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()

    def generate_json_web_token_for_zephyr(self, method, endpoint):
        now = int(time.time())
        qsh = self.create_query_string_hash(method, endpoint)
        payload = {
            'iss': self.access_key,
            'iat': now,
            'exp': now + 180,
            'qsh': qsh
        }
        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        return token.decode('utf-8') if isinstance(token, bytes) else token

    @keyword("Get All Execution Navigation Results")
    def get_all_execution_navigation_results(self, project_name, version_name, cycle_names, folder_names=None):
        method = "POST"
        endpoint_path = "/public/rest/api/1.0/zql/search"
        full_endpoint = endpoint_path
        full_url = f"{self.zephyr_base_url}{full_endpoint}"

        max_records = 50
        offset = 0
        all_executions = []

        cycle_clause = ', '.join(f'"{cycle}"' for cycle in cycle_names)
        
        folder_clause = ""
        if folder_names:
            formatted_folders = ', '.join(f'"{folder}"' for folder in folder_names)
            folder_clause = f'AND folderName IN ({formatted_folders}) '

        zql_query = (
            f'project = "{project_name}" '
            f'AND fixVersion = "{version_name}" '
            f'AND cycleName IN ({cycle_clause}) '
            f'{folder_clause}'
        )

        while True:
            body = {
                "zqlQuery": zql_query,
                "maxRecords": max_records,
                "offset": offset
            }

            headers = {
                "Authorization": f"JWT {self.generate_json_web_token_for_zephyr(method, full_endpoint)}",
                "zapiAccessKey": self.access_key,
                "Content-Type": "application/json"
            }
            
            response = requests.post(full_url, headers=headers, json=body)
            if response.status_code != 200:
                print(f"ZQL search failed. Status: {response.status_code}")
                print(response.text)
                sys.exit(1)

            data = response.json()
            ObjectList = data.get("searchObjectList", [])
            all_executions.extend(ObjectList)
            # print(f"Fetched {len(ObjectList)} executions; offset now at {offset}")
            total_count = data.get("totalCount", 0)
            offset += max_records

            if offset >= total_count:
                break
        data_list = []
        print(all_executions)
        issue_key_expr = parse('$.issueKey')
        execution_status_expr = parse('$.execution.status.name')
        cycle_name_expr = parse('$.execution.cycleName')
        folder_name_expr = parse('$.execution.folderName')

        for issue in all_executions:
            # Extract values using JSONPath
            issue_key_matches = issue_key_expr.find(issue)
            execution_status_matches = execution_status_expr.find(issue)
            cycle_matches = cycle_name_expr.find(issue)
            folder_matches = folder_name_expr.find(issue)

            # Safely extract first match or fallback to None
            issue_key = issue_key_matches[0].value if issue_key_matches else None
            execution_status = execution_status_matches[0].value if execution_status_matches else None
            cycle_val = cycle_matches[0].value if cycle_matches else None
            folder_val = folder_matches[0].value if folder_matches else None

            # Append the extracted data
            new_data = {
                "issue_key": issue_key,
                "status": execution_status,
                "cycle_name": cycle_val,
                "folder_name": folder_val
            }
            data_list.append(new_data)

        return data_list
    
if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python zephyr_token.py <project_name> <version_name> <cycle_name> [folder_names...]")
        sys.exit(1)

    project_name = sys.argv[1]
    version_name = sys.argv[2]
    cycle_name = sys.argv[3]
    folder_names = sys.argv[4:] if len(sys.argv) > 4 else None

    zephyr = ZephyrLibraryUat()
    
    print(f"Fetching executions for project='{project_name}', version='{version_name}', cycle='{cycle_name}'...")
    all_results = zephyr.get_all_execution_navigation_results(project_name, version_name, cycle_name, folder_names)

    if not all_results:
        print("No executions found.")
    else:
        print(f"Total executions fetched: {len(all_results)}")
        for exec_item in all_results:
            print(exec_item)