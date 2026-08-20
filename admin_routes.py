from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from functools import wraps
from db import get_db
import os
import re

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            flash('You need to be an admin to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrap

def get_existing_data(table_name):
    db = get_db()
    cur = db.cursor()
    cur.execute(f'SELECT * FROM {table_name}')
    data = cur.fetchall()
    cur.close()
    return data

@admin_bp.route('/manage_stadiums', methods=['GET', 'POST'])
@admin_required
def manage_stadiums():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            stadium_id = request.form.get('stadium_id')
            name = request.form['name']
            location = request.form['location']
            capacity = request.form['capacity']

            if 'add' in request.form:
                # Get the next available stadium_id
                cur.execute('SELECT MAX(stadium_id) FROM stadiums')
                max_id = cur.fetchone()[0]
                next_id = max_id + 1 if max_id else 1
                
                cur.execute('INSERT INTO stadiums (stadium_id, name, location, capacity) VALUES (%s, %s, %s, %s)', 
                            (next_id, name, location, capacity))
                
                # Add the new stadium to the schema file
                update_schema_file('stadiums', next_id, 'add', {'name': name, 'location': location, 'capacity': capacity})
                flash('Stadium added successfully', 'success')
            elif 'edit' in request.form and stadium_id:
                cur.execute('UPDATE stadiums SET name = %s, location = %s, capacity = %s WHERE stadium_id = %s', 
                            (name, location, capacity, stadium_id))
                # Update the stadium in the schema file
                update_schema_file('stadiums', stadium_id, 'edit', {'name': name, 'location': location, 'capacity': capacity})
                flash('Stadium updated successfully', 'success')
            elif 'delete' in request.form and stadium_id:
                # First update any teams that use this stadium to have NULL stadium_id
                cur.execute('UPDATE teams SET stadium_id = NULL WHERE stadium_id = %s', (stadium_id,))
                # Then delete the stadium
                cur.execute('DELETE FROM stadiums WHERE stadium_id = %s', (stadium_id,))
                
                # Update clean_schema.sql to remove this stadium
                update_schema_file('stadiums', stadium_id, 'delete')
                
                flash('Stadium deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_stadiums'))

    cur.execute('SELECT stadium_id, name, location, capacity FROM stadiums')
    stadiums = cur.fetchall()
    cur.close()
    return render_template('manage_stadiums.html', stadiums=stadiums)

# Helper function to update schema file
def update_schema_file(table_name, item_id, action, data=None):
    try:
        # Path to clean_schema.sql
        schema_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'clean_schema.sql')
        
        # Read the file content
        with open(schema_file_path, 'r') as file:
            content = file.read()
        
        if table_name == 'stadiums':
            # Pattern to match an INSERT statement for this stadium
            pattern = re.compile(r'INSERT INTO (?:public\.)?stadiums.*\(' + str(item_id) + r'.*\);')
            
            if action == 'delete':
                # Replace matches with empty string
                new_content = pattern.sub('', content)
            elif action == 'edit' and data:
                # Find the original INSERT statement
                match = pattern.search(content)
                if match:
                    old_insert = match.group(0)
                    
                    # Create the new INSERT statement
                    # This assumes the format: INSERT INTO stadiums (stadium_id, name, city, country, capacity) VALUES
                    new_insert = f"INSERT INTO stadiums (stadium_id, name, city, country, capacity) VALUES\n({item_id}, '{data['name']}', "
                    
                    # Split location into city and country if it contains a comma
                    location_parts = data['location'].split(',', 1)
                    city = location_parts[0].strip()
                    country = location_parts[1].strip() if len(location_parts) > 1 else ''
                    
                    new_insert += f"'{city}', '{country}', {data['capacity']});"
                    
                    # Replace the old INSERT with the new one
                    new_content = content.replace(old_insert, new_insert)
                else:
                    # If we couldn't find the old statement, don't modify the file
                    new_content = content
            elif action == 'add' and data:
                # Find the last stadium insert
                stadium_inserts_pattern = re.compile(r'INSERT INTO (?:public\.)?stadiums.*\(.*\);')
                stadium_inserts = stadium_inserts_pattern.findall(content)
                
                if stadium_inserts:
                    # Get the last stadium insert
                    last_insert = stadium_inserts[-1]
                    
                    # Create the new INSERT statement for the new stadium
                    # Split location into city and country if it contains a comma
                    location_parts = data['location'].split(',', 1)
                    city = location_parts[0].strip()
                    country = location_parts[1].strip() if len(location_parts) > 1 else ''
                    
                    new_insert = f"INSERT INTO stadiums (stadium_id, name, city, country, capacity) VALUES\n({item_id}, '{data['name']}', '{city}', '{country}', {data['capacity']});"
                    
                    # Add the new insert after the last one
                    new_content = content.replace(last_insert, last_insert + "\n" + new_insert)
                else:
                    # If there are no stadium inserts yet, add it after the stadium table creation
                    stadium_table_pattern = re.compile(r'CREATE TABLE public\.stadiums.*?;', re.DOTALL)
                    match = stadium_table_pattern.search(content)
                    if match:
                        stadium_table = match.group(0)
                        
                        # Split location into city and country if it contains a comma
                        location_parts = data['location'].split(',', 1)
                        city = location_parts[0].strip()
                        country = location_parts[1].strip() if len(location_parts) > 1 else ''
                        
                        new_insert = f"\n\n-- Insert stadiums\nINSERT INTO stadiums (stadium_id, name, city, country, capacity) VALUES\n({item_id}, '{data['name']}', '{city}', '{country}', {data['capacity']});"
                        
                        # Add the new insert after the stadium table creation
                        new_content = content.replace(stadium_table, stadium_table + new_insert)
                    else:
                        # Couldn't find a place to add the insert
                        new_content = content
            else:
                # No action needed
                new_content = content
            
            # Write back to the file
            with open(schema_file_path, 'w') as file:
                file.write(new_content)
                
    except Exception as e:
        print(f"Error updating schema file: {str(e)}")
        # Don't raise the exception, as this is a non-critical operation

