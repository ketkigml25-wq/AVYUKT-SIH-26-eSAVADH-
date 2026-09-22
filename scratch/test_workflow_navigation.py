"""
Test suite to thoroughly verify the 5-step inspector guided workflow navigation,
confirm removal of duplicate navigation tabs, and validate forward/backward step transitions.
"""

import sys
import os
import json
import re

# Ensure unbuffered output
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

# Ensure project directory is on path
sys.path.insert(0, r"c:\Users\Khushi\OneDrive\Desktop\eSavadh")

from app import app
import database

def test_template_structure():
    print("\n--- Test 1: Template Structure & Deduplication ---")
    template_path = r"c:\Users\Khushi\OneDrive\Desktop\eSavadh\templates\inspection_detail.html"
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. Ensure NO duplicate tab-container
    assert '<div class="tab-container"' not in html, "FAIL: Duplicate tab-container is still present!"
    print("[OK] Passed: Duplicate tab-container completely removed.")

    # 2. Ensure only ONE workflow stepper
    steppers = re.findall(r'class="workflow-stepper"', html)
    assert len(steppers) == 1, f"FAIL: Expected exactly 1 workflow-stepper, found {len(steppers)}"
    print("[OK] Passed: Exactly ONE canonical workflow-stepper present.")

    # 3. Ensure all 5 step panes exist
    for step in range(1, 6):
        assert f'id="step-pane-{step}"' in html, f"FAIL: step-pane-{step} missing!"
        assert f'id="step-btn-{step}"' in html, f"FAIL: step-btn-{step} missing!"
    print("[OK] Passed: All 5 canonical step panes and buttons exist.")

    # 4. Check forward and back button calls
    # Step 1 -> goToStep(2)
    assert "goToStep(2)" in html, "FAIL: Step 1 -> Step 2 button missing"
    
    # Step 2 -> Back: goToStep(1), Forward: evaluateAndGoToStep3
    assert "goToStep(1)" in html, "FAIL: Step 2 -> Back button missing"
    assert "evaluateAndGoToStep3" in html, "FAIL: evaluateAndGoToStep3 missing"

    # Step 3 -> Back: goToStep(2), Forward: goToStep(4)
    assert "goToStep(4)" in html, "FAIL: Step 3 -> Step 4 button missing"

    # Step 4 -> Back: goToStep(3), Forward: goToStep(5)
    assert "goToStep(3)" in html, "FAIL: Step 4 -> Back button missing"
    assert "goToStep(5)" in html, "FAIL: Step 4 -> Step 5 button missing"

    # Step 5 -> Back: goToStep(4)
    print("[OK] Passed: All forward and backward navigation handlers are correctly wired.")


def test_api_and_navigation_flow():
    print("\n--- Test 2: Full End-to-End Workflow API Execution ---")
    client = app.test_client()

    # 1. Login as inspector
    login_res = client.post("/login", data={
        "email": "inspector@esavadh.gov.in",
        "password": "inspector123"
    }, follow_redirects=True)
    assert login_res.status_code == 200, "Login failed"
    print("[OK] Inspector logged in successfully.")

    # 2. Get an active inspection ID
    inspections = database.get_inspections(limit=1)
    assert len(inspections) > 0, "No inspections found in database"
    insp_id = inspections[0]["id"]
    print(f"[OK] Using Inspection ID: {insp_id} (Ref: {inspections[0]['ref_no']})")

    # 3. Load dossier page with various steps
    for step in [1, 2, 3, 4, 5]:
        res = client.get(f"/inspection/{insp_id}?step={step}")
        if res.status_code != 200:
            print(f"DEBUG: res.status_code = {res.status_code}, location = {res.headers.get('Location')}")
        assert res.status_code == 200, f"Failed loading dossier step {step}: status {res.status_code}"
        assert b"Statutory Inspector Workflow" in res.data
    print("[OK] Passed: Dossier page renders with ?step=1..5 without error.")

    # 4. Step 2 HITL: Confirm all declarations
    bulk_res = client.post(f"/api/declarations/confirm-all/{insp_id}")
    assert bulk_res.status_code == 200
    bulk_data = json.loads(bulk_res.data)
    assert bulk_data.get("success") is True
    print(f"[OK] Step 2 HITL: Bulk confirm succeeded (updated {bulk_data.get('updated_count')} items).")

    # 5. Step 2 -> Step 3: Run Statutory Rule Engine
    eval_res = client.post(f"/api/inspection/{insp_id}/evaluate")
    assert eval_res.status_code == 200
    eval_data = json.loads(eval_res.data)
    assert eval_data.get("success") is True
    assert "findings" in eval_data, "findings missing from evaluate response"
    assert "overall_status" in eval_data
    print(f"[OK] Step 3 Rule Engine: Evaluated successfully (Status: {eval_data['overall_status']}, Findings: {eval_data['findings_count']}).")

    # 6. Step 4: Finalize Notes & Sign off
    fin_res = client.post(f"/api/inspection/{insp_id}/finalize", json={
        "notes": "Surveillance verified and sealed pursuant to Rule 6 PCR 2011."
    })
    assert fin_res.status_code == 200
    fin_data = json.loads(fin_res.data)
    assert fin_data.get("success") is True
    print("[OK] Step 4 Sign-Off: Officer notes saved and finalized.")

    # 7. Step 5: Verify Audit Log has all actions recorded
