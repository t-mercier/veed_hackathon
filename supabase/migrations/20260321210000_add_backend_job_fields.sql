-- Add backend_job_id and job_type to video_requests
-- so the frontend can redirect to /repo/:jobId for repo results
ALTER TABLE public.video_requests
  ADD COLUMN IF NOT EXISTS backend_job_id TEXT,
  ADD COLUMN IF NOT EXISTS job_type TEXT;
