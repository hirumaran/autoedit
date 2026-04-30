import { animate, stagger } from 'animejs';

const STYLE_ID = 'talos-loader-styles';

function ensureLoaderStyles() {
  if (document.getElementById(STYLE_ID)) return;

  const style = document.createElement('style');
  style.id = STYLE_ID;
  style.textContent = `
    .talos-loader {
      --talos-bg: #050505;
      --talos-panel: #09090b;
      --talos-line: rgba(244, 224, 77, 0.34);
      --talos-line-soft: rgba(244, 224, 77, 0.12);
      --talos-gold: #f4e04d;
      --talos-text: #ededed;
      --talos-muted: #6b7280;
      position: fixed;
      inset: 0;
      width: 100vw;
      height: 100vh;
      overflow: hidden;
      background:
        radial-gradient(circle at 50% 47%, rgba(244, 224, 77, 0.13), transparent 33%),
        radial-gradient(circle at 18% 18%, rgba(255, 255, 255, 0.055), transparent 24%),
        #050505;
      color: var(--talos-text);
      z-index: 50;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      isolation: isolate;
    }

    .talos-loader::before {
      content: "";
      position: absolute;
      inset: 0;
      opacity: 0.085;
      background-image:
        linear-gradient(rgba(255,255,255,0.42) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.42) 1px, transparent 1px);
      background-size: 44px 44px;
      mask-image: radial-gradient(circle at center, black 0 42%, transparent 78%);
      pointer-events: none;
    }

    .talos-loader::after {
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.045), transparent 13%, transparent 86%, rgba(244,224,77,0.08)),
        repeating-linear-gradient(180deg, rgba(255,255,255,0.025) 0 1px, transparent 1px 4px);
      mix-blend-mode: screen;
      opacity: 0.32;
      pointer-events: none;
    }

    .talos-loader__shell {
      position: relative;
      z-index: 3;
      min-height: 100%;
      display: grid;
      place-items: center;
      padding: 104px 24px 72px;
    }

    .talos-loader__system {
      width: min(620px, 88vw);
      display: grid;
      justify-items: center;
      gap: 18px;
      transform: translateY(8px);
    }

    .talos-loader__preview {
      position: relative;
      width: clamp(190px, 22vw, 278px);
      aspect-ratio: 9 / 16;
      overflow: hidden;
      border: 1px solid rgba(244, 224, 77, 0.36);
      border-radius: 8px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.08), transparent 16%),
        radial-gradient(circle at 50% 32%, rgba(244, 224, 77, 0.18), transparent 42%),
        #070707;
      box-shadow:
        0 0 0 1px rgba(255,255,255,0.045) inset,
        0 24px 90px rgba(0,0,0,0.74),
        0 0 70px rgba(244, 224, 77, 0.13);
    }

    .talos-loader__preview::before {
      content: "";
      position: absolute;
      inset: 0;
      background-image:
        linear-gradient(rgba(255,255,255,0.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.06) 1px, transparent 1px);
      background-size: 33.333% 25%;
      opacity: 0.7;
      z-index: 1;
    }

    .talos-loader__preview::after {
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(90deg, rgba(0,0,0,0.76), transparent 18%, transparent 82%, rgba(0,0,0,0.76)),
        linear-gradient(180deg, rgba(0,0,0,0.68), transparent 20%, transparent 74%, rgba(0,0,0,0.72));
      z-index: 5;
      pointer-events: none;
    }

    .talos-loader__strip {
      position: absolute;
      left: -18%;
      width: 136%;
      height: 12.5%;
      border-block: 1px solid rgba(255,255,255,0.055);
      background:
        linear-gradient(90deg, transparent 0 6%, rgba(255,255,255,0.075) 12%, rgba(244,224,77,0.17) 44%, rgba(255,255,255,0.08) 68%, transparent 96%),
        linear-gradient(180deg, rgba(255,255,255,0.04), rgba(0,0,0,0.16));
      opacity: 0.78;
      transform: skewX(-8deg);
      animation: talos-strip-drift 3.6s cubic-bezier(.4,0,.2,1) infinite;
      z-index: 2;
    }

    .talos-loader__strip:nth-child(even) {
      animation-direction: reverse;
      opacity: 0.48;
    }

    .talos-loader__strip:nth-child(1) { top: 6%; animation-delay: -0.3s; }
    .talos-loader__strip:nth-child(2) { top: 20%; animation-delay: -1.1s; }
    .talos-loader__strip:nth-child(3) { top: 34%; animation-delay: -0.7s; }
    .talos-loader__strip:nth-child(4) { top: 48%; animation-delay: -1.8s; }
    .talos-loader__strip:nth-child(5) { top: 62%; animation-delay: -1.3s; }
    .talos-loader__strip:nth-child(6) { top: 76%; animation-delay: -2.4s; }

    .talos-loader__subject {
      position: absolute;
      inset: 22% 22% 19%;
      border-radius: 999px 999px 14px 14px;
      background:
        radial-gradient(circle at 50% 18%, rgba(237,237,237,0.78) 0 8%, transparent 8.6%),
        linear-gradient(180deg, transparent 0 19%, rgba(237,237,237,0.1) 19.5% 43%, transparent 44%),
        linear-gradient(145deg, rgba(244,224,77,0.18), rgba(255,255,255,0.035));
      border: 1px solid rgba(244,224,77,0.18);
      filter: blur(0.2px);
      opacity: 0.64;
      z-index: 3;
      animation: talos-subject-pulse 2.4s ease-in-out infinite;
    }

    .talos-loader__scan {
      position: absolute;
      left: -18%;
      right: -18%;
      height: 23%;
      top: -24%;
      background:
        linear-gradient(180deg, transparent, rgba(244,224,77,0.08) 32%, rgba(244,224,77,0.38) 50%, rgba(244,224,77,0.08) 68%, transparent);
      filter: blur(0.2px);
      transform: rotate(-6deg);
      animation: talos-scan 2.8s cubic-bezier(.45,0,.2,1) infinite;
      z-index: 4;
    }

    .talos-loader__playhead {
      position: absolute;
      top: 0;
      bottom: 0;
      width: 1px;
      left: 50%;
      background: linear-gradient(180deg, transparent, rgba(244,224,77,0.84), transparent);
      box-shadow: 0 0 18px rgba(244,224,77,0.42);
      opacity: 0.74;
      z-index: 6;
      animation: talos-playhead 3.8s ease-in-out infinite;
    }

    .talos-loader__corner {
      position: absolute;
      width: 26px;
      height: 26px;
      z-index: 7;
      border-color: rgba(244, 224, 77, 0.86);
      filter: drop-shadow(0 0 8px rgba(244,224,77,0.24));
    }

    .talos-loader__corner--tl { top: 14px; left: 14px; border-top: 1px solid; border-left: 1px solid; }
    .talos-loader__corner--tr { top: 14px; right: 14px; border-top: 1px solid; border-right: 1px solid; }
    .talos-loader__corner--bl { bottom: 14px; left: 14px; border-bottom: 1px solid; border-left: 1px solid; }
    .talos-loader__corner--br { bottom: 14px; right: 14px; border-bottom: 1px solid; border-right: 1px solid; }

    .talos-loader__status {
      width: min(560px, 84vw);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 11px;
      letter-spacing: 0.18em;
      color: rgba(237,237,237,0.88);
      text-transform: uppercase;
    }

    .talos-loader__status strong {
      color: var(--talos-gold);
      font-weight: 700;
    }

    .talos-loader__timeline {
      position: relative;
      width: min(560px, 84vw);
      height: 54px;
      display: grid;
      grid-template-columns: 1.3fr 0.55fr 0.95fr 0.7fr 1.15fr;
      gap: 7px;
      align-items: center;
      padding: 0 1px;
    }

    .talos-loader__clip {
      position: relative;
      height: 26px;
      overflow: hidden;
      border: 1px solid rgba(244,224,77,0.18);
      border-radius: 4px;
      background:
        linear-gradient(90deg, rgba(244,224,77,0.32), rgba(255,255,255,0.09), rgba(244,224,77,0.14)),
        #0b0b0b;
      box-shadow: 0 0 18px rgba(244,224,77,0.055) inset;
    }

    .talos-loader__clip::after {
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(90deg, transparent, rgba(255,255,255,0.18), transparent);
      transform: translateX(-120%);
      animation: talos-clip-shine 2.9s ease-in-out infinite;
      animation-delay: inherit;
    }

    .talos-loader__timeline-head {
      position: absolute;
      top: 2px;
      bottom: 2px;
      width: 1px;
      left: 0;
      background: var(--talos-gold);
      box-shadow: 0 0 18px rgba(244,224,77,0.6);
      animation: talos-timeline-head 3.1s linear infinite;
    }

    .talos-loader__wave {
      width: min(360px, 74vw);
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
    }

    .talos-loader__bar {
      width: 3px;
      height: var(--h);
      min-height: 7px;
      border-radius: 999px;
      background: linear-gradient(180deg, rgba(244,224,77,0.95), rgba(244,224,77,0.16));
      opacity: 0.78;
      transform-origin: center;
      animation: talos-wave 1.05s ease-in-out infinite;
      animation-delay: var(--d);
    }

    .talos-loader__meter {
      position: fixed;
      right: 32px;
      bottom: 30px;
      z-index: 4;
      display: grid;
      gap: 6px;
      justify-items: end;
      font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 10px;
      letter-spacing: 0.24em;
      color: rgba(107,114,128,0.95);
      text-transform: uppercase;
    }

    .talos-loader__meter-line {
      width: 126px;
      height: 1px;
      overflow: hidden;
      background: rgba(255,255,255,0.08);
    }

    .talos-loader__meter-line::before {
      content: "";
      display: block;
      width: 38%;
      height: 100%;
      background: var(--talos-gold);
      box-shadow: 0 0 16px rgba(244,224,77,0.72);
      animation: talos-meter 1.7s ease-in-out infinite;
    }

    .talos-loader__flash {
      position: absolute;
      inset: -20%;
      z-index: 12;
      pointer-events: none;
      background: radial-gradient(circle at center, rgba(244,224,77,0.82), rgba(244,224,77,0.08) 24%, transparent 52%);
      opacity: 0;
      transform: scale(0.45);
    }

    @keyframes talos-strip-drift {
      0%, 100% { transform: translateX(-10%) skewX(-8deg); }
      50% { transform: translateX(10%) skewX(-8deg); }
    }

    @keyframes talos-subject-pulse {
      0%, 100% { opacity: 0.48; transform: scale(0.985); }
      50% { opacity: 0.72; transform: scale(1.015); }
    }

    @keyframes talos-scan {
      0% { transform: translateY(0) rotate(-6deg); opacity: 0; }
      12% { opacity: 1; }
      76% { opacity: 1; }
      100% { transform: translateY(620%) rotate(-6deg); opacity: 0; }
    }

    @keyframes talos-playhead {
      0%, 100% { transform: translateX(-74px); opacity: 0.35; }
      50% { transform: translateX(74px); opacity: 0.86; }
    }

    @keyframes talos-clip-shine {
      0%, 25% { transform: translateX(-120%); }
      70%, 100% { transform: translateX(120%); }
    }

    @keyframes talos-timeline-head {
      from { left: 0; }
      to { left: 100%; }
    }

    @keyframes talos-wave {
      0%, 100% { transform: scaleY(0.55); opacity: 0.38; }
      50% { transform: scaleY(1.18); opacity: 0.95; }
    }

    @keyframes talos-meter {
      0%, 100% { transform: translateX(-105%); }
      50% { transform: translateX(265%); }
    }

    @media (max-width: 640px) {
      .talos-loader__shell {
        padding-top: 88px;
      }

      .talos-loader__status {
        font-size: 9px;
        letter-spacing: 0.12em;
      }

      .talos-loader__meter {
        right: 20px;
        bottom: 20px;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .talos-loader *,
      .talos-loader *::before,
      .talos-loader *::after {
        animation-duration: 0.001ms !important;
        animation-iteration-count: 1 !important;
      }
    }
  `;

  document.head.appendChild(style);
}

