/* ==========================================================================
   OmniSight dashboard: vanilla JavaScript, no dependencies.
   Everything here runs locally. There are no network requests, and all
   scans, issues and review actions are demo data held in memory.
   ========================================================================== */
(function () {
  'use strict';

  /* ---------- Constants ---------- */

  var SEVERITIES = ['Critical', 'High', 'Medium', 'Low'];
  var SEV_COLORS = { Critical: '#b3261e', High: '#cf5f0e', Medium: '#b98a00', Low: '#5c7c90' };

  // The six lifecycle states are kept distinct on purpose.
  var STATES = {
    detected: { label: 'Detected', glyph: '\u25CB', text: 'The issue was found in a demo record. No fix has been proposed for review yet.' },
    proposed: { label: 'Fix proposed', glyph: '\u25D0', text: 'A CSS fix is waiting for a decision. Approving it does not apply or verify anything.' },
    applied: { label: 'Applied', glyph: '\u25CF', text: 'Recorded as applied in this demo. It is not verified yet, and no live website was changed.' },
    verified: { label: 'Verified', glyph: '\u2713', text: 'A demo outcome of verified was recorded. No real verification scan ran.' },
    failed: { label: 'Verification failed', glyph: '\u2715', text: 'A demo outcome of verification failed was recorded. The issue still needs attention.' },
    inconclusive: { label: 'Inconclusive', glyph: '?', text: 'A demo outcome of inconclusive was recorded. The result could not be confirmed either way.' }
  };

  var DECISIONS = {
    none: 'No fix proposed yet',
    pending: 'Awaiting review',
    approved: 'Approved',
    rejected: 'Rejected'
  };

  var SCAN_STATES = {
    completed: 'Completed',
    partial: 'Partial',
    failed: 'Failed',
    demo: 'Demo record'
  };

  /* ---------- Demo data (all of it is sample data) ---------- */

  var SAMPLE_SCANS = [
    { id: 'DS-1042', url: 'https://store.example.com', date: '2026-10-09', viewports: ['Desktop', 'Mobile'], status: 'completed', origin: 'sample' },
    { id: 'DS-1041', url: 'https://docs.example.org', date: '2026-10-07', viewports: ['Desktop'], status: 'completed', origin: 'sample' },
    { id: 'DS-1040', url: 'https://www.example.com/pricing', date: '2026-10-05', viewports: ['Mobile'], status: 'completed', origin: 'sample' },
    { id: 'DS-1039', url: 'https://app.example.net/login', date: '2026-10-02', viewports: ['Desktop', 'Mobile'], status: 'partial', origin: 'sample' },
    { id: 'DS-1038', url: 'https://blog.example.com', date: '2026-09-28', viewports: ['Desktop'], status: 'failed', origin: 'sample' },
    { id: 'DS-1037', url: 'https://store.example.com/checkout', date: '2026-09-24', viewports: ['Mobile'], status: 'completed', origin: 'sample' }
  ];

  var SAMPLE_ISSUES = [
    {
      id: 'OS-101', scanId: 'DS-1037', title: 'Checkout button hidden behind the sticky footer', type: 'Layout', viewport: 'Mobile', severity: 'Critical', state: 'proposed',
      selector: '.checkout-bar',
      description: 'On a 390 px screen the sticky order bar covers the Place order button, so the last step of checkout cannot be completed without zooming out.',
      css: '.checkout-bar {\n  position: sticky;\n  bottom: 0;\n}\n\nmain {\n  padding-bottom: calc(72px + env(safe-area-inset-bottom));\n}'
    },
    {
      id: 'OS-102', scanId: 'DS-1042', title: 'Hero image overflows its container', type: 'Layout', viewport: 'Mobile', severity: 'High', state: 'detected',
      selector: '.hero__media img',
      description: 'The hero image keeps its desktop width and pushes the page sideways, which creates a horizontal scrollbar on small screens.',
      css: '.hero__media img {\n  max-width: 100%;\n  height: auto;\n}'
    },
    {
      id: 'OS-103', scanId: 'DS-1042', title: 'Secondary button text has low contrast', type: 'Accessibility', viewport: 'Desktop', severity: 'High', state: 'proposed',
      selector: '.btn-secondary',
      description: 'Grey text on the light grey secondary button measures 2.6:1, below the 4.5:1 minimum for body-size text.',
      css: '.btn-secondary {\n  color: #1f2933;\n  background: #e4e7eb;\n}'
    },
    {
      id: 'OS-104', scanId: 'DS-1042', title: 'Product cards use different corner radii', type: 'Visual Consistency', viewport: 'Desktop', severity: 'Medium', state: 'applied',
      selector: '.product-grid .card',
      description: 'Cards in the first row use a 4 px radius and cards in later rows use 12 px, so the grid looks uneven.',
      css: '.product-grid .card {\n  border-radius: 8px;\n}'
    },
    {
      id: 'OS-105', scanId: 'DS-1039', title: 'Form fields show no visible focus outline', type: 'Accessibility', viewport: 'Desktop', severity: 'High', state: 'verified',
      selector: 'input, select, textarea',
      description: 'The login form removes the default outline, so keyboard users cannot tell which field is active.',
      css: 'input:focus-visible,\nselect:focus-visible,\ntextarea:focus-visible {\n  outline: 3px solid #0b7a75;\n  outline-offset: 2px;\n}'
    },
    {
      id: 'OS-106', scanId: 'DS-1040', title: 'Pricing table runs off the screen', type: 'Layout', viewport: 'Mobile', severity: 'Medium', state: 'failed',
      selector: '.pricing-table',
      description: 'The comparison table is wider than the viewport and its right-hand plan column cannot be reached.',
      css: '.pricing-wrap {\n  overflow-x: auto;\n}\n\n.pricing-table {\n  min-width: 560px;\n}'
    },
    {
      id: 'OS-107', scanId: 'DS-1041', title: 'Section headings use different font sizes', type: 'Visual Consistency', viewport: 'Desktop', severity: 'Low', state: 'inconclusive',
      selector: 'article h2',
      description: 'Second-level headings render at 26 px in some sections and 22 px in others without a clear reason.',
      css: 'article h2 {\n  font-size: 1.5rem;\n  line-height: 1.3;\n}'
    },
    {
      id: 'OS-108', scanId: 'DS-1040', title: 'Footer links are smaller than 44 px tap targets', type: 'Accessibility', viewport: 'Mobile', severity: 'Medium', state: 'detected',
      selector: '.site-footer a',
      description: 'Footer links are 22 px tall and sit 4 px apart, which makes them hard to tap accurately.',
      css: '.site-footer a {\n  display: inline-block;\n  min-height: 44px;\n  padding: 10px 4px;\n}'
    },
    {
      id: 'OS-109', scanId: 'DS-1039', title: 'Modal close icon has no accessible name', type: 'Accessibility', viewport: 'Desktop', severity: 'Critical', state: 'proposed',
      selector: '.modal__close',
      description: 'The close control is an icon with no text or label, so screen reader users hear only "button".',
      css: '/* HTML change also needed: add aria-label="Close dialog" to .modal__close */\n.modal__close {\n  min-width: 44px;\n  min-height: 44px;\n}'
    },
    {
      id: 'OS-110', scanId: 'DS-1041', title: 'Vertical spacing between doc sections varies', type: 'Visual Consistency', viewport: 'Desktop', severity: 'Low', state: 'detected',
      selector: '.doc-section',
      description: 'Gaps between sections range from 24 px to 64 px, so the page rhythm feels uneven.',
      css: '.doc-section + .doc-section {\n  margin-top: 40px;\n}'
    }
  ];

  /* ---------- App state ---------- */

  var app = {
    scans: SAMPLE_SCANS.map(function (s) { return Object.assign({}, s); }),
    issues: SAMPLE_ISSUES.map(function (i) {
      var decision = i.state === 'detected' ? 'none' : (i.state === 'proposed' ? 'pending' : 'approved');
      return Object.assign({}, i, {
        decision: decision,
        initialState: i.state,
        initialDecision: decision,
        log: [],
        evidence: { before: null, after: null }
      });
    }),
    filters: { q: '', severity: 'all', status: 'all' },
    evidenceMode: 'side',
    sliderPos: 50,
    activeIssueId: null,
    nextScanNumber: 1043,
    firstRoute: true
  };

  /* ---------- Small helpers ---------- */

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  function esc(value) {
    return String(value).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function fmtDate(iso) {
    var d = new Date(iso + 'T00:00:00');
    return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  function todayISO() {
    var d = new Date();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    return d.getFullYear() + '-' + m + '-' + day;
  }

  function nowTime() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function findIssue(id) { return app.issues.filter(function (i) { return i.id === id; })[0]; }
  function findScan(id) { return app.scans.filter(function (s) { return s.id === id; })[0]; }
  function issuesForScan(id) { return app.issues.filter(function (i) { return i.scanId === id; }); }
  function needsReview(i) { return i.state === 'proposed' || i.state === 'failed' || i.state === 'inconclusive'; }
  function viewportText(list) { return list.join(' and '); }
  function shortUrl(url) { return url.replace(/\/$/, ''); }

  function icon(id) { return '<svg class="icon" aria-hidden="true"><use href="#' + id + '"/></svg>'; }

  /* ---------- Badges ---------- */

  function sevBadge(sev) {
    return '<span class="badge sev-' + sev.toLowerCase() + '">' + esc(sev) + '</span>';
  }
  function stateBadge(key) {
    var s = STATES[key];
    return '<span class="badge st st-' + key + '"><span class="st-glyph" aria-hidden="true">' + s.glyph + '</span>' + esc(s.label) + '</span>';
  }
  function scanBadge(key) {
    return '<span class="badge scanst-' + key + '">' + esc(SCAN_STATES[key]) + '</span>';
  }
  function decisionBadge(key) {
    return '<span class="badge dec-' + key + '">' + esc(DECISIONS[key]) + '</span>';
  }
  function verificationBadge(issue) {
    if (issue.state === 'verified' || issue.state === 'failed' || issue.state === 'inconclusive') return stateBadge(issue.state);
    return '<span class="badge st st-none"><span class="st-glyph" aria-hidden="true">\u2013</span>Not verified</span>';
  }
  function issueCountText(scan) {
    if (scan.origin === 'user') return 'None (no scan ran)';
    return String(issuesForScan(scan.id).length);
  }

  /* ---------- Toasts ---------- */

  function showToast(type, message) {
    var box = $('#toasts');
    var iconId = type === 'success' ? 'i-check' : (type === 'error' ? 'i-alert' : 'i-info');
    var el = document.createElement('div');
    el.className = 'toast toast-' + type;
    el.innerHTML = icon(iconId) + '<p class="toast-msg">' + esc(message) + '</p>' +
      '<button class="toast-close" type="button" aria-label="Dismiss message">' + icon('i-close') + '</button>';
    box.appendChild(el);
    while (box.children.length > 3) box.removeChild(box.firstChild);
    var remove = function () { if (el.parentNode) el.parentNode.removeChild(el); };
    $('.toast-close', el).addEventListener('click', remove);
    window.setTimeout(remove, type === 'error' ? 9000 : 6500);
  }

  /* ---------- Routing ---------- */

  var VIEW_IDS = ['dashboard', 'scan', 'issues', 'history', 'scan-detail', 'issue'];

  function goTo(path) {
    if (location.hash === path) route(); else location.hash = path;
  }

  function showView(name, navKey, heading, title, crumbs) {
    VIEW_IDS.forEach(function (v) { $('#view-' + v).hidden = v !== name; });
    $$('.nav-link').forEach(function (a) {
      if (a.dataset.nav === navKey) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
    });
    document.title = title + ' | OmniSight (demo data)';
    renderCrumbs(crumbs);
    closeNav(false);
    if (!app.firstRoute) {
      window.scrollTo(0, 0);
      var h = typeof heading === 'string' ? $(heading) : heading;
      if (h) h.focus({ preventScroll: true });
    }
    app.firstRoute = false;
  }

  function renderCrumbs(list) {
    $('#crumbs').innerHTML = list.map(function (c, i) {
      var last = i === list.length - 1;
      if (last) return '<li><span aria-current="page">' + esc(c.label) + '</span></li>';
      return '<li><a href="' + c.path + '">' + esc(c.label) + '</a></li>';
    }).join('');
  }

  function route() {
    var parts = location.hash.replace(/^#\/?/, '').split('/');
    var root = parts[0] || 'dashboard';
    var id = parts[1] ? decodeURIComponent(parts[1]) : '';
    var home = { label: 'OmniSight', path: '#/dashboard' };

    if (root === 'scan') {
      showView('scan', 'scan', '#title-scan-page', 'New scan', [home, { label: 'New scan' }]);
    } else if (root === 'issues' && id) {
      var issue = findIssue(id);
      renderIssueDetail(id);
      showView('issue', 'issues', '#title-issue', issue ? issue.id : 'Issue not found',
        [home, { label: 'Issues', path: '#/issues' }, { label: issue ? issue.id : 'Not found' }]);
    } else if (root === 'issues') {
      renderIssuesView();
      showView('issues', 'issues', '#title-issues', 'Issues', [home, { label: 'Issues' }]);
    } else if (root === 'history' && id) {
      var scan = findScan(id);
      renderScanDetail(id);
      showView('scan-detail', 'history', '#title-scan-record', scan ? 'Scan ' + scan.id : 'Scan not found',
        [home, { label: 'Scan history', path: '#/history' }, { label: scan ? scan.id : 'Not found' }]);
    } else if (root === 'history') {
      renderHistory();
      showView('history', 'history', '#title-history', 'Scan history', [home, { label: 'Scan history' }]);
    } else {
      renderDashboard();
      showView('dashboard', 'dashboard', '#title-dashboard', 'Overview', [home, { label: 'Overview' }]);
    }
    updateNavCount();
  }

  function updateNavCount() {
    var el = $('#navIssueCount');
    el.textContent = app.issues.length;
    el.setAttribute('aria-label', app.issues.length + ' issues');
  }

  /* ---------- Mobile drawer ---------- */

  function openNav() {
    document.body.classList.add('nav-open');
    $('#menuBtn').setAttribute('aria-expanded', 'true');
    window.setTimeout(function () { $('#drawerClose').focus(); }, 50);
  }

  function closeNav(restoreFocus) {
    if (!document.body.classList.contains('nav-open')) return;
    document.body.classList.remove('nav-open');
    $('#menuBtn').setAttribute('aria-expanded', 'false');
    if (restoreFocus) $('#menuBtn').focus();
  }

  /* ---------- Dashboard ---------- */

  function renderDashboard() {
    var total = app.scans.length;
    var found = app.issues.length;
    var verified = app.issues.filter(function (i) { return i.state === 'verified'; }).length;
    var review = app.issues.filter(needsReview).length;

    var cards = [
      { icon: 'i-scan', label: 'Total scans', value: total, note: 'Demo records, no real scans' },
      { icon: 'i-alert', label: 'Issues found', value: found, note: 'Sample issues from demo scans' },
      { icon: 'i-check', label: 'Verified resolutions', value: verified, note: 'Marked verified in demo, of ' + found },
      { icon: 'i-flag', label: 'Issues requiring review', value: review, note: 'Proposed, failed or inconclusive' }
    ];
    $('#stats').innerHTML = cards.map(function (c) {
      return '<article class="stat slab tilt">' +
        '<span class="stat-icon">' + icon(c.icon) + '</span>' +
        '<div><p class="stat-label">' + c.label + '</p><p class="stat-value">' + c.value + '</p><p class="stat-note">' + c.note + '</p></div>' +
        '</article>';
    }).join('');

    var recent = sortedScans().slice(0, 5);
    $('#recentScans').innerHTML = recent.map(scanRow).join('');

    renderSeverityChart();
    renderReviewList();
  }

  function sortedScans() {
    return app.scans.slice().sort(function (a, b) {
      if (a.date !== b.date) return a.date < b.date ? 1 : -1;
      return a.id < b.id ? 1 : -1;
    });
  }

  function scanRow(scan) {
    return '<tr>' +
      '<td><span class="url">' + esc(shortUrl(scan.url)) + '</span></td>' +
      '<td class="nowrap">' + fmtDate(scan.date) + '</td>' +
      '<td class="num">' + esc(issueCountText(scan)) + '</td>' +
      '<td class="nowrap">' + esc(viewportText(scan.viewports)) + '</td>' +
      '<td>' + scanBadge(scan.status) + '</td>' +
      '<td><button class="btn btn-small" type="button" data-open-scan="' + scan.id + '" aria-label="Inspect scan record ' + scan.id + '">Inspect</button></td>' +
      '</tr>';
  }

  function renderSeverityChart() {
    var counts = SEVERITIES.map(function (s) {
      return app.issues.filter(function (i) { return i.severity === s; }).length;
    });
    var max = Math.max.apply(null, counts.concat([1]));
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    $('#severityChart').innerHTML = SEVERITIES.map(function (s, idx) {
      var n = counts[idx];
      var h = n ? Math.max(14, Math.round(n / max * 118)) : 6;
      return '<button class="sev-col" type="button" data-filter-severity="' + s + '" aria-label="' + s + ': ' + n + ' issues. Show these issues.">' +
        '<span class="sev-stage" aria-hidden="true">' +
        '<span class="cuboid' + (n ? '' : ' is-zero') + '" data-h="' + h + '" style="--c:' + SEV_COLORS[s] + ';--h:' + (reduce ? h : 0) + 'px">' +
        '<i class="f front"></i><i class="f back"></i><i class="f left"></i><i class="f right"></i><i class="f top"></i></span></span>' +
        '<span class="sev-num">' + n + '</span><span class="sev-name">' + s + '</span></button>';
    }).join('');

    // Columns grow once, after they exist in the DOM
    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(function () {
        $$('#severityChart .cuboid').forEach(function (c) { c.style.setProperty('--h', c.dataset.h + 'px'); });
      });
    });
  }

  function renderReviewList() {
    var order = { Critical: 0, High: 1, Medium: 2, Low: 3 };
    var list = app.issues.filter(needsReview).sort(function (a, b) { return order[a.severity] - order[b.severity]; }).slice(0, 5);
    var el = $('#reviewList');
    if (!list.length) {
      el.innerHTML = '<li class="review-empty">Nothing is waiting for a decision right now.</li>';
      return;
    }
    el.innerHTML = list.map(function (i) {
      return '<li class="review-item">' +
        '<div class="grow"><strong>' + esc(i.title) + '</strong><span class="muted small">' + i.id + ' in ' + esc(i.viewport) + ' view</span></div>' +
        sevBadge(i.severity) + stateBadge(i.state) +
        '<button class="btn btn-small" type="button" data-open-issue="' + i.id + '" aria-label="Open details for ' + esc(i.title) + '">Open details</button>' +
        '</li>';
    }).join('');
  }

  /* ---------- Scan history and scan records ---------- */

  function renderHistory() {
    $('#historyRows').innerHTML = sortedScans().map(function (scan) {
      return '<tr>' +
        '<td><span class="url">' + esc(shortUrl(scan.url)) + '</span></td>' +
        '<td class="nowrap">' + fmtDate(scan.date) + '</td>' +
        '<td class="nowrap">' + esc(viewportText(scan.viewports)) + '</td>' +
        '<td class="num">' + esc(issueCountText(scan)) + '</td>' +
        '<td>' + scanBadge(scan.status) + '</td>' +
        '<td><button class="btn btn-small" type="button" data-open-scan="' + scan.id + '" aria-label="Inspect scan record ' + scan.id + '">Inspect</button></td>' +
        '</tr>';
    }).join('');
  }

  function renderScanDetail(id) {
    var scan = findScan(id);
    var mount = $('#scanDetail');
    var back = '<div class="detail-top"><button class="link-btn" type="button" data-go="#/history">' + icon('i-back') + 'Back to scan history</button></div>';

    if (!scan) {
      mount.innerHTML = back + '<header class="page-head"><h1 id="title-scan-record" tabindex="-1">Scan record not found</h1><p>No demo record has the ID ' + esc(id) + '. It may have been created before the page was reloaded.</p></header>';
      return;
    }

    var issues = issuesForScan(scan.id);
    var userMade = scan.origin === 'user';
    var issueBlock;
    if (userMade) {
      issueBlock = '<p class="muted">This record reports no issues because no scan ran. It only shows how a submitted scan would be filed.</p>';
    } else if (!issues.length) {
      issueBlock = '<p class="muted">This demo record has no issues attached. ' + (scan.status === 'failed' ? 'Its state is Failed, so nothing was reported.' : '') + '</p>';
    } else {
      issueBlock = '<ul class="review-list">' + issues.map(function (i) {
        return '<li class="review-item"><div class="grow"><strong>' + esc(i.title) + '</strong><span class="muted small">' + i.id + ' in ' + esc(i.viewport) + ' view</span></div>' +
          sevBadge(i.severity) + stateBadge(i.state) +
          '<button class="btn btn-small" type="button" data-open-issue="' + i.id + '" aria-label="Open details for ' + esc(i.title) + '">Open details</button></li>';
      }).join('') + '</ul>';
    }

    mount.innerHTML = back +
      '<header class="page-head"><h1 id="title-scan-record" tabindex="-1">Scan record ' + scan.id + '</h1>' +
      '<p>' + (userMade ? 'Created from the New scan form. No scan was run and no website was contacted.' : 'Sample record. It was not produced by a real scan.') + '</p></header>' +
      '<div class="detail-grid two">' +
      '<section class="card slab" aria-labelledby="h-rec"><h2 id="h-rec">Record details</h2>' +
      '<dl class="facts" style="margin-top:0;padding-top:0;border-top:0">' +
      '<dt>Scan ID</dt><dd>' + scan.id + '</dd>' +
      '<dt>Target URL</dt><dd>' + esc(shortUrl(scan.url)) + '</dd>' +
      '<dt>Scan date</dt><dd>' + fmtDate(scan.date) + '</dd>' +
      '<dt>Viewport</dt><dd>' + esc(viewportText(scan.viewports)) + '</dd>' +
      '<dt>Issues reported</dt><dd>' + esc(issueCountText(scan)) + '</dd>' +
      '<dt>Scan state</dt><dd>' + scanBadge(scan.status) + '</dd>' +
      '<dt>Data origin</dt><dd>' + (userMade ? 'Demo record created in this session' : 'Sample data bundled with the frontend') + '</dd>' +
      '</dl></section>' +
      '<section class="card slab" aria-labelledby="h-rec-issues"><h2 id="h-rec-issues">Issues in this record</h2>' + issueBlock + '</section>' +
      '</div>';
  }

  /* ---------- New scan form ---------- */

  function validateUrl(raw) {
    var value = raw.trim();
    if (!value) return { ok: false, message: 'Enter the website address you want to scan.' };
    if (/\s/.test(value)) return { ok: false, message: 'Web addresses cannot contain spaces. Check for stray spaces and try again.' };
    if (!/^https?:\/\//i.test(value)) return { ok: false, message: 'Start the address with http:// or https://, for example https://www.example.com.' };

    var url;
    try { url = new URL(value); } catch (e) {
      return { ok: false, message: 'That address is not formatted correctly. Try something like https://www.example.com.' };
    }
    if (url.username || url.password) return { ok: false, message: 'Remove the username and password from the address.' };

    var host = url.hostname;
    var isIp = /^\d{1,3}(\.\d{1,3}){3}$/.test(host);
    if (isIp) {
      var okIp = host.split('.').every(function (n) { return Number(n) <= 255; });
      if (!okIp) return { ok: false, message: 'That IP address is not valid. Each number must be between 0 and 255.' };
    } else if (host !== 'localhost') {
      var labels = host.split('.');
      var okHost = labels.length >= 2 && labels.every(function (l) { return /^[a-z0-9-]{1,63}$/i.test(l) && l[0] !== '-' && l[l.length - 1] !== '-'; });
      if (!okHost) return { ok: false, message: 'The domain looks incomplete. Add a full domain such as example.com.' };
      if (!/^[a-z]{2,}$/i.test(labels[labels.length - 1]) && !/^xn--/i.test(labels[labels.length - 1])) {
        return { ok: false, message: 'The ending of the domain (like .com) is not valid. Check the spelling.' };
      }
    }
    return { ok: true, url: url.href };
  }

  function handleScanSubmit(e) {
    e.preventDefault();
    var input = $('#scanUrl');
    var err = $('#urlError');
    var result = $('#scanResult');
    var check = validateUrl(input.value);

    result.innerHTML = '';
    if (!check.ok) {
      err.textContent = check.message;
      input.setAttribute('aria-invalid', 'true');
      input.focus();
      showToast('error', 'The scan was not created. ' + check.message);
      return;
    }
    err.textContent = '';
    input.removeAttribute('aria-invalid');

    var choice = $('input[name="viewport"]:checked').value;
    var viewports = choice === 'Both' ? ['Desktop', 'Mobile'] : [choice];
    var scan = {
      id: 'DS-' + app.nextScanNumber++,
      url: check.url,
      date: todayISO(),
      viewports: viewports,
      status: 'demo',
      origin: 'user'
    };
    app.scans.push(scan);

    result.innerHTML = '<div class="result-box">' +
      '<strong>Demo record ' + scan.id + ' created</strong>' +
      '<p>No scan ran and no website was contacted. This only adds a labelled demo record for ' + esc(shortUrl(scan.url)) + ' (' + esc(viewportText(viewports).toLowerCase()) + ') to Scan history. It has no issues and no screenshots.</p>' +
      '<div class="row"><button class="btn btn-primary" type="button" data-open-scan="' + scan.id + '">Inspect demo record</button>' +
      '<button class="btn" type="button" data-go="#/history">Open scan history</button></div></div>';
    showToast('success', 'Demo record ' + scan.id + ' created. No real scan was run.');
    input.value = '';
    updateNavCount();
  }

  /* ---------- Issues list: search and filters ---------- */

  function filteredIssues() {
    var f = app.filters;
    var q = f.q.trim().toLowerCase();
    return app.issues.filter(function (i) {
      if (f.severity !== 'all' && i.severity !== f.severity) return false;
      if (f.status !== 'all' && i.state !== f.status) return false;
      if (!q) return true;
      var scan = findScan(i.scanId);
      var hay = [i.id, i.title, i.type, i.viewport, i.severity, i.description, STATES[i.state].label, scan ? scan.url : ''].join(' ').toLowerCase();
      return hay.indexOf(q) !== -1;
    });
  }

  function renderIssuesView() {
    $('#issueSearch').value = app.filters.q;
    $('#filterSeverity').value = app.filters.severity;
    $('#filterStatus').value = app.filters.status;
    renderIssueList();
  }

  function renderIssueList() {
    var list = filteredIssues();
    var total = app.issues.length;
    var active = app.filters.q || app.filters.severity !== 'all' || app.filters.status !== 'all';
    $('#resultsLine').textContent = 'Showing ' + list.length + ' of ' + total + ' issues' + (active ? ' with the current search and filters' : '');
    $('#clearFilters').disabled = !active;
    $('#issueEmpty').hidden = list.length !== 0;
    $('#issueList').hidden = list.length === 0;

    $('#issueList').innerHTML = list.map(function (i) {
      return '<li class="issue slab sevline-' + i.severity.toLowerCase() + '">' +
        '<div class="issue-main">' +
        '<h2 class="issue-title">' + esc(i.title) + '</h2>' +
        '<div class="issue-ids"><span class="issue-id">' + i.id + '</span><span class="chip">' + esc(i.type) + '</span><span class="chip">' + esc(i.viewport) + '</span></div>' +
        '<p class="issue-desc">' + esc(i.description) + '</p>' +
        '</div>' +
        '<div class="issue-side"><div class="issue-badges">' + sevBadge(i.severity) + stateBadge(i.state) + '</div>' +
        '<button class="btn btn-small" type="button" data-open-issue="' + i.id + '" aria-label="Open details for ' + esc(i.title) + '">Open details</button></div>' +
        '</li>';
    }).join('');
  }

  function clearFilters() {
    app.filters = { q: '', severity: 'all', status: 'all' };
    renderIssuesView();
    $('#issueSearch').focus();
  }

  /* ---------- Issue details ---------- */

  function renderIssueDetail(id) {
    var issue = findIssue(id);
    var mount = $('#issueDetail');
    var back = '<div class="detail-top"><button class="link-btn" type="button" data-go="#/issues">' + icon('i-back') + 'Back to issues</button></div>';

    if (!issue) {
      app.activeIssueId = null;
      mount.innerHTML = back + '<header class="page-head"><h1 id="title-issue" tabindex="-1">Issue not found</h1><p>No issue has the ID ' + esc(id) + '. Return to the list to pick another.</p></header>';
      return;
    }

    app.activeIssueId = issue.id;
    app.evidenceMode = 'side';
    var scan = findScan(issue.scanId);

    mount.innerHTML = back +
      '<header class="page-head detail-head">' +
      '<h1 id="title-issue" tabindex="-1">' + esc(issue.title) + '</h1>' +
      '<div class="head-badges" id="issueBadges"></div>' +
      '<p class="issue-ids">Issue <span class="issue-id">' + issue.id + '</span> from scan <button class="text-link" type="button" data-open-scan="' + scan.id + '">' + scan.id + '</button> (demo record)</p>' +
      '</header>' +

      '<div class="detail-grid">' +

      '<section class="card slab area-desc" aria-labelledby="h-orig"><h2 id="h-orig">Original issue</h2>' +
      '<p>' + esc(issue.description) + '</p>' +
      '<dl class="facts">' +
      '<dt>Target website</dt><dd>' + esc(shortUrl(scan.url)) + '</dd>' +
      '<dt>Affected viewport</dt><dd>' + esc(issue.viewport) + '</dd>' +
      '<dt>Severity</dt><dd>' + sevBadge(issue.severity) + '</dd>' +
      '<dt>Issue type</dt><dd>' + esc(issue.type) + '</dd>' +
      '<dt>Element</dt><dd>' + esc(issue.selector) + '</dd>' +
      '</dl></section>' +

      '<section class="card slab area-fix" aria-labelledby="h-fix"><h2 id="h-fix">Suggested CSS fix</h2>' +
      '<p class="muted">A suggestion for you to review. It has not been applied to any website.</p>' +
      '<pre class="code-block" tabindex="0" aria-label="Suggested CSS"><code>' + esc(issue.css) + '</code></pre>' +
      '<button class="btn btn-small" type="button" data-copy-css>' + icon('i-copy') + 'Copy CSS</button>' +
      '</section>' +

      '<aside class="card slab area-review" id="reviewPanel" aria-label="Status and review"></aside>' +

      '<section class="card slab area-evidence" aria-labelledby="h-evidence">' +
      '<div class="card-head"><h2 id="h-evidence">Screenshot evidence</h2><span class="tag">Demo: nothing captured</span></div>' +
      '<p class="muted">Evidence for ' + issue.id + ' from scan ' + scan.id + ', ' + esc(issue.viewport.toLowerCase()) + ' viewport.</p>' +
      '<fieldset class="seg"><legend class="sr-only">Preview mode</legend>' +
      '<label class="seg-opt"><input type="radio" name="evmode" value="side" checked><span>Side by side</span></label>' +
      '<label class="seg-opt"><input type="radio" name="evmode" value="slider" id="evSlider"><span>Slider</span></label>' +
      '<label class="seg-opt"><input type="radio" name="evmode" value="stack"><span>3D stack</span></label>' +
      '</fieldset>' +
      '<div class="evidence-stage" id="evidenceStage"></div>' +
      '<div class="evidence-controls">' +
      fileRow('before', 'Before') + fileRow('after', 'After') +
      '</div>' +
      '<p class="evidence-note">Images you add here are local previews on your device. They are not captured by OmniSight and are not saved. The slider needs both images.</p>' +
      '</section>' +
      '</div>';

    renderIssueStatus(issue);
    renderEvidence(issue);
  }

  function fileRow(kind, label) {
    return '<div class="file-row">' +
      '<label class="btn btn-small file-btn">Add ' + kind + ' image<input class="file-input" type="file" accept="image/*" data-evidence="' + kind + '"></label>' +
      '<span class="name" id="evname-' + kind + '">No ' + kind + ' image</span>' +
      '<button class="btn btn-small" type="button" data-remove-evidence="' + kind + '" id="evremove-' + kind + '" hidden>Remove ' + kind + '</button>' +
      '</div>';
  }

  function renderIssueStatus(issue) {
    $('#issueBadges').innerHTML = sevBadge(issue.severity) + '<span class="chip">' + esc(issue.type) + '</span>' + '<span class="chip">' + esc(issue.viewport) + '</span>' + stateBadge(issue.state);
    $('#reviewPanel').innerHTML = reviewPanelHTML(issue);
  }

  function trackHTML(issue) {
    var idx = { detected: 0, proposed: 1, applied: 2, verified: 3, failed: 3, inconclusive: 3 }[issue.state];
    var steps = ['Detected', 'Fix proposed', 'Applied', idx === 3 ? STATES[issue.state].label : 'Verification'];
    return '<ol class="track" aria-label="Progress of this issue">' + steps.map(function (label, i) {
      var cls = i < idx ? 'is-done' : (i === idx ? 'is-current' : '');
      if (i === 3 && idx === 3) cls += ' out-' + issue.state;
      var aria = i === idx ? ' aria-current="step"' : '';
      var note = i < idx ? '<span class="sr-only"> (reached)</span>' : (i > idx ? '<span class="sr-only"> (not reached)</span>' : '<span class="sr-only"> (current)</span>');
      return '<li class="' + cls + '"' + aria + '>' + esc(label) + note + '</li>';
    }).join('') + '</ol>';
  }

  function reviewPanelHTML(issue) {
    var s = issue.state, d = issue.decision;
    var canReview = s === 'proposed';
    var hint;
    if (s === 'detected') hint = d === 'rejected' ? 'The suggestion was rejected. Propose a fix again to reopen the review.' : 'Propose the fix first. Approve and Reject unlock once a fix is proposed.';
    else if (s === 'proposed' && d === 'approved') hint = 'Approved in this demo. Approval does not mean the fix is applied or verified.';
    else if (s === 'proposed') hint = 'Choose Approve fix or Reject suggestion.';
    else if (s === 'applied') hint = 'Next, record what a verification would have found.';
    else hint = 'A demo outcome is recorded. You can reset this issue to its sample state.';

    var next = '';
    if (s === 'detected') next = '<button class="btn" type="button" data-action="propose">Propose fix (demo)</button>';
    else if (s === 'proposed' && d === 'approved') next = '<button class="btn" type="button" data-action="apply">Mark as applied (demo)</button>';
    else if (s === 'applied') {
      next = '<p class="actions-title">Record a verification outcome (demo)</p><div class="actions stack-col">' +
        '<button class="btn" type="button" data-action="verified">Verified</button>' +
        '<button class="btn" type="button" data-action="failed">Verification failed</button>' +
        '<button class="btn" type="button" data-action="inconclusive">Inconclusive</button></div>';
    }
    var changed = s !== issue.initialState || d !== issue.initialDecision;

    var log = issue.log.length
      ? '<ol class="log">' + issue.log.slice().reverse().slice(0, 6).map(function (l) { return '<li><time>' + l.t + '</time><span>' + esc(l.text) + '</span></li>'; }).join('') + '</ol>'
      : '<p class="muted small">No review actions yet.</p>';

    return '<h2 id="reviewHeading" tabindex="-1">Status and review</h2>' +
      '<dl class="status-list">' +
      '<div><dt>Issue status</dt><dd>' + stateBadge(s) + '</dd></div>' +
      '<div><dt>Review decision</dt><dd>' + decisionBadge(d) + '</dd></div>' +
      '<div><dt>Verification</dt><dd>' + verificationBadge(issue) + '</dd></div>' +
      '</dl>' +
      '<p class="status-explain">' + STATES[s].text + '</p>' +
      trackHTML(issue) +
      '<div class="actions">' +
      '<button class="btn btn-primary" type="button" data-action="approve"' + (canReview && d !== 'approved' ? '' : ' disabled') + '>Approve fix</button>' +
      '<button class="btn btn-reject" type="button" data-action="reject"' + (canReview ? '' : ' disabled') + '>Reject suggestion</button>' +
      '</div>' +
      '<p class="action-hint" id="actionHint">' + hint + '</p>' +
      (next ? '<div class="next-step">' + (s === 'applied' ? '' : '<div class="actions">') + next + (s === 'applied' ? '' : '</div>') + '</div>' : '') +
      (changed ? '<div class="actions"><button class="btn btn-small" type="button" data-action="reset">Reset to sample state</button></div>' : '') +
      '<p class="demo-note">' + icon('i-info') + '<span>Local demo only. These buttons change what you see on this page. They never touch a live website or run a verification scan.</span></p>' +
      '<h3 class="log-title">Review log</h3>' + log;
  }

  function reviewAction(action) {
    var issue = findIssue(app.activeIssueId);
    if (!issue) return;
    var entry, toast;

    switch (action) {
      case 'propose':
        issue.state = 'proposed'; issue.decision = 'pending';
        entry = 'Fix marked as proposed for review.';
        toast = ['info', 'Fix marked as proposed. It is waiting for your decision, and nothing was sent anywhere.'];
        break;
      case 'approve':
        if (issue.state !== 'proposed') return;
        issue.decision = 'approved';
        entry = 'Fix approved. Not applied, not verified.';
        toast = ['success', 'Fix approved in this demo. It is not applied and not verified.'];
        break;
      case 'reject':
        if (issue.state !== 'proposed') return;
        issue.state = 'detected'; issue.decision = 'rejected';
        entry = 'Suggestion rejected. Issue returned to Detected.';
        toast = ['info', 'Suggestion rejected in this demo. The issue is back to Detected.'];
        break;
      case 'apply':
        issue.state = 'applied';
        entry = 'Marked as applied in the demo. No website was changed.';
        toast = ['info', 'Marked as applied in this demo. No CSS was added to any live website.'];
        break;
      case 'verified':
        issue.state = 'verified';
        entry = 'Demo outcome recorded: verified. No scan ran.';
        toast = ['success', 'Recorded as verified in this demo. No verification scan ran.'];
        break;
      case 'failed':
        issue.state = 'failed';
        entry = 'Demo outcome recorded: verification failed. No scan ran.';
        toast = ['error', 'Recorded as verification failed in this demo. No verification scan ran.'];
        break;
      case 'inconclusive':
        issue.state = 'inconclusive';
        entry = 'Demo outcome recorded: inconclusive. No scan ran.';
        toast = ['info', 'Recorded as inconclusive in this demo. No verification scan ran.'];
        break;
      case 'reset':
        issue.state = issue.initialState; issue.decision = issue.initialDecision;
        entry = 'Reset to the sample state.';
        toast = ['info', 'This issue was reset to its sample state.'];
        break;
      default:
        return;
    }

    issue.log.push({ t: nowTime(), text: entry });
    renderIssueStatus(issue);
    updateNavCount();
    showToast(toast[0], toast[1]);
    $('#reviewHeading').focus({ preventScroll: true });
  }

  function copyCss() {
    var issue = findIssue(app.activeIssueId);
    if (!issue) return;
    copyText(issue.css).then(function () {
      showToast('success', 'CSS copied to the clipboard.');
    }, function () {
      showToast('error', 'Could not copy automatically. Select the code and copy it with your keyboard.');
    });
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
    return new Promise(function (resolve, reject) {
      var ta = document.createElement('textarea');
      ta.value = text; ta.setAttribute('readonly', '');
      ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
      document.body.removeChild(ta);
      if (ok) resolve(); else reject();
    });
  }

  /* ---------- Screenshot evidence ---------- */

  function placeholderHTML(kind) {
    return '<div class="placeholder">' + icon('i-image') +
      '<strong>No ' + kind + ' screenshot</strong>' +
      '<span>Placeholder only. No evidence was captured for this demo record.</span></div>';
  }

  function shotInner(issue, kind) {
    var item = issue.evidence[kind];
    if (!item) return placeholderHTML(kind);
    var label = (kind === 'before' ? 'Before' : 'After') + ' screenshot for ' + issue.id + ', ' + issue.viewport.toLowerCase() + ' viewport, added from your device';
    return '<img src="' + item.url + '" alt="' + esc(label) + '">';
  }

  function renderEvidence(issue) {
    var ev = issue.evidence;
    var both = !!(ev.before && ev.after);
    var vp = issue.viewport.toLowerCase();
    var mode = app.evidenceMode;
    if (mode === 'slider' && !both) mode = app.evidenceMode = 'side';

    // Controls and mode switch
    $('#evSlider').disabled = !both;
    $$('input[name="evmode"]').forEach(function (r) { r.checked = r.value === mode; });
    ['before', 'after'].forEach(function (k) {
      $('#evname-' + k).textContent = ev[k] ? ev[k].name + ' (local preview)' : 'No ' + k + ' image';
      $('#evremove-' + k).hidden = !ev[k];
    });

    var html = '';
    if (mode === 'side') {
      html = '<div class="side-grid ' + vp + '">' +
        ['before', 'after'].map(function (k) {
          return '<figure class="slot"><figcaption>' + (k === 'before' ? 'Before' : 'After') + '</figcaption>' +
            '<div class="shot ' + vp + '">' + shotInner(issue, k) + '</div></figure>';
        }).join('') + '</div>';
    } else if (mode === 'slider') {
      html = '<div class="compare" style="--pos:' + app.sliderPos + '%"><div class="shot ' + vp + '">' +
        '<img src="' + ev.after.url + '" alt="After screenshot for ' + issue.id + ', ' + vp + ' viewport, added from your device">' +
        '<div class="compare-before"><img src="' + ev.before.url + '" alt="Before screenshot for ' + issue.id + ', ' + vp + ' viewport, added from your device"></div>' +
        '<span class="compare-handle"></span><span class="compare-tag l">Before</span><span class="compare-tag r">After</span></div>' +
        '<label class="slider-label">Comparison position<input type="range" id="comparePos" min="0" max="100" value="' + app.sliderPos + '"></label></div>';
    } else {
      html = '<div class="stack-stage ' + vp + '" role="group" aria-label="Before and after screenshots stacked in 3D. Hover to flatten.">' +
        '<div class="stack">' +
        '<div class="plate plate-before"><span class="plate-tag">Before</span>' + shotInner(issue, 'before') + '</div>' +
        '<div class="plate plate-after"><span class="plate-tag">After</span>' + shotInner(issue, 'after') + '</div>' +
        '</div></div>';
    }
    $('#evidenceStage').innerHTML = html;
  }

  function setEvidence(kind, file) {
    var issue = findIssue(app.activeIssueId);
    if (!issue || !file) return;
    if (!/^image\//.test(file.type)) {
      showToast('error', 'That file is not an image. Choose a PNG, JPG, WebP or GIF screenshot.');
      return;
    }
    if (issue.evidence[kind]) URL.revokeObjectURL(issue.evidence[kind].url);
    issue.evidence[kind] = { url: URL.createObjectURL(file), name: file.name };
    renderEvidence(issue);
    showToast('info', 'The ' + kind + ' image is a local preview. It is not scan evidence from OmniSight.');
  }

  function removeEvidence(kind) {
    var issue = findIssue(app.activeIssueId);
    if (!issue || !issue.evidence[kind]) return;
    URL.revokeObjectURL(issue.evidence[kind].url);
    issue.evidence[kind] = null;
    renderEvidence(issue);
  }

  /* ---------- Pointer tilt for summary cards ---------- */

  function initTilt() {
    var fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!fine || reduce) return;
    var stats = $('#stats');
    stats.addEventListener('pointermove', function (e) {
      var el = e.target.closest('.tilt');
      if (!el) return;
      var r = el.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - 0.5;
      var y = (e.clientY - r.top) / r.height - 0.5;
      el.style.setProperty('--ry', (x * 9).toFixed(2) + 'deg');
      el.style.setProperty('--rx', (-y * 9).toFixed(2) + 'deg');
    });
    stats.addEventListener('pointerout', function (e) {
      var el = e.target.closest('.tilt');
      if (el && !el.contains(e.relatedTarget)) {
        el.style.setProperty('--rx', '0deg');
        el.style.setProperty('--ry', '0deg');
      }
    });
  }

  /* ---------- Events ---------- */

  function bindEvents() {
    document.addEventListener('click', function (e) {
      var t;
      if ((t = e.target.closest('[data-go]'))) { e.preventDefault(); goTo(t.dataset.go); return; }
      if ((t = e.target.closest('[data-open-issue]'))) { goTo('#/issues/' + encodeURIComponent(t.dataset.openIssue)); return; }
      if ((t = e.target.closest('[data-open-scan]'))) { goTo('#/history/' + encodeURIComponent(t.dataset.openScan)); return; }
      if ((t = e.target.closest('[data-filter-severity]'))) {
        app.filters = { q: '', severity: t.dataset.filterSeverity, status: 'all' };
        goTo('#/issues');
        return;
      }
      if (e.target.closest('[data-clear-filters]')) { clearFilters(); return; }
      if ((t = e.target.closest('[data-action]'))) { if (!t.disabled) reviewAction(t.dataset.action); return; }
      if (e.target.closest('[data-copy-css]')) { copyCss(); return; }
      if ((t = e.target.closest('[data-remove-evidence]'))) { removeEvidence(t.dataset.removeEvidence); return; }
    });

    document.addEventListener('change', function (e) {
      var t = e.target;
      if (t.classList && t.classList.contains('file-input')) {
        setEvidence(t.dataset.evidence, t.files && t.files[0]);
        t.value = '';
      } else if (t.name === 'evmode') {
        app.evidenceMode = t.value;
        var issue = findIssue(app.activeIssueId);
        if (issue) renderEvidence(issue);
      }
    });

    document.addEventListener('input', function (e) {
      if (e.target.id === 'comparePos') {
        app.sliderPos = Number(e.target.value);
        var box = e.target.closest('.compare');
        if (box) box.style.setProperty('--pos', app.sliderPos + '%');
      }
    });

    $('#issueSearch').addEventListener('input', function (e) { app.filters.q = e.target.value; renderIssueList(); });
    $('#filterSeverity').addEventListener('change', function (e) { app.filters.severity = e.target.value; renderIssueList(); });
    $('#filterStatus').addEventListener('change', function (e) { app.filters.status = e.target.value; renderIssueList(); });
    $('#clearFilters').addEventListener('click', clearFilters);

    $('#scanForm').addEventListener('submit', handleScanSubmit);
    $('#scanUrl').addEventListener('input', function (e) {
      if ($('#urlError').textContent) { $('#urlError').textContent = ''; e.target.removeAttribute('aria-invalid'); }
    });

    $('#menuBtn').addEventListener('click', openNav);
    $('#drawerClose').addEventListener('click', function () { closeNav(true); });
    $('#scrim').addEventListener('click', function () { closeNav(true); });
    $$('.nav-link').forEach(function (a) { a.addEventListener('click', function () { closeNav(false); }); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeNav(true); });
    window.addEventListener('resize', function () { if (window.innerWidth > 960) closeNav(false); });

    window.addEventListener('hashchange', route);
  }

  /* ---------- Start ---------- */

  bindEvents();
  initTilt();
  route();
})();