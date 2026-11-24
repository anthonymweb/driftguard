import { formatDate, formatPorts, formatScope } from '../lib/format';

export function AuthorisationStamp({ target, compact = false }) {
  if (target.authorization_status !== 'authorized') {
    return (
      <div className="stamp is-pending" data-compact={compact || undefined}>
        <p className="engraved">AUTHORISATION</p>
        <p className="stamp-state">PENDING — scanning refused</p>
        <p className="stamp-line">No authorisation record is stored for this target.</p>
      </div>
    );
  }

  return (
    <div className="stamp" data-compact={compact || undefined}>
      <p className="engraved">AUTHORISATION</p>
      <p className="stamp-state">AUTHORIZED</p>
      <p className="stamp-line">
        <strong>{target.authorized_by}</strong> ·{' '}
        <span>{formatDate(target.authorized_at)}</span>
      </p>
      <p className="stamp-line">{target.authorization_basis}</p>
      <p className="stamp-line mono">
        SCOPE {formatScope(target.approved_scope)} · PORTS {formatPorts(target.approved_ports)}
      </p>
    </div>
  );
}
