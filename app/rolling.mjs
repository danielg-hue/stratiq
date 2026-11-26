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
}

initialize().catch(() => {
  cutoff.textContent = 'Rolling revenue data could not load. Reload the page to retry.';
});
