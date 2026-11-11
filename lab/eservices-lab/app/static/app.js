(function () {
  // Records lookup: visitor supplies record id and API key; key is never baked in.
  var form = document.getElementById('record-form');
  if (form) {
    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      var rid = document.getElementById('record-id').value.trim();
      var key = document.getElementById('api-key').value;
      var out = document.getElementById('record-result');
      out.className = 'result';
      out.textContent = 'Looking up record…';
      try {
        var res = await fetch('/api/v1/records/' + encodeURIComponent(rid), {
          headers: { 'X-API-Key': key }
        });
        if (res.status === 401) {
          out.className = 'result error';
          out.textContent = 'Access denied (401). A valid API key is required to view this record.';
          return;
        }
        if (res.status === 404) {
          out.className = 'result error';
          out.textContent = 'Record not found (404). Check the reference and try again.';
          return;
        }
        if (!res.ok) {
          out.className = 'result error';
          out.textContent = 'Request failed (' + res.status + ').';
          return;
        }
        var data = await res.json();
        var dl = document.createElement('dl');
        dl.className = 'dl';
        var fields = [
          ['id', 'Record reference'],
          ['name', 'Name'],
          ['phone', 'Phone'],
          ['national_id', 'National ID'],
          ['pension_status', 'Pension status'],
          ['district', 'District'],
          ['programme', 'Programme'],
          ['last_updated', 'Last updated']
        ];
        out.textContent = '';
        var h = document.createElement('h3');
        h.textContent = 'Record details';
        h.style.marginTop = '0';
        out.appendChild(h);
        fields.forEach(function (f) {
          if (data[f[0]] !== undefined) {
            var dt = document.createElement('dt');
            dt.textContent = f[1];
            var dd = document.createElement('dd');
            dd.textContent = String(data[f[0]]);
            dl.appendChild(dt);
            dl.appendChild(dd);
          }
        });
        out.appendChild(dl);
      } catch (err) {
        out.className = 'result error';
        out.textContent = 'Could not complete the request.';
      }
    });
  }

  // Start a request: creates a fictional sample application via the API.
  var appForm = document.getElementById('application-form');
  if (appForm) {
    appForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      var out = document.getElementById('application-result');
      var serviceId = document.getElementById('service-id').value;
      var applicant = document.getElementById('applicant-name').value.trim() || 'Sample Applicant';
      out.className = 'result';
      out.textContent = 'Submitting request…';
      try {
        var res = await fetch('/api/v1/applications', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ service_id: serviceId, applicant: applicant })
        });
        var data = await res.json();
        if (!res.ok) {
          out.className = 'result error';
          out.textContent = 'Could not create the request.';
          return;
        }
        out.className = 'result';
        out.innerHTML = '<strong>Sample request created.</strong><br>Reference: <code>' +
          data.reference + '</code><br>Status: ' + data.status + ' (fictional).';
        // prepend to table if present
        var tbody = document.getElementById('applications-body');
        if (tbody) {
          var tr = document.createElement('tr');
          tr.innerHTML = '<td><code>' + data.reference + '</code></td>' +
            '<td>' + data.service_name + '</td>' +
            '<td>' + data.applicant + '</td>' +
            '<td class="status">' + data.status + '</td>' +
            '<td>' + data.submitted + '</td>';
          tbody.insertBefore(tr, tbody.firstChild);
        }
        appForm.reset();
      } catch (err) {
        out.className = 'result error';
        out.textContent = 'Could not complete the request.';
      }
    });
  }
})();