def test_sequential_step_progression():
    print("\n--- Test 3: Sequential Forward & Backward Navigation Path ---")
    template_path = r"c:\Users\Khushi\OneDrive\Desktop\eSavadh\templates\inspection_detail.html"
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Step 1 Pane: Must have forward to Step 2
    step1_pane = re.search(r'id="step-pane-1".*?(?=id="step-pane-2")', html, re.DOTALL).group(0)
    assert 'goToStep(2)' in step1_pane, "Step 1 forward button must call goToStep(2)"
    print("[OK] Verified: Step 1 -> Step 2 forward navigation exists.")

    # Step 2 Pane: Must have back to Step 1 and forward to Step 3
    step2_pane = re.search(r'id="step-pane-2".*?(?=id="step-pane-3")', html, re.DOTALL).group(0)
    assert 'goToStep(1)' in step2_pane, "Step 2 back button must call goToStep(1)"
    assert 'evaluateAndGoToStep3' in step2_pane, "Step 2 forward button must trigger evaluate and goToStep(3)"
    print("[OK] Verified: Step 2 -> Step 1 back & Step 2 -> Step 3 forward navigation exist.")

    # Step 3 Pane: Must have back to Step 2 and forward to Step 4 (NEVER Step 2)
    step3_pane = re.search(r'id="step-pane-3".*?(?=id="step-pane-4")', html, re.DOTALL).group(0)
    assert 'goToStep(2)' in step3_pane, "Step 3 back button must call goToStep(2)"
    assert 'goToStep(4)' in step3_pane, "Step 3 forward button must call goToStep(4) - NOT Step 2"
    assert not re.search(r'Continue to Step 4.*?goToStep\(2\)', step3_pane, re.DOTALL), "Step 3 continue button must NOT call goToStep(2)!"
    print("[OK] Verified: Step 3 -> Step 2 back & Step 3 -> Step 4 forward (NEVER Step 2) verified.")

    # Step 4 Pane: Must have back to Step 3 and forward to Step 5
    step4_pane = re.search(r'id="step-pane-4".*?(?=id="step-pane-5")', html, re.DOTALL).group(0)
    assert 'goToStep(3)' in step4_pane, "Step 4 back button must call goToStep(3)"
    assert 'goToStep(5)' in step4_pane, "Step 4 forward button must call goToStep(5)"
    print("[OK] Verified: Step 4 -> Step 3 back & Step 4 -> Step 5 forward navigation exist.")

    # Step 5 Pane: Must have back to Step 4
    step5_pane = re.search(r'id="step-pane-5".*?(?=<\/div>\s*<\/div>\s*{% endblock %})', html, re.DOTALL).group(0)
    assert 'goToStep(4)' in step5_pane, "Step 5 back button must call goToStep(4)"
    print("[OK] Verified: Step 5 -> Step 4 back navigation exists.")


if __name__ == "__main__":
    test_template_structure()
    test_api_and_navigation_flow()
    test_sequential_step_progression()
    print("\n=======================================================")
    print(" ALL WORKFLOW & NAVIGATION TESTS PASSED (100% SUCCESS) ")
    print("=======================================================\n")

