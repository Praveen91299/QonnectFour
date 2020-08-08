#!/usr/bin/env python
# coding: utf-8

# # Qonnect Four  
# 
# Inspired from the classical game Connect four, Qonnect Four works using the principles of quantum circuits.  
# 
# A game by Praveen Jayakumar (praveen91299 (at) gmail.com)
# 
#


get_ipython().run_line_magic('matplotlib', 'inline')
#import matplotlib as mpl
import numpy as np
from PIL import Image
from matplotlib.pyplot import imshow
from IPython.display import Image as Im
from IPython.display import display, clear_output

from qiskit import *
from qiskit import QuantumRegister, QuantumCircuit, ClassicalRegister
from qiskit import BasicAer
from qiskit.visualization import plot_state_qsphere, plot_bloch_multivector
from qiskit.quantum_info import Statevector, Operator
from qiskit.circuit import Gate

black = [0, 0, 0]
yellow = [255, 255, 0]
red = [255, 0, 0]

coin_colours = [yellow, red]

scale = 20
zeros = np.array([0]*4)
ones = np.array([1]*4)

gates = ["h", "z", "x", "y", "s", "t", "cx", "ccx"]

class coord:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    def relocate(self, coords_new):
        self.x = coords_new
        self.y = coords_new
        
    def displace(self, coords_disp):
        self.x += coords_disp.x
        self.y += coords_disp.y
        
    def rescale(self, scale):
        self.x *= scale
        self.y *= scale
        
class rect(coord):
    def __init__(self, height, width, coords, colour = black, label = 'rectangle'):
        self.name = label
        self.height = height
        self.width = width
        self.x = coords.x
        self.y = coords.y
        
        #image data
        self.data = np.zeros((height, width, 3), dtype=np.uint8)
        if colour != black:
            self.recolour(self, rect(height, width, coords, black), colour)
    
    def recolour(self, location, colour):
        for a in range(location.width):
            for b in range(location.height):
                self.data[b + location.y][a + location.x] = colour
    
    def save_image(self):
        img = Image.fromarray(self.data, 'RGB')
        img.save(self.name + '.png')
        return self.name + '.png'

