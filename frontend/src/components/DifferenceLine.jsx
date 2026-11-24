import { describeDifference } from '../lib/difference';

export function DifferenceLine({ model }) {
  const { text, state } = describeDifference(model);
  return (
    <p
      className={`difference-line difference-${state.toLowerCase().replaceAll(' ', '-')}`}
      aria-live="polite"
    >
      {text}
    </p>
  );
}
