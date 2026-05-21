/**
 * Core Web Vitals 측정 및 콘솔 리포팅
 * 실제 운영 시 GA4나 자체 로깅 엔드포인트로 전송하도록 sendToAnalytics 수정
 *
 * 사용: <script src="/js/vitals.js" defer></script>
 */

function sendToAnalytics({ name, value, rating, id }) {
  // 개발 환경에서는 콘솔 출력
  // 운영: navigator.sendBeacon('/analytics', JSON.stringify({ name, value, rating, id }));
  console.log(`[Web Vitals] ${name}: ${Math.round(value)} (${rating}) — id: ${id}`);
}

// PerformanceObserver를 이용해 각 지표 측정
// web-vitals 라이브러리 없이 직접 구현

// LCP (Largest Contentful Paint)
function observeLCP() {
  if (!('PerformanceObserver' in window)) return;
  try {
    const po = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const last = entries[entries.length - 1];
      const value = last.startTime;
      const rating = value <= 2500 ? 'good' : value <= 4000 ? 'needs-improvement' : 'poor';
      sendToAnalytics({ name: 'LCP', value, rating, id: last.id || 'lcp' });
    });
    po.observe({ type: 'largest-contentful-paint', buffered: true });
  } catch (e) { /* 미지원 브라우저 무시 */ }
}

// CLS (Cumulative Layout Shift)
function observeCLS() {
  if (!('PerformanceObserver' in window)) return;
  let clsValue = 0;
  let sessionValue = 0;
  let sessionEntries = [];

  try {
    const po = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (!entry.hadRecentInput) {
          const firstEntry = sessionEntries[0];
          const lastEntry = sessionEntries[sessionEntries.length - 1];
          if (
            sessionValue &&
            entry.startTime - lastEntry.startTime < 1000 &&
            entry.startTime - firstEntry.startTime < 5000
          ) {
            sessionValue += entry.value;
            sessionEntries.push(entry);
          } else {
            sessionValue = entry.value;
            sessionEntries = [entry];
          }
          if (sessionValue > clsValue) {
            clsValue = sessionValue;
          }
        }
      }
      const rating = clsValue <= 0.1 ? 'good' : clsValue <= 0.25 ? 'needs-improvement' : 'poor';
      sendToAnalytics({ name: 'CLS', value: clsValue, rating, id: 'cls' });
    });
    po.observe({ type: 'layout-shift', buffered: true });
  } catch (e) { /* 미지원 브라우저 무시 */ }
}

// INP (Interaction to Next Paint) — Chrome 96+ 지원
function observeINP() {
  if (!('PerformanceObserver' in window)) return;
  let maxDuration = 0;
  try {
    const po = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.duration > maxDuration) {
          maxDuration = entry.duration;
          const rating = maxDuration <= 200 ? 'good' : maxDuration <= 500 ? 'needs-improvement' : 'poor';
          sendToAnalytics({ name: 'INP', value: maxDuration, rating, id: 'inp' });
        }
      }
    });
    po.observe({ type: 'event', durationThreshold: 16, buffered: true });
  } catch (e) { /* 미지원 브라우저 무시 */ }
}

// FID (First Input Delay) — INP 이전 지표, 구형 브라우저 호환용
function observeFID() {
  if (!('PerformanceObserver' in window)) return;
  try {
    const po = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const value = entry.processingStart - entry.startTime;
        const rating = value <= 100 ? 'good' : value <= 300 ? 'needs-improvement' : 'poor';
        sendToAnalytics({ name: 'FID', value, rating, id: entry.name });
        po.disconnect();
      }
    });
    po.observe({ type: 'first-input', buffered: true });
  } catch (e) { /* 미지원 브라우저 무시 */ }
}

// TTFB (Time to First Byte) — 서버 응답 속도
function measureTTFB() {
  if (!('performance' in window)) return;
  const nav = performance.getEntriesByType('navigation')[0];
  if (!nav) return;
  const value = nav.responseStart - nav.requestStart;
  const rating = value <= 800 ? 'good' : value <= 1800 ? 'needs-improvement' : 'poor';
  sendToAnalytics({ name: 'TTFB', value, rating, id: 'ttfb' });
}

// DOM 로드 후 실행
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    observeLCP();
    observeCLS();
    observeINP();
    observeFID();
    measureTTFB();
  });
} else {
  observeLCP();
  observeCLS();
  observeINP();
  observeFID();
  measureTTFB();
}
