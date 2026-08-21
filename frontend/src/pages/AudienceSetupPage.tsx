import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Button, Card, ErrorNote, Field, Loading, PageHeader } from '@/components/ui';
import { useAsync } from '@/hooks/useAsync';
import { useLabState } from '@/hooks/useLabState';
import { discoverAudience } from '@/services/reellabApi';
import type { AudienceRequest } from '@/types';

/**
 * Step 1 — the creator's brief.
 *
 * This is the only input the entire pipeline gets. Everything downstream —
 * sub-niches, personas, simulation, bottlenecks, counterfactuals — is derived
 * from these six fields.
 */
const BLANK: AudienceRequest = {
  niche: '',
  targetAudience: '',
  secondaryAudience: '',
  location: '',
  language: '',
  creatorGoal: '',
};

const EXAMPLE: AudienceRequest = {
  niche: 'fitness',
  targetAudience: 'natural bodybuilding beginners',
  secondaryAudience: 'college students interested in fitness',
  location: 'India',
  language: 'English',
  creatorGoal: 'increase reach among beginners',
};

export default function AudienceSetupPage() {
  const navigate = useNavigate();
  const { setRequest, setGraph } = useLabState();
  const [form, setForm] = useState<AudienceRequest>(BLANK);

  const discovery = useAsync(discoverAudience);

  const canSubmit =
    form.niche.trim() !== '' &&
    form.targetAudience.trim() !== '' &&
    form.location.trim() !== '' &&
    form.language.trim() !== '' &&
    form.creatorGoal.trim() !== '';

  const update = (key: keyof AudienceRequest) => (value: string) =>
    setForm((previous) => ({ ...previous, [key]: value }));

  async function submit() {
    setRequest(form);
    const graph = await discovery.run(form);
    if (graph) {
      setGraph(graph);
      navigate('/segments');
    }
  }

  return (
    <>
      <PageHeader
        title="Audience Setup"
        description="Describe who you are making this for. The AI discovers the sub-niches inside that audience and builds a synthetic viewer for each one."
        action={
          <Button variant="ghost" onClick={() => setForm(EXAMPLE)}>
            Fill example
          </Button>
        }
      />

      <Card>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label="Niche"
            required
            value={form.niche}
            onChange={update('niche')}
            placeholder="fitness"
          />
          <Field
            label="Location"
            required
            value={form.location}
            onChange={update('location')}
            placeholder="India"
          />
          <Field
            label="Target audience"
            required
            value={form.targetAudience}
            onChange={update('targetAudience')}
            placeholder="natural bodybuilding beginners"
            hint="In your own words. The more specific, the better the segmentation."
          />
          <Field
            label="Secondary audience"
            value={form.secondaryAudience ?? ''}
            onChange={update('secondaryAudience')}
            placeholder="college students interested in fitness"
            hint="Optional. Often the segment that actually spreads your reel."
          />
          <Field
            label="Language"
            required
            value={form.language}
            onChange={update('language')}
            placeholder="English"
          />
          <Field
            label="Creator goal"
            required
            value={form.creatorGoal}
            onChange={update('creatorGoal')}
            placeholder="increase reach among beginners"
            hint="What you are optimising for. Segments are scored against this."
          />
        </div>

        <div className="mt-6 flex items-center gap-4">
          <Button onClick={submit} disabled={!canSubmit || discovery.state === 'loading'}>
            {discovery.state === 'loading' ? 'Discovering…' : 'Discover audience'}
          </Button>
          {!canSubmit && (
            <span className="text-xs text-slate-500">Fill the required fields to continue.</span>
          )}
        </div>

        {discovery.state === 'loading' && <Loading label="Finding sub-niches…" />}
        {discovery.state === 'error' && discovery.error && (
          <div className="mt-4">
            <ErrorNote message={discovery.error} code={discovery.errorCode} />
          </div>
        )}
      </Card>
    </>
  );
}