function buildWaveBars() {
  const heights = [11, 24, 16, 30, 18, 34, 22, 38, 17, 29, 14, 33, 20, 36, 18, 27, 12, 31, 16, 25, 10, 22];
  return heights.map((height, index) => {
    const bar = document.createElement('span');
    bar.className = 'talos-loader__bar';
    bar.style.setProperty('--h', `${height}px`);
    bar.style.setProperty('--d', `${index * -0.055}s`);
    return bar;
  });
}

export function createAtomLoader(container) {
  ensureLoaderStyles();

  const root = document.createElement('div');
  root.className = 'talos-loader';
  root.setAttribute('role', 'status');
  root.setAttribute('aria-live', 'polite');
  root.setAttribute('aria-label', 'Processing video');

  const shell = document.createElement('div');
  shell.className = 'talos-loader__shell';

  const system = document.createElement('div');
  system.className = 'talos-loader__system';

  const preview = document.createElement('div');
  preview.className = 'talos-loader__preview';
  for (let i = 0; i < 6; i++) {
    const strip = document.createElement('span');
    strip.className = 'talos-loader__strip';
    preview.appendChild(strip);
  }

  const subject = document.createElement('span');
  subject.className = 'talos-loader__subject';
  const scan = document.createElement('span');
  scan.className = 'talos-loader__scan';
  const playhead = document.createElement('span');
  playhead.className = 'talos-loader__playhead';
  preview.append(subject, scan, playhead);

  ['tl', 'tr', 'bl', 'br'].forEach(pos => {
    const corner = document.createElement('span');
    corner.className = `talos-loader__corner talos-loader__corner--${pos}`;
    preview.appendChild(corner);
  });

  const status = document.createElement('div');
  status.className = 'talos-loader__status';
  status.innerHTML = '<span>Rendering <strong>cut</strong></span><span>AI pass 04</span>';

  const timeline = document.createElement('div');
  timeline.className = 'talos-loader__timeline';
  for (let i = 0; i < 5; i++) {
    const clip = document.createElement('span');
    clip.className = 'talos-loader__clip';
    clip.style.animationDelay = `${i * 0.18}s`;
    timeline.appendChild(clip);
  }
  const timelineHead = document.createElement('span');
  timelineHead.className = 'talos-loader__timeline-head';
  timeline.appendChild(timelineHead);

  const wave = document.createElement('div');
  wave.className = 'talos-loader__wave';
  buildWaveBars().forEach(bar => wave.appendChild(bar));

  system.append(preview, status, timeline, wave);
  shell.appendChild(system);

  const meter = document.createElement('div');
  meter.className = 'talos-loader__meter';
  meter.innerHTML = '<span>Compositing</span><span class="talos-loader__meter-line"></span>';

  const flash = document.createElement('span');
  flash.className = 'talos-loader__flash';

  root.append(shell, meter, flash);
  container.appendChild(root);

  const intro = animate(system, {
    opacity: [0, 1],
    translateY: [18, 0],
    scale: [0.98, 1],
    duration: 720,
    ease: 'easeOutCubic',
  });

  const pulse = animate(preview, {
    boxShadow: [
      '0 0 0 1px rgba(255,255,255,0.045) inset, 0 24px 90px rgba(0,0,0,0.74), 0 0 54px rgba(244,224,77,0.09)',
      '0 0 0 1px rgba(255,255,255,0.065) inset, 0 24px 90px rgba(0,0,0,0.74), 0 0 92px rgba(244,224,77,0.19)',
      '0 0 0 1px rgba(255,255,255,0.045) inset, 0 24px 90px rgba(0,0,0,0.74), 0 0 54px rgba(244,224,77,0.09)',
    ],
    duration: 2600,
    loop: true,
    ease: 'easeInOutSine',
  });

  const state = { finished: false };

  const instance = {
    root,
    complete() {
      if (state.finished) return;
      state.finished = true;
      intro.pause();
      pulse.pause();

      animate(flash, {
        opacity: [0, 0.65, 0],
        scale: [0.45, 1.35],
        duration: 620,
        ease: 'easeOutExpo',
      });

      animate(system, {
        opacity: [1, 0],
        translateY: [0, -18],
        scale: [1, 1.03],
        duration: 420,
        ease: 'easeInCubic',
      });

      animate(root, {
        opacity: [1, 0],
        duration: 560,
        delay: 220,
        ease: 'easeOutCubic',
        onComplete: () => instance.destroy(),
      });
    },
    destroy() {
      if (intro) intro.pause();
      if (pulse) pulse.pause();
      if (root && root.parentNode) root.parentNode.removeChild(root);
    },
  };

  return instance;
}