@admin_bp.route('/manage_leagues', methods=['GET', 'POST'])
@admin_required
def manage_leagues():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            league_id = request.form.get('league_id')
            name = request.form['name']
            country = request.form['country']

            if 'add' in request.form:
                cur.execute('INSERT INTO leagues (name, country) VALUES (%s, %s)', 
                            (name, country))
                flash('League added successfully', 'success')
            elif 'edit' in request.form and league_id:
                cur.execute('UPDATE leagues SET name = %s, country = %s WHERE league_id = %s', 
                            (name, country, league_id))
                flash('League updated successfully', 'success')
            elif 'delete' in request.form and league_id:
                cur.execute('DELETE FROM leagues WHERE league_id = %s', (league_id,))
                flash('League deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_leagues'))

    cur.execute('SELECT league_id, name, country FROM leagues')
    leagues = cur.fetchall()
    cur.close()
    return render_template('manage_leagues.html', leagues=leagues)

@admin_bp.route('/manage_seasons', methods=['GET', 'POST'])
@admin_required
def manage_seasons():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            season_id = request.form.get('season_id')
            league_id = request.form['league_id']
            year = request.form['year']

            if 'add' in request.form:
                cur.execute('INSERT INTO seasons (league_id, year) VALUES (%s, %s)', (league_id, year))
                flash('Season added successfully', 'success')
            elif 'edit' in request.form and season_id:
                cur.execute('UPDATE seasons SET league_id = %s, year = %s WHERE season_id = %s', (league_id, year, season_id))
                flash('Season updated successfully', 'success')
            elif 'delete' in request.form:
                season_id = request.form['deleteItemId']
                cur.execute('DELETE FROM seasons WHERE season_id = %s', (season_id,))
                flash('Season deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_seasons'))

    cur.execute('''
        SELECT s.season_id, s.league_id, s.name AS year, l.name
        FROM seasons s
        JOIN leagues l ON s.league_id = l.league_id
    ''')
    seasons = cur.fetchall()
    cur.execute('SELECT league_id, name FROM leagues')
    leagues = cur.fetchall()
    cur.close()
    return render_template('manage_seasons.html', seasons=seasons, leagues=leagues)

