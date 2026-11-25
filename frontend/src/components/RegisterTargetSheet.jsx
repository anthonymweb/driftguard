import { useState } from 'react';

import {
  SCOPE_OPTIONS,
  emptyTargetForm,
  parsePorts,
  toTargetPayload,
  validateTargetForm,
} from '../lib/target-form';

export function RegisterTargetSheet({ onSubmit, onClose, busy = false, error = null }) {
  const [form, setForm] = useState(emptyTargetForm);
  const [portsText, setPortsText] = useState('');
  const [errors, setErrors] = useState({});

  const update = (patch) => setForm((current) => ({ ...current, ...patch }));

  function toggleScope(scope) {
    setForm((current) => ({
      ...current,
      approved_scope: current.approved_scope.includes(scope)
        ? current.approved_scope.filter((item) => item !== scope)
        : [...current.approved_scope, scope],
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const parsed = parsePorts(portsText);
    const candidate = { ...form, approved_ports: parsed.ports };
    const nextErrors = validateTargetForm(candidate);
    if (parsed.error) nextErrors.approved_ports = parsed.error;
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    await onSubmit(toTargetPayload(candidate));
  }

  return (
    <div className="sheet-backdrop is-drawer">
      <section
        className="register-sheet sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="register-title"
      >
        <header className="register-head">
          <div>
            <p className="engraved">TARGET REGISTER</p>
            <h1 id="register-title">Register target</h1>
          </div>
          <button type="button" className="text-button" onClick={onClose} disabled={busy}>
            Close
          </button>
        </header>

        <form onSubmit={handleSubmit} noValidate>
          <fieldset>
            <legend className="engraved">Identity</legend>
            <label htmlFor="target-name">Name</label>
            <input
              id="target-name"
              value={form.name}
              onChange={(event) => update({ name: event.target.value })}
              aria-invalid={Boolean(errors.name)}
              aria-describedby={errors.name ? 'target-name-error' : undefined}
            />
            {errors.name && <p id="target-name-error" className="field-error">{errors.name}</p>}

            <label htmlFor="target-address">Address</label>
            <input
              id="target-address"
              value={form.address}
              onChange={(event) => update({ address: event.target.value })}
              aria-invalid={Boolean(errors.address)}
              aria-describedby={errors.address ? 'target-address-error' : undefined}
            />
            {errors.address && <p id="target-address-error" className="field-error">{errors.address}</p>}

            <label htmlFor="target-type">Type</label>
            <select
              id="target-type"
              value={form.target_type}
              onChange={(event) => update({ target_type: event.target.value })}
            >
              <option value="web">web</option>
              <option value="api">api</option>
              <option value="host">host</option>
            </select>
          </fieldset>

          <fieldset>
            <legend className="engraved">Authorisation</legend>
            <label>
              <input
                type="radio"
                name="authorization_status"
                value="pending"
                checked={form.authorization_status === 'pending'}
                onChange={() => update({ authorization_status: 'pending' })}
              />
              Pending — inventory only, scanning refused
            </label>
            <label>
              <input
                type="radio"
                name="authorization_status"
                value="authorized"
                checked={form.authorization_status === 'authorized'}
                onChange={() => update({ authorization_status: 'authorized' })}
              />
              Authorized
            </label>

            {form.authorization_status === 'authorized' && (
              <>
                <label htmlFor="authorized-by">Authorized by</label>
                <input
                  id="authorized-by"
                  value={form.authorized_by}
                  onChange={(event) => update({ authorized_by: event.target.value })}
                />
                {errors.authorized_by && <p className="field-error">{errors.authorized_by}</p>}

                <label htmlFor="authorized-at">Authorized at</label>
                <input
                  id="authorized-at"
                  type="date"
                  value={form.authorized_at}
                  onChange={(event) => update({ authorized_at: event.target.value })}
                />
                {errors.authorized_at && <p className="field-error">{errors.authorized_at}</p>}

                <label htmlFor="authorization-basis">Basis</label>
                <input
                  id="authorization-basis"
                  value={form.authorization_basis}
                  onChange={(event) => update({ authorization_basis: event.target.value })}
                />
                {errors.authorization_basis && <p className="field-error">{errors.authorization_basis}</p>}
              </>
            )}
          </fieldset>

          <fieldset>
            <legend className="engraved">Scope</legend>
            {SCOPE_OPTIONS.map(([value, label]) => (
              <label key={value}>
                <input
                  type="checkbox"
                  checked={form.approved_scope.includes(value)}
                  onChange={() => toggleScope(value)}
                />
                {label}
              </label>
            ))}
            {errors.approved_scope && <p className="field-error">{errors.approved_scope}</p>}

            <label htmlFor="approved-ports">Approved ports</label>
            <input
              id="approved-ports"
              placeholder="8443, 8080"
              value={portsText}
              onChange={(event) => setPortsText(event.target.value)}
            />
            {errors.approved_ports && <p className="field-error">{errors.approved_ports}</p>}

            <label>
              <input
                type="checkbox"
                checked={form.discovery_enabled}
                onChange={(event) => update({ discovery_enabled: event.target.checked })}
              />
              Discovery enabled
            </label>
            {form.discovery_enabled && (
              <>
                <label htmlFor="discovery-wordlist">Discovery wordlist</label>
                <input
                  id="discovery-wordlist"
                  value={form.discovery_wordlist}
                  onChange={(event) => update({ discovery_wordlist: event.target.value })}
                />
                {errors.discovery_wordlist && <p className="field-error">{errors.discovery_wordlist}</p>}
              </>
            )}
          </fieldset>

          {error && <p className="form-error" role="alert">{error}</p>}

          <div className="register-actions">
            <button type="submit" className="primary-button" disabled={busy}>
              {busy ? 'Registering…' : 'Register target'}
            </button>
            <button type="button" className="secondary-button" onClick={onClose} disabled={busy}>
              Cancel
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
