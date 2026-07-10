export const meta = {
  name: 'run-process',
  description: 'Drive the card process engine to completion — parallel chunk-workers per stage, then ship',
  whenToUse: 'Generate a deck through the staged process engine (scaffold→emphasis→spec consensus→generate→accuracy→markup→style→coverage). Pass args {jobPath}. Replaces build-week.js.',
  phases: [
    { title: 'Init',  detail: 'process_init the job → enumerate anchor units' },
    { title: 'Run',   detail: 'per stage: fetch frontier → bounded-parallel chunk-workers → submit (lock-serialized)' },
    { title: 'Ship',  detail: 'lint + review gates, then build_apkg (the immutable backstop)' },
  ],
}

// The DRIVER. Per stage it fetches the frontier ids, splits them into chunks, and runs the chunks with
// BOUNDED parallelism (≤ MAX_PARALLEL at once). Concurrent submits are serialized by the engine's
// per-run lock, and ALL cards.jsonl writes go through the engine (agents return card data / fixes), so
// parallel workers never race on the file. Heavy per-item stages are chunked; spec + coverage stay
// single-agent so they keep whole-deck view.
const JOB = (args && args.jobPath) || (typeof args === 'string' ? args : null)
if (!JOB) throw new Error('run-process: pass args {jobPath} — abs path to the run job.yaml')
const CHUNK = (args && args.chunk) || 8
const MAX_PARALLEL = (args && args.maxParallel) || 4    // concurrent chunk-workers per workflow — a server-friendly ceiling
const CHUNKED = new Set(['scaffold', 'emphasis', 'generate', 'accuracy', 'markup', 'style'])   // per-item, no cross-unit need

// Bounded rolling-window concurrency: at most `limit` chunk-workers hit the MCP server at once, even
// when a deck fans out to dozens of chunks. The engine is hardened to survive load, but capping the
// driver keeps pressure sane — especially since the operator may run more than one deck at a time
// (safe ceiling: 2 workflows; see classes/ISF/PROCESS-ENGINE.md). A rolling window (not batched
// barriers) keeps `limit` in flight continuously so one slow chunk never idles the others.
async function runPool(items, limit, fn) {
  const out = new Array(items.length)
  let next = 0
  const worker = async () => { while (next < items.length) { const i = next++; out[i] = await fn(items[i], i) } }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker))
  return out
}

const FETCH = { type: 'object', additionalProperties: false,
  properties: { done: { type: 'boolean' }, halted: { type: 'boolean' }, stage: { type: 'string' },
                ids: { type: 'array', items: { type: 'string' } }, note: { type: 'string' } } }
const WORKER = { type: 'object', additionalProperties: false,
  properties: { submitted: { type: 'number' }, note: { type: 'string' } } }

phase('Init')
const init = await agent(
  `Start a run: call process_init {job_path: "${JOB}", force: ${!!(args && args.force)}}. Return {cards_dir, units}.`,
  { schema: { type: 'object', additionalProperties: false, required: ['cards_dir'],
              properties: { cards_dir: { type: 'string' }, units: { type: 'number' } } },
    phase: 'Init', label: 'init' })
const CARDS_DIR = init && init.cards_dir
if (!CARDS_DIR) throw new Error('process_init failed: ' + JSON.stringify(init))
log(`init: ${init.units} anchor units → ${CARDS_DIR}`)

phase('Run')
let done = false, halted = false, round = 0
while (!done && round++ < 80) {
  const b = await agent(
`Call process_next_batch {cards_dir: "${CARDS_DIR}"}.
- {done:true}   → return {done:true}.
- {halted:true} → return {done:true, halted:true, note:"<escalated/blocked>"}.
- else → return {stage, ids:[the target_id of EVERY item]}.  (ids only — not the payloads.)`,
    { schema: FETCH, phase: 'Run', label: `fetch-${round}` })
  if (!b || b.done) { done = true; halted = !!(b && b.halted); if (b && b.note) log(`HALTED — ${b.note}`); break }
  const ids = b.ids || []
  if (!ids.length) { log(`round ${round}: ${b.stage} returned 0 ids — stopping`); break }
  const size = CHUNKED.has(b.stage) ? CHUNK : ids.length            // single agent for spec/coverage
  const chunks = []
  for (let i = 0; i < ids.length; i += size) chunks.push(ids.slice(i, i + size))
  log(`round ${round}: ${b.stage} × ${ids.length} items in ${chunks.length} chunk(s), ≤${MAX_PARALLEL} at a time`)
  await runPool(chunks, MAX_PARALLEL, (chunk, ci) => agent(
`Do the '${b.stage}' step for ONLY these items (cards_dir "${CARDS_DIR}"): ${JSON.stringify(chunk)}

1. Call process_next_batch {cards_dir: "${CARDS_DIR}"} to get the batch {stage, instructions, items}. Use ONLY the
   items whose target_id is in YOUR list above — ignore all others.
2. For each of YOUR items, do the stage's work per the batch "instructions" (read the SKILL/MARKUP/HIGH-YIELD
   files it names + each item's payload sources; stay grounded in those). NEVER write or edit files:
   - generate: author each card and RETURN it in the result → result = {cards:[{id,type,text,extra,source,tags}, ...]}.
   - accuracy/style: if you change a card, RETURN the full corrected card as result.fixed (same id).
3. Call process_submit_batch {cards_dir:"${CARDS_DIR}", results:[{target_id, stage:"${b.stage}", result}, ...]} for
   YOUR items only. If any entry errors, fix and resubmit just that one.
Return {submitted:<count>}.`,
    { schema: WORKER, phase: 'Run', label: `${b.stage}-c${ci}` }))
}
log(`run: ${round} rounds; done=${done} halted=${halted}`)

if (done && !halted) {
  phase('Ship')
  await agent(
`The process run at "${CARDS_DIR}" is complete. Ship it (bash):
- Read the deck name from "${CARDS_DIR}/.process_state.json" → .config.run.deck.
- Build with the venv python (lint + review gates run INSIDE build_apkg and must pass):
  classes/ISF/.venv/bin/python "classes/ISF/build_apkg.py" --cards "${CARDS_DIR}" --deck "<deck>" --out "<subject-dir>/<name>-Engine.apkg"
Report the gate results and final note/card counts.`,
    { phase: 'Ship', label: 'ship' })
}

return { cardsDir: CARDS_DIR, rounds: round, done, halted }