@admin_bp.route('/manage_teams', methods=['GET', 'POST'])
@admin_required
def manage_teams():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            # Print request data for debugging
            print("POST data received:", request.form)
            
            # Check which button was pressed
            if 'submit' in request.form or 'add' in request.form or 'edit' in request.form:
                # Get form data
                team_id = request.form.get('team_id')
                name = request.form.get('name')
                founded_year = request.form.get('founded_year')
                stadium_id = request.form.get('stadium_id')
                league_id = request.form.get('league_id')
                coach_id = request.form.get('coach_id')

                # Validate required fields
                if not name:
                    raise ValueError("Team name is required")
                if not founded_year:
                    raise ValueError("Founded year is required")
                if not stadium_id:
                    raise ValueError("Stadium is required")
                if not league_id:
                    raise ValueError("League is required")
                if not coach_id:
                    raise ValueError("Coach is required")

                print(f"Processing team with data: name={name}, founded_year={founded_year}, stadium_id={stadium_id}, league_id={league_id}, coach_id={coach_id}")

                # Check if stadium exists
                cur.execute('SELECT stadium_id FROM stadiums WHERE stadium_id = %s', (stadium_id,))
                if not cur.fetchone():
                    raise ValueError(f"Stadium with ID {stadium_id} does not exist")

                # Check if league exists
                cur.execute('SELECT league_id FROM leagues WHERE league_id = %s', (league_id,))
                if not cur.fetchone():
                    raise ValueError(f"League with ID {league_id} does not exist")

                # Check if coach exists
                cur.execute('SELECT coach_id FROM coaches WHERE coach_id = %s', (coach_id,))
                if not cur.fetchone():
                    raise ValueError(f"Coach with ID {coach_id} does not exist")

                if 'submit' in request.form:
                    if team_id:  # Edit existing team
                        print(f"Editing team ID {team_id}")
                        cur.execute('UPDATE teams SET name = %s, founded_year = %s, stadium_id = %s, league_id = %s, coach_id = %s WHERE team_id = %s', 
                                    (name, founded_year, stadium_id, league_id, coach_id, team_id))
                        if cur.rowcount == 0:
                            raise ValueError(f"No team found with ID {team_id}")
                        print(f"Successfully updated team {team_id}")
                        flash('Team updated successfully', 'success')
                    else:  # Add new team
                        print(f"Adding new team: {name}")
                        try:
                            # First, get the current max team_id
                            cur.execute('SELECT MAX(team_id) FROM teams')
                            max_id = cur.fetchone()[0]
                            if max_id is None:
                                max_id = 0
                            
                            # Reset the sequence to the next available ID
                            cur.execute(f"ALTER SEQUENCE teams_team_id_seq RESTART WITH {max_id + 1}")
                            
                            # Now insert the new team
                            cur.execute('''
                                INSERT INTO teams (name, founded_year, stadium_id, league_id, coach_id) 
                                VALUES (%s, %s, %s, %s, %s) 
                                RETURNING team_id
                            ''', (name, founded_year, stadium_id, league_id, coach_id))
                            new_team_id = cur.fetchone()[0]
                            print(f"Created new team with ID: {new_team_id}")
                            
                            # Update clean_schema.sql to add this team
                            update_schema_file('teams', new_team_id, 'add')
                            
                            flash('Team added successfully', 'success')
                        except Exception as e:
                            print(f"Error adding team: {str(e)}")
                            db.rollback()
                            flash(f'Error adding team: {str(e)}', 'error')
                            return redirect(url_for('admin.manage_teams'))
                elif 'add' in request.form:
                    print(f"Adding new team with 'add' button: {name}")
                    try:
                        # First, get the current max team_id
                        cur.execute('SELECT MAX(team_id) FROM teams')
                        max_id = cur.fetchone()[0]
                        if max_id is None:
                            max_id = 0
                        
                        # Reset the sequence to the next available ID
                        cur.execute(f"ALTER SEQUENCE teams_team_id_seq RESTART WITH {max_id + 1}")
                        
                        # Now insert the new team
                        cur.execute('''
                            INSERT INTO teams (name, founded_year, stadium_id, league_id, coach_id) 
                            VALUES (%s, %s, %s, %s, %s) 
                            RETURNING team_id
                        ''', (name, founded_year, stadium_id, league_id, coach_id))
                        new_team_id = cur.fetchone()[0]
                        print(f"Created new team with ID: {new_team_id}")
                        flash('Team added successfully', 'success')
                    except Exception as e:
                        print(f"Error adding team: {str(e)}")
                        db.rollback()
                        flash(f'Error adding team: {str(e)}', 'error')
                        return redirect(url_for('admin.manage_teams'))
                elif 'edit' in request.form and team_id:
                    print(f"Editing team ID {team_id} with 'edit' button")
                    cur.execute('UPDATE teams SET name = %s, founded_year = %s, stadium_id = %s, league_id = %s, coach_id = %s WHERE team_id = %s', 
                                (name, founded_year, stadium_id, league_id, coach_id, team_id))
                    if cur.rowcount == 0:
                        raise ValueError(f"No team found with ID {team_id}")
                    print(f"Successfully updated team {team_id}")
                    flash('Team updated successfully', 'success')
            elif 'delete' in request.form:
                del_team_id = request.form.get('team_id', '')
                if not del_team_id:  # If team_id is not directly available, check for deleteTeamId
                    del_team_id = request.form.get('deleteTeamId', '')
                
                if del_team_id:
                    print(f"Deleting team ID {del_team_id}")
                    # Check if team exists
                    cur.execute('SELECT team_id FROM teams WHERE team_id = %s', (del_team_id,))
                    if not cur.fetchone():
                        raise ValueError(f"No team found with ID {del_team_id}")
                    
                    # First update related entities that have team_id as a foreign key
                    cur.execute('UPDATE coaches SET team_id = NULL WHERE team_id = %s', (del_team_id,))
                    cur.execute('UPDATE players SET team_id = NULL WHERE team_id = %s', (del_team_id,))
                    # Then delete the team
                    cur.execute('DELETE FROM teams WHERE team_id = %s', (del_team_id,))
                    print(f"Successfully deleted team {del_team_id}")
                    
                    # Update clean_schema.sql to remove this team
                    update_schema_file('teams', del_team_id, 'delete')
                    
                    flash('Team deleted successfully', 'success')
                else:
                    print("Delete requested but no team_id provided")
                    flash('No team ID provided for deletion', 'error')
            db.commit()
        except ValueError as ve:
            db.rollback()
            print(f"Validation error in manage_teams: {str(ve)}")
            flash(str(ve), 'error')
        except Exception as e:
            db.rollback()
            print(f"Error in manage_teams: {str(e)}")
            flash(f'Error: {str(e)}', 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_teams'))

    # For GET requests, prepare data for the template
    try:
        # Get teams data with joined names
        cur.execute('''
            SELECT t.team_id, t.name, t.founded_year, s.name, l.name, c.name, 
                   t.stadium_id, t.league_id, t.coach_id
            FROM teams t
            LEFT JOIN stadiums s ON t.stadium_id = s.stadium_id
            LEFT JOIN leagues l ON t.league_id = l.league_id
            LEFT JOIN coaches c ON t.coach_id = c.coach_id
            ORDER BY t.name
        ''')
        teams = cur.fetchall()
        
        # Get dropdown options
        cur.execute('SELECT stadium_id, name FROM stadiums ORDER BY name')
        stadiums = cur.fetchall()
        cur.execute('SELECT league_id, name FROM leagues ORDER BY name')
        leagues = cur.fetchall()
        cur.execute('SELECT coach_id, name FROM coaches ORDER BY name')
        coaches = cur.fetchall()
        
        cur.close()
        return render_template('manage_teams.html', teams=teams, stadiums=stadiums, leagues=leagues, coaches=coaches)
    except Exception as e:
        print(f"Error preparing team data: {str(e)}")
        flash('An error occurred: ' + str(e), 'error')
        cur.close()
        return redirect(url_for('admin'))

@admin_bp.route('/manage_coaches', methods=['GET', 'POST'])
@admin_required
def manage_coaches():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            coach_id = request.form.get('coach_id')
            name = request.form['name']
            nationality = request.form['nationality']
            team_id = request.form['team_id']

            if 'add' in request.form:
                cur.execute('INSERT INTO coaches (name, nationality, team_id) VALUES (%s, %s, %s)', 
                            (name, nationality, team_id))
                flash('Coach added successfully', 'success')
            elif 'submit' in request.form and coach_id:
                cur.execute('UPDATE coaches SET name = %s, nationality = %s, team_id = %s WHERE coach_id = %s', 
                            (name, nationality, team_id, coach_id))
                flash('Coach updated successfully', 'success')
            elif 'delete' in request.form:
                coach_id = request.form['deleteEntityId']
                cur.execute('DELETE FROM coaches WHERE coach_id = %s', (coach_id,))
                flash('Coach deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_coaches'))

    cur.execute('''
        SELECT c.coach_id, c.name, c.team_id, c.nationality, t.name AS team_name
        FROM coaches c
        JOIN teams t ON c.team_id = t.team_id
    ''')
    coaches = cur.fetchall()
    cur.execute('SELECT team_id, name FROM teams')
    teams = cur.fetchall()
    cur.close()
    return render_template('manage_coaches.html', coaches=coaches, teams=teams)

