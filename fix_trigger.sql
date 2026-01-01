-- Alternative solution: Modify the trigger to allow the function to work
-- Run this AFTER running create_database_function.sql if the function still doesn't work
-- This modifies the trigger to check if the update is coming from our function

-- First, find the trigger name (you may need to adjust this)
-- Check in Supabase: Database -> Triggers -> find the one on 'profiles' table related to roles

-- Example: If your trigger is named 'check_role_permission', you would modify it like this:
/*
CREATE OR REPLACE FUNCTION check_role_permission()
RETURNS TRIGGER AS $$
BEGIN
    -- Allow updates if called from update_user_role function
    IF current_setting('app.bypass_role_check', true) = 'true' THEN
        RETURN NEW;
    END IF;
    
    -- Your existing trigger logic here...
    -- Only administrators can change user roles
    IF (TG_OP = 'UPDATE' AND OLD.role IS DISTINCT FROM NEW.role) THEN
        -- Check if current user is admin (your existing logic)
        -- ...
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
*/

-- OR, simpler: Disable/Modify the trigger entirely if you trust the function
-- (Only do this if you're sure the function has proper security)
/*
-- Find trigger name first:
SELECT tgname FROM pg_trigger WHERE tgrelid = 'profiles'::regclass;

-- Then disable it (replace 'trigger_name' with actual name):
ALTER TABLE profiles DISABLE TRIGGER trigger_name;
*/

