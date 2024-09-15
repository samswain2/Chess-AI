import pygame
from abc import ABC, abstractmethod
from collections import defaultdict, namedtuple
import math
import chess
from tqdm import tqdm
import random

class MCTS:
    "Monte Carlo tree searcher. First rollout the tree then choose a move."

    def __init__(self, exploration_weight=1):
        self.Q = defaultdict(int)  # total reward of each node
        self.N = defaultdict(int)  # total visit count for each node
        self.children = dict()  # children of each node
        self.exploration_weight = exploration_weight

    def choose(self, node):
        print(node)
        "Choose the best successor of node. (Choose a move in the game)"
        if node.is_terminal(node.board)[0]:
            raise RuntimeError(f"choose called on terminal node {node}")

        if node not in self.children:
            return node.find_random_child()

        def score(n):
            if self.N[n] == 0:
                return float("-inf")  # avoid unseen moves
            return self.Q[n] / self.N[n]  # average reward

        return max(self.children[node], key=score)

    def do_rollout(self, node):
        "Make the tree one layer better. (Train for one iteration.)"
        path = self._select(node)
        leaf = path[-1]
        self._expand(leaf)
        reward = self._simulate(leaf)
        self._backpropagate(path, reward)

    def _select(self, node):
        "Find an unexplored descendent of `node`"
        path = []
        while True:
            path.append(node)
            if node not in self.children or not self.children[node]:
                # node is either unexplored or terminal
                return path
            unexplored = self.children[node] - self.children.keys()
            if unexplored:
                n = unexplored.pop()
                path.append(n)
                return path
            node = self._uct_select(node)  # descend a layer deeper

    def _expand(self, node):
        "Update the `children` dict with the children of `node`"
        if node in self.children:
            return  # already expanded
        self.children[node] = node.find_children()

    def _simulate(self, node):
        "Returns the reward for a random simulation (to completion) of `node`"
        invert_reward = True
        while True:
            if node.is_terminal(node.board)[0]:
                reward = node.reward()
                return 1 - reward if invert_reward else reward
            node = node.find_random_child()
            invert_reward = not invert_reward

    def _backpropagate(self, path, reward):
        "Send the reward back up to the ancestors of the leaf"
        for node in reversed(path):
            self.N[node] += 1
            self.Q[node] += reward
            reward = 1 - reward  # 1 for me is 0 for my enemy, and vice versa

    def _uct_select(self, node):
        "Select a child of node, balancing exploration & exploitation"

        # All children of node should already be expanded:
        assert all(n in self.children for n in self.children[node])

        log_N_vertex = math.log(self.N[node])

        def uct(n):
            "Upper confidence bound for trees"
            return self.Q[n] / self.N[n] + self.exploration_weight * math.sqrt(
                log_N_vertex / self.N[n]
            )

        return max(self.children[node], key=uct)
    
class Node(ABC):
    """
    A representation of a single board state.
    MCTS works by constructing a tree of these Nodes.
    Could be e.g. a chess or checkers board state.
    """

    @abstractmethod
    def find_children(self):
        "All possible successors of this board state"
        return set()

    @abstractmethod
    def find_random_child(self):
        "Random successor of this board state (for more efficient simulation)"
        return None

    @abstractmethod
    def is_terminal(self):
        "Returns True if the node has no children"
        return True

    @abstractmethod
    def reward(self):
        "Assumes `self` is terminal node. 1=win, 0=loss, .5=tie, etc"
        return 0

    @abstractmethod
    def __hash__(self):
        "Nodes must be hashable"
        return 123456789

    @abstractmethod
    def __eq__(node1, node2):
        "Nodes must be comparable"
        return True

"""
A chess implementation, will be used along side RL
"""

_CB = namedtuple("ChessBoard", "board turn winner terminal")

