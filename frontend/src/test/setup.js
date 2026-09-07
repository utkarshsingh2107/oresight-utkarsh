import '@testing-library/jest-dom'

// jsdom does not implement ResizeObserver, which Recharts' ResponsiveContainer requires.
global.ResizeObserver = class ResizeObserver {
  observe()   {}
  unobserve() {}
  disconnect(){}
}

// Stub SVGElement methods used by Recharts
if (typeof SVGElement !== 'undefined') {
  SVGElement.prototype.getTotalLength    = () => 0
  SVGElement.prototype.getPointAtLength = () => ({ x: 0, y: 0 })
}
