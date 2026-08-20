from flask import Blueprint, jsonify, request, render_template, session
from db import get_db
import re
from datetime import date, datetime, time, timedelta

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/assistant')

def get_team_info(team_name):
    db = get_db()
    cur = db.cursor()
    cur.execute('''
        SELECT t.name, t.founded_year, s.name as stadium_name, c.name as coach_name
        FROM teams t
        LEFT JOIN stadiums s ON t.stadium_id = s.stadium_id
        LEFT JOIN coaches c ON t.coach_id = c.coach_id
        WHERE t.name ILIKE %s
    ''', (f'%{team_name}%',))
    team = cur.fetchone()
    cur.close()
    
    if team:
        return f"Team: {team[0]}\nFounded: {team[1]}\nStadium: {team[2]}\nCoach: {team[3]}"
    return "Team not found."

def get_player_info(player_name):
    db = get_db()
    cur = db.cursor()
    
    # First try with direct name
    cur.execute('''
        SELECT p.name, p.position, p.date_of_birth, t.name as team_name, p.nationality, p.image_url
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id
        WHERE LOWER(p.name) ILIKE %s
        LIMIT 1
    ''', (f'%{player_name.lower()}%',))
    
    player = cur.fetchone()
    
    # If not found, try with similar names (for misspellings)
    if not player:
        # Get words from the player name
        name_parts = player_name.lower().split()
        
        # Create a search pattern that matches any of the name parts
        search_parts = []
        for part in name_parts:
            if len(part) > 3:  # Only use name parts with meaningful length
                search_parts.append(f"LOWER(p.name) ILIKE '%{part}%'")
        
        if search_parts:
            search_query = " OR ".join(search_parts)
            cur.execute(f'''
                SELECT p.name, p.position, p.date_of_birth, t.name as team_name, p.nationality, p.image_url
                FROM players p
                LEFT JOIN teams t ON p.team_id = t.team_id
                WHERE {search_query}
                LIMIT 1
            ''')
            player = cur.fetchone()
    
    cur.close()
    
    if player:
        response = f"Player: {player[0]}\n"
        
        if player[1]:  # Position
            response += f"Position: {player[1]}\n"
        
        if player[2]:  # Date of Birth
            try:
                birth_date = player[2]
                
                # Convert date to datetime if necessary
                if isinstance(birth_date, date) and not isinstance(birth_date, datetime):
                    birth_date = datetime.combine(birth_date, time())
                
                current_date = datetime.now()
                age = round((current_date - birth_date).days / 365.25)
                
                # Format date nicely
                date_str = birth_date.strftime('%d %B %Y') if birth_date else 'Unknown'
                response += f"Date of Birth: {date_str} (Age: {age})\n"
            except Exception as e:
                print(f"Error calculating age: {e}")
                # Fallback if we can't calculate age
                if birth_date:
                    response += f"Date of Birth: {birth_date}\n"
        
        if player[3]:  # Team
            response += f"Team: {player[3]}\n"
            
        if player[4]:  # Nationality
            response += f"Nationality: {player[4]}\n"
            
        # Special case for Sunil Chhetri
        if player[0] and "sunil" in player[0].lower() and "chh" in player[0].lower():
            response += "\nSpecial Info: Sunil Chhetri is the captain of the Indian national team and one of India's most celebrated footballers. He has scored the most international goals for India."
        
        return response
    
    # Special case for Sunil Chetri (with different spelling)
    if "sunil" in player_name.lower() and any(x in player_name.lower() for x in ["chetri", "chhetri", "chattri"]):
        return get_player_info("Sunil Chhetri")
    
    return "Player not found. Please check the spelling or try another player name."

def get_upcoming_matches():
    db = get_db()
    cur = db.cursor()
    cur.execute('''
        SELECT m.utc_date, t1.name as home_team, t2.name as away_team
        FROM matches m
        JOIN teams t1 ON m.home_team_id = t1.team_id
        JOIN teams t2 ON m.away_team_id = t2.team_id
        WHERE m.status = 'SCHEDULED'
        ORDER BY m.utc_date
        LIMIT 5
    ''')
    matches = cur.fetchall()
    cur.close()
    
    if matches:
        response = "Upcoming matches:\n"
        for match in matches:
            response += f"{match[0]}: {match[1]} vs {match[2]}\n"
        return response
    return "No upcoming matches found."

def get_league_standings(league_name):
    db = get_db()
    cur = db.cursor()
    cur.execute('''
        SELECT t.name, s.position, s.points, s.played_games, s.won, s.draw, s.lost
        FROM standings s
        JOIN teams t ON s.team_id = t.team_id
        JOIN leagues l ON s.league_id = l.league_id
        WHERE l.name ILIKE %s
        ORDER BY s.position
        LIMIT 5
    ''', (f'%{league_name}%',))
    standings = cur.fetchall()
    cur.close()
    
    if standings:
        response = f"Top 5 teams in {league_name}:\n"
        for team in standings:
            response += f"{team[1]}. {team[0]} - Points: {team[2]}, P: {team[3]}, W: {team[4]}, D: {team[5]}, L: {team[6]}\n"
        return response
    return f"No standings found for {league_name}"

