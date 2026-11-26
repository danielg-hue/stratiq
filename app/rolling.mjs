const issuerSelect = document.querySelector('#rolling-issuer');
const cutoff = document.querySelector('#rolling-cutoff');
const result = document.querySelector('#rolling-result');
const usd = new Intl.NumberFormat('en-US', {
  style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 2,
});

const labels = {annual: 'Annual filing', current_ytd: 'Current year to date', prior_ytd: 'Prior year to date'};

function node(tag, text) {
  const item = document.createElement(tag);
  item.textContent = text;
  return item;
}

function render(row) {
  if (row.unavailable) {
    result.replaceChildren(node('p', 'Rolling revenue is unavailable. The latest eligible filing data could not be reconciled.'));
    return;
  }
  const value = node('strong', usd.format(Number(row.trailing_four_quarter_revenue_usd)));
  value.className = 'rolling-value';
  const period = node('p', `Four quarters ended ${row.period_end} · USD`);
  const sources = node('details', '');
  sources.append(node('summary', 'Filing inputs'));
  const list = node('ul', '');
  for (const input of row.inputs) {
    const item = node('li', `${labels[input.role]} · ${input.start} to ${input.end} · ${usd.format(Number(input.revenue_usd))} · `);
    if (/^\d{10}-\d{2}-\d{6}$/.test(input.accession) && Number.isInteger(row.cik)) {
      const accession = input.accession.replaceAll('-', '');
      const link = node('a', input.accession);
      link.href = `https://www.sec.gov/Archives/edgar/data/${row.cik}/${accession}/${input.accession}-index.htm`;
      item.append(link);
    }
    list.append(item);
  }
  sources.append(list);
  result.replaceChildren(value, period, sources);
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
  }
  if (!issuers.size) throw new Error('Rolling snapshot has no issuers');
  issuerSelect.disabled = false;
  issuerSelect.addEventListener('change', () => render(issuers.get(issuerSelect.value)));
  render(issuers.get(issuerSelect.value));
}

initialize().catch(() => {
  cutoff.textContent = 'Rolling revenue data could not load. Reload the page to retry.';
});
