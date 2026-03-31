
ALTER TABLE public.video_requests
  ADD COLUMN mode text NOT NULL DEFAULT 'prompt',
  ADD COLUMN github_url text;