export function createLoader(container, size = 'compact') {
  ensureLoaderStyles();

  const dim = size === 'compact' ? 80 : 120;
  const ring = document.createElement('div');
  ring.style.cssText = [
    `width:${dim}px`,
    `height:${dim}px`,
    'position:relative',
    'display:grid',
    'place-items:center',
  ].join(';');

  const core = document.createElement('div');
  core.style.cssText = [
    `width:${Math.round(dim * 0.62)}px`,
    `height:${Math.round(dim * 0.62)}px`,
    'border-radius:8px',
    'border:1px solid rgba(244,224,77,0.34)',
    'background:linear-gradient(135deg, rgba(244,224,77,0.16), rgba(255,255,255,0.03))',
    'box-shadow:0 0 32px rgba(244,224,77,0.12)',
  ].join(';');

  const sweep = document.createElement('span');
  sweep.style.cssText = [
    'position:absolute',
    'inset:0',
    'border-radius:50%',
    'border:1px solid rgba(244,224,77,0.16)',
    'border-top-color:#f4e04d',
    'filter:drop-shadow(0 0 10px rgba(244,224,77,0.35))',
  ].join(';');

  const bars = document.createElement('div');
  bars.style.cssText = [
    'position:absolute',
    'display:flex',
    'align-items:center',
    'gap:3px',
  ].join(';');
  buildWaveBars().slice(4, 14).forEach(bar => bars.appendChild(bar));

  ring.append(core, sweep, bars);
  container.appendChild(ring);

  const spin = animate(sweep, {
    rotate: 360,
    duration: 1200,
    loop: true,
    ease: 'linear',
  });

  const breathe = animate(core, {
    scale: [0.96, 1.04, 0.96],
    duration: 1600,
    loop: true,
    ease: 'easeInOutSine',
  });

  return {
    svg: ring,
    anim: {
      pause() {
        spin.pause();
        breathe.pause();
      },
    },
  };
}

export function destroyLoader(instance) {
  if (!instance) return;
  if (instance.destroy) {
    instance.destroy();
    return;
  }
  if (instance.anim) instance.anim.pause();
  if (instance.svg && instance.svg.parentNode) instance.svg.parentNode.removeChild(instance.svg);
}
