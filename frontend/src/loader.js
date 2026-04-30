import { animate, stagger } from 'animejs';

/* ─── Ramanujan's 2nd approximation for ellipse circumference ───
   π × ( 3(a+b) − √( (3a+b)(a+3b) ) )
   Let: m = a+b   then expression becomes  π × ( 3m − √( (3a+b)(a+3b) ) )   */
function ellipseLen(rx, ry) {
  const a = rx;
  const b = ry;
  const A = 3 * a + b;
  const B = a + 3 * b;
  return Math.PI * ( (a + b) * 3 - Math.sqrt(A * B) );
}

const activeInstances = new Set();

export function createLoader(container, size = 'full') {
  const dim       = size === 'compact' ? 80 : 280;
  const r         = dim / 2 - 12;          // sphere radius
  const cx        = dim / 2;
  const cy        = dim / 2;
  const tilt      = 0.35;
  const latCount  = 8;
  const meridians = 10;

  const STROKE   = 'rgba(168, 196, 232, 0.45)';
  const BG       = '#080810';

  /* ── Root (background + sphere + text) ── */
  const root = document.createElement('div');
  root.style.display        = 'flex';
  root.style.flexDirection  = 'column';
  root.style.alignItems     = 'center';
  root.style.gap            = size === 'compact' ? '8px' : '12px';

  /* ── Sphere wrapper (gets the pulse) ── */
  const sphereWrap = document.createElement('div');
  sphereWrap.style.width  = dim + 'px';
  sphereWrap.style.height = dim + 'px';
  sphereWrap.style.background =
    size === 'compact'
      ? 'none'
      : `radial-gradient(ellipse at center, #0d1a2e 0%, ${BG} 65%)`;

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', `0 0 ${dim} ${dim}`);
  svg.setAttribute('width',  dim);
  svg.setAttribute('height', dim);
  svg.style.display   = 'block';
  svg.style.overflow  = 'visible';
  svg.setAttribute('stroke-linecap', 'round');

  const elements = [];          // { el, len }

  /* ── Meridians: full ellipses rotated around the vertical axis ── */
  for (let i = 0; i < meridians; i++) {
    const rot = (180 / meridians) * i;
    const el  = document.createElementNS('http://www.w3.org/2000/svg', 'ellipse');
    el.setAttribute('cx', cx);
    el.setAttribute('cy', cy);
    el.setAttribute('rx', r);
    el.setAttribute('ry', r * tilt);
    el.setAttribute('fill', 'none');
    el.setAttribute('stroke', STROKE);
    el.setAttribute('stroke-width', size === 'compact' ? '1' : '0.8');
    el.setAttribute('transform', `rotate(${rot} ${cx} ${cy})`);
    svg.appendChild(el);

    const len = ellipseLen(r, r * tilt);
    el.setAttribute('stroke-dasharray',  len.toFixed(2));
    el.setAttribute('stroke-dashoffset', len.toFixed(2));
    el.dataset.len = len.toFixed(2);
    elements.push(el);
  }

  /* ── Latitudes: horizontal rings, rx = full sphere width, ry compresses toward poles ── */
  const latStep = 85 / latCount;
  for (let i = 1; i <= latCount; i++) {
    const latDeg = i * latStep;                // 10.625, 21.25, … up to 85
    const rad    = (latDeg * Math.PI) / 180;
    const sinL   = Math.sin(rad);
    const cosL   = Math.cos(rad);

    const offsetY = r * sinL * tilt;           // vertical shift from center
    const latRy   = r * tilt * cosL;           // small ry near poles, larger at equator

    for (const sign of [-1, 1]) {
      const el = document.createElementNS('http://www.w3.org/2000/svg', 'ellipse');
      el.setAttribute('cx', cx);
      el.setAttribute('cy', cy + sign * offsetY);
      el.setAttribute('rx', r);                // stays full width!
      el.setAttribute('ry', latRy);            // compresses toward poles
      el.setAttribute('fill', 'none');
      el.setAttribute('stroke', STROKE);
      el.setAttribute('stroke-width', size === 'compact' ? '1' : '0.8');
      svg.appendChild(el);

      const len = ellipseLen(r, latRy);
      el.setAttribute('stroke-dasharray',  len.toFixed(2));
      el.setAttribute('stroke-dashoffset', len.toFixed(2));
      el.dataset.len = len.toFixed(2);
      elements.push(el);
    }
  }

  sphereWrap.appendChild(svg);
  root.appendChild(sphereWrap);

  /* ── LOADING text (full size only) ── */
  let label = null;
  if (size !== 'compact') {
    label = document.createElement('p');
    label.textContent   = 'LOADING';
    label.style.fontFamily    = "'Space Grotesk', sans-serif";
    label.style.fontSize      = '11px';
    label.style.letterSpacing   = '0.35em';
    label.style.color         = '#6b8cae';
    label.style.fontWeight    = '400';
    label.style.textTransform = 'uppercase';
    label.style.opacity       = '0';
    label.style.marginTop     = '40px';        // 52px below sphere edge ≈ 40px gap
    root.appendChild(label);
  }

  container.appendChild(root);

  /* ── Draw-in ── */
  const drawAnim = animate(elements, {
    strokeDashoffset: (el, i) => [+el.dataset.len, 0],
    delay: stagger(70, { from: 'center' }),
    duration: 2600,
    ease: 'inOutQuart',
    onComplete: () => {
      /* Lines stay drawn — only the whole sphere gets a tiny pulse */
      const pulse = animate(sphereWrap, {
        opacity: [1, 0.65, 1],
        scale:   [1, 1.025, 1],
        duration: 3200,
        ease: 'easeInOutSine',
        loop: true,
      });

      /* Fade label in 600ms after draw starts (≈ now minus draw overlap) */
      let labelAnim = null;
      if (label) {
        labelAnim = animate(label, {
          opacity: [0, 1],
          duration: 800,
          delay: 200,
          ease: 'easeInOutSine',
        });
      }

      /* Store on instance for cleanup */
      instance.pulse    = pulse;
      instance.labelAnim = labelAnim;
    },
  });

  const instance = { root, sphereWrap, drawAnim, pulse: null, labelAnim: null };
  activeInstances.add(instance);
  return instance;
}

export function createLoaderHTML(size = 'full') {
  const container = document.createElement('div');
  container.className = 'flex flex-col items-center gap-4';
  createLoader(container, size);
  return container;
}

export function destroyLoader(instance) {
  if (!instance) return;
  if (instance.drawAnim)  instance.drawAnim.pause();
  if (instance.pulse)     instance.pulse.pause();
  if (instance.labelAnim) instance.labelAnim.pause();
  if (instance.root && instance.root.parentNode) {
    instance.root.parentNode.removeChild(instance.root);
  }
  activeInstances.delete(instance);
}

export function destroyAllLoaders() {
  activeInstances.forEach(destroyLoader);
  activeInstances.clear();
}
