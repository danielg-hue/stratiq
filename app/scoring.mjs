const file = document.querySelector('#score-file');
const filter = document.querySelector('#score-filter');
const pilot = document.querySelector('#score-pilot');
const pilotLabel = document.querySelector('#score-pilot-label');
const status = document.querySelector('#score-status');
const result = document.querySelector('#score-result');
const frameworkNames = {
  porter: 'Porter’s Five Forces', steeple: 'STEEPLE', vrio: 'VRIO', financial: 'Financial strength',
  governance: 'Governance', growth: 'Innovation and growth', market: 'Market intelligence', operations: 'Operations',
};

function node(tag, value) {
  const element = document.createElement(tag);
  element.textContent = value;
  return element;
}

function validatedDraft(draft, registry) {
  if (draft?.status !== 'internal_draft' || draft.publication?.publishable !== false
      || typeof draft.company !== 'string' || typeof draft.as_of !== 'string'
      || !Number.isFinite(Date.parse(draft.as_of)) || !Array.isArray(draft.sources)) {
    throw new Error('Choose a StratIQ internal draft.');
  }
  const sources = new Map();
  for (const source of draft.sources) {
    if (typeof source?.id !== 'string' || typeof source.origin !== 'string' || sources.has(source.id)) {
      throw new Error('Draft includes an invalid source.');
    }
    sources.set(source.id, source);
  }
  const groups = [];
  for (const [key, criteria] of Object.entries(registry)) {
    const received = draft.frameworks?.[key]?.elements;
    if (!Array.isArray(received) || received.length !== Object.keys(criteria).length) {
      throw new Error('Draft scoring registry is incomplete.');
    }
    const seen = new Set();
    for (const item of received) {
      const points = Number(item?.score);
      if (!item || !Object.hasOwn(criteria, item.element) || seen.has(item.element)
          || !['unknown', 'assessed'].includes(item.status) || typeof item.rationale !== 'string'
          || !Array.isArray(item.citations)
          || (item.status === 'unknown' && item.score !== null)
          || (item.status === 'assessed' && (typeof item.score !== 'string' || !/^[+-]?(?:[0-9]+(?:[.][0-9]*)?|[.][0-9]+)(?:e[+-]?[0-9]+)?$/i.test(item.score)
              || !Number.isFinite(points) || Math.abs(points) > 2 || !Number.isInteger(points * 4)
              || !item.rationale.trim() || !item.citations.some((citation) => citation?.stance === 'supports')))
          || item.citations.some((citation) => !citation || !sources.has(citation.document_id)
              || !Number.isInteger(citation.start) || !Number.isInteger(citation.end)
              || citation.start < 0 || citation.end <= citation.start
              || !['supports', 'contradicts', 'context'].includes(citation.stance))) {
        throw new Error('Draft includes an invalid score or citation.');
      }
      seen.add(item.element);
    }
    groups.push({key, criteria, elements: received});
  }
  return {draft, sources, groups};
}

function evidenceLink(source) {
  const label = 'Source filing';
  try {
    const url = new URL(source.origin);
    if (url.protocol === 'https:' && !url.username && !url.password) {
      const link = node('a', label);
      link.href = url.href;
      return link;
    }
  } catch {
    // Older draft bundles may use plain source descriptions.
  }
  return node('span', 'Source reference');
}

