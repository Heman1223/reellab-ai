import { useState, useRef, useEffect } from 'react';
import type { DragEvent } from 'react';

import { Badge, Button, Card, ErrorNote, Loading, MockBanner, PageHeader } from '@/components/ui';
import { useAsync } from '@/hooks/useAsync';
import { useLabState } from '@/hooks/useLabState';
import { analyzeReel, uploadReel, getConfig } from '@/services/reellabApi';
import { cn, fileSize, percent, seconds } from '@/utils/format';

/**
 * Step 3 — upload the reel and run multimodal analysis.
 */
export default function ReelUploadPage() {
  const { reel, contentDna, setReel, setContentDna, audienceDescription, setAudienceDescription } = useLabState();
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [maxUploadMb, setMaxUploadMb] = useState<number>(100);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const upload = useAsync(uploadReel);
  const analyze = useAsync(analyzeReel);

  useEffect(() => {
    getConfig().then(res => {
      if (res.data) setMaxUploadMb(res.data.maxUploadMb);
    }).catch(console.error);
  }, []);

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

  const checkFile = (dropped: File) => {
    if (dropped.size > maxUploadMb * 1024 * 1024) {
      alert(`File size exceeds the limit of ${maxUploadMb}MB`);
      return;
    }
    setFile(dropped);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped && dropped.type.startsWith('video/')) {
      checkFile(dropped);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      checkFile(selected);
    }
  };

  const busy = upload.state === 'loading' || analyze.state === 'loading';

  return (
    <>
      <PageHeader
        title="Reel Upload"
        description="Upload the reel you are about to publish. Multimodal analysis turns it into Content DNA — the description your synthetic audience reacts to."
      />

      <Card title="Target Audience (Optional)" subtitle="Describe your ideal viewers. We'll use this to generate the 10 distinct AI personas that will watch your reel.">
        <div className="relative mt-2 rounded-md shadow-sm border border-ink-600 focus-within:border-accent focus-within:ring-1 focus-within:ring-accent overflow-hidden transition-all duration-200">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-5 w-5 text-slate-400">
              <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
            </svg>
          </div>
          <input
            type="text"
            value={audienceDescription ?? ''}
            onChange={(e) => setAudienceDescription(e.target.value)}
            placeholder="e.g. College students interested in fitness"
            className="block w-full border-0 bg-slate-50 py-3 pl-10 pr-4 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-0 sm:leading-6"
            disabled={busy}
          />
        </div>
        <p className="mt-2 text-xs text-slate-500">Leave blank to let the AI infer the best audience for this reel automatically.</p>
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
            isDragging ? "border-accent bg-accent/10" : "border-ink-600 hover:border-ink-700 hover:bg-ink-700/20",
            busy && "pointer-events-none opacity-50"
          )}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            onChange={handleFileChange}
            className="hidden"
          />
          {file ? (
            <div className="text-center">
              <p className="text-sm font-medium text-slate-900">{file.name}</p>
              <p className="mt-1 text-xs text-slate-500">{fileSize(file.size)}</p>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-sm font-medium text-slate-900">Click to upload or drag and drop</p>
              <p className="mt-1 text-xs text-slate-500">MP4, MOV, WEBM up to {maxUploadMb}MB</p>
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

            <blockquote className="mt-4 border-l-2 border-accent/50 pl-4 text-sm italic text-slate-700 font-serif">
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
                    <span className="text-slate-700">{scene.description}</span>
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
      <div className="text-sm text-slate-700">{value}</div>
    </div>
  );
}
