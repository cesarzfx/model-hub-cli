cd service
pip install -r requirements.txt
$env:PYTHONPATH='.'
python -m uvicorn app.main:app --reload --port 8080

# new terminal
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8080/v1/admin/bootstrap"
$token = (Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8080/v1/auth/login" `
  -ContentType "application/json" `
  -Body '{"username":"ece30861defaultadminuser","password":"ChangeMe!123"}').token
$pkg = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8080/v1/packages" `
  -Headers @{Authorization="Bearer $token"} -ContentType "application/json" `
  -Body '{"name":"demo-model","version":"1.0.0","meta":{"how_to_run":"echo hello world"},"parents":[],"sensitive":false}'
Invoke-RestMethod -Method Post -Uri ("http://127.0.0.1:8080/v1/rate/" + $pkg.id) `
  -Headers @{Authorization="Bearer $token"}
