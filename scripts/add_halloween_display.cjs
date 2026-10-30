// Add only center-display RGB to the existing show; no exterior recomposition.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const source = path.resolve(__dirname, '../LightShow/ponzoo-this-is-halloween');
const target = source + '-display-rgb';
const input = fs.readFileSync(source + '.fseq');
const wav = fs.readFileSync(source + '.wav');
const offset = input.readUInt16LE(4), channels = input.readUInt32LE(10);
const frames = input.readUInt32LE(14), step = input[18];
assert.equal(input.toString('ascii', 0, 4), 'PSEQ');
assert.equal(input[7], 2); assert.equal(input[20], 0);
assert.equal(input[21], 0); assert.equal(input[22], 0);
assert.equal(channels, 48); assert.equal(input.length, offset + channels * frames);
assert.equal(wav.toString('ascii', 0, 4), 'RIFF');
assert.equal(wav.toString('ascii', 8, 12), 'WAVE');
let format, audio;
for (let p = 12; p + 8 <= wav.length;) {
  const id = wav.toString('ascii', p, p + 4), size = wav.readUInt32LE(p + 4);
  assert(p + 8 + size <= wav.length);
  if (id === 'fmt ') format = wav.subarray(p + 8, p + 8 + size);
  if (id === 'data') audio = wav.subarray(p + 8, p + 8 + size);
  p += 8 + size + (size % 2);
}
assert(format && audio); assert.equal(format.readUInt16LE(0), 1);
assert.equal(format.readUInt16LE(14), 16);
const rate = format.readUInt32LE(4), block = format.readUInt16LE(12);
const tracks = format.readUInt16LE(2);
assert.equal(rate, 44100); assert.equal(block, tracks * 2);
const duration = frames * step / 1000;
assert(Math.abs(audio.length / block / rate - duration) <= step / 1000);
const energy = Array.from({length: frames}, (_, f) => {
  const start = Math.floor(f * step / 1000 * rate);
  const end = Math.min(audio.length / block, Math.floor((f + 1) * step / 1000 * rate));
  let sum = 0;
  for (let i = start; i < end; i++) for (let c = 0; c < tracks; c++) {
    const x = audio.readInt16LE(i * block + c * 2) / 32768;
    sum += x * x;
  }
  return Math.sqrt(sum / Math.max(1, (end - start) * tracks));
});
const reference = [...energy].sort((a,b) => a-b)[Math.floor(frames * .95)] || 1;
const output = Buffer.alloc(offset + frames * 200);
input.copy(output, 0, 0, offset); // retain metadata and timing
output.writeUInt32LE(200, 10);
const palette = [[255, 55, 0], [135, 0, 255], [35, 255, 0], [190, 0, 230]];
let envelope = 0;
for (let f = 0; f < frames; f++) {
  const base = offset + f * 200, t = f * step / 1000;
  input.copy(output, base, offset + f * channels, offset + (f + 1) * channels);
  const level = Math.min(1, energy[f] / reference);
  envelope += (level - envelope) * (level > envelope ? .4 : .09);
  const position = t / 4, phase = position % 1;
  const mix = phase * phase * (3 - 2 * phase);
  const a = palette[Math.floor(position) % palette.length];
  const b = palette[(Math.floor(position) + 1) % palette.length];
  const fade = Math.max(0, Math.min(1, t / 1.2, (duration - step / 1000 - t) / 2));
  const value = (.12 + .68 * envelope) * fade;
  for (let c = 0; c < 3; c++) output[base + 175 + c] = Math.round((a[c] * (1-mix) + b[c] * mix) * value);
}
// Tesla validator format/length checks, plus complete payload preservation.
assert([48,200].includes(output.readUInt32LE(10)));
assert(offset >= 24 && frames >= 1 && step >= 15 && step <= 100);
assert(duration <= 14400 && output[20] === 0 && output[7] === 2);
assert([0,2].includes(output[6]));
let coloredFrames = 0;
for (let f = 0; f < frames; f++) {
  const base = offset + f * 200;
  assert(input.subarray(offset + f * 48, offset + (f + 1) * 48).equals(output.subarray(base, base + 48)));
  for (let c = 48; c < 200; c++) if (c < 175 || c > 177) assert.equal(output[base+c], 0);
  if (output.subarray(base+175,base+178).some(v => v > 0)) coloredFrames++;
}
assert(coloredFrames > frames * .9);
fs.writeFileSync(target + '.fseq', output, {flag: 'wx'});
fs.copyFileSync(source + '.wav', target + '.wav', fs.constants.COPYFILE_EXCL);
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
assert.equal(hash(wav), hash(fs.readFileSync(target + '.wav')));
assert(fs.readFileSync(target + '.fseq').equals(output));
const report = {source, target, frames, step_ms: step, duration_s: duration, channels: 200,
  display_channels: [176,177,178], coloredFrames, original_channels_preserved: true,
  audio_sha256: hash(wav), fseq_sha256: hash(output), vehicle_tested: false};
fs.writeFileSync(target + '.validation.json', JSON.stringify(report, null, 2), {flag:'wx'});
console.log(JSON.stringify(report, null, 2));