class ChessGame(_CB, Node):
    # def find_children(self):
    #     return set(self.board.legal_moves)

    def find_children(self):
        # Return a set of ChessGame objects resulting from all legal moves
        children = set()
        for move in self.board.legal_moves:
            new_board = self.board.copy()
            new_board.push(move)
            turn = new_board.turn  # True for white, False for black
            terminal, winner = self.is_terminal(self.board)            
            children.add(ChessGame(board=new_board, turn=turn, winner=winner, terminal=terminal))
        
        return children
    
    def find_random_child(self):
        if self.terminal:
            print('returning no child')
            return None
        move = random.choice(list(self.board.legal_moves))
        new_board = self.board.copy(stack=False)
        new_board.push(move)
        terminal, winner = self.is_terminal(new_board)
        return ChessGame(board=new_board, turn=new_board.turn, winner=winner, terminal=terminal)

    def is_terminal(self, board):
        # Check for checkmate
        if board.is_checkmate():
            return True, True if board.turn == chess.BLACK else False # True if white wins, False for black

        # Check for stalemate
        if board.is_stalemate():
            return True, None

        # Check for insufficient material
        if board.is_insufficient_material():
            return True, None

        # Check for the seventy-five-move rule
        if board.is_seventyfive_moves():
            return True, None

        # Check for fivefold repetition
        if board.is_fivefold_repetition():
            return True, None

        # Check if the game is still ongoing
        if not board.is_game_over():
            return False, None

    def make_move(self, move):
        move = chess.Move.from_uci(move)
        self.board.push(move)
        turn = self.board.turn # White true Black false
        terminal, winner = self.is_terminal(board=self.board)
        return ChessGame(board=self.board, turn=turn, winner=winner, terminal=terminal)

    def reward(self):
        if not self.terminal:
            raise RuntimeError(f"reward called on nonterminal board {self.board}")
        if self.winner is self.turn:
            # It's your turn and you've already won. Should be impossible.
            raise RuntimeError(f"reward called on unreachable board {self.board}")
        if self.turn is (not self.winner):
            return 0  # Your opponent has just won. Bad.
        if self.winner is None:
            return 0.5  # Board is a tie
        # The winner is neither True, False, nor None
        raise RuntimeError(f"board has unknown winner type {self.winner}")

    def __hash__(self):
        # Use the FEN representation of the board for hashing
        return hash(self.board.fen())

    def __eq__(self, other):
        # Equality is based on FEN, which uniquely represents the game state
        return isinstance(other, ChessGame) and self.board.fen() == other.board.fen()

# Play chess manually
#  def play_chess():
#     game = ChessGame(board=chess.Board(), turn=True, winner=None, terminal=False)
#     print(game.board)
#     print("")
    
#     while True:
#         # Check if the game is over
#         if game.is_terminal()[0]:
#             result = game.board.result()
#             print(f"Game over: {result}")
#             break

#         # Human player move (assuming human is white)
#         if game.turn:  # White's turn (human)
#             move = input("Your move (in UCI format, e.g., e2e4): ")
#             try:
#                 game = game.make_move(move)
#             except Exception as e:
#                 print(f"Invalid move: {e}. Please try again.")
#                 continue
#         else:  # Black's turn (MCTS bot)
#             # Initialize a new MCTS tree for each move
#             tree = MCTS()
            
#             # Run MCTS to select the next move
#             for _ in range(1000):  # Adjust the number of rollouts as needed
#                 tree.do_rollout(game)
            
#             # Choose the best move from the current position
#             game = tree.choose(game)
#             print("Bot move:")
#             print(game.board)
#             print("")

#         # After each move, check if the game is over
#         if game.is_terminal()[0]:
#             result = game.board.result()
#             print(f"Game over: {result}")
#             break

# Play chess automatically
def play_chess():
    game = ChessGame(board=chess.Board(), turn=True, winner=None, terminal=False)
    print(game.board)
    print("")
    
    while True:
        # Check if the game is over
        if game.is_terminal(game.board)[0]:
            result = game.board.result()
            print(f"Game over: {result}")
            break
        
        # Initialize a new MCTS tree for each move (optional)
        tree = MCTS()
        
        # Define the number of rollouts
        num_rollouts = 5
        for _ in tqdm(range(num_rollouts), desc="MCTS Rollouts"):
            tree.do_rollout(game)
        
        # Choose the best move from the current position
        game = tree.choose(game)
        print(game.board)
        print("")
        
        # After choosing a move, check if the game is over
        if game.is_terminal(game.board)[0]:
            result = game.board.result()
            print(f"Game over: {result}")
            break


if __name__=="__main__":
    play_chess()