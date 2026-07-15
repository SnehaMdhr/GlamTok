import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';

// Components fetch from the Express API on mount; stub fetch with inert data
// so the test never touches the network. Note: CRA's jest config sets
// resetMocks: true, which wipes implementations of mocks created in
// beforeAll - so the stub is installed in beforeEach instead.
beforeEach(() => {
  global.fetch = jest.fn(() => Promise.resolve({
    ok: true,
    json: () => Promise.resolve({
      matrix: Array.from({ length: 7 }, () => Array(24).fill(0)),
      businesses: [],
      recommendations: [],
    }),
  }));
});

test('renders the dashboard shell', async () => {
  render(<App />);
  await act(async () => {}); // flush the stubbed data fetches
  expect(screen.getByText('GlamTok')).toBeInTheDocument();
  expect(screen.getByText('Predict')).toBeInTheDocument();
  expect(screen.getByText('Descriptive')).toBeInTheDocument();
  expect(screen.getByText('Predict Engagement')).toBeInTheDocument();
  expect(screen.getAllByText('5,331').length).toBeGreaterThan(0);
});

test('navigates from predict to the analysis sections', async () => {
  render(<App />);
  await act(async () => {}); // flush the stubbed data fetches

  await userEvent.click(screen.getByText('Predictive'));
  expect(screen.getByText('Predictive Analysis')).toBeInTheDocument();
  expect(screen.getByText('Model comparison')).toBeInTheDocument();

  await userEvent.click(screen.getByText('Prescriptive'));
  expect(screen.getByText('Prescriptive Analysis')).toBeInTheDocument();
  expect(screen.getByText('Content levers')).toBeInTheDocument();
});
