import { useState } from 'react';

import { Badge, Button, Card, ErrorNote, Loading, MockBanner, PageHeader } from '@/components/ui';
import { useAsync } from '@/hooks/useAsync';
import { useLabState } from '@/hooks/useLabState';
import { analyzeReel, uploadReel } from '@/services/reellabApi';
import { fileSize, percent, seconds } from '@/utils/format';

/**
 * Step 3 — upload the reel and run multimodal analysis.
 *
 * The output is Content DNA: what the reel *is*, not how good it is. Scoring
 * happens in simulation, against personas.
 */
export default function ReelUploadPage() {
  const { reel, contentDna, setReel, setContentDna } = useLabState();
  const [file, setFile] = useState<File | null>(null);

  const upload = useAsync(uploadReel);
  const analyze = useAsync(analyzeReel);

  async function submit() {
    if (!file) return;

    const uploaded = await upload.run(file);
    if (!uploaded) return;
    setReel(uploaded);

    const dna = await analyze.run({ reelId: uploaded.id });
    if (dna) setContentDna(dna);
  }

  const busy = upload.state === 'loading' || analyze.state === 'loading';

  return (
    <>
      <PageHeader
        title="Reel Upload"
        description="Upload the reel you are about to publish. Multimodal analysis turns it into Content DNA — the description your synthetic audience reacts to."
      />

      <Card>
        <label className="label">Video file</label>
        <input
          type="file"
          accept="video/*"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          className="block w-full text-sm text-slate-400 file:mr-4 file:rounded-lg file:border-0
                     file:bg-ink-600 file:px-4 file:py-2 file:text-sm file:text-slate-700
                     hover:file:bg-ink-500"
        />

        {file && (
          <p className="mt-3 text-xs text-slate-500">
            {file.name} · {fileSize(file.size)}
          </p>
        )}

        <div className="mt-5 flex items-center gap-3">
          <Button onClick={submit} disabled={!file || busy}>
            {busy ? 'Analysing…' : 'Upload and analyse'}
          </Button>
          {reel && <Badge>{reel.status}</Badge>}
        </div>

        {upload.state === 'loading' && <Loading label="Uploading…" />}
        {analyze.state === 'loading' && <Loading label="Reading frames, audio and transcript…" />}

        {upload.error && (
          <div className="mt-4">
            <ErrorNote message={upload.error} code={upload.errorCode} />
          </div>
        )}
        {analyze.error && (
          <div className="mt-4">
            <ErrorNote message={analyze.error} code={analyze.errorCode} />
          </div>
        )}
      </Card>

      {contentDna && (
        <div className="mt-6 space-y-4">
          <MockBanner mock={analyze.mock} />

          <Card title="Content DNA" subtitle={contentDna.topic}>
            <div className="grid gap-4 sm:grid-cols-2">
              <Detail label="Duration" value={seconds(contentDna.durationSeconds)} />
              <Detail label="Tone" value={`${contentDna.tone} · ${contentDna.emotion}`} />
              <Detail
                label="Hook"
                value={`${seconds(contentDna.hook.durationSeconds)} · ${contentDna.hook.type} · strength ${percent(contentDna.hook.strength)}`}
              />
              <Detail
                label="Call to action"
                value={contentDna.cta.present ? (contentDna.cta.text ?? 'present') : 'none'}
              />
            </div>

            <blockquote className="mt-4 border-l-2 border-accent-dim pl-4 text-sm italic text-slate-700">
              “{contentDna.hook.text}”
            </blockquote>

            <div className="mt-5">
              <h3 className="label">Scenes</h3>
              <ol className="space-y-1.5 text-sm">
                {contentDna.scenes.map((scene) => (
                  <li key={scene.index} className="flex gap-3">
                    <span className="w-24 shrink-0 font-mono text-xs text-slate-500">
                      {scene.startSeconds.toFixed(1)}–{scene.endSeconds.toFixed(1)}s
                    </span>
                    <span className="text-slate-400">{scene.description}</span>
                  </li>
                ))}
              </ol>
            </div>

            {contentDna.warnings && contentDna.warnings.length > 0 && (
              <ul className="mt-5 space-y-1 border-t border-ink-600 pt-4 text-xs text-signal-mixed">
                {contentDna.warnings.map((warning) => (
                  <li key={warning}>· {warning}</li>
                ))}
              </ul>
            )}
          </Card>

          <Button onClick={() => document.getElementById('simulate')?.scrollIntoView({ behavior: 'smooth' })}>Run simulation</Button>
        </div>
      )}
    </>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="label">{label}</div>
      <div className="text-sm text-slate-700">{value}</div>
    </div>
  );
}
