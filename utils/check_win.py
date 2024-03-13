import chess

def check_game_outcome(board):
    # Check for checkmate
    if board.is_checkmate():
        return "Checkmate", "White wins" if board.turn == chess.BLACK else "Black wins"

    # Check for stalemate
    if board.is_stalemate():
        return "Stalemate", "Draw"

    # Check for insufficient material
    if board.is_insufficient_material():
        return "Insufficient material", "Draw"

    if board.has_insufficient_material():
        return "Insufficient material", "Draw"

    # Check for the seventy-five-move rule
    if board.is_seventyfive_moves():
        return "Seventy-five-move rule", "Draw"

    # Check for fivefold repetition
    if board.is_fivefold_repetition():
        return "Fivefold repetition", "Draw"

    # Check if the game is still ongoing
    if not board.is_game_over():
        return "Game not over", "No outcome yet"

    # # If the game is over but none of the above conditions are met, it's a draw by other reasons (e.g., fifty-move rule, threefold repetition before it reaches fivefold)
    # return "Draw", "Game over with a draw by other reasons"