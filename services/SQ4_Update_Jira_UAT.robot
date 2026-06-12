*** Settings ***
Documentation     Robot Framework script to query multiple Zephyr cycles 
...               and batch update results to Google Sheets via Webhook.
Library           Collections
Library           JSONLibrary
Library           RequestsLibrary
Library           String
# เรียกใช้ Custom Library ของมุก
Library           ${CURDIR}/ZephyrLibraryUat.py    WITH NAME    ZephyrLibraryUat

*** Variables ***
${WEBHOOK_BASE_URL}    https://script.google.com
${WEBHOOK_PATH}        ${EMPTY}    # รับมาจาก Python (record['webhook_path'])
${PROJECT}             ${EMPTY}    # รับมาจาก Python (record['project_name'])
${VERSION}             ${EMPTY}    # รับมาจาก Python (record['version_name'])
${CYCLES_STR}          ${EMPTY}    # รับมาจาก Python (cycle_names join ด้วย ;)
${FOLDERS_STR}         ${EMPTY}    # รับมาจาก Python (folders join ด้วย ;)
${ENV}                 ${EMPTY}    # รับมาจาก Python (record['env'])

*** Keywords ***
Append To Google Sheet Via Webhook
    [Arguments]    ${all_results}    ${env_name}
    ${payload_dict}=    Create Dictionary    results=${all_results}    env=${env_name}
    # แปลง Dictionary เป็น JSON String
    ${payload}=    Evaluate    json.dumps(${payload_dict})    json
    ${headers}=    Create Dictionary    Content-Type=application/json
    
    Log    Sending ${all_results.__len__()} records to Google Sheet...
    Create Session    mysession    ${WEBHOOK_BASE_URL}    verify=${True}
    
    # ยิง POST ไปยัง Webhook Path ที่ได้รับมา
    ${response}=    POST On Session    mysession    ${WEBHOOK_PATH}    data=${payload}    headers=${headers}
    
    # เช็กว่า Google Script ตอบกลับมา OK (200 หรือ 302 สำหรับ Redirect)
    Should Be True    ${response.status_code} < 400
    Log    Successfully sent data: ${response.text}

*** Test Cases ***
Batch Update Zephyr Executions To Sheet
    [Documentation]    Loop through all cycles, collect data, and send once.
    
    # 1. เตรียม List ว่างสำหรับเก็บผลลัพธ์รวม
    ${FINAL_DATA_LIST}=    Create List
    
    # 2. แปลง String ของ Cycles และ Folders ให้เป็น List
    @{CYCLE_LIST}=     Split String    ${CYCLES_STR}    ;
    @{FOLDER_LIST}=    Run Keyword If    '${FOLDERS_STR}' != '${EMPTY}'    Split String    ${FOLDERS_STR}    ;
    ...                ELSE              Create List
    ${FINAL_DATA_LIST}=     Run Keyword If    '${FOLDERS_STR}' != '${EMPTY}'
    ...    ZephyrLibraryUat.Get All Execution Navigation Results    ${PROJECT}    ${VERSION}    ${CYCLE_LIST}    ${FOLDER_LIST}
    ...    ELSE        
    ...    ZephyrLibraryUat.Get All Execution Navigation Results    ${PROJECT}    ${VERSION}    ${CYCLE_LIST}


    # 6. ส่งข้อมูลทั้งหมดขึ้น Google Sheet ทีเดียวหลังจากจบ Loop
    ${total_records}=    Get Length    ${FINAL_DATA_LIST}
    Run Keyword If    ${total_records} > 0
    ...    Append To Google Sheet Via Webhook    ${FINAL_DATA_LIST}    ${ENV}
    ...    ELSE
    ...    Log    ⚠️ No data found to send.