@admin_bp.route('/manage_players', methods=['GET', 'POST'])
@admin_required
def manage_players():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            player_id = request.form.get('player_id')
            team_id = request.form['team_id']
            name = request.form['name']
            position = request.form['position']
            date_of_birth = request.form['date_of_birth']
            nationality = request.form['nationality']

            if 'submit' in request.form:
                if player_id:
                    cur.execute('UPDATE players SET team_id = %s, name = %s, position = %s, date_of_birth = %s, nationality = %s WHERE player_id = %s', 
                                (team_id, name, position, date_of_birth, nationality, player_id))
                    flash('Player updated successfully', 'success')
                else:
                    cur.execute('INSERT INTO players (team_id, name, position, date_of_birth, nationality) VALUES (%s, %s, %s, %s, %s)', 
                                (team_id, name, position, date_of_birth, nationality))
                    flash('Player added successfully', 'success')
            elif 'delete' in request.form:
                player_id = request.form['deleteEntityId']
                cur.execute('DELETE FROM players WHERE player_id = %s', (player_id,))
                flash('Player deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_players'))

    cur.execute('SELECT p.player_id, t.name AS team, p.name, p.position, p.date_of_birth, p.nationality, p.team_id FROM players p JOIN teams t ON p.team_id = t.team_id')
    players = cur.fetchall()
    cur.execute('SELECT team_id, name FROM teams')
    teams = cur.fetchall()
    cur.close()
    return render_template('manage_players.html', players=players, teams=teams)

