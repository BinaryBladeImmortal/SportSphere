from flask import Flask, render_template, jsonify, request
import json

app = Flask(__name__)

# Sample tournament data
TOURNAMENT_DATA = {
    "name": "ISL Playoffs 2024",
    "rounds": [
        {
            "name": "Quarter Finals",
            "matches": [
                {"id": 1, "team1": {"name": "Mohun Bagan", "score": None}, "team2": {"name": "East Bengal", "score": None}},
                {"id": 2, "team1": {"name": "Kerala Blasters", "score": None}, "team2": {"name": "Bengaluru FC", "score": None}},
                {"id": 3, "team1": {"name": "Mumbai City", "score": None}, "team2": {"name": "FC Goa", "score": None}},
                {"id": 4, "team1": {"name": "Hyderabad FC", "score": None}, "team2": {"name": "Chennaiyin FC", "score": None}}
            ]
        },
        {
            "name": "Semi Finals",
            "matches": [
                {"id": 5, "team1": {"name": None, "score": None}, "team2": {"name": None, "score": None}},
                {"id": 6, "team1": {"name": None, "score": None}, "team2": {"name": None, "score": None}}
            ]
        },
        {
            "name": "Final",
            "matches": [
                {"id": 7, "team1": {"name": None, "score": None}, "team2": {"name": None, "score": None}}
            ]
        }
    ]
}

@app.route('/')
def index():
    return render_template('bracket.html', tournament=TOURNAMENT_DATA)

@app.route('/update_match', methods=['POST'])
def update_match():
    data = request.json
    match_id = data['match_id']
    score1 = data['score1']
    score2 = data['score2']
    
    # Update the match scores in our data structure
    for round in TOURNAMENT_DATA['rounds']:
        for match in round['matches']:
            if match['id'] == match_id:
                match['team1']['score'] = score1
                match['team2']['score'] = score2
                
                # Determine winner and update next round
                if score1 > score2:
                    winner = match['team1']['name']
                else:
                    winner = match['team2']['name']
                    
                # Update next match
                if match_id in [1, 2]:
                    next_match_id = 5
                    is_first_team = match_id == 1
                elif match_id in [3, 4]:
                    next_match_id = 6
                    is_first_team = match_id == 3
                elif match_id in [5, 6]:
                    next_match_id = 7
                    is_first_team = match_id == 5
                
                if match_id < 7:  # Not the final
                    for r in TOURNAMENT_DATA['rounds']:
                        for m in r['matches']:
                            if m['id'] == next_match_id:
                                if is_first_team:
                                    m['team1']['name'] = winner
                                else:
                                    m['team2']['name'] = winner
                
                return jsonify({"success": True})
    
    return jsonify({"success": False})

if __name__ == '__main__':
    app.run(debug=True) 