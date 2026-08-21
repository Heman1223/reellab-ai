import { useState, useRef } from 'react';
import type { DragEvent } from 'react';

import { Badge, Button, Card, ErrorNote, Loading, MockBanner, PageHeader } from '@/components/ui';
import { useAsync } from '@/hooks/useAsync';
import { useLabState } from '@/hooks/useLabState';
import { analyzeReel, uploadReel } from '@/services/reellabApi';
import { cn, fileSize, percent, seconds } from '@/utils/format';

/**
 * Step 3 — upload the reel and run multimodal analysis.
 */
export default function ReelUploadPage() {
  const { reel, contentDna, setReel, setContentDna, audienceDescription, setAudienceDescription } = useLabState();
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped && dropped.type.startsWith('video/')) {
      setFile(dropped);
    }
  };

  const busy = upload.state === 'loading' || analyze.state === 'loading';

  return (
    <>
      <PageHeader
        title="Reel Upload"
        description="Upload the reel you are about to publish. Multimodal analysis turns it into Content DNA — the description your synthetic audience reacts to."
      />

      <Card title="Who do you want to reach? (Optional)" subtitle="Leave blank to let the AI infer the best audience for this reel.">
        <input
          type="text"
          value={audienceDescription ?? ''}
          onChange={(e) => setAudienceDescription(e.target.value)}
          placeholder="e.g. College students interested in fitness"
          className="w-full rounded-md border border-ink-600 bg-ink-800 px-4 py-2 text-sm text-slate-200 placeholder:text-slate-600 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          disabled={busy}
        />
      </Card>

      <Card className="mt-6">
        <label className="label mb-3 block">Video file</label>
        
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={cn(
            "relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 transition-colors",
            isDragging ? "border-accent bg-accent/10" : "border-ink-600 hover:border-ink-500 hover:bg-ink-700/50",
            busy && "pointer-events-none opacity-50"
          )}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            className="hidden"
          />
          {file ? (
            <div className="text-center">
              <p className="text-sm font-medium text-slate-200">{file.name}</p>
              <p className="mt-1 text-xs text-slate-500">{fileSize(file.size)}</p>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-sm font-medium text-slate-200">Click to upload or drag and drop</p>
              <p className="mt-1 text-xs text-slate-500">MP4, MOV, WEBM up to 100MB</p>
            </div>
          )}
        </div>

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
        <div className="mt-6 space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
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

            <blockquote className="mt-4 border-l-2 border-accent/50 pl-4 text-sm italic text-slate-300">
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
      <div className="label text-slate-500">{label}</div>
      <div className="text-sm text-slate-300">{value}</div>
    </div>
  );
}
