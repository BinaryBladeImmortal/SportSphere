-- Update team logo URLs for FC Goa and Bengaluru FC
UPDATE teams 
SET logo_url = CASE team_id
    WHEN 3 THEN '/static/images/teams/benglaru_fc.png'  -- Bengaluru FC
    WHEN 7 THEN '/static/images/teams/fc_goa.png'       -- FC Goa
END
WHERE team_id IN (3, 7); 