class QonnectFour:
    def __init__(self, cols, seed, depth = 2, StartPlayer = 0):
        self.columns = cols
        self.backend = Aer.get_backend('statevector_simulator')
        self.depth = depth
        self.seed = seed
        self.ready = 0
        self.turn = StartPlayer
        
        #board with initial flags of -1
        self.board = np.full((cols, cols), -1, dtype=int)
        self.coin_array = np.array([0]*cols)
        self.board_img = rect(cols*scale, cols*scale,  coord(0, 0), black, "board")
        
        #initialise pseudo-random circuit and corresponding statevector
        self.circuit = QuantumCircuit(cols, cols)
        self.state = Statevector(execute(self.circuit, self.backend).result().get_statevector())
        self.generate_random()
        self.ready = 1
        
        #display after starting game
        clear_output()
        print("Welcome to Qonnect four! \n Player " + str(self.turn) + " to begin. \n Initial state:")
        self.disp_game_state()
    
    def disp_game_state(self):
        print("Board:")
        self.disp_board()
        print("Circuit:")
        self.disp_circuit()
        return
    
    def disp_circuit(self):
        self.circuit.draw('mpl').savefig('circuit.png')
        display(Im(filename='circuit.png', unconfined = True))
        return
        
    def disp_board(self):
        self.board_img.save_image()
        display(Im(filename='board.png'))
        return
    
    def disp_qsphere(self):
        plot_state_qsphere(self.state).savefig('qsphere.png')
        display(Im(filename='qsphere.png', unconfined = True))
        return
    
    def disp_bloch_multivector(self):
        plot_bloch_multivector(self.state).savefig('bloch.png')
        display(Im(filename='bloch.png', unconfined = True))
        return
    
    def pass_turn(self):
        print("Player " + str(self.turn) + " has played their turn.")
        self.turn = 1 - self.turn
        print("Player " + str(self.turn) + "'s turn now.")
    
    def check_pure(self):
        temp = [0]*self.columns
        for a in range(self.columns):
            if np.isclose(self.state.probabilities([a])[0], 0.0, 1e-3) or np.isclose(self.state.probabilities([a])[0], 1.0, 1e-3):
                temp[a] = 1
        return temp
        
    def perform_measurement(self, qubit_pos):
        
        #check if the column is not full already
        if self.coin_array[qubit_pos] == self.columns:
            print("Column full, try different move")
            return 0
        else:
            self.coin_array[qubit_pos] +=1
        
        #get premeasurement pure states
        pure_before = self.check_pure()
        
        #perform measurement
        result, self.state = self.state.measure([qubit_pos])
        result = int(result)
        self.circuit.measure([qubit_pos], [qubit_pos])
        self.circuit.barrier()
        
        #check if any other qubits collapsed to pure due to measurement
        pure_after = self.check_pure()
        
        positions = [qubit_pos]
        results = [result]
        
        for a in range(self.columns):
            if pure_after[a] == 1 and pure_before[a] == 0 and a != qubit_pos:
                positions.append(a)
                res_extra, self.state = self.state.measure([a])
                res_extra = int(res_extra)
                results.append(res_extra)
                self.coin_array[a] += 1
        
        #update board and display
        for a in range(len(positions)):
            temp_coord = coord(positions[a], self.columns - self.coin_array[positions[a]])
            #print(a)
            self.board[temp_coord.x][temp_coord.y] = results[a]
            temp_coord.rescale(scale)
            #add coin
            self.board_img.recolour(rect(scale, scale, temp_coord), coin_colours[results[a]])
        
        #check for matches
        end, player = self.check_board()
        if end:
            clear_output()
            print("Player "+ str(player) + " wins! \n ")
            print("Final state: ")
            self.disp_game_state()
            wrap_up(self)
            return
        
        clear_output()
        print("Current state:")
        self.disp_game_state()
        self.pass_turn()
        #print("Current Qsphere:")
        #print(self.state.is_valid())
        #self.disp_qsphere()
        #self.disp_bloch_multivector()
        return
    
    def generate_random(self):
        seed_digits = [int(d) for d in str(bin((self.seed + 500)**3))[2:]]
        seed_digits = seed_digits[:(len(seed_digits) - (len(seed_digits)%3))]
        
        gate_sequence = []
        for a in range(int(len(seed_digits)/3)):
            gate_sequence.append(4*seed_digits[3*a] + 2*seed_digits[3*a + 1] + seed_digits[3*a + 2])
        
        number_temp = self.depth*self.columns*3
        gate_sequence_temp = gate_sequence
        
        if len(gate_sequence_temp) < number_temp:
            for a in range(int(number_temp/len(gate_sequence_temp))):
                gate_sequence += [int((d + self.seed*a)%8) for d in gate_sequence_temp]
        
        for d in range(self.depth):
            for a in range(self.columns):
                if gate_sequence[0] <= 5:
                    self.add_gate(gates[gate_sequence[0]], [a])
                    gate_sequence = gate_sequence[1:]
                    continue
                    
                if gate_sequence[0] == 6:
                    b = gate_sequence[1]%self.columns - int(a == gate_sequence[1]%self.columns)
                    self.add_gate('cx', [a, b])
                    gate_sequence = gate_sequence[2:]
                    continue
                    
                if gate_sequence[0] == 7:
                    b = gate_sequence[1]%self.columns - int(a == gate_sequence[1]%self.columns)
                    c = gate_sequence[2]%self.columns
                    c = c - int(c==a) - int(((c - int(c==a)) == b))
                    self.add_gate('ccx', [a, b, c])
                    gate_sequence = gate_sequence[3:]
                    continue
        self.circuit.barrier()
        return
    
    def add_gate(self, gate, args):
        for a in range(len(args)):
            if self.coin_array[args[a]] == self.columns:
                print("Column full, try different move")
                return 0
        
        #apply corresponding gates/operators
        qc_temp = QuantumCircuit(self.columns)
        
        if gate == "h" and len(args) == 1:
            self.circuit.h(args)
            qc_temp.h(args)
            self.state = self.state.evolve(Operator(qc_temp))
        
        if gate == "z" and len(args) == 1:
            self.circuit.z(args)
            qc_temp.z(args)
            self.state = self.state.evolve(Operator(qc_temp))
        
        if gate == "x" and len(args) == 1:
            self.circuit.x(args)
            qc_temp.x(args)
            self.state = self.state.evolve(Operator(qc_temp))
        
        if gate == "y" and len(args) == 1:
            self.circuit.y(args)
            qc_temp.y(args)
            self.state = self.state.evolve(Operator(qc_temp))
        
        if gate == "s" and len(args) == 1:
            self.circuit.s(args)
            qc_temp.s(args)
            self.state = self.state.evolve(Operator(qc_temp))
        
        if gate == "t" and len(args) == 1:
            self.circuit.t(args)
            qc_temp.t(args)
            self.state = self.state.evolve(Operator(qc_temp))
        
        if gate == "cx" and len(args) == 2:
            self.circuit.cx(args[0], args[1])
            qc_temp.cx(args[0], args[1])
            self.state = self.state.evolve(Operator(qc_temp))
        
        if gate == "ccx" and len(args) == 3:
            self.circuit.ccx(args[0], args[1], args[2])
            qc_temp.ccx(args[0], args[1], args[2])
            self.state = self.state.evolve(Operator(qc_temp))
        
        if self.ready:
            clear_output()
            print("Current state:")
            self.disp_game_state()
            self.pass_turn()
        return
    
    def check_board(self):
        temp = np.array([0]*4)
        for x in range(self.columns):
            for y in range(self.columns):
                if self.board[x][y] !=-1:
                    
                    if x<= (self.columns - 4):
                        for a in range(4):
                            temp[a] = self.board[x + a][y]
                                
                        if (temp == zeros).all() or (temp == ones).all():
                            return True, self.board[x][y]
                        
                        #diagonal
                        if y<= (self.columns - 4):
                            #temp = np.array([0]*4)
                            for a in range(4):
                                temp[a] = self.board[x + a][y + a]
                            
                            if (temp == zeros).all() or (temp == ones).all():
                                return True, self.board[x][y]
                    
                    if y<= (self.columns - 4):
                        #temp = np.array([0]*4)
                        for a in range(4):
                            temp[a] = self.board[x][y + a]
                            
                        if (temp == zeros).all() or (temp == ones).all():
                            return True, self.board[x][y]
                        
                        #antidiagonal
                        if x >= 4:
                            for a in range(4):
                                temp = self.board[x - a][y + a]
                            
                            if (temp == zeros).all() or (temp == ones).all():
                                return True, self.board[x][y]
        return False, -1
    #def __delete__(self)
            
def wrap_up(Game):
    print("Hope you enjoyed! \n This is a project in progress, leave your feedback, suggestions and comment (if any) at praveen91299@gmail.com")
    del Game