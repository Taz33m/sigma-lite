import fs from "node:fs";
import path from "node:path";

const sampleRate = 44100;
const duration = 55;
const channels = 1;
const samples = sampleRate * duration;
const data = new Int16Array(samples);

function env(t, start, end, attack = 0.02, release = 0.08) {
  if (t < start || t > end) return 0;
  const local = t - start;
  const len = end - start;
  const a = Math.min(1, local / attack);
  const r = Math.min(1, (len - local) / release);
  return Math.max(0, Math.min(a, r));
}

function sine(freq, t) {
  return Math.sin(2 * Math.PI * freq * t);
}

function tick(t, period, width, start = 0) {
  const p = ((t - start) % period + period) % period;
  if (p > width) return 0;
  const e = Math.exp(-p * 95);
  return e * (sine(2600, t) * 0.55 + sine(3900, t) * 0.25);
}

function stamp(t, at, width = 0.18) {
  const e = env(t, at, at + width, 0.006, width);
  return e * (sine(92, t) * 0.8 + sine(146, t) * 0.3);
}

function sweep(t, at, len = 0.55) {
  const e = env(t, at, at + len, 0.04, 0.18);
  const f = 420 + 1400 * Math.max(0, Math.min(1, (t - at) / len));
  return e * sine(f, t) * 0.22;
}

for (let i = 0; i < samples; i += 1) {
  const t = i / sampleRate;
  const arc = t < 10 ? 0.45 : t < 29 ? 0.72 : t < 44 ? 0.86 : 0.5;
  const fadeIn = Math.min(1, t / 3);
  const fadeOut = Math.min(1, (duration - t) / 4);
  const master = fadeIn * fadeOut;
  const pulse = (sine(51.91, t) * 0.26 + sine(103.82, t) * 0.11) * arc;
  const sub = sine(38.89, t) * 0.12 * Math.sin(Math.PI * Math.min(1, t / duration));
  const clock = tick(t, 0.58, 0.022) * (t < 10 ? 0.32 : 0.2);
  const perc = tick(t, 1.16, 0.018, 0.29) * (t > 10 && t < 44 ? 0.24 : 0.08);
  const pluck = env(t, 10, 44, 3, 6) * sine(659.25, t) * 0.045 * (0.5 + 0.5 * sine(0.25, t));
  const lift = env(t, 29, 44, 4, 4) * (sine(196, t) + sine(246.94, t) * 0.55) * 0.06;
  const events =
    stamp(t, 4.65) +
    sweep(t, 5.05) +
    stamp(t, 10.25, 0.13) +
    sweep(t, 16.25, 0.45) +
    stamp(t, 22.2, 0.12) +
    sweep(t, 28.8, 0.55) +
    stamp(t, 35.2, 0.18) +
    sweep(t, 44.25, 0.65) +
    stamp(t, 52.55, 0.32);
  const sample = (pulse + sub + clock + perc + pluck + lift + events * 0.42) * master;
  data[i] = Math.max(-1, Math.min(1, sample)) * 32767;
}

const bytesPerSample = 2;
const blockAlign = channels * bytesPerSample;
const byteRate = sampleRate * blockAlign;
const dataSize = data.length * bytesPerSample;
const buffer = Buffer.alloc(44 + dataSize);

buffer.write("RIFF", 0);
buffer.writeUInt32LE(36 + dataSize, 4);
buffer.write("WAVE", 8);
buffer.write("fmt ", 12);
buffer.writeUInt32LE(16, 16);
buffer.writeUInt16LE(1, 20);
buffer.writeUInt16LE(channels, 22);
buffer.writeUInt32LE(sampleRate, 24);
buffer.writeUInt32LE(byteRate, 28);
buffer.writeUInt16LE(blockAlign, 32);
buffer.writeUInt16LE(16, 34);
buffer.write("data", 36);
buffer.writeUInt32LE(dataSize, 40);

for (let i = 0; i < data.length; i += 1) {
  buffer.writeInt16LE(data[i], 44 + i * 2);
}

const output = path.join(process.cwd(), "assets", "blueprint-pulse.wav");
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, buffer);
console.log(`Wrote ${output}`);
