// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// jsdom lacks ResizeObserver - recharts' ResponsiveContainer needs it.
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
if (!global.ResizeObserver) global.ResizeObserver = ResizeObserverMock;

// jsdom lacks matchMedia - used by responsive helpers.
if (!window.matchMedia) {
  window.matchMedia = query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
}
