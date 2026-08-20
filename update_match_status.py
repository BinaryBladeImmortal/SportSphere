from main import app
from db import get_db

def update_match_status():
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        
        try:
            # First, let's find the match ID for Bengaluru FC vs Hyderabad FC
            cur.execute('''
                SELECT m.match_id
                FROM matches m
                JOIN teams t1 ON m.home_team_id = t1.team_id
                JOIN teams t2 ON m.away_team_id = t2.team_id
                WHERE t1.name = 'Bengaluru FC' AND t2.name = 'Hyderabad FC'
            ''')
            
            matches = cur.fetchall()
            
            if not matches:
                print("No matches found between Bengaluru FC and Hyderabad FC")
                return
            
            # Update all found matches to FINISHED status
            for match in matches:
                match_id = match[0]
                cur.execute('UPDATE matches SET status = %s WHERE match_id = %s', ('FINISHED', match_id))
                print(f"Updated match ID {match_id} to FINISHED status")
            
            # Commit the changes
            db.commit()
            print("All updates committed successfully!")
            
        except Exception as e:
            db.rollback()
            print(f"Error updating match status: {str(e)}")
        finally:
            cur.close()

if __name__ == "__main__":
    update_match_status() 