@admin_bp.route('/manage_matches', methods=['GET', 'POST'])
@admin_required
def manage_matches():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            # Handle deletion first since it's straightforward
            if 'delete' in request.form:
                match_id = request.form.get('deleteEntityId')
                if match_id:
                    # Delete related records first
                    cur.execute('DELETE FROM scores WHERE match_id = %s', (match_id,))
                    cur.execute('DELETE FROM goals WHERE match_id = %s', (match_id,))
                    cur.execute('DELETE FROM match_referees WHERE match_id = %s', (match_id,))
                    # Then delete the match
                    cur.execute('DELETE FROM matches WHERE match_id = %s', (match_id,))
                    flash('Match deleted successfully', 'success')
                    db.commit()
                    return redirect(url_for('admin.manage_matches'))
            
            # Get form data
            match_id = request.form.get('match_id')
            date = request.form['date']
            team1_id = request.form['team1_id']
            team2_id = request.form['team2_id']
            season_id = request.form['season_id']
            league_id = request.form['league_id']
            stadium_id = request.form['stadium_id']
            referee_id = request.form['referee_id']

            if 'submit' in request.form:
                if match_id:  # Update existing match
                    cur.execute('UPDATE matches SET utc_date = %s, home_team_id = %s, away_team_id = %s, season_id = %s, league_id = %s, stadium_id = %s WHERE match_id = %s', 
                                (date, team1_id, team2_id, season_id, league_id, stadium_id, match_id))
                    
                    # Update referee assignment
                    cur.execute('SELECT * FROM match_referees WHERE match_id = %s', (match_id,))
                    if cur.fetchone():
                        cur.execute('UPDATE match_referees SET referee_id = %s WHERE match_id = %s', (referee_id, match_id))
                    else:
                        cur.execute('INSERT INTO match_referees (match_id, referee_id) VALUES (%s, %s)', (match_id, referee_id))
                    
                    flash('Match updated successfully', 'success')
                else:  # Insert new match with next available ID
                    # Find the highest match_id and add 1
                    cur.execute('SELECT MAX(match_id) FROM matches')
                    max_id = cur.fetchone()[0]
                    next_id = max_id + 1 if max_id else 1
                    
                    cur.execute('''
                        INSERT INTO matches 
                        (match_id, utc_date, home_team_id, away_team_id, season_id, league_id, stadium_id, status, matchday) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 'SCHEDULED', 1)
                    ''', (next_id, date, team1_id, team2_id, season_id, league_id, stadium_id))
                    
                    # Add referee assignment
                    cur.execute('INSERT INTO match_referees (match_id, referee_id) VALUES (%s, %s)', (next_id, referee_id))
                    
                    flash('Match added successfully', 'success')
                db.commit()
            
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_matches'))

    # Get existing matches for the table
    cur.execute('''
        SELECT m.match_id, m.utc_date, t1.name AS team1, t2.name AS team2, s.name AS season, l.name AS league,
               m.home_team_id, m.away_team_id, m.season_id, m.league_id, m.stadium_id, st.name AS stadium_name,
               r.referee_id, r.name AS referee_name
        FROM matches m
        JOIN teams t1 ON m.home_team_id = t1.team_id
        JOIN teams t2 ON m.away_team_id = t2.team_id
        JOIN seasons s ON m.season_id = s.season_id
        JOIN leagues l ON m.league_id = l.league_id
        LEFT JOIN stadiums st ON m.stadium_id = st.stadium_id
        LEFT JOIN match_referees mr ON m.match_id = mr.match_id
        LEFT JOIN referees r ON mr.referee_id = r.referee_id
        ORDER BY m.utc_date DESC
    ''')
    matches = cur.fetchall()
    
    # Get lookups for dropdowns
    cur.execute('SELECT team_id, name FROM teams ORDER BY name')
    teams = cur.fetchall()
    cur.execute('SELECT season_id, name FROM seasons ORDER BY name')
    seasons = cur.fetchall()
    cur.execute('SELECT league_id, name FROM leagues ORDER BY name')
    leagues = cur.fetchall()
    cur.execute('SELECT stadium_id, name FROM stadiums ORDER BY name')
    stadiums = cur.fetchall()
    cur.execute('SELECT referee_id, name FROM referees ORDER BY name')
    referees = cur.fetchall()
    cur.close()
    
    return render_template('manage_matches.html', matches=matches, teams=teams, seasons=seasons, 
                          leagues=leagues, stadiums=stadiums, referees=referees)

