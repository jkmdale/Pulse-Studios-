/**
 * Pulse & Heirloom Studios — Haptic Experience
 * No external dependencies. Runs entirely offline after first load.
 *
 * iOS Safari note: navigator.vibrate is permanently blocked by Apple.
 * The visual CSS pulse is the PRIMARY experience for iPhone users.
 * Vibration is an Android-only enhancement.
 */

const canVibrate = typeof navigator !== 'undefined' && 'vibrate' in navigator;

let vibrationTimer = null;
let animationFrameId = null;
let peaks = [];
let audioDuration = 0;

// ---------------------------------------------------------------------------
// Haptic / visual pulse
// ---------------------------------------------------------------------------

function startHapticPattern(bpm) {
  const intervalMs = Math.round(60000 / bpm);
  const pulseWidth = Math.min(120, Math.round(intervalMs * 0.3));

  if (canVibrate) {
    // Android Chrome — real tactile feedback
    function pulse() {
      navigator.vibrate([pulseWidth, intervalMs - pulseWidth]);
    }
    pulse();
    vibrationTimer = setInterval(pulse, intervalMs);
  } else {
    // iOS Safari fallback — CSS keyframe animation
    const heart = document.getElementById('heart');
    if (heart) {
      document.documentElement.style.setProperty('--pulse-duration', `${intervalMs}ms`);
      heart.classList.add('pulsing');
    }
  }
}

function stopHapticPattern() {
  if (vibrationTimer !== null) {
    clearInterval(vibrationTimer);
    vibrationTimer = null;
    if (canVibrate) navigator.vibrate(0);
  }
  const heart = document.getElementById('heart');
  if (heart) heart.classList.remove('pulsing');
}

// ---------------------------------------------------------------------------
// Waveform canvas renderer
// ---------------------------------------------------------------------------

function initWaveform(peaksData) {
  peaks = peaksData || [];
  const canvas = document.getElementById('waveform');
  if (!canvas || peaks.length === 0) return;

  const ctx = canvas.getContext('2d');
  const audio = document.getElementById('lullaby-audio');

  function draw() {
    const W = canvas.width;
    const H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    // Scroll offset based on audio playback position
    let progress = 0;
    if (audio && audio.duration > 0) {
      progress = audio.currentTime / audio.duration;
    }

    const n = peaks.length;
    const scrollOffset = Math.floor(progress * n);
    const midY = H / 2;
    const maxAmp = midY * 0.85;

    // Draw filled waveform
    ctx.beginPath();
    // Top half
    for (let i = 0; i < n; i++) {
      const idx = (i + scrollOffset) % n;
      const x = (i / (n - 1)) * W;
      const y = midY - peaks[idx] * maxAmp;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    // Bottom half (mirror, reversed)
    for (let i = n - 1; i >= 0; i--) {
      const idx = (i + scrollOffset) % n;
      const x = (i / (n - 1)) * W;
      const y = midY + peaks[idx] * maxAmp;
      ctx.lineTo(x, y);
    }
    ctx.closePath();

    const gradient = ctx.createLinearGradient(0, 0, W, 0);
    gradient.addColorStop(0, 'rgba(210, 155, 135, 0.6)');
    gradient.addColorStop(0.5, 'rgba(210, 155, 135, 1.0)');
    gradient.addColorStop(1, 'rgba(210, 155, 135, 0.6)');
    ctx.fillStyle = gradient;
    ctx.fill();

    animationFrameId = requestAnimationFrame(draw);
  }

  if (animationFrameId !== null) cancelAnimationFrame(animationFrameId);
  draw();
}

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------

async function loadOrderData(orderId) {
  const res = await fetch(`/api/order/${orderId}`);
  if (!res.ok) throw new Error(`Order not found (${res.status})`);
  return res.json();
}
