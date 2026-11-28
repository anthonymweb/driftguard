import { useEffect, useState } from 'react';

import { Icon } from '../components/Icon';
import { SheetError, SheetLoading } from '../components/StateBlocks';
import { formatDateTime, formatRate } from '../lib/format';

const AREA_ORDER = ['TLS', 'Network', 'API'];

const COLUMNS = [
  ['detections', 'Detections'],
  ['misses', 'Misses'],
  ['false_positives', 'False positives'],
  ['unmeasured_scans', 'Unmeasured scans'],
  ['down_observations', 'Down observations'],
];

function KpiCard({ label, value, note, icon, footerValue, footerLabel }) {
  return (
    <li className="kpi-card">
      <div className="kpi-body">
        <div className="kpi-top">
          <p className="engraved kpi-label">{label}</p>
          <span className="kpi-icon"><Icon name={icon} /></span>
        </div>
        <p className="kpi-value">{value}</p>
        <p className="kpi-note">{note}</p>
      </div>
      <div className="kpi-footer">
        <span className="mono">{footerValue}</span>
        <span>{footerLabel}</span>
      </div>
    </li>
  );
}

function FidelityRow({ area, row }) {
  const accuracy = formatRate(row?.detection_accuracy);
  const width = Math.max(0, Math.min(100, (row?.detection_accuracy ?? 0) * 100));

  return (
    <li className="fidelity-row">
      <div className="fidelity-row-head">
        <span className="fidelity-name">{area}</span>
        <span className="fidelity-measure mono">
          {accuracy}
          <span className="fidelity-fraction"> ({row?.detections ?? 0}/{row?.present_total ?? 0})</span>
        </span>
      </div>
      <div className="progress-track" aria-hidden="true">
        <div className="progress-fill" style={{ width: `${width}%` }} />
      </div>
      <p className="fidelity-note">
        False positives {row?.false_positives ?? 0} · unmeasured {row?.unmeasured_scans ?? 0}
        {' '}· down {row?.down_observations ?? 0}
      </p>
    </li>
  );
}