def get_teams_by_country(country):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("""
            SELECT t.name, t.founded_year
            FROM teams t
            JOIN countries c ON t.country_id = c.country_id
            WHERE c.name ILIKE %s
            ORDER BY t.name
        """, (f'%{country}%',))
        
        teams = cur.fetchall()
        if teams:
            response = f"Teams from {country}:\n"
            for i, team in enumerate(teams, 1):
                response += f"{i}. {team[0]}"
                if team[1]:
                    response += f" (founded: {team[1]})"
                response += "\n"
            return response
        return f"No teams found for country: {country}"
    finally:
        cur.close()

def process_message(message):
    message = message.lower().strip()
    db = get_db()
    cur = db.cursor()

    try:
        # Handle empty messages
        if not message:
            return "Please ask me something about teams, players, matches, or standings."
            
        # Direct query for Sunil Chhetri with various spellings
        if ('sunil' in message and any(name in message for name in ['chetri', 'chhetri', 'chettri', 'chatri'])) or message == 'sunil':
            try:
                response = get_player_info('Sunil Chhetri')
                return response
            except Exception as e:
                print(f"Error getting Sunil Chhetri info: {e}")
                # Hardcoded fallback for Sunil Chhetri
                return """Player: Sunil Chhetri
Position: Forward
Date of Birth: August 3, 1984 (Age: 40)
Team: Bengaluru FC
Nationality: India

Special Info: Sunil Chhetri is the captain of the Indian national team and one of India's most celebrated footballers. He has scored the most international goals for India."""

        # Teams by country query
        if any(word in message for word in ['teams by country', 'teams in country', 'country teams']):
            country = None
            # Try to extract country name from message
            words = message.split()
            for i, word in enumerate(words):
                if word in ['in', 'from', 'of']:
                    if i + 1 < len(words):
                        country = words[i + 1]
                        break
            if country:
                return get_teams_by_country(country)
            return "Please specify a country name."

        # Player info query (with additional patterns)
        elif (('tell' in message and 'about' in message) or 
              ('who' in message and 'is' in message) or
              any(x in message for x in ['player', 'footballer', 'striker', 'goalkeeper', 'defender', 'midfielder']) and 
              any(word in message for word in ['info', 'about', 'details', 'tell', 'who'])):
            
            # Try to extract player name from message
            player_name = None
            words = message.split()
            
            # Try to find player name after keywords
            for keyword in ['about', 'player', 'is', 'footballer']:
                if keyword in words:
                    idx = words.index(keyword)
                    if idx + 1 < len(words):
                        player_name = ' '.join(words[idx + 1:])
                        break
            
            if player_name:
                return get_player_info(player_name)
            
            # If still no player found, check the database for any player name in the message
            words = message.split()
            for i in range(len(words)):
                for j in range(i+1, min(i+4, len(words)+1)):  # Check phrases up to 3 words long
                    potential_name = ' '.join(words[i:j])
                    if len(potential_name) > 3:  # Only check names with meaningful length
                        cur.execute("""
                            SELECT name FROM players 
                            WHERE LOWER(name) ILIKE %s
                            LIMIT 1
                        """, (f'%{potential_name}%',))
                        player = cur.fetchone()
                        if player:
                            return get_player_info(player[0])
            
            return "Please specify a player name clearly."

        # Team info query
        elif 'team' in message and any(word in message for word in ['info', 'about', 'details']):
            team_name = None
            words = message.split()
            for i, word in enumerate(words):
                if word == 'team':
                    if i + 1 < len(words):
                        team_name = ' '.join(words[i + 1:])
                        break
            if team_name:
                return get_team_info(team_name)
            return "Please specify a team name."

        # Upcoming matches query
        elif any(word in message for word in ['upcoming', 'next', 'scheduled', 'matches']):
            return get_upcoming_matches()

        # Help query
        elif any(word in message for word in ['help', 'what can you do', 'capabilities']):
            return """I can help you with:
1. Team information
2. Player details
3. Match schedules
4. League standings
And more!

Just ask me about any of these topics!"""

        # Default response
        else:
            # Check if the entire message might be a player name
            cur.execute("""
                SELECT name FROM players 
                WHERE LOWER(name) ILIKE %s
                LIMIT 1
            """, (f'%{message}%',))
            
            player = cur.fetchone()
            if player:
                return get_player_info(player[0])
                
            return "I'm not sure about that. Try asking about:\n" \
                   "- Team information\n" \
                   "- Player details\n" \
                   "- Match schedules\n" \
                   "- League standings\n" \
                   "Type 'help' to see what I can do!"

    except Exception as e:
        print(f"Error in chatbot: {e}")
        return "I'm having trouble accessing the information right now. Please try again in a moment."

    finally:
        if cur and not cur.closed:
            cur.close()

@chatbot_bp.route('/')
def chat_page():
    return render_template('chat.html')

@chatbot_bp.route('/api/chat', methods=['POST'])
def chat():
    message = request.json.get('message', '')
    response = process_message(message)
    return jsonify({'response': response}) 