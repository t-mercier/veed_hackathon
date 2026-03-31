-- Grant table-level permissions to authenticated role
GRANT SELECT, INSERT, UPDATE ON public.profiles TO authenticated;

-- Also grant to anon for the trigger (handle_new_user runs as SECURITY DEFINER so this may not be needed, but just in case)
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT USAGE ON SCHEMA public TO anon;