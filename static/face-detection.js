import { FilesetResolver, FaceDetector } from '/static/vendor/mediapipe/vision_bundle.mjs';

let detector = null;
let running = false;
let rafId = null;
let lastRun = 0;
const TARGET_FPS = 12;
const FRAME_MS = 1000 / TARGET_FPS;

async function init() {
  if (detector) return detector;
  const fileset = await FilesetResolver.forVisionTasks('/static/vendor/mediapipe');
  const modelBytes = await fetch('/static/vendor/mediapipe/blaze_face_short_range.tflite')
    .then(r => r.arrayBuffer())
    .then(b => new Uint8Array(b));
  detector = await FaceDetector.createFromModelBuffer(fileset, modelBytes);
  await detector.setOptions({ runningMode: 'VIDEO', minDetectionConfidence: 0.4 });
  return detector;
}

function pickLargest(detections) {
  if (!detections || !detections.length) return null;
  let best = null, bestArea = 0;
  for (const d of detections) {
    const b = d.boundingBox;
    const area = b.width * b.height;
    if (area > bestArea) { bestArea = area; best = d; }
  }
  return best;
}

function render(detection, video) {
  const overlay = document.getElementById('faceOverlay');
  const bbox = document.getElementById('faceBbox');
  const label = document.getElementById('faceLabel');
  const badge = document.getElementById('liveBadge');
  const btnCapture = document.getElementById('btnCapture');

  if (!detection) {
    bbox.classList.add('hidden');
    overlay.classList.add('searching');
    overlay.classList.remove('low-conf');
    badge.textContent = 'PROCURANDO';
    if (btnCapture) btnCapture.disabled = true;
    return;
  }

  const b = detection.boundingBox;
  const conf = detection.categories?.[0]?.score || 0;
  const lowConf = conf < 0.6;

  const vw = video.videoWidth || 640;
  const vh = video.videoHeight || 480;
  const rect = video.getBoundingClientRect();
  const scaleX = rect.width / vw;
  const scaleY = rect.height / vh;

  bbox.classList.remove('hidden');
  overlay.classList.remove('searching');
  overlay.classList.toggle('low-conf', lowConf);
  bbox.style.left = `${b.originX * scaleX}px`;
  bbox.style.top = `${b.originY * scaleY}px`;
  bbox.style.width = `${b.width * scaleX}px`;
  bbox.style.height = `${b.height * scaleY}px`;
  label.textContent = lowConf ? 'FACE BAIXA QUALIDADE' : `FACE ${Math.round(conf * 100)}%`;
  badge.textContent = 'DETECTANDO';
  if (btnCapture) btnCapture.disabled = lowConf;
}

async function loop(video) {
  if (!running) return;
  const now = performance.now();
  if (now - lastRun >= FRAME_MS && video.readyState >= 2) {
    lastRun = now;
    try {
      const res = detector.detectForVideo(video, now);
      render(pickLargest(res.detections), video);
    } catch (e) { console.warn('[face-detect] frame error', e); }
  }
  rafId = requestAnimationFrame(() => loop(video));
}

export async function start() {
  if (running) return;
  try {
    await init();
  } catch (e) {
    console.warn('[face-detect] init failed', e);
    return;
  }
  const video = document.getElementById('webcam');
  if (!video) return;
  running = true;
  lastRun = 0;
  loop(video);
}

export function stop() {
  running = false;
  if (rafId) cancelAnimationFrame(rafId);
  const btnCapture = document.getElementById('btnCapture');
  if (btnCapture) btnCapture.disabled = false;
  const bbox = document.getElementById('faceBbox');
  if (bbox) bbox.classList.add('hidden');
}

window.__faceDetect = { start, stop };
