import subprocess
import time
import requests
import json
import sys

def run_tests():
    # Start the FastAPI server in the background
    print("Starting FastAPI server with Uvicorn...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for the server to start
    time.sleep(3)
    
    base_url = "http://127.0.0.1:8000"
    
    print("\n" + "="*50)
    print("VERIFICATION AND VALIDATION TESTS: EMPLEADO RESOURCE")
    print("="*50 + "\n")
    
    try:
        # TEST 1: GET /empleados/ (List existing employees)
        print("--- TEST 1: List all employees (GET /empleados/) ---")
        r = requests.get(f"{base_url}/empleados/")
        print(f"Status Code: {r.status_code}")
        print("Response JSON:")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        print("-" * 50 + "\n")
        
        # TEST 2: POST /empleados/ (Create a new employee with valid JSON)
        print("--- TEST 2: Create new employee JSON (POST /empleados/) ---")
        new_emp = {
            "cedula": "1723456701",
            "nombres": "Carlos Mendoza",
            "sueldo_basico": 950.0,
            "aporte_iess": 0.0945,
            "bonificaciones": 75.0,
            "cuenta_bancaria": "9998887776",
            "prestamos": 0.0,
            "decimos": True,
            "fondos_reserva": True
        }
        r = requests.post(f"{base_url}/empleados/", json=new_emp)
        print(f"Status Code: {r.status_code}")
        print("Response JSON:")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        print("-" * 50 + "\n")
        
        # TEST 3: GET /empleados/{cedula} (Query the created employee)
        print("--- TEST 3: Query created employee (GET /empleados/1723456701) ---")
        r = requests.get(f"{base_url}/empleados/1723456701")
        print(f"Status Code: {r.status_code}")
        print("Response JSON:")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        print("-" * 50 + "\n")
        
        # TEST 4: POST /empleados/ (Attempt to create duplicate employee)
        print("--- TEST 4: Attempt to create duplicate employee (POST /empleados/) ---")
        r = requests.post(f"{base_url}/empleados/", json=new_emp)
        print(f"Status Code: {r.status_code} (Expected: 400)")
        print("Response JSON:")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        print("-" * 50 + "\n")
        
        # TEST 5: POST /empleados/ (Attempt to create employee with negative salary)
        print("--- TEST 5: Attempt to create employee with negative salary (POST /empleados/) ---")
        bad_emp = new_emp.copy()
        bad_emp["cedula"] = "1723456702"
        bad_emp["sueldo_basico"] = -100.0
        r = requests.post(f"{base_url}/empleados/", json=bad_emp)
        print(f"Status Code: {r.status_code} (Expected: 400)")
        print("Response JSON:")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        print("-" * 50 + "\n")
        
        # TEST 6: POST /empleados_form/ (Create employee via HTML Form)
        print("--- TEST 6: Create employee via HTML Form (POST /empleados_form/) ---")
        form_data = {
            "cedula": "0912345602",
            "nombres": "Ana María Silva",
            "sueldo_basico": 500.0,
            "cuenta_bancaria": "1112223334",
            "aporte_iess": 0.0945,
            "bonificaciones": 20.0,
            "prestamos": 0.0,
            "decimos": "True",
            "fondos_reserva": "True"
        }
        r = requests.post(f"{base_url}/empleados_form/", data=form_data)
        print(f"Status Code: {r.status_code} (Expected: 201)")
        print("Response Text:")
        print(r.text)
        print("-" * 50 + "\n")
        
        # TEST 7: POST /empleados_form/ (Attempt to create employee via Form with salary < SBU)
        print("--- TEST 7: Attempt to create employee via Form with salary < SBU (POST /empleados_form/) ---")
        bad_form_data = form_data.copy()
        bad_form_data["cedula"] = "0912345603"
        bad_form_data["sueldo_basico"] = 350.0  # Under SBU $460
        r = requests.post(f"{base_url}/empleados_form/", data=bad_form_data)
        print(f"Status Code: {r.status_code} (Expected: 400)")
        print("Response JSON:")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        print("-" * 50 + "\n")
        
        # TEST 8: PUT /empleados/{cedula} (Update the employee details)
        print("--- TEST 8: Update employee (PUT /empleados/1723456701) ---")
        updated_emp = {
            "cedula": "1723456701",
            "nombres": "Carlos Mendoza Alaba", # Changed name
            "sueldo_basico": 1050.0,            # Changed salary
            "aporte_iess": 0.0945,
            "bonificaciones": 100.0,           # Changed bonus
            "cuenta_bancaria": "9998887776",
            "prestamos": 50.0,                 # Changed loan
            "decimos": True,
            "fondos_reserva": True
        }
        r = requests.put(f"{base_url}/empleados/1723456701", json=updated_emp)
        print(f"Status Code: {r.status_code}")
        print("Response JSON:")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        print("-" * 50 + "\n")
        
        # TEST 9: DELETE /empleados/{cedula} (Delete the employee)
        print("--- TEST 9: Delete employee (DELETE /empleados/1723456701) ---")
        r = requests.delete(f"{base_url}/empleados/1723456701")
        print(f"Status Code: {r.status_code}")
        print("Response JSON:")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        print("-" * 50 + "\n")
        
        # TEST 10: GET /empleados/{cedula} (Verify deletion - Not Found)
        print("--- TEST 10: Verify deletion of employee (GET /empleados/1723456701) ---")
        r = requests.get(f"{base_url}/empleados/1723456701")
        print(f"Status Code: {r.status_code} (Expected: 404)")
        print("Response JSON:")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        print("-" * 50 + "\n")
        
    finally:
        # Terminate server
        print("Shutting down FastAPI server...")
        server_process.terminate()
        server_process.wait()
        print("FastAPI server shut down successfully.")

if __name__ == "__main__":
    run_tests()
