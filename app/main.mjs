import './rolling.mjs';

const year = document.querySelector('#year');
const search = document.querySelector('#search');
const coverage = document.querySelector('#coverage');
const table = document.querySelector('#issuer-rows');
const summary = document.querySelector('#cohort-summary');
const count = document.querySelector('#issuer-count');
const correlations = document.querySelector('#correlations');
const download = document.querySelector('#export');
const savedOnly = document.querySelector('#saved-only');
const savedCount = document.querySelector('#saved-count');
const watchlistStatus = document.querySelector('#watchlist-status');
const watchlistKey = 'stratiq.watchlist.v1';
const names = {
  return_on_assets: 'Return on assets',
  negative_sloan_accruals: 'Negative Sloan accruals',
};
const exclusionLabels = {
  'missing December fiscal period with eligible revenue': 'No eligible December fiscal period',
  'incomplete point-in-time accounts or outcome': 'Incomplete accounts or growth outcome',
  'outcome missing under the feature-period revenue tag': 'Growth outcome missing for selected revenue tag',
  'fiscal periods are not adjacent': 'Fiscal periods are not adjacent',
};

function element(tag, value) {
  const item = document.createElement(tag);
  if (value !== undefined) item.textContent = value;
  return item;
}

function rowFor(issuer, saved, toggle) {
  const row = element('tr');
  const company = element('td');
  company.append(element('strong', issuer.ticker), element('small', issuer.name || `CIK ${issuer.cik}`));
  const status = element('td', issuer.included ? 'Matched' : 'Excluded');
  if (!issuer.included) status.append(element('small', exclusionLabels[issuer.reason] ?? issuer.reason));
  const source = element('td');
  const link = element('a', 'SEC filings');
  link.href = `https://www.sec.gov/edgar/browse/?CIK=${issuer.cik}`;
  source.append(link);
  const actions = element('td');
  const button = element('button', saved ? 'Saved' : 'Save');
  button.type = 'button';
  button.className = 'save';
  button.dataset.cik = issuer.cik;
  button.setAttribute('aria-pressed', String(saved));
  button.setAttribute('aria-label', `Watchlist: ${issuer.ticker}`);
  button.addEventListener('click', toggle);
  actions.append(button);
  row.append(company, status, source, actions);
  return row;
}

async function initialize() {
  const response = await fetch(new URL('./cohorts.json', import.meta.url));
  if (!response.ok) throw new Error('Cohort data unavailable');
  const reports = await response.json();
  for (const report of reports) {
    const option = element('option', report.feature_year);
    option.value = report.feature_year;
    year.append(option);
  }

  const known = new Set(reports.flatMap((report) => report.coverage.map((issuer) => String(issuer.cik))));
  function readWatchlist() {
    try {
      const stored = JSON.parse(localStorage.getItem(watchlistKey) ?? '[]');
      return new Set(Array.isArray(stored) ? stored.filter((cik) => known.has(cik)) : []);
    } catch {
      return new Set();
    }
  }

  let watchlist = readWatchlist();
  const active = () => reports.find((report) => String(report.feature_year) === year.value);
  function renderIssuers() {
    const query = search.value.trim().toLowerCase();
    const issuers = active().coverage.filter((issuer) =>
      (!savedOnly.checked || watchlist.has(String(issuer.cik))) &&
      (coverage.value === 'all' || issuer.included === (coverage.value === 'included')) &&
      [issuer.ticker, issuer.name || '', String(issuer.cik), String(issuer.cik).padStart(10, '0')]
        .some((value) => value.toLowerCase().includes(query)));
    count.textContent = `${issuers.length} issuer${issuers.length === 1 ? '' : 's'} shown`;
    savedCount.textContent = `${watchlist.size} saved`;
    table.replaceChildren(...issuers.map((issuer) => {
      const cik = String(issuer.cik);
      return rowFor(issuer, watchlist.has(cik), () => toggleIssuer(issuer));
    }));
    if (!issuers.length) {
      const empty = element('td', 'No issuers match these filters.');
      empty.colSpan = 4;
      const row = element('tr');
      row.append(empty);
      table.append(row);
    }
  }

  function toggleIssuer(issuer) {
    const cik = String(issuer.cik);
    const removing = watchlist.delete(cik);
    if (!removing) watchlist.add(cik);
    const action = removing ? 'Removed' : 'Saved';
    try {
      localStorage.setItem(watchlistKey, JSON.stringify([...watchlist]));
      watchlistStatus.textContent = `${action} ${issuer.ticker}.`;
    } catch {
      watchlistStatus.textContent = `${action} ${issuer.ticker} for this session. Browser storage is unavailable.`;
    }
    renderIssuers();
    (table.querySelector(`button[data-cik="${cik}"]`) ?? savedOnly).focus();
  }

  function renderCohort() {
    const report = active();
    summary.textContent = `${report.matched_size} of ${report.universe_size} issuers matched · Outcome: next fiscal-year revenue growth`;
    const ranks = report.comparison.cohorts[0]?.rank_ic ?? {};
    correlations.replaceChildren(...Object.entries(names).map(([key, label]) => {
      const card = element('div');
      card.className = 'metric';
      const score = ranks[key];
      const printed = Number.isFinite(score) ? `${score > 0 ? '+' : ''}${score.toFixed(3)}` : 'Unavailable';
      card.append(element('span', label), element('strong', printed));
      return card;
    }));
    renderIssuers();
  }

  year.addEventListener('change', renderCohort);
  search.addEventListener('input', renderIssuers);
  coverage.addEventListener('change', renderIssuers);
  savedOnly.addEventListener('change', renderIssuers);
  window.addEventListener('storage', (event) => {
    if (event.key === watchlistKey || event.key === null) {
      watchlist = readWatchlist();
      renderIssuers();
    }
  });
  download.addEventListener('click', () => {
    const report = active();
    const uri = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], {type: 'application/json'}));
    const link = element('a');
    link.href = uri;
    link.download = `stratiq-sec-${report.feature_year}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(uri), 1000);
  });
  renderCohort();
  download.disabled = false;
}

initialize().catch(() => {
  summary.textContent = 'Cohort data could not load. Reload the page to retry.';
});
