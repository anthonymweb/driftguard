export const SCOPE_OPTIONS = [
  ['tls', 'TLS'],
  ['network', 'Network'],
  ['http_api', 'API'],
];

export function emptyTargetForm() {
  return {
    name: '',
    address: '',
    target_type: 'web',
    authorization_status: 'pending',
    authorized_by: '',
    authorized_at: '',
    authorization_basis: '',
    approved_scope: [],
    approved_ports: [],
    discovery_enabled: false,
    discovery_wordlist: '',
    status: 'active',
  };
}

export function parsePorts(value) {
  const tokens = String(value ?? '').split(/[\s,]+/).filter(Boolean);
  const ports = [];
  for (const token of tokens) {
    if (!/^\d+$/.test(token)) {
      return { ports: [], error: `“${token}” is not a port number.` };
    }
    const port = Number(token);
    if (port < 1 || port > 65535) {
      return { ports: [], error: `Port ${port} is outside 1–65535.` };
    }
    ports.push(port);
  }
  return { ports: [...new Set(ports)].sort((a, b) => a - b), error: null };
}

export function validateTargetForm(form) {
  const errors = {};
  if (!form.name.trim()) errors.name = 'Enter a target name.';
  if (!form.address.trim()) {
    errors.address = 'Enter an address, for example https://127.0.0.1:8443.';
  }
  if (!['web', 'api', 'host'].includes(form.target_type)) {
    errors.target_type = 'Choose a target type.';
  }
  if (form.authorization_status === 'authorized') {
    if (!form.authorized_by.trim()) {
      errors.authorized_by = 'Record who authorised this assessment.';
    }
    if (!form.authorized_at) {
      errors.authorized_at = 'Record when authorisation was given.';
    }
    if (!form.authorization_basis.trim()) {
      errors.authorization_basis = 'Record the basis for authorisation.';
    }
    if (form.approved_scope.length === 0) {
      errors.approved_scope = 'Select at least one approved area.';
    }
    if (form.approved_ports.length === 0) {
      errors.approved_ports = 'Add at least one approved port.';
    }
  }
  if (form.discovery_enabled && !form.discovery_wordlist.trim()) {
    errors.discovery_wordlist = 'Add a wordlist path for discovery.';
  }
  return errors;
}

export function toTargetPayload(form) {
  const authorized = form.authorization_status === 'authorized';
  return {
    name: form.name.trim(),
    address: form.address.trim(),
    target_type: form.target_type,
    authorization_status: form.authorization_status,
    authorized_by: authorized ? form.authorized_by.trim() : null,
    authorized_at: authorized
      ? new Date(`${form.authorized_at}T00:00:00Z`).toISOString()
      : null,
    authorization_basis: authorized ? form.authorization_basis.trim() : null,
    approved_scope: [...form.approved_scope],
    approved_ports: [...form.approved_ports],
    discovery_enabled: form.discovery_enabled,
    discovery_wordlist: form.discovery_enabled
      ? form.discovery_wordlist.trim()
      : null,
    status: form.status,
  };
}
