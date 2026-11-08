"""eServices Lab - a SIMULATED government e-services backend (all data fictional).
Case-study target for DriftGuard. Never deploy publicly."""
from flask import Flask, jsonify, request, abort

app = Flask(__name__)
API_KEY = "lab-demo-key"
SERVICES = [
    {"id": "SVC-01", "name": "Citizen Records Lookup", "dept": "Registry (simulated)"},
    {"id": "SVC-02", "name": "Pension Benefit Status", "dept": "Pensions (simulated)"},
    {"id": "SVC-03", "name": "Business Licence Check", "dept": "Licensing (simulated)"},
]
# Seeded FAKE personal data - used to prove the redaction layer never leaks identifiers to the AI API.
RECORDS = {f"TEST-{i:04d}": {"id": f"TEST-{i:04d}", "name": n, "phone": f"+256700000{i:03d}",
           "national_id": f"CMTEST{i:08d}", "pension_status": s}
           for i, (n, s) in enumerate([("Test Citizen One", "ACTIVE"), ("Test Citizen Two", "SUSPENDED"),
                                       ("Test Citizen Three", "ACTIVE")], start=1)}

@app.get("/")
def portal():
    items = "".join(f"<li>{s['id']} - {s['name']} <i>({s['dept']})</i></li>" for s in SERVICES)
    return (f"<h1>eServices Lab Portal</h1><p>Simulated e-government services. Fictional data only.</p>"
            f"<ul>{items}</ul><p><a href='/api/v1/services'>API: /api/v1/services</a></p>")

@app.get("/health")
def health():
    return jsonify(status="ok", service="eservices-lab")

@app.get("/api/v1/services")
def services():
    return jsonify(SERVICES)

@app.get("/api/v1/records/<rid>")
def record(rid):
    if request.headers.get("X-API-Key") != API_KEY:
        abort(401)
    return jsonify(RECORDS.get(rid) or abort(404))

@app.get("/api/v1/admin/debug")   # must NEVER be public: blocked at the proxy unless 'api-debug' drift is on
def debug():
    return jsonify(db="postgres://svc_admin:lab-secret@db-internal.eservices.test:5432/records",
                   internal_hosts=["10.20.0.5", "10.20.0.6"], api_key=API_KEY,
                   sample_record=RECORDS["TEST-0001"])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
