"""Civic Services Portal API (simulated). All data fictional."""
from flask import Flask, jsonify

app = Flask(__name__)

SERVICES = [
    {"id": "SVC-01", "name": "Birth Certificate Request", "dept": "Civil Registry (simulated)"},
    {"id": "SVC-02", "name": "Property Tax Inquiry", "dept": "Revenue (simulated)"},
    {"id": "SVC-03", "name": "Business Permit Renewal", "dept": "Licensing (simulated)"},
    {"id": "SVC-04", "name": "Waste Collection Schedule", "dept": "Sanitation (simulated)"},
]


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "civic-portal-api"})


@app.get("/api/v1/services")
def services():
    return jsonify(SERVICES)


@app.get("/api/v1/admin/debug")
def debug():
    return jsonify(
        db="postgres://svc_admin:lab-secret@db-internal.eservices.test:5432/records",
        internal_hosts=["10.20.0.5", "10.20.0.6"],
        api_key="lab-demo-key",
        sample_record={
            "id": "TEST-0001",
            "name": "Test Citizen One",
            "phone": "+256700000001",
            "national_id": "CMTEST00000001",
            "pension_status": "ACTIVE",
        },
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
