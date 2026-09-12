function queueModel(input, capacity, buffer) {
  if (!Array.isArray(input) || capacity < 0 || buffer < 0) throw new Error('Invalid queue input');
  let stored = 0, delivered = 0, spillTotal = 0;
  const out = [], spill = [], stock = [];
  const tail = capacity > 0 ? Math.ceil(buffer / capacity) + 20 : 20;
  const q = input.concat(Array(tail).fill(0));
  for (const value of q) {
    if (!Number.isFinite(value) || value < -1e-9) throw new Error('Non-finite / negative input');
    const available = stored + Math.max(0, value);
    const discharge = Math.min(capacity, available);
    const excess = Math.max(0, available - discharge - buffer);
    stored = available - discharge - excess;
    delivered += discharge; spillTotal += excess;
    out.push(discharge); spill.push(excess); stock.push(stored);
  }
  const received = input.reduce((a,b)=>a+b,0);
  return {q, out, spill, stock, received, delivered, spillTotal, remaining:stored,
          error:Math.abs(received-delivered-spillTotal-stored)};
}
if (typeof module !== 'undefined') module.exports = {queueModel};
