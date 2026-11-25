import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { Evaluation } from './Evaluation';

const available = {
  available: true,
  generated_at: '2026-11-24T10:00:00Z',
  overall: {
    detections: 38, present_total: 40, detection_accuracy: 0.95,
    false_positives: 1, absent_total: 45, false_positive_rate: 0.0222,
    unmeasured_scans: 4, down_observations: 2,
  },
  per_area: {
    TLS: {
      detections: 18, present_total: 18, detection_accuracy: 1,
      false_positives: 0, absent_total: 20, false_positive_rate: 0,
      unmeasured_scans: 2, down_observations: 1,
    },
    Network: {
      detections: 12, present_total: 13, detection_accuracy: 0.923,
      false_positives: 1, absent_total: 15, false_positive_rate: 0.0667,
      unmeasured_scans: 1, down_observations: 1,
    },
    API: {
      detections: 8, present_total: 9, detection_accuracy: 0.889,
      false_positives: 0, absent_total: 10, false_positive_rate: 0,
      unmeasured_scans: 1, down_observations: 0,
    },
  },
  per_target: {},
  unmeasured: {
    ground_truth_scans_without_engine_scan: ['S5'],
    engine_scans_without_ground_truth: [],
  },
  scan_labels: ['S0', 'S1', 'S2', 'S3', 'S4', 'S5'],
};

describe('Evaluation', () => {
  it('shows the two readouts with numerator and denominator', async () => {
    const client = { evaluation: vi.fn().mockResolvedValue(available) };
    render(<Evaluation client={client} />);

    await screen.findByText('DETECTION ACCURACY');
    expect(screen.getByText('95.0%')).toBeTruthy();
    expect(screen.getByText(/38\/40/)).toBeTruthy();
    expect(screen.getByText('FALSE-POSITIVE RATE')).toBeTruthy();
    expect(screen.getByText('2.2%')).toBeTruthy();
    expect(screen.getByText(/1\/45/)).toBeTruthy();
  });

  it('lists areas in audited order with counts', async () => {
    const client = { evaluation: vi.fn().mockResolvedValue(available) };
    render(<Evaluation client={client} />);
    await screen.findByText('DETECTION ACCURACY');

    const areas = screen.getAllByRole('rowheader').map((cell) => cell.textContent);
    expect(areas).toEqual(['TLS', 'Network', 'API', 'Overall']);
    expect(screen.getByText(/Scored against the lab's ground truth/)).toBeTruthy();
    expect(screen.getByText(/Console scans are exploratory and are not scored/)).toBeTruthy();
  });

  it('shows no numbers when the report is unavailable', async () => {
    const client = {
      evaluation: vi.fn().mockResolvedValue({
        available: false,
        reason: 'Scan labels S1 and S2 are each recorded twice.',
        duplicates: ['S1', 'S2'],
      }),
    };
    render(<Evaluation client={client} />);

    await screen.findByText(/Scan labels S1 and S2 are each recorded twice/);
    expect(screen.getByText('S1, S2')).toBeTruthy();
    expect(screen.queryByText('95.0%')).toBeNull();
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('reports an unreachable evaluation without inventing a score', async () => {
    const client = { evaluation: vi.fn().mockRejectedValue(new Error('API unreachable at 127.0.0.1:8000. Start the backend, then retry.')) };
    render(<Evaluation client={client} />);
    await waitFor(() => expect(screen.getByRole('alert').textContent)
      .toContain('API unreachable'));
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('shows unmeasured scans and down observations as KPI cards', async () => {
    const client = { evaluation: vi.fn().mockResolvedValue(available) };
    render(<Evaluation client={client} />);

    await screen.findByText('DETECTION ACCURACY');
    expect(screen.getByText('UNMEASURED SCANS').closest('li').textContent).toContain('4');
    expect(screen.getByText('DOWN OBSERVATIONS').closest('li').textContent).toContain('2');
  });
});
