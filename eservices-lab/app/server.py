"""eServices Lab - a SIMULATED government e-services backend (all data fictional).
Case-study target for DriftGuard. Never deploy publicly."""
from flask import Flask, abort, jsonify, render_template, request

import demo_data

app = Flask(__name__)
API_KEY = demo_data.API_KEY

# Exposed for compatibility: services list (frozen shape: entries keep id/name/dept)
SERVICES = demo_data.SERVICES
# Records (frozen fields for lookups; TEST-0001..3 keep exact original values)
RECORDS = demo_data.RECORDS

# Byte-identical pre-change debug payload (frozen contract).
DEBUG_PAYLOAD = (
    b'{"api_key":"lab-demo-key","db":"postgres://svc_admin:lab-secret@db-internal.eservices.test:5432/records",'
    b'"internal_hosts":["10.20.0.5","10.20.0.6"],"sample_record":{"id":"TEST-0001","name":"Test Citizen One",'
    b'"national_id":"CMTEST00000001","pension_status":"ACTIVE","phone":"+256700000001"}}\n'
)


@app.context_processor
def inject_globals():
    return {
        "departments": demo_data.DEPARTMENTS,
        "services_all": demo_data.SERVICES,
    }


# ----- Portal pages -----

@app.get("/")
def portal():
    grouped = {}
    for s in demo_data.SERVICES:
        grouped.setdefault(s["dept"], []).append(s)
    popular = demo_data.SERVICES[:4]
    return render_template(
        "index.html",
        grouped=grouped,
        popular=popular,
        notices=demo_data.NOTICES[:3],
        active="home",
    )


@app.get("/services/<sid>")
def service_page(sid):
    svc = demo_data.get_service(sid)
    if not svc:
        abort(404)
    return render_template("service.html", service=svc, active="services")


@app.get("/records")
def records_page():
    return render_template("records.html", active="records")


@app.get("/applications")
def applications_page():
    return render_template(
        "applications.html",
        applications=list(reversed(demo_data.APPLICATIONS)),
        services=demo_data.SERVICES,
        active="applications",
    )


@app.get("/notices")
def notices_page():
    return render_template("notices.html", notices=demo_data.NOTICES, active="notices")


@app.get("/help")
def help_page():
    return render_template("help.html", faq=demo_data.FAQ, active="help")


# ----- API (contract frozen + additive routes) -----

@app.get("/health")
def health():
    return jsonify(status="ok", service="eservices-lab")


@app.get("/api/v1/services")
def services():
    return jsonify(SERVICES)


@app.get("/api/v1/services/<sid>")
def service_detail(sid):
    svc = demo_data.get_service(sid)
    if not svc:
        abort(404)
    return jsonify(svc)


@app.get("/api/v1/records/<rid>")
def record(rid):
    if request.headers.get("X-API-Key") != API_KEY:
        abort(401)
    return jsonify(RECORDS.get(rid) or abort(404))


@app.get("/api/v1/admin/debug")   # must NEVER be public: blocked at the proxy unless 'api-debug' drift is on
def debug():
    return app.response_class(DEBUG_PAYLOAD, mimetype="application/json")


@app.get("/api/v1/departments")
def departments():
    return jsonify(demo_data.DEPARTMENTS)


@app.get("/api/v1/applications")
def applications():
    return jsonify(demo_data.APPLICATIONS)


@app.get("/api/v1/applications/<ref>")
def application_detail(ref):
    item = demo_data.get_application(ref)
    if not item:
        abort(404)
    return jsonify(item)


@app.get("/api/v1/notices")
def notices():
    return jsonify(demo_data.NOTICES)


@app.post("/api/v1/applications")
def create_application():
    data = request.get_json(silent=True) or {}
    service_id = data.get("service_id", "SVC-01")
    applicant = data.get("applicant", "Sample Applicant")
    svc = demo_data.get_service(service_id) or demo_data.SERVICES[0]
    ref = demo_data.next_application_ref()
    item = {
        "reference": ref,
        "service_id": svc["id"],
        "service_name": svc["name"],
        "applicant": applicant,
        "status": "Received",
        "submitted": "2026-11-11",
        "district": "Central District",
    }
    demo_data.APPLICATIONS.append(item)
    return jsonify(item), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
