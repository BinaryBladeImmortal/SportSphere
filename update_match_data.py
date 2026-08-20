from main import app
from db import get_db

def update_match_details():
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        
        try:
            # First, let's find the match ID for Bengaluru FC vs Hyderabad FC
            cur.execute('''
                SELECT m.match_id, m.stadium_id
                FROM matches m
                JOIN teams t1 ON m.home_team_id = t1.team_id
                JOIN teams t2 ON m.away_team_id = t2.team_id
                WHERE t1.name = 'Bengaluru FC' AND t2.name = 'Hyderabad FC'
            ''')
            
            matches = cur.fetchall()
            
            if not matches:
                print("No matches found between Bengaluru FC and Hyderabad FC")
                return
            
            # Get available stadiums
            cur.execute('SELECT stadium_id, name, city FROM stadiums')
            stadiums = cur.fetchall()
            print("Available stadiums:")
            for stadium in stadiums:
                print(f"ID: {stadium[0]}, Name: {stadium[1]}, City: {stadium[2]}")
                
            # Get available referees
            cur.execute('SELECT referee_id, name, nationality FROM referees')
            referees = cur.fetchall()
            print("\nAvailable referees:")
            for referee in referees:
                print(f"ID: {referee[0]}, Name: {referee[1]}, Nationality: {referee[2]}")
            
            # Update matches with venue and referee
            for match in matches:
                match_id = match[0]
                
                # Use Sree Kanteerava Stadium (ID: 3) for Bengaluru FC home matches
                cur.execute('UPDATE matches SET stadium_id = %s WHERE match_id = %s', (3, match_id))
                print(f"Updated match ID {match_id} with stadium ID 3 (Sree Kanteerava Stadium)")
                
                # Assign referee Crystal John (ID: 1) to the match
                cur.execute('SELECT * FROM match_referees WHERE match_id = %s', (match_id,))
                if not cur.fetchone():
                    cur.execute('INSERT INTO match_referees (match_id, referee_id) VALUES (%s, %s)', (match_id, 1))
                    print(f"Added referee ID 1 (Crystal John) to match ID {match_id}")
                else:
                    cur.execute('UPDATE match_referees SET referee_id = %s WHERE match_id = %s', (1, match_id))
                    print(f"Updated match ID {match_id} with referee ID 1 (Crystal John)")
            
            # Commit the changes
            db.commit()
            print("All updates committed successfully!")
            
        except Exception as e:
            db.rollback()
            print(f"Error updating match details: {str(e)}")
        finally:
            cur.close()

if __name__ == "__main__":
    update_match_details() 