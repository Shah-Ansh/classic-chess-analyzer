import requests
import csv
from datetime import timedelta
import chess

game_info = {'White': None, 'Black': None, 'Winner': None}

def extract_game_info(response_text):
    

    # Split the response text by newline characters
    lines = response_text.split("\n")
    count_1 = 0
    count_2 = 0
    # Iterate over each line
    for line in lines:
        # Check if the line contains player information
        if line.startswith("[White"):
          if count_1 == 0:
            game_info['White'] = line.split('"')[1]
            count_1 = 1
        elif line.startswith("[Black"):
          if count_2 == 0:
            game_info['Black'] = line.split('"')[1]
            count_2 = 1
        # Check if the line contains the game result
        elif line.startswith("[Result"):
            result = line.split('"')[1]
            if result == "1-0":
                game_info['Winner'] = game_info['White']
            elif result == "0-1":
                game_info['Winner'] = game_info['Black']
            else:
                game_info['Winner'] = "Draw"
    return game_info


all_moves = []

def get_and_convert_game(game_id):
    url = f"https://lichess.org/game/export/{game_id}"
    response = requests.get(url)

    if response.status_code == 200:
        splitted = response.text.split("\n\n")[1].split(" ")

        game_info = extract_game_info(response.text)
        moves = []
        move_count = 1
        count = 0
        current_move = {}
        for i in splitted:
            if (count % 8 == 0):
             current_move['Index'] = move_count
            elif(count % 8 == 1):
              current_move['Move'] = i
              all_moves.append(i)
            elif(count % 8 == 4):
              current_move['Eval_Value'] = i[:-1]
            elif(count % 8 == 6):
              current_move['Clock_time'] = i[:-1] 
            elif(count%8 == 7):
              moves.append(current_move)
              current_move = {}
              move_count += 1
            count+=1
          
        return moves

    else:
        print(
            f"Error fetching game data (status code: {response.status_code})")
        return None, None
    

# Enter Game Id Here
game_id = input("Enter Game Url to Analyse : ").split("/")[3]
moves = get_and_convert_game(game_id)


def str_to_timedelta(time_str):
    try:
        hours, minutes, seconds = map(int, time_str.split(':'))
        return timedelta(hours=hours, minutes=minutes, seconds=seconds)
    except ValueError:
        print("[Alert] We Currently Cannot Analyse Your Game, Come Back Later!")
        exit()

# Function to convert timedelta to time string
def timedelta_to_str(delta):
    total_seconds = delta.total_seconds()
    hours = int(total_seconds // 3600)
    total_seconds %= 3600
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# Initialize variables to store all the data
final_moves_data = []
timedelta_data = []

# Process moves and calculate time differences
total_time = timedelta()  # Total time passed
prev_prev_time = None  # Time at i-2th index
prev_time = None  # Time at i-1th index
count = 0
zero_time = timedelta(hours=0, minutes=0, seconds=0)

for move in moves:
    # Calculate time taken for the current move
    if count > 1:
        time_taken = str_to_timedelta(move['Clock_time'])
        if prev_prev_time and prev_time:
            if(time_taken>prev_prev_time):
                time_taken = time_taken-prev_prev_time
            else:
                time_taken = prev_prev_time - time_taken
        
        total_time = time_taken

        # Add the total time to the row
        move['Time'] = timedelta_to_str(total_time)

    else:
        time_taken = "00:00:00"
        move['Time'] = time_taken
    move['White'] = game_info['White']
    move['Black'] = game_info['Black']
    move['Winner'] = game_info['Winner']
    # Store the move data
    final_moves_data.append(move)

    # Update previous times for the next iteration
    count += 1
    prev_prev_time = prev_time
    prev_time = str_to_timedelta(move['Clock_time'])

max_abs_value = 0
for move in final_moves_data:
    eval_value = move['Eval_Value']
    # Check if the entry contains a hash followed by a number
    if '#' not in eval_value:
        max_abs_value = max(abs(float(eval_value)), max_abs_value)

# Step 2: Replace hash followed by a number with the calculated value
for move in final_moves_data:
    eval_value = move['Eval_Value']
    # Check if the entry contains a hash followed by a number
    if '#' in eval_value:
        hash_index = eval_value.index('#')
        hash_sign = eval_value[hash_index+1]
        number_str = eval_value[hash_index+2:]
        try:
            number = int(number_str)
            # Calculate the new value based on the absolute maximum value
            new_value = round((max_abs_value + max_abs_value/number) * (-1 if hash_sign == "-" else 1), 2)
            move['Eval_Value'] = str(new_value)
        except ValueError:
            pass

# Add the 'Killed' column to the data
captured_pieces = []
board = chess.Board()

for move in all_moves:
    try:
        new_move = move
        if(move[-1] == '+'):
            move = move[:-1]
        if 'x' in move:
            captured_square = move.split('x')[-1]
            captured_piece = board.piece_at(chess.parse_square(captured_square))
            captured_pieces.append(captured_piece.symbol())
        else:
            captured_pieces.append("-")
        board.push_san(new_move)
    except:
        print("[Alert] We Currently Cannot Analyse Your Game, Come Back Later!")
        exit()

for move, captured_piece in zip(final_moves_data, captured_pieces):
    move['Killed'] = captured_piece

# Save all the data in one CSV file
with open('final.csv', 'w', newline='') as csvfile:
    fieldnames = ['Index', 'Move', 'Eval_Value', 'Clock_time', 'Time', 'Killed', 'White', 'Black', 'Winner']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows([{'Index': 0, 'Move': 0, 'Eval_Value': 0, 'Clock_time': 0, 'Time': 0, 'Killed': 0, 'White': 0, 'Black': 0, 'Winner': 0}])
    writer.writerows(final_moves_data)
  