export function Evaluation({ client }) {
  const [refreshKey, setRefreshKey] = useState(0);
  const [state, setState] = useState({ data: null, loading: true, error: null });

  useEffect(() => {
    let active = true;
    setState({ data: null, loading: true, error: null });
    client.evaluation()
      .then((data) => active && setState({ data, loading: false, error: null }))
      .catch((error) => active && setState({ data: null, loading: false, error }));
    return () => { active = false; };
  }, [client, refreshKey]);

  const retry = () => setRefreshKey((key) => key + 1);

  if (state.loading) return <SheetLoading label="Scoring against the lab ground truth" />;
  if (state.error) return <SheetError message={state.error.message} onRetry={retry} />;

  const { data } = state;

  return (
    <section className="evaluation-page">
      <header className="page-head">
        <div>
          <p className="engraved">ACCURACY REPORT</p>
          <h1>Evaluation</h1>
          {data.generated_at && (
            <p className="subject-meta mono">Generated {formatDateTime(data.generated_at)}</p>
          )}
        </div>
      </header>

      {!data.available ? (
        <section className="unavailable" role="status">
          <p className="engraved">REPORT UNAVAILABLE</p>
          <p>{data.reason}</p>
          {data.duplicates?.length > 0 && (
            <p className="duplicate-list">
              Duplicate labels: <span>{data.duplicates.join(', ')}</span>
            </p>
          )}
          <p>
            Rename the duplicate labels in the lab sequence so each ground-truth scan has
            one engine scan, then regenerate the report.
          </p>
        </section>
      ) : (
        <>
          <section className="methodology-notice" aria-label="Scoring method">
            <span className="methodology-icon"><Icon name="science" /></span>
            <div>
              <h2>Decoupled scoring</h2>
              <p>
                Only the controlled lab sequence contributes to these figures. Exploratory
                console observations stay outside the calculation, and labels without a
                matching observation are unmeasured, not correct.
              </p>
            </div>
          </section>

          <ul className="kpi-grid" aria-label="Key metrics">
            <KpiCard
              label="DETECTION ACCURACY"
              value={formatRate(data.overall.detection_accuracy)}
              note="Present observations detected"
              icon="accuracy"
              footerValue={`${data.overall.detections ?? 0}/${data.overall.present_total ?? 0}`}
              footerLabel="detections / present"
            />
            <KpiCard
              label="FALSE-POSITIVE RATE"
              value={formatRate(data.overall.false_positive_rate)}
              note="Spurious findings on absent observations"
              icon="gpp_maybe"
              footerValue={`${data.overall.false_positives ?? 0}/${data.overall.absent_total ?? 0}`}
              footerLabel="false positives / absent"
            />
            <KpiCard
              label="UNMEASURED SCANS"
              value={String(data.overall.unmeasured_scans ?? 0)}
              note="Labels without a comparable observation"
              icon="help_outline"
              footerValue={`${data.overall.unmeasured_scans ?? 0} scans`}
              footerLabel="not counted as correct"
            />
            <KpiCard
              label="DOWN OBSERVATIONS"
              value={String(data.overall.down_observations ?? 0)}
              note="Targets unreachable during observation"
              icon="cloud_off"
              footerValue={`${data.overall.down_observations ?? 0} observations`}
              footerLabel="recorded, not inferred"
            />
          </ul>

          <section className="table-card">
            <div className="table-head">
              <div>
                <h2>Controlled evaluation areas</h2>
                <p>Detection results by lab observation surface.</p>
              </div>
              {data.scan_labels?.length > 0 && (
                <span className="mono-chip">{data.scan_labels.length} labelled scans</span>
              )}
            </div>
            <div className="table-scroll">
              <table className="area-table">
                <caption>Per-area accuracy</caption>
                <thead>
                  <tr>
                    <th scope="col">Area</th>
                    {COLUMNS.map(([key, label]) => <th scope="col" key={key}>{label}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {[...AREA_ORDER, ...Object.keys(data.per_area ?? {})
                    .filter((area) => !AREA_ORDER.includes(area))
                    .sort()]
                    .filter((area) => Boolean(data.per_area?.[area]))
                    .map((area) => (
                      <tr key={area}>
                        <th scope="row">{area}</th>
                        {COLUMNS.map(([key, label]) => (
                          <td key={key} data-label={label}>{String(data.per_area[area][key] ?? 0)}</td>
                        ))}
                      </tr>
                    ))}
                </tbody>
                <tfoot>
                  <tr>
                    <th scope="row">Overall</th>
                    {COLUMNS.map(([key, label]) => (
                      <td key={key} data-label={label}>{String(data.overall[key] ?? 0)}</td>
                    ))}
                  </tr>
                </tfoot>
              </table>
            </div>
          </section>

          {((data.unmeasured?.ground_truth_scans_without_engine_scan?.length ?? 0) > 0
            || (data.unmeasured?.engine_scans_without_ground_truth?.length ?? 0) > 0) && (
            <section className="unmeasured">
              <p className="engraved">UNMEASURED LABELS</p>
              {data.unmeasured.ground_truth_scans_without_engine_scan.length > 0 && (
                <p>
                  Ground-truth scans without an engine scan:{' '}
                  {data.unmeasured.ground_truth_scans_without_engine_scan.join(', ')}
                </p>
              )}
              {data.unmeasured.engine_scans_without_ground_truth.length > 0 && (
                <p>
                  Engine scans without ground truth:{' '}
                  {data.unmeasured.engine_scans_without_ground_truth.join(', ')}
                </p>
              )}
            </section>
          )}

          <div className="caveat">
            <p>
              Scored against the lab&apos;s ground truth. A label with no engine scan is
              unmeasured, not correct.
            </p>
            <p>
              Console scans are exploratory and are not scored. Accuracy requires the
              labelled lab sequence (sequence.py).
            </p>
          </div>

          <div className="lower-module">
            <article className="fidelity-panel">
              <header className="lower-head">
                <div>
                  <h2>Detection accuracy by area</h2>
                  <p>Real per-area results from the scored lab sequence.</p>
                </div>
                <span className="mono-chip">detections / present</span>
              </header>
              <ul className="fidelity-rows">
                {[...AREA_ORDER, ...Object.keys(data.per_area ?? {})
                  .filter((area) => !AREA_ORDER.includes(area))
                  .sort()]
                  .filter((area) => Boolean(data.per_area?.[area]))
                  .map((area) => (
                    <FidelityRow key={area} area={area} row={data.per_area[area]} />
                  ))}
              </ul>
            </article>

            <article className="scope-panel">
              <header className="lower-head">
                <div>
                  <h2>Measurement scope</h2>
                  <p>What this report actually covered.</p>
                </div>
                <span className="scope-icon"><Icon name="verified_user" /></span>
              </header>
              {data.generated_at && (
                <p className="scope-generated mono">Generated {formatDateTime(data.generated_at)}</p>
              )}
              <div className="scope-block">
                <p className="engraved">Unmeasured labels</p>
                {(data.unmeasured?.ground_truth_scans_without_engine_scan?.length ?? 0) > 0 && (
                  <p>
                    Ground truth without an engine scan:{' '}
                    <span className="mono">{data.unmeasured.ground_truth_scans_without_engine_scan.join(', ')}</span>
                  </p>
                )}
                {(data.unmeasured?.engine_scans_without_ground_truth?.length ?? 0) > 0 && (
                  <p>
                    Engine scan without ground truth:{' '}
                    <span className="mono">{data.unmeasured.engine_scans_without_ground_truth.join(', ')}</span>
                  </p>
                )}
                {((data.unmeasured?.ground_truth_scans_without_engine_scan?.length ?? 0) === 0
                  && (data.unmeasured?.engine_scans_without_ground_truth?.length ?? 0) === 0) && (
                  <p>No unmeasured labels in this report.</p>
                )}
              </div>
              <p className="scope-caveat">
                A label without a matching observation is unmeasured, not correct. Console
                observations are outside this report.
              </p>
            </article>
          </div>
        </>
      )}
    </section>
  );
}
