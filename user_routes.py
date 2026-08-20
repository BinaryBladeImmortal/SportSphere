from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from functools import wraps
from db import get_db

user_bp = Blueprint('user', __name__)

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            flash('You need to be logged in to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrap

@user_bp.route('/dashboard')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db()
    cur = db.cursor()
    
    # Get total teams count
    cur.execute('SELECT COUNT(*) FROM teams')
    teams_count = cur.fetchone()[0]
    
    # Get total players count
    cur.execute('SELECT COUNT(*) FROM players')
    players_count = cur.fetchone()[0]
    
    # Get upcoming matches count
    cur.execute("SELECT COUNT(*) FROM matches WHERE status = 'SCHEDULED'")
    upcoming_matches = cur.fetchone()[0]
    
    cur.close()
    
    return render_template('user_dashboard.html', 
                           teams_count=teams_count,
                           players_count=players_count,
                           upcoming_matches=upcoming_matches)

@user_bp.route('/user/teams')
@login_required
def user_teams():
    db = get_db()
    cur = db.cursor()

    # Get filter parameters from the request
    league_id = request.args.get('league_id')
    country_id = request.args.get('country_id')

    # Fetch available leagues and countries for filtering
    cur.execute('SELECT league_id, name FROM leagues')
    leagues = cur.fetchall()

    cur.execute('SELECT country_id, name FROM countries ORDER BY country_id ASC')
    countries = cur.fetchall()

    # Build the base query
    query = """
        SELECT team_id, name, logo_url 
        FROM teams
        WHERE 1=1
    """
    filters = []

    # Add filters based on the selected values
    if league_id:
        query += " AND league_id = %s"
        filters.append(league_id)
    if country_id:
        query += " AND nationality = (SELECT name FROM countries WHERE country_id = %s)"
        filters.append(country_id)

    query += " LIMIT %s OFFSET %s"
    filters.append(20)
    filters.append((request.args.get('page', 1, type=int) - 1) * 20)

    cur.execute(query, filters)
    teams = cur.fetchall()

    cur.execute('SELECT COUNT(*) FROM teams WHERE 1=1 ' + (' AND league_id = %s' if league_id else '') + (' AND nationality = (SELECT name FROM countries WHERE country_id = %s)' if country_id else ''), filters[:-2])
    total_teams = cur.fetchone()[0]
    cur.close()

    total_pages = (total_teams + 19) // 20

    return render_template('user_teams.html', teams=teams, page=request.args.get('page', 1, type=int), total_pages=total_pages, leagues=leagues, countries=countries, max=max, min=min, str=str)

@user_bp.route('/user/players')
@login_required
def user_players():
    db = get_db()
    cur = db.cursor()

    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    # Get filter parameters from the request
    league_id = request.args.get('league_id')
    country_id = request.args.get('country_id')
    team_id = request.args.get('team_id')
    position = request.args.get('position')

    # Fetch available leagues, countries, teams, and positions for filtering
    cur.execute('SELECT league_id, name FROM leagues')
    leagues = cur.fetchall()

    cur.execute('SELECT country_id, name FROM countries ORDER BY country_id ASC')
    countries = cur.fetchall()

    cur.execute('SELECT team_id, name FROM teams')
    teams = cur.fetchall()

    positions = ['Goalkeeper', 'Defence', 'Midfield', 'Offence']

    # Build the base query
    query = """
        SELECT DISTINCT p.player_id, p.name, p.position, t.logo_url, t.name, c.flag_url,
               COALESCE(s.goals, 0) as goals,
               COALESCE(s.assists, 0) as assists
        FROM players p
        JOIN teams t ON p.team_id = t.team_id
        JOIN countries c ON p.nationality = c.name
        LEFT JOIN scorers s ON p.player_id = s.player_id
        WHERE 1=1
    """
    filters = []

    # Add filters based on the selected values
    if league_id:
        query += " AND t.league_id = %s"
        filters.append(league_id)
    if country_id:
        query += " AND c.country_id = %s"
        filters.append(country_id)
    if team_id:
        query += " AND p.team_id = %s"
        filters.append(team_id)
    if position:
        query += " AND p.position = %s"
        filters.append(position)

    query += " ORDER BY COALESCE(s.goals, 0) DESC, COALESCE(s.assists, 0) DESC"
    query += " LIMIT %s OFFSET %s"
    filters.append(per_page)
    filters.append(offset)

    cur.execute(query, filters)
    players = cur.fetchall()

    cur.execute('SELECT COUNT(*) FROM players p JOIN teams t ON p.team_id = t.team_id JOIN countries c ON p.nationality = c.name WHERE 1=1' + (' AND t.league_id = %s' if league_id else '') + (' AND c.country_id = %s' if country_id else '') + (' AND p.team_id = %s' if team_id else '') + (' AND p.position = %s' if position else ''), filters[:-2])
    total_players = cur.fetchone()[0]
    cur.close()

    total_pages = (total_players + per_page - 1) // per_page

    return render_template('user_players.html', players=players, page=page, total_pages=total_pages, leagues=leagues, countries=countries, teams=teams, positions=positions, max=max, min=min, str=str)

@user_bp.route('/user/leagues')
@login_required
def user_leagues():
    db = get_db()
    cur = db.cursor()
    cur.execute('''
        SELECT l.league_id, l.name, c.flag_url, l.icon_url
        FROM leagues l
        JOIN countries c ON l.country_id = c.country_id
    ''')
    leagues = cur.fetchall()
    cur.close()

    return render_template('user_leagues.html', leagues=leagues)
    
@user_bp.route('/user/matches')
@login_required
def user_matches():
    db = get_db()
    cur = db.cursor()
    
    # Get all matches with team names and scores
    cur.execute("""
        SELECT m.match_id, ht.name as home_team, at.name as away_team,
               s.full_time_home, s.full_time_away, m.utc_date::date,
               ht.logo_url as home_logo, at.logo_url as away_logo,
               m.matchday, m.status
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.team_id
        JOIN teams at ON m.away_team_id = at.team_id
        LEFT JOIN scores s ON m.match_id = s.match_id
        ORDER BY m.utc_date DESC
    """)
    matches = cur.fetchall()
    
    # Get leagues for filter
    cur.execute('SELECT league_id, name FROM leagues ORDER BY name')
    leagues = cur.fetchall()
    
    # Get countries for filter
    cur.execute('SELECT country_id, name FROM countries ORDER BY name')
    countries = cur.fetchall()
    
    # Get teams for filter
    cur.execute('SELECT team_id, name FROM teams ORDER BY name')
    teams = cur.fetchall()
    
    # Get unique matchdays
    cur.execute('SELECT DISTINCT matchday FROM matches ORDER BY matchday')
    matchdays = [row[0] for row in cur.fetchall()]
    
    cur.close()
    return render_template('user_matches.html', 
                         matches=matches, 
                         leagues=leagues, 
                         countries=countries, 
                         teams=teams, 
                         matchdays=matchdays,
                         str=str)

@user_bp.route('/team/<int:team_id>')
@login_required
def profile_team(team_id):
    db = get_db()
    cur = db.cursor()

    # Get team details along with stadium, coach, league, and flags
    cur.execute("""
        SELECT 
            t.name,
            t.founded_year,
            s.name AS stadium_name, 
            c.name AS coach_name, 
            l.name AS league_name, 
            t.logo_url, 
            co.flag_url
        FROM teams t 
        LEFT JOIN stadiums s ON t.stadium_id = s.stadium_id 
        LEFT JOIN coaches c ON t.team_id = c.team_id 
        LEFT JOIN countries co ON LOWER(c.nationality) = LOWER(co.name)  -- Case-insensitive join
        LEFT JOIN leagues l ON t.league_id = l.league_id
        WHERE t.team_id = %s
    """, (team_id,))
    team = cur.fetchone()
    print(f"Team data: {team}")

    # Get team's players with nationality flags
    cur.execute("""
        SELECT 
            p.player_id, 
            p.name, 
            p.position, 
            p.date_of_birth, 
            p.nationality,
            co.flag_url
        FROM players p
        LEFT JOIN countries co ON LOWER(p.nationality) = LOWER(co.name)  -- Case-insensitive join
        WHERE p.team_id = %s
        ORDER BY p.name
    """, (team_id,))
    players = cur.fetchall()
    
    # Debug logging
    print("\nDetailed data:")
    print(f"Coach nationality in teams query: {team[3] if team else 'No team data'}")
    print(f"Coach flag URL in teams query: {team[6] if team else 'No team data'}")
    print("\nPlayers data:")
    for player in players:
        print(f"Player: {player[1]}, Nationality: {player[4]}, Flag URL: {player[5]}")

    # Get team's recent matches
    cur.execute("""
        SELECT m.match_id, 
               t1.name AS home_team_name, 
               t2.name AS away_team_name, 
               s.home_score, 
               s.away_score,
               TO_CHAR(m.utc_date, 'Month DD, YYYY') AS formatted_date
        FROM matches m
        JOIN teams t1 ON m.home_team_id = t1.team_id
        JOIN teams t2 ON m.away_team_id = t2.team_id
        LEFT JOIN scores s ON m.match_id = s.match_id
        WHERE m.home_team_id = %s OR m.away_team_id = %s
        ORDER BY m.utc_date DESC
        LIMIT 5
    """, (team_id, team_id))
    recent_matches = cur.fetchall()

    cur.close()

    return render_template('profile_team.html', team=team, players=players, recent_matches=recent_matches)

@user_bp.route('/player/<int:player_id>')
@login_required
def profile_player(player_id):
    db = get_db()
    cur = db.cursor()

    # Fetch player details
    cur.execute("""
        SELECT p.name, p.date_of_birth, p.position, t.team_id, t.name AS team_name, c.flag_url, c.name AS nationality, p.image_url
        FROM players p 
        JOIN teams t ON p.team_id = t.team_id 
        JOIN countries c ON p.nationality = c.name
        WHERE p.player_id = %s
    """, (player_id,))
    player = cur.fetchone()

    # Fetch player statistics if they are in the top scorers list
    cur.execute("""
        SELECT sc.goals, sc.assists, sc.penalties
        FROM scorers sc
        WHERE sc.player_id = %s
    """, (player_id,))
    statistics = cur.fetchone()

    cur.close()

    if player:
        return render_template('profile_player.html', player=player, statistics=statistics)
    else:
        flash('Player not found', 'error')
        return redirect(url_for('user.user_dashboard'))

@user_bp.route('/match/<int:match_id>')
@login_required
def profile_match(match_id):
    db = get_db()
    cur = db.cursor()
    print(f"Fetching match with ID: {match_id}")
    
    # Get match details with team and referee information
    cur.execute('''
        SELECT m.match_id, m.home_team_id, m.away_team_id, 
               s.full_time_home, s.full_time_away, s.half_time_home, s.half_time_away,
               m.utc_date, 
               ht.logo_url as home_logo, at.logo_url as away_logo,
               st.name as stadium,
               r.name as referee_name, c.flag_url as referee_country_flag,
               ht.name as home_team_name, at.name as away_team_name,
               m.status
        FROM matches m
        LEFT JOIN scores s ON m.match_id = s.match_id
        JOIN teams ht ON m.home_team_id = ht.team_id
        JOIN teams at ON m.away_team_id = at.team_id
        LEFT JOIN stadiums st ON m.stadium_id = st.stadium_id
        LEFT JOIN match_referees mr ON m.match_id = mr.match_id
        LEFT JOIN referees r ON mr.referee_id = r.referee_id
        LEFT JOIN countries c ON r.nationality = c.name
        WHERE m.match_id = %s
    ''', (match_id,))
    match = cur.fetchone()
    print("Match data:", match)

    # Get goals for this match
    cur.execute('''
        SELECT g.minute, p.name as scorer_name, g.team_id, g.is_penalty, g.is_own_goal
        FROM goals g
        JOIN players p ON g.player_id = p.player_id
        WHERE g.match_id = %s
        ORDER BY g.minute
    ''', (match_id,))
    goals = [dict(zip(['minute', 'scorer_name', 'team_id', 'is_penalty', 'is_own_goal'], row)) 
            for row in cur.fetchall()]
            
    # Get top 3 scoring players from each team for the MOTM voting
    home_team_id = match[1]
    away_team_id = match[2]
    
    # Get top scorers from home team
    cur.execute('''
        SELECT p.player_id, p.name, COUNT(g.goal_id) as goals
        FROM players p
        LEFT JOIN goals g ON p.player_id = g.player_id
        WHERE p.team_id = %s
        GROUP BY p.player_id, p.name
        ORDER BY goals DESC
        LIMIT 3
    ''', (home_team_id,))
    home_team_top_scorers = cur.fetchall()
    
    # Get top scorers from away team
    cur.execute('''
        SELECT p.player_id, p.name, COUNT(g.goal_id) as goals
        FROM players p
        LEFT JOIN goals g ON p.player_id = g.player_id
        WHERE p.team_id = %s
        GROUP BY p.player_id, p.name
        ORDER BY goals DESC
        LIMIT 3
    ''', (away_team_id,))
    away_team_top_scorers = cur.fetchall()
    
    # If we don't have 3 players with goals, get the top 3 players from each team regardless of goals
    if len(home_team_top_scorers) < 3:
        cur.execute('''
            SELECT p.player_id, p.name, 0 as goals
            FROM players p
            WHERE p.team_id = %s
            ORDER BY p.name
            LIMIT %s
        ''', (home_team_id, 3 - len(home_team_top_scorers)))
        home_team_top_scorers.extend(cur.fetchall())
    
    if len(away_team_top_scorers) < 3:
        cur.execute('''
            SELECT p.player_id, p.name, 0 as goals
            FROM players p
            WHERE p.team_id = %s
            ORDER BY p.name
            LIMIT %s
        ''', (away_team_id, 3 - len(away_team_top_scorers)))
        away_team_top_scorers.extend(cur.fetchall())

    cur.close()
    return render_template('profile_match.html', match=match, goals=goals, 
                          home_team_top_scorers=home_team_top_scorers,
                          away_team_top_scorers=away_team_top_scorers)

@user_bp.route('/league/<int:league_id>')
@login_required
def profile_league(league_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT l.name, c.name AS country, l.icon_url, c.flag_url, l.cl_spot, l.uel_spot, l.relegation_spot
        FROM leagues l
        JOIN countries c ON l.country_id = c.country_id
        WHERE l.league_id = %s
    """, (league_id,))
    league = cur.fetchone()

    cur.execute('SELECT team_id, name, logo_url FROM teams WHERE league_id = %s', (league_id,))
    teams = cur.fetchall()

    cur.execute("""
        SELECT s.position, s.team_id, t.name AS team_name, s.played_games, s.won, s.draw, s.lost, 
               s.points, s.goals_for, s.goals_against, s.goal_difference, s.form, t.logo_url,
               CASE WHEN s.position <= l.cl_spot THEN TRUE ELSE FALSE END AS cl_spot,
               CASE WHEN s.position > l.cl_spot AND s.position <= l.uel_spot THEN TRUE ELSE FALSE END AS uel_spot,
               CASE WHEN s.position >= l.relegation_spot THEN TRUE ELSE FALSE END AS relegation_spot
        FROM standings s
        JOIN teams t ON s.team_id = t.team_id
        JOIN leagues l ON s.league_id = l.league_id
        WHERE s.league_id = %s
        ORDER BY s.position
    """, (league_id,))
    standings = cur.fetchall()

    cur.close()

    return render_template('profile_league.html', league=league, teams=teams, standings=standings)

@user_bp.route('/user/scorers')
@login_required
def user_scorers():
    db = get_db()
    cur = db.cursor()

    # Get filter parameters from the request
    league_id = request.args.get('league_id')
    country_id = request.args.get('country_id')
    team_id = request.args.get('team_id')

    # Fetch available leagues, countries, and teams for filtering
    cur.execute('SELECT league_id, name FROM leagues')
    leagues = cur.fetchall()

    cur.execute('SELECT country_id, name FROM countries ORDER BY country_id ASC')
    countries = cur.fetchall()

    cur.execute('SELECT team_id, name FROM teams')
    teams = cur.fetchall()

    # Build the base query
    query = """
        SELECT sc.scorer_id, p.name, sc.goals, sc.assists, sc.penalties, t.logo_url, c.name AS nationality
        FROM scorers sc
        JOIN players p ON sc.player_id = p.player_id
        JOIN teams t ON p.team_id = t.team_id
        JOIN countries c ON p.nationality = c.name
        WHERE 1=1
    """
    filters = []

    # Add filters based on the selected values
    if league_id:
        query += " AND sc.league_id = %s"
        filters.append(league_id)
    if country_id:
        query += " AND c.country_id = %s"
        filters.append(country_id)
    if team_id:
        query += " AND p.team_id = %s"
        filters.append(team_id)

    query += " ORDER BY sc.goals DESC"

    cur.execute(query, filters)
    scorers = cur.fetchall()
    cur.close()

    return render_template('user_scorers.html', scorers=scorers, leagues=leagues, countries=countries, teams=teams, str=str)

@user_bp.route('/isl_stats')
def isl_stats():
    # Get ISL top scorers
    isl_scorers_query = """
    SELECT * FROM top_isl_scorers LIMIT 20
    """
    isl_scorers = database_execute_fetch(isl_scorers_query)
    
    # Get ISL teams
    isl_teams_query = """
    SELECT t.team_id, t.name, t.logo_url, COUNT(m.match_id) as matches_played,
           SUM(CASE WHEN m.home_team_id = t.team_id AND s.full_time_home > s.full_time_away THEN 1
                    WHEN m.away_team_id = t.team_id AND s.full_time_away > s.full_time_home THEN 1
                    ELSE 0 END) as wins,
           SUM(CASE WHEN s.full_time_home = s.full_time_away THEN 1 ELSE 0 END) as draws,
           SUM(CASE WHEN m.home_team_id = t.team_id AND s.full_time_home < s.full_time_away THEN 1
                    WHEN m.away_team_id = t.team_id AND s.full_time_away < s.full_time_home THEN 1
                    ELSE 0 END) as losses
    FROM teams t
    JOIN matches m ON t.team_id = m.home_team_id OR t.team_id = m.away_team_id
    JOIN scores s ON m.match_id = s.match_id
    WHERE m.league_id = 3
    GROUP BY t.team_id, t.name, t.logo_url
    ORDER BY wins DESC, draws DESC
    """
    isl_teams = database_execute_fetch(isl_teams_query)
    
    # Get recent ISL matches
    recent_matches_query = """
    SELECT 
        m.match_id, 
        ht.name as home_team, 
        ht.logo_url as home_logo,
        at.name as away_team,
        at.logo_url as away_logo,
        s.full_time_home,
        s.full_time_away,
        m.utc_date,
        stadium.name as stadium
    FROM matches m
    JOIN teams ht ON m.home_team_id = ht.team_id
    JOIN teams at ON m.away_team_id = at.team_id
    LEFT JOIN scores s ON m.match_id = s.match_id
    LEFT JOIN stadiums stadium ON m.stadium_id = stadium.stadium_id
    WHERE m.league_id = 3
    ORDER BY m.utc_date DESC
    LIMIT 10
    """
    recent_matches = database_execute_fetch(recent_matches_query)
    
    return render_template('isl_stats.html', 
                           scorers=isl_scorers, 
                           teams=isl_teams, 
                           matches=recent_matches,
                           title="Indian Super League Statistics")

@user_bp.route('/test_dashboard')
def test_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('test_user_dashboard.html')

@user_bp.route('/compare/players', methods=['GET', 'POST'])
@login_required
def compare_players():
    db = get_db()
    cur = db.cursor()
    
    # Get player IDs from request
    player1_id = request.args.get('player1_id', type=int)
    player2_id = request.args.get('player2_id', type=int)
    
    # Variables to store player data
    player1 = None
    player2 = None
    player1_stats = None
    player2_stats = None
    
    # Fetch all players for selection
    cur.execute("""
        SELECT p.player_id, p.name, t.name AS team_name, p.position
        FROM players p
        JOIN teams t ON p.team_id = t.team_id
        ORDER BY p.name
    """)
    all_players = cur.fetchall()
    
    # If both player IDs are provided, fetch their details
    if player1_id and player2_id:
        # Fetch player 1 details
        cur.execute("""
            SELECT p.name, p.date_of_birth, p.position, t.team_id, t.name AS team_name, 
                   c.flag_url, c.name AS nationality, p.image_url, p.player_id
            FROM players p 
            JOIN teams t ON p.team_id = t.team_id 
            JOIN countries c ON p.nationality = c.name
            WHERE p.player_id = %s
        """, (player1_id,))
        player1 = cur.fetchone()

        # Fetch player 1 statistics
        cur.execute("""
            SELECT sc.goals, sc.assists, sc.penalties
            FROM scorers sc
            WHERE sc.player_id = %s
        """, (player1_id,))
        player1_stats = cur.fetchone() or (0, 0, 0)
        
        # Fetch player 2 details
        cur.execute("""
            SELECT p.name, p.date_of_birth, p.position, t.team_id, t.name AS team_name, 
                   c.flag_url, c.name AS nationality, p.image_url, p.player_id
            FROM players p 
            JOIN teams t ON p.team_id = t.team_id 
            JOIN countries c ON p.nationality = c.name
            WHERE p.player_id = %s
        """, (player2_id,))
        player2 = cur.fetchone()

        # Fetch player 2 statistics
        cur.execute("""
            SELECT sc.goals, sc.assists, sc.penalties
            FROM scorers sc
            WHERE sc.player_id = %s
        """, (player2_id,))
        player2_stats = cur.fetchone() or (0, 0, 0)
    
    cur.close()
    
    return render_template('compare_players.html', 
                          player1=player1, player2=player2,
                          player1_stats=player1_stats, player2_stats=player2_stats,
                          all_players=all_players)

@user_bp.route('/compare/teams', methods=['GET', 'POST'])
@login_required
def compare_teams():
    db = get_db()
    cur = db.cursor()
    
    # Get team IDs from request
    team1_id = request.args.get('team1_id', type=int)
    team2_id = request.args.get('team2_id', type=int)
    
    # Variables to store team data
    team1 = None
    team2 = None
    team1_players = None
    team2_players = None
    team1_stats = None
    team2_stats = None
    
    # Fetch all teams for selection
    cur.execute("""
        SELECT team_id, name, league_id
        FROM teams
        ORDER BY name
    """)
    all_teams = cur.fetchall()
    
    # If both team IDs are provided, fetch their details
    if team1_id and team2_id:
        # Fetch team 1 details
        cur.execute("""
            SELECT t.team_id, t.name, t.founded_year, s.name AS stadium_name, 
                  c.name AS coach_name, l.name AS league_name, 
                  t.logo_url, co.flag_url
            FROM teams t 
            LEFT JOIN stadiums s ON t.stadium_id = s.stadium_id 
            LEFT JOIN coaches c ON t.team_id = c.team_id 
            LEFT JOIN countries co ON LOWER(c.nationality) = LOWER(co.name)
            LEFT JOIN leagues l ON t.league_id = l.league_id
            WHERE t.team_id = %s
        """, (team1_id,))
        team1 = cur.fetchone()
        
        # Fetch team 2 details
        cur.execute("""
            SELECT t.team_id, t.name, t.founded_year, s.name AS stadium_name, 
                  c.name AS coach_name, l.name AS league_name, 
                  t.logo_url, co.flag_url
            FROM teams t 
            LEFT JOIN stadiums s ON t.stadium_id = s.stadium_id 
            LEFT JOIN coaches c ON t.team_id = c.team_id 
            LEFT JOIN countries co ON LOWER(c.nationality) = LOWER(co.name)
            LEFT JOIN leagues l ON t.league_id = l.league_id
            WHERE t.team_id = %s
        """, (team2_id,))
        team2 = cur.fetchone()
        
        # Fetch team 1 players
        cur.execute("""
            SELECT p.player_id, p.name, p.position, 
                  COUNT(DISTINCT g.goal_id) as goals,
                  COALESCE(s.assists, 0) as assists
            FROM players p
            LEFT JOIN goals g ON p.player_id = g.player_id
            LEFT JOIN scorers s ON p.player_id = s.player_id
            WHERE p.team_id = %s
            GROUP BY p.player_id, p.name, p.position, s.assists
            ORDER BY goals DESC, assists DESC
        """, (team1_id,))
        team1_players = cur.fetchall()
        
        # Fetch team 2 players
        cur.execute("""
            SELECT p.player_id, p.name, p.position, 
                  COUNT(DISTINCT g.goal_id) as goals,
                  COALESCE(s.assists, 0) as assists
            FROM players p
            LEFT JOIN goals g ON p.player_id = g.player_id
            LEFT JOIN scorers s ON p.player_id = s.player_id
            WHERE p.team_id = %s
            GROUP BY p.player_id, p.name, p.position, s.assists
            ORDER BY goals DESC, assists DESC
        """, (team2_id,))
        team2_players = cur.fetchall()
        
        # Fetch team 1 stats
        cur.execute("""
            SELECT 
                COUNT(CASE WHEN (m.home_team_id = %s AND sc.home_score > sc.away_score) OR
                            (m.away_team_id = %s AND sc.away_score > sc.home_score) 
                      THEN 1 END) as wins,
                COUNT(CASE WHEN (m.home_team_id = %s OR m.away_team_id = %s) AND
                            sc.home_score = sc.away_score
                      THEN 1 END) as draws,
                COUNT(CASE WHEN (m.home_team_id = %s AND sc.home_score < sc.away_score) OR
                            (m.away_team_id = %s AND sc.away_score < sc.home_score)
                      THEN 1 END) as losses,
                SUM(CASE WHEN m.home_team_id = %s THEN sc.home_score
                         WHEN m.away_team_id = %s THEN sc.away_score
                         ELSE 0 END) as goals_scored,
                SUM(CASE WHEN m.home_team_id = %s THEN sc.away_score
                         WHEN m.away_team_id = %s THEN sc.home_score
                         ELSE 0 END) as goals_conceded
            FROM matches m
            JOIN scores sc ON m.match_id = sc.match_id
            WHERE (m.home_team_id = %s OR m.away_team_id = %s)
              AND m.status = 'FINISHED'
        """, (team1_id, team1_id, team1_id, team1_id, team1_id, team1_id, team1_id, team1_id, team1_id, team1_id, team1_id, team1_id))
        team1_stats = cur.fetchone()
        
        # Fetch team 2 stats
        cur.execute("""
            SELECT 
                COUNT(CASE WHEN (m.home_team_id = %s AND sc.home_score > sc.away_score) OR
                            (m.away_team_id = %s AND sc.away_score > sc.home_score) 
                      THEN 1 END) as wins,
                COUNT(CASE WHEN (m.home_team_id = %s OR m.away_team_id = %s) AND
                            sc.home_score = sc.away_score
                      THEN 1 END) as draws,
                COUNT(CASE WHEN (m.home_team_id = %s AND sc.home_score < sc.away_score) OR
                            (m.away_team_id = %s AND sc.away_score < sc.home_score)
                      THEN 1 END) as losses,
                SUM(CASE WHEN m.home_team_id = %s THEN sc.home_score
                         WHEN m.away_team_id = %s THEN sc.away_score
                         ELSE 0 END) as goals_scored,
                SUM(CASE WHEN m.home_team_id = %s THEN sc.away_score
                         WHEN m.away_team_id = %s THEN sc.home_score
                         ELSE 0 END) as goals_conceded
            FROM matches m
            JOIN scores sc ON m.match_id = sc.match_id
            WHERE (m.home_team_id = %s OR m.away_team_id = %s)
              AND m.status = 'FINISHED'
        """, (team2_id, team2_id, team2_id, team2_id, team2_id, team2_id, team2_id, team2_id, team2_id, team2_id, team2_id, team2_id))
        team2_stats = cur.fetchone()
        
        # Fetch head-to-head history
        cur.execute("""
            SELECT 
                m.match_id, m.utc_date as match_date, sc.home_score, sc.away_score,
                ht.name as home_team_name, at.name as away_team_name
            FROM matches m
            JOIN teams ht ON m.home_team_id = ht.team_id
            JOIN teams at ON m.away_team_id = at.team_id
            JOIN scores sc ON m.match_id = sc.match_id
            WHERE ((m.home_team_id = %s AND m.away_team_id = %s) OR
                  (m.home_team_id = %s AND m.away_team_id = %s))
              AND m.status = 'FINISHED'
            ORDER BY m.utc_date DESC
            LIMIT 5
        """, (team1_id, team2_id, team2_id, team1_id))
        h2h_matches = cur.fetchall()
        
        # Calculate head-to-head summary
        team1_wins = 0
        team2_wins = 0
        draws = 0
        
        if h2h_matches:
            for match in h2h_matches:
                # Check if scores are not None before comparing
                if match[2] is not None and match[3] is not None:
                    if match[2] > match[3]:  # home team won
                        if match[4] == team1[1]:
                            team1_wins += 1
                        else:
                            team2_wins += 1
                    elif match[2] < match[3]:  # away team won
                        if match[5] == team1[1]:
                            team1_wins += 1
                        else:
                            team2_wins += 1
                    else:
                        draws += 1
        
    return render_template('compare_teams.html', 
                         all_teams=all_teams,
                         team1=team1,
                         team2=team2,
                         team1_players=team1_players,
                         team2_players=team2_players,
                         team1_stats=team1_stats,
                         team2_stats=team2_stats,
                         h2h_matches=h2h_matches if 'h2h_matches' in locals() else None,
                         team1_wins=team1_wins if 'team1_wins' in locals() else 0,
                         team2_wins=team2_wins if 'team2_wins' in locals() else 0,
                         draws=draws if 'draws' in locals() else 0)


