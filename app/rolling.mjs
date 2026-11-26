const issuerSelect = document.querySelector('#rolling-issuer');
const peerSelect = document.querySelector('#rolling-peer');
const comparison = document.querySelector('#rolling-comparison');
const cutoff = document.querySelector('#rolling-cutoff');
const result = document.querySelector('#rolling-result');
const usd = new Intl.NumberFormat('en-US', {
  style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 2,
});

const percentage = new Intl.NumberFormat('en-US', {maximumFractionDigits: 1, signDisplay: 'exceptZero'});

const labels = {annual: 'Annual filing', current_ytd: 'Current year to date', prior_ytd: 'Prior year to date'};

function node(tag, text) {
  const item = document.createElement(tag);
  item.textContent = text;
  return item;
}

function issuerCard(row) {
  const card = node('article', '');
  card.className = 'rolling-card';
  card.append(node('h3', row.company ? `${row.ticker} · ${row.company}` : row.ticker));
  if (row.unavailable) {
    const reason = row.unavailable_reason === 'reporting_basis'
      ? 'Rolling revenue is unavailable. The annual and interim filings are on different reporting bases.'
      : 'Rolling revenue is unavailable. The latest eligible filing data could not be reconciled.';
    card.append(node('p', reason));
    return card;
  }
  const value = node('strong', usd.format(Number(row.trailing_four_quarter_revenue_usd)));
  value.className = 'rolling-value';
  const period = node('p', `Four quarters ended ${row.period_end} · USD`);
  const sources = node('details', '');
  sources.append(node('summary', 'Filing inputs'));
  const list = node('ul', '');
  const inputs = [...row.inputs, ...(row.year_over_year?.inputs ?? []).map((input) => ({...input, priorWindow: true}))];
  for (const input of inputs) {
    const item = node('li', `${input.priorWindow ? 'Prior window · ' : ''}${labels[input.role]} · ${input.start} to ${input.end} · ${usd.format(Number(input.revenue_usd))} · `);
    if (/^\d{10}-\d{2}-\d{6}$/.test(input.accession) && Number.isInteger(row.cik)) {
      const accession = input.accession.replaceAll('-', '');
      const link = node('a', input.accession);
      const file = input.document && /^[a-zA-Z0-9_-]+[.]html?$/.test(input.document)
        ? input.document : `${input.accession}-index.htm`;
      link.href = `https://www.sec.gov/Archives/edgar/data/${row.cik}/${accession}/${file}`;
      item.append(link);
    }
    list.append(item);
  }
  sources.append(list);
  const growth = row.year_over_year;
  const change = growth
    ? node('p', `${percentage.format(growth.percent)}% year over year · Prior period ended ${growth.prior_period_end}`)
    : node('p', 'Year-over-year growth unavailable.');
  change.className = 'rolling-growth';
  card.append(value, period, change);
  if (row.reporting_basis) card.append(node('p', row.reporting_basis));
  card.append(sources);
  return card;
}

function initializeScreener(snapshot, openIssuer) {
  const minimum = document.querySelector('#screen-minimum');
  const sort = document.querySelector('#screen-sort');
  const summary = document.querySelector('#screen-summary');
  const rows = document.querySelector('#screen-rows');
  const score = {
    growth: (row) => row.year_over_year?.percent ?? -Infinity,
    revenue: (row) => row.unavailable ? -Infinity : Number(row.trailing_four_quarter_revenue_usd),
  };

  function renderScreen() {
    if (minimum.validity.badInput) {
      summary.textContent = 'Enter a valid percentage to filter the table.';
      rows.replaceChildren();
      return;
    }
    const lowerBound = minimum.value === '' ? -Infinity : minimum.valueAsNumber;
    const ordered = snapshot.issuers.filter((row) => score.growth(row) >= lowerBound);
    ordered.sort((left, right) => {
      const getValue = score[sort.value];
      if (getValue && getValue(left) !== getValue(right)) {
        return getValue(left) > getValue(right) ? -1 : 1;
      }
      return left.ticker.localeCompare(right.ticker);
    });
    summary.textContent = `${ordered.length} of ${snapshot.issuers.length} issuers · Filing cutoff ${snapshot.cutoff.slice(0, 10)} UTC`;
    rows.replaceChildren(...ordered.map((issuer) => {
      const row = node('tr', '');
      const company = node('th', '');
      company.scope = 'row';
      const link = node('a', issuer.ticker);
      link.href = '#rolling';
      link.addEventListener('click', () => openIssuer(issuer.ticker));
      company.append(link);
      if (issuer.company) company.append(node('small', issuer.company));
      row.append(company, node('td', issuer.period_end ?? 'Unavailable'),
        node('td', issuer.unavailable ? 'Unavailable' : usd.format(score.revenue(issuer))),
        node('td', issuer.year_over_year ? `${percentage.format(score.growth(issuer))}%` : 'Unavailable'));
      return row;
    }));
    if (!ordered.length) {
      const row = node('tr', '');
      const cell = node('td', 'No issuers meet this growth threshold.');
      cell.colSpan = 4;
      row.append(cell);
      rows.append(row);
    }
  }
  minimum.disabled = false;
  sort.disabled = false;
  minimum.addEventListener('input', renderScreen);
  sort.addEventListener('change', renderScreen);
  renderScreen();
}

async function initialize() {
  const response = await fetch(new URL('./rolling.json', import.meta.url));
  if (!response.ok) throw new Error('Rolling data unavailable');
  const snapshot = await response.json();
  cutoff.textContent = `Filing cutoff ${snapshot.cutoff.slice(0, 10)} UTC · Archived snapshot`;
  const issuers = new Map();
  for (const row of snapshot.issuers) {
    issuers.set(row.ticker, row);
    const option = node('option', row.company ? `${row.ticker} · ${row.company}` : row.ticker);
    option.value = row.ticker;
    issuerSelect.append(option);
    peerSelect.append(option.cloneNode(true));
  }
  if (!issuers.size) throw new Error('Rolling snapshot has no issuers');
  function render() {
    const primary = issuers.get(issuerSelect.value);
    if (peerSelect.value === primary.ticker) peerSelect.value = '';
    for (const option of peerSelect.options) option.disabled = option.value === primary.ticker;
    const peer = issuers.get(peerSelect.value);
    result.replaceChildren(...(peer ? [primary, peer] : [primary]).map(issuerCard));
    comparison.textContent = peer && !primary.unavailable && !peer.unavailable && primary.period_end !== peer.period_end
      ? 'These reporting periods end on different dates.'
      : '';
  }
  issuerSelect.disabled = false;
  peerSelect.disabled = false;
  issuerSelect.addEventListener('change', render);
  peerSelect.addEventListener('change', render);
  render();
  initializeScreener(snapshot, (ticker) => {
    issuerSelect.value = ticker;
    render();
    issuerSelect.focus({preventScroll: true});
  });
}

initialize().catch(() => {
  cutoff.textContent = 'Rolling revenue data could not load. Reload the page to retry.';
  document.querySelector('#screen-summary').textContent = 'Screener data could not load.';
});