function render(model) {
  const {draft, sources, groups} = model;
  const assessed = groups.reduce((total, group) => total + group.elements.filter((item) => item.status === 'assessed').length, 0);
  const total = groups.reduce((sum, group) => sum + group.elements.length, 0);
  const title = node('h3', draft.company);
  const cutoff = node('p', `Internal draft · Evidence cutoff ${new Date(draft.as_of).toISOString().slice(0, 10)} UTC`);
  const eligible = assessed >= 40 && groups.every((group) =>
    group.elements.filter((item) => item.status === 'assessed').length * 2 >= group.elements.length);
  const raw = groups.flatMap((group) => group.elements)
    .filter((item) => item.status === 'assessed').reduce((sum, item) => sum + Number(item.score), 0);
  const coverage = node('p', `${assessed} of ${total} elements scored. ${eligible
    ? `Draft index ${(50 + 25 * raw / assessed).toFixed(2)} / 100.`
    : 'An index requires at least 40 scored elements and half of each framework.'}`);
  const sections = groups.map(({key, criteria, elements}) => {
    const block = node('details', '');
    block.className = 'score-framework';
    const scored = elements.filter((item) => item.status === 'assessed').length;
    block.append(node('summary', `${frameworkNames[key]} · ${scored}/${elements.length} scored`));
    block.open = filter.value !== 'all' || scored > 0;
    const items = elements.filter((item) => filter.value === 'all' || item.status === filter.value);
    for (const item of items) {
      const row = node('div', '');
      row.className = 'score-element';
      const points = Number(item.score);
      const rating = item.status === 'assessed' ? `${points > 0 ? '+' : ''}${points.toFixed(2)}` : 'Unknown';
      const rubric = criteria[item.element];
      row.append(node('strong', `${rubric.criterion} · ${rating}`));
      if (item.status === 'unknown') {
        row.append(node('p', `Evidence to look for: ${rubric.evidence}`));
        const anchors = node('details', '');
        anchors.append(node('summary', 'Scoring anchors'),
          node('p', `Adverse: ${rubric.adverse}`), node('p', `Favorable: ${rubric.favorable}`));
        row.append(anchors);
      }
      if (item.rationale) row.append(node('p', item.rationale));
      if (item.citations.length) {
        const citations = node('ul', '');
        for (const cite of item.citations) {
          const line = node('li', '');
          line.append(evidenceLink(sources.get(cite.document_id)),
            document.createTextNode(` · bytes ${cite.start}–${cite.end} · ${cite.stance}`));
          citations.append(line);
        }
        row.append(citations);
      }
      block.append(row);
    }
    return items.length ? block : null;
  });
  result.replaceChildren(title, cutoff, coverage, ...sections.filter(Boolean));
}

async function initialize() {
  const registryResponse = await fetch(new URL('./scoring-registry.json', import.meta.url));
  if (!registryResponse.ok) throw new Error('Scoring registry could not load.');
  const registry = await registryResponse.json();
  let model;
  let drafts = [];
  let request = 0;
  function show(draft) {
    model = validatedDraft(draft, registry);
    filter.disabled = false;
    render(model);
  }
  file.disabled = false;
  status.textContent = 'Open a local JSON draft. Uploaded files are read in this browser.';
  file.addEventListener('change', async () => {
    const selection = file.files[0];
    if (!selection) return;
    const current = ++request;
    try {
      if (selection.size > 2_000_000) throw new Error('Draft exceeds the 2 MB limit.');
      const draft = JSON.parse(await selection.text());
      if (current !== request) return;
      show(draft);
      pilot.value = '';
      status.textContent = 'Local draft opened in this browser.';
    } catch (error) {
      if (current === request) status.textContent = error instanceof SyntaxError ? 'Draft JSON is invalid.' : error.message;
    }
  });
  filter.addEventListener('change', () => { if (model) render(model); });
  pilot.addEventListener('change', () => {
    if (pilot.value === '') return;
    ++request;
    model = drafts[Number(pilot.value)];
    filter.disabled = false;
    render(model);
    status.textContent = 'Owner-only pilot draft loaded.';
  });
  try {
    const response = await fetch(new URL('./internal-scoring-drafts.json', import.meta.url));
    if (response.ok) {
      const received = await response.json();
      if (!Array.isArray(received) || !received.length) return;
      drafts = received.map((draft) => validatedDraft(draft, registry));
      const placeholder = node('option', 'Select a pilot draft');
      placeholder.value = '';
      placeholder.disabled = true;
      pilot.append(placeholder);
      drafts.forEach(({draft}, index) => {
        const option = node('option', `${draft.company} · ${draft.as_of.slice(0, 10)}`);
        option.value = String(index);
        pilot.append(option);
      });
      pilotLabel.hidden = false;
      pilot.disabled = false;
      if (request === 0) {
        pilot.value = '0';
        show(drafts[0].draft);
        status.textContent = 'Owner-only pilot draft loaded.';
      }
    }
  } catch {
    // Local draft import remains available if the optional pilot library is absent.
  }
}

initialize().catch(() => { status.textContent = 'Scoring workspace could not load.'; });
