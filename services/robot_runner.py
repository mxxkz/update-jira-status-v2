import os
import yaml
from robot import run as robot_run

CONFIG_FILE = "config/data.yml"

def get_phase_names():
    with open(CONFIG_FILE, "r") as f:
        config = yaml.safe_load(f)
    return [record["name"] for record in config["data"]]

def run_update_jira(selected_name):
    with open(CONFIG_FILE, "r") as f:
        config = yaml.safe_load(f)

    record = next((r for r in config["data"] if r["name"] == selected_name), None)
    if not record:
        return None, "⚠️ Selected test not found in YAML config."

    robot_file = os.path.join("services", "SQ4_Update_Jira_UAT.robot")

    # --- จุดที่ 1: จัดการเรื่อง Cycle (รองรับทั้งแบบเดี่ยวและแบบ List) ---
    # ถ้าใน YAML ใช้ 'cycle_names' (List) ให้เอามา join ด้วย ; 
    # แต่ถ้าไม่มี ให้ถอยไปใช้ 'cycle_name' (String) ตัวเดียวแทนเพื่อไม่ให้โค้ดพัง
    cycle_str = ";".join(record["cycle_names"])

    # --- จุดที่ 2: เตรียม variables ให้ตรงกับชื่อในไฟล์ .robot ใหม่ ---
    variables = [
        f"WEBHOOK_PATH:{record['webhook_path']}",
        f"PROJECT:{record['project_name']}",
        f"VERSION:{record['version_name']}",
        f"CYCLES_STR:{cycle_str}",  # เปลี่ยนจาก CYCLE เป็น CYCLES_STR
        f"ENV:{record['env']}"
    ]

    # Add folders if present (เหมือนเดิม)
    if "folders" in record and record["folders"]:
        folder_str = ";".join(record["folders"])
        variables.append(f"FOLDERS_STR:{folder_str}")
    else:
        # ส่งค่าว่างไปเพื่อให้ Robot ไม่ Error เวลาดึงตัวแปร
        variables.append("FOLDERS_STR:")

    # Run Robot Framework using Python API
    result_code = robot_run(
        robot_file,
        variable=variables,
        log=None,       
        report=None,    
        output=None,   
        console='NONE'
    )

    return result_code, f"Robot run finished for cycles: {cycle_str}"