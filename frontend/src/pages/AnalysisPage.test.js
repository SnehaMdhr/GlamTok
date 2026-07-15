import { render, screen } from '@testing-library/react';
import AnalysisPage from './AnalysisPage';

test('analysis page renders descriptive content by default', () => {
  render(<AnalysisPage />);
  expect(screen.getByText('Total posts')).toBeInTheDocument();
});

test('analysis page renders the section matching the tab prop', () => {
  const { rerender } = render(<AnalysisPage tab="predictive" />);
  expect(screen.getByText('Model comparison')).toBeInTheDocument();

  rerender(<AnalysisPage tab="prescriptive" />);
  expect(screen.getByText('Content levers')).toBeInTheDocument();
});