@admin_bp.route('/manage_countries', methods=['GET', 'POST'])
@admin_required
def manage_countries():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            country_id = request.form.get('country_id')
            name = request.form['name']
            flag_url = request.form['flag_url']

            if 'submit' in request.form:
                if country_id:
                    cur.execute('UPDATE countries SET name = %s, flag_url = %s WHERE country_id = %s', 
                                (name, flag_url, country_id))
                    flash('Country updated successfully', 'success')
                else:
                    cur.execute('INSERT INTO countries (name, flag_url) VALUES (%s, %s)', 
                                (name, flag_url))
                    flash('Country added successfully', 'success')
            elif 'delete' in request.form:
                country_id = request.form['deleteEntityId']
                cur.execute('DELETE FROM countries WHERE country_id = %s', (country_id,))
                flash('Country deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_countries'))

    cur.execute('SELECT country_id, name, flag_url FROM countries')
    countries = cur.fetchall()
    cur.close()
    return render_template('manage_countries.html', countries=countries)

@admin_bp.route('/manage_referees', methods=['GET', 'POST'])
@admin_required
def manage_referees():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            referee_id = request.form.get('referee_id')
            name = request.form['name']
            nationality = request.form['nationality']

            if 'submit' in request.form:
                if referee_id:
                    cur.execute('UPDATE referees SET name = %s, nationality = %s WHERE referee_id = %s', 
                                (name, nationality, referee_id))
                    flash('Referee updated successfully', 'success')
                else:
                    cur.execute('INSERT INTO referees (name, nationality) VALUES (%s, %s)', 
                                (name, nationality))
                    flash('Referee added successfully', 'success')
            elif 'delete' in request.form:
                referee_id = request.form['deleteEntityId']
                cur.execute('DELETE FROM referees WHERE referee_id = %s', (referee_id,))
                flash('Referee deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_referees'))

    cur.execute('SELECT referee_id, name, nationality FROM referees')
    referees = cur.fetchall()
    cur.close()
    return render_template('manage_referees.html', referees=referees)

