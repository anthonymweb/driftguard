import { useEffect, useState } from 'react';

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

function Readout({ label, value, numerator, denominator }) {
  return (
    <div className="readout">
      <p className="engraved">{label}</p>
      <p className="readout-value mono">{value}</p>
      <p className="readout-fraction mono">{numerator}/{denominator}</p>
    </div>
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
          <div className="readouts">
            <Readout
              label="DETECTION ACCURACY"
              value={formatRate(data.overall.detection_accuracy)}
              numerator={data.overall.detections}
              denominator={data.overall.present_total}
            />
            <Readout
              label="FALSE-POSITIVE RATE"
              value={formatRate(data.overall.false_positive_rate)}
              numerator={data.overall.false_positives}
              denominator={data.overall.absent_total}
            />
          </div>

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
                    {COLUMNS.map(([key]) => (
                      <td key={key}>{String(data.per_area[area][key] ?? 0)}</td>
                    ))}
                  </tr>
                ))}
            </tbody>
            <tfoot>
              <tr>
                <th scope="row">Overall</th>
                {COLUMNS.map(([key]) => (
                  <td key={key}>{String(data.overall[key] ?? 0)}</td>
                ))}
              </tr>
            </tfoot>
          </table>

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
        </>
      )}
    </section>
  );
}