@admin_bp.route('/manage_scorers', methods=['GET', 'POST'])
@admin_required
def manage_scorers():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            if 'delete' in request.form:
                scorer_id = request.form.get('deleteEntityId')
                if scorer_id:
                    try:
                        scorer_id = int(scorer_id)
                        cur.execute('DELETE FROM scorers WHERE scorer_id = %s', (scorer_id,))
                        db.commit()
                        flash('Scorer deleted successfully', 'success')
                    except ValueError:
                        flash('Invalid scorer ID', 'error')
                    return redirect(url_for('admin.manage_scorers'))
            
            player_id = request.form['player_id']
            season_id = request.form['season_id']
            league_id = request.form['league_id']
            new_goals = int(request.form.get('goals', 0) or 0)
            new_assists = int(request.form.get('assists', 0) or 0)
            new_penalties = int(request.form.get('penalties', 0) or 0)

            # Check if a scorer already exists for this player in this league and season
            cur.execute('SELECT scorer_id, goals, assists, penalties FROM scorers WHERE player_id = %s AND season_id = %s AND league_id = %s',
                        (player_id, season_id, league_id))
            existing_scorer = cur.fetchone()
            
            if existing_scorer:
                # Add new stats to existing totals
                total_goals = existing_scorer[1] + new_goals
                total_assists = existing_scorer[2] + new_assists
                total_penalties = existing_scorer[3] + new_penalties
                
                cur.execute('UPDATE scorers SET goals = %s, assists = %s, penalties = %s WHERE scorer_id = %s',
                            (total_goals, total_assists, total_penalties, existing_scorer[0]))
                flash('Scorer statistics updated successfully', 'success')
            else:
                # Create new scorer entry
                cur.execute('SELECT MAX(scorer_id) FROM scorers')
                max_id = cur.fetchone()[0]
                next_id = max_id + 1 if max_id else 1
                
                cur.execute('INSERT INTO scorers (scorer_id, player_id, season_id, league_id, goals, assists, penalties) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                            (next_id, player_id, season_id, league_id, new_goals, new_assists, new_penalties))
                flash('New scorer added successfully', 'success')
            
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_scorers'))

    cur.execute('''
        SELECT s.scorer_id, p.name, se.name, l.name, s.goals, s.assists, s.penalties, p.player_id, s.season_id, s.league_id
        FROM scorers s 
        JOIN players p ON s.player_id = p.player_id 
        JOIN seasons se ON s.season_id = se.season_id 
        JOIN leagues l ON s.league_id = l.league_id
        ORDER BY s.goals DESC, s.assists DESC
    ''')
    scorers = cur.fetchall()
    cur.execute('SELECT player_id, name FROM players ORDER BY name')
    players = cur.fetchall()
    cur.execute('SELECT season_id, name FROM seasons')
    seasons = cur.fetchall()
    cur.execute('SELECT league_id, name FROM leagues')
    leagues = cur.fetchall()
    cur.close()
    return render_template('manage_scorers.html', scorers=scorers, players=players, seasons=seasons, leagues=leagues)

@admin_bp.route('/manage_scores', methods=['GET', 'POST'])
@admin_required
def manage_scores():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            score_id = request.form.get('score_id')
            match_id = request.form['match_id']
            full_time_home = request.form['full_time_home']
            full_time_away = request.form['full_time_away']
            half_time_home = request.form['half_time_home']
            half_time_away = request.form['half_time_away']

            # Get the team IDs for the match
            cur.execute('SELECT home_team_id, away_team_id FROM matches WHERE match_id = %s', (match_id,))
            team_ids = cur.fetchone()
            home_team_id = team_ids[0]
            away_team_id = team_ids[1]

            if 'submit' in request.form:
                if score_id:
                    # Update existing score
                    cur.execute('UPDATE scores SET match_id = %s, full_time_home = %s, full_time_away = %s, half_time_home = %s, half_time_away = %s WHERE score_id = %s',
                                (match_id, full_time_home, full_time_away, half_time_home, half_time_away, score_id))
                    flash('Score updated successfully', 'success')
                else:
                    # Find the highest score_id and increment it
                    cur.execute('SELECT MAX(score_id) FROM scores')
                    max_id = cur.fetchone()[0]
                    next_id = max_id + 1 if max_id else 1
                    
                    # Insert new score with the next available ID
                    cur.execute('INSERT INTO scores (score_id, match_id, home_team_id, away_team_id, full_time_home, full_time_away, half_time_home, half_time_away) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                                (next_id, match_id, home_team_id, away_team_id, full_time_home, full_time_away, half_time_home, half_time_away))
                    flash('Score added successfully', 'success')
                
                # Update match status to FINISHED when scores are added
                cur.execute('UPDATE matches SET status = %s WHERE match_id = %s', ('FINISHED', match_id))
                
            elif 'delete' in request.form:
                score_id = request.form['deleteEntityId']
                
                # Get the match_id before deleting the score
                cur.execute('SELECT match_id FROM scores WHERE score_id = %s', (score_id,))
                result = cur.fetchone()
                if result:
                    deleted_match_id = result[0]
                    
                    # Delete the score
                    cur.execute('DELETE FROM scores WHERE score_id = %s', (score_id,))
                    
                    # Update match status back to SCHEDULED
                    cur.execute('UPDATE matches SET status = %s WHERE match_id = %s', ('SCHEDULED', deleted_match_id))
                    
                flash('Score deleted successfully', 'success')
                
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_scores'))

    # Join with matches and teams to get more detailed information
    cur.execute('''
        SELECT s.score_id, m.utc_date, 
               ht.name || ' vs ' || at.name as match_name,
               s.full_time_home, s.full_time_away, 
               s.half_time_home, s.half_time_away, 
               m.match_id, m.status
        FROM scores s 
        JOIN matches m ON s.match_id = m.match_id
        JOIN teams ht ON m.home_team_id = ht.team_id
        JOIN teams at ON m.away_team_id = at.team_id
        ORDER BY m.utc_date DESC
    ''')
    scores = cur.fetchall()
    
    # Get matches with team names for the dropdown
    cur.execute('''
        SELECT m.match_id, m.utc_date || ' - ' || ht.name || ' vs ' || at.name, m.status
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.team_id
        JOIN teams at ON m.away_team_id = at.team_id
        ORDER BY m.utc_date DESC
    ''')
    matches = cur.fetchall()
    cur.close()
    return render_template('manage_scores.html', scores=scores, matches=matches)

@admin_bp.route('/manage_standings', methods=['GET', 'POST'])
@admin_required
def manage_standings():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            standing_id = request.form.get('standing_id')
            position = request.form['position']
            team_id = request.form['team_id']
            played_games = request.form['played_games']
            won = request.form['won']
            draw = request.form['draw']
            lost = request.form['lost']
            points = request.form['points']
            goals_for = request.form['goals_for']
            goals_against = request.form['goals_against']
            goal_difference = request.form['goal_difference']
            form = request.form['form']

            if 'add' in request.form:
                cur.execute('''
                    INSERT INTO standings (position, team_id, played_games, won, draw, lost, points, goals_for, goals_against, goal_difference, form)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (position, team_id, played_games, won, draw, lost, points, goals_for, goals_against, goal_difference, form))
                flash('Standing added successfully', 'success')
            elif 'edit' in request.form and standing_id:
                cur.execute('''
                    UPDATE standings
                    SET position = %s, team_id = %s, played_games = %s, won = %s, draw = %s, lost = %s, points = %s, goals_for = %s, goals_against = %s, goal_difference = %s, form = %s
                    WHERE standing_id = %s
                ''', (position, team_id, played_games, won, draw, lost, points, goals_for, goals_against, goal_difference, form, standing_id))
                flash('Standing updated successfully', 'success')
            elif 'delete' in request.form:
                standing_id = request.form['deleteItemId']
                cur.execute('DELETE FROM standings WHERE standing_id = %s', (standing_id,))
                flash('Standing deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_standings'))

    cur.execute('''
        SELECT s.standing_id, s.position, t.name, s.played_games, s.won, s.draw, s.lost, s.points, s.goals_for, s.goals_against, s.goal_difference, s.form, s.team_id
        FROM standings s
        JOIN teams t ON s.team_id = t.team_id
    ''')
    standings = cur.fetchall()
    cur.execute('SELECT team_id, name FROM teams')
    teams = cur.fetchall()
    cur.close()
    return render_template('manage_standings.html', standings=standings, teams=teams)

@admin_bp.route('/manage_users', methods=['GET', 'POST'])
@admin_required
def manage_users():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            user_id = request.form.get('user_id')
            is_admin = request.form.get('is_admin') == 'true'

            cur.execute('UPDATE users SET is_admin = %s WHERE user_id = %s', (is_admin, user_id))
            db.commit()
            flash('User privilege updated successfully', 'success')
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_users'))

    cur.execute('SELECT user_id, username, is_admin FROM users')
    users = cur.fetchall()
    cur.close()

    return render_template('manage_users.html', users=users)

@admin_bp.route('/manage_goals', methods=['GET', 'POST'])
@admin_required
def manage_goals():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            if 'delete' in request.form:
                goal_id = request.form.get('deleteEntityId')
                if goal_id:
                    try:
                        goal_id = int(goal_id)
                        cur.execute('DELETE FROM goals WHERE goal_id = %s', (goal_id,))
                        db.commit()
                        flash('Goal deleted successfully', 'success')
                    except ValueError:
                        flash('Invalid goal ID', 'error')
                    return redirect(url_for('admin.manage_goals'))
            
            match_id = request.form['match_id']
            player_id = request.form['player_id']
            team_id = request.form['team_id']
            minute = int(request.form.get('minute', 0) or 0)
            is_penalty = 'is_penalty' in request.form
            is_own_goal = 'is_own_goal' in request.form

            # Find the highest goal_id and increment it
            cur.execute('SELECT MAX(goal_id) FROM goals')
            max_id = cur.fetchone()[0]
            next_id = max_id + 1 if max_id else 1
            
            # Add new goal with explicit goal_id
            cur.execute('INSERT INTO goals (goal_id, match_id, player_id, team_id, minute, is_penalty, is_own_goal) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                        (next_id, match_id, player_id, team_id, minute, is_penalty, is_own_goal))
            
            # Update scorer statistics automatically through the trigger
            db.commit()
            flash('Goal added successfully', 'success')
            
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_goals'))

    # Get all goals with related information
    cur.execute('''
        SELECT g.goal_id, m.utc_date, 
               ht.name as home_team, at.name as away_team, 
               p.name as scorer, t.name as team,
               g.minute, g.is_penalty, g.is_own_goal,
               m.match_id, p.player_id, g.team_id
        FROM goals g
        JOIN matches m ON g.match_id = m.match_id
        JOIN teams ht ON m.home_team_id = ht.team_id
        JOIN teams at ON m.away_team_id = at.team_id
        JOIN players p ON g.player_id = p.player_id
        JOIN teams t ON g.team_id = t.team_id
        ORDER BY m.utc_date DESC, g.minute ASC
    ''')
    goals = cur.fetchall()

    # Get matches for the dropdown
    cur.execute('''
        SELECT m.match_id, m.utc_date, ht.name as home_team, at.name as away_team, m.home_team_id, m.away_team_id
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.team_id
        JOIN teams at ON m.away_team_id = at.team_id
        ORDER BY m.utc_date DESC
    ''')
    matches = cur.fetchall()

    # Get players for the dropdown
    cur.execute('SELECT player_id, name, team_id FROM players ORDER BY name')
    players = cur.fetchall()

    # Get teams for the dropdown
    cur.execute('SELECT team_id, name FROM teams ORDER BY name')
    teams = cur.fetchall()

    cur.close()
    return render_template('manage_goals.html', goals=goals, matches=matches, players=players, teams=teams)
