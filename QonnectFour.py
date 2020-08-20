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

#server stuff
import os
from Network import *

#colour codes
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
    def __init__(self, cols, seed, depth = 2, StartPlayer = 0, MultiPlayer = 0, host = 1, Server_IP = '0'):
        self.columns = cols
        self.backend = Aer.get_backend('statevector_simulator')
        self.depth = depth
        self.seed = seed
        self.ready = 0
        self.turn = StartPlayer
        self.MultiPlayer = MultiPlayer
        
        #for multiplayer stuff
        self.host = "localhost"
        self.move_no = 0
        self.move_no_opp = 0
        self.move = "0:0:h:0"
        self.StartPlayer = StartPlayer # the person's role: 0 - Start first, else start second.
        self.host_bin = host # 1 if local system is host and host is Player 0.
        
        #board with initial flags of -1
        self.board = np.full((cols, cols), -1, dtype=int)
        self.coin_array = np.array([0]*cols)
        self.board_img = rect(cols*scale, cols*scale,  coord(0, 0), black, "board")
        
        #start server if multiplayer
        if MultiPlayer == 1:
            if self.host_bin == 0: # if not host, then take in the Server_IP
                self.host = Server_IP
            self.net = Network(self.host)
            if self.host_bin == 1: # if game host, send seed.
                self.net.send("seed:" + str(self.seed) + ":" + str(self.depth) + ":" + str(self.columns) + ":" + str(self.StartPlayer))
            else: # the player is player 1 as not host
                received = self.net.send("seed:want")
                received = received.split(":")
                self.seed = int(received[0])
                self.depth = int(received[1])
                self.column = int(received[2])
                if int(received[3]) == 0:
                    self.StartPlayer = 1
                    self.turn = 0
                else:
                    self.StartPlayer = 0
                    self.turn = 1
        
        #initialise pseudo-random circuit and corresponding statevector
        self.circuit = QuantumCircuit(cols, cols)
        self.state = Statevector(execute(self.circuit, self.backend).result().get_statevector())
        self.generate_random()
        self.ready = 1
        
        #display after starting game
        clear_output()
        print("Welcome to Qonnect four! \n Player " + str(self.turn) + " to begin. \n Initial state:")
        self.disp_game_state()
        
    
    def send_move(self): #for user
        if self.MultiPlayer == 0:
            print("You are playing in local mode, no one there to send moves to.")
            return
        
        data = self.move
        reply = self.net.send(data)
        return
    
    def get_move(self): #for user
        if self.MultiPlayer == 0:
            print("You are playing in local mode, no one moves to get.")
            return
        
        data = str(self.StartPlayer)
        reply = self.net.send(data)
        info = self.parse_move(reply)
        
        if info[1] == 0:
            print("No move performed yet")
            return
        
        #check if already received
        if info[1] == self.move_no_opp:
            print("Already updated opponent's move")
            return
        
        #check type of move
        if info[2] == "measure":
            self.measure(info[3:], 0)
            print("Player " + str(info[0]) + " performed measurement on qubit " + str(info[3]))
            self.move_no_opp = info[1]
            return
        else:
            self.add_gate(info[2], info[3:], 0)
            print("Player " + str(info[0]) + " performed " + info[2] + " gate")
            self.move_no_opp = info[1]
        return
    
    def parse_move(self, mess):
        data = mess.split(":")
        reply = [0, 0, "h"] #default placeholder
        reply[0] = int(data[0])
        reply[1] = int(data[1])
        reply[2] = data[2]
        for a in range(len(data) - 3):
            reply.append(int(data[a + 3]))
        return reply
    
    def make_move(self, move, qubit_pos = []):
        data = str(self.StartPlayer) + ":" + str(self.move_no) + ":" + move
        for a in qubit_pos:
            data = data + ":" + str(a)
        self.move = data
        return
        
    def disp_game_state(self):
        print("Board:")
        self.disp_board()
        print("Circuit:")
        self.disp_circuit()
        print("Qsphere:")
        self.disp_qsphere()
        print("Bloch spheres:")
        self.disp_bloch_multivector()
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
        plot_state_qsphere(self.state.data).savefig('qsphere.png')
        display(Im(filename='qsphere.png', unconfined = True))
        return
    
    def disp_bloch_multivector(self):
        plot_bloch_multivector(self.state.data).savefig('bloch.png')
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
    
    def measure(self, qubit_pos, flag = 1):
        
        #when multiplayer, check if valid
        if flag: # if performing own move
            if self.MultiPlayer == 1:
                if self.StartPlayer == 0 and self.move_no != self.move_no_opp: # if player 0, then should play first
                    print("Invalid move. Wait for other player to play move or try receiving move by game.get_move().")
                    return
                if self.StartPlayer == 1 and self.move_no != (self.move_no_opp - 1):
                    print("Invalid move. Wait for other player to play move or try receiving move by game.get_move().")
                    return

            #check if the column is not full already
            if type(qubit_pos) != type(2):
                clear_output()
                print("Invalid input! Provide an integer for position number")
                self.disp_game_state()
                return 0
            if self.coin_array[qubit_pos] == self.columns:
                clear_output()
                print("Column full, try different move")
                self.disp_game_state()
                return 0
            if qubit_pos >= self.columns:
                clear_output()
                print("Column out of bounds! Enter value between 0 and " + str(self.column))
                self.disp_game_state()
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

            #for making move to send (for multiplayer)
            temp = [-1]*7
            for a in range(len(positions)):
                temp[positions[a]] = results[a]
            self.move_no += 1
            temp = [positions[0]] + temp # so we can mark where measurement was performed
            #temp = np.concatenate([temp, self.state.data])
            self.make_move("measure", temp)
        
        if not flag: # when updating opponent's move
            self.circuit.measure([qubit_pos[0]], [qubit_pos[0]])
            self.circuit.barrier()
            
            temp2 = qubit_pos[1:(self.columns+1)]
            
            meas = -2
            while meas != qubit_pos[qubit_pos[0] + 1]:
                res, state = self.state.measure([qubit_pos[0]])
                meas = int(res)
            self.state = state
            
            positions = []
            results = []
            for a in range(self.columns):
                if temp2[a] == 0:
                    results.append(0)
                    positions.append(a)
                    self.coin_array[a] += 1
                elif temp2[a] == 1:
                    results.append(1)
                    positions.append(a)
                    self.coin_array[a] += 1
        
        #update board and display
        for a in range(len(positions)):
            temp_coord = coord(positions[a], self.columns - self.coin_array[positions[a]])
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
            if self.MultiPlayer:
                self.send_move()
            wrap_up(self)
            return
        
        clear_output()
        print("Current state:")
        self.disp_game_state()
        
        if flag:
            self.pass_turn()
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
    
    def h(self, args):
        if type(args) != type(2):
            clear_output()
            print("Invalid positional argument. Please pass a single position as argument.")
            self.disp_game_state()
            return 0
        self.add_gate('h', [args])
        return
    
    def z(self, args):
        if type(args) != type(2):
            clear_output()
            print("Invalid positional argument. Please pass a single position as argument.")
            self.disp_game_state()
            return 0
        self.add_gate('z', [args])
        return
    
    def x(self, args):
        if type(args) != type(2):
            clear_output()
            print("Invalid positional argument. Please pass a single position as argument.")
            self.disp_game_state()
            return 0
        self.add_gate('x', [args])
        return
    
    def y(self, args):
        if type(args) != type(2):
            clear_output()
            print("Invalid positional argument. Please pass a single position as argument.")
            self.disp_game_state()
            return 0
        self.add_gate('y', [args])
        return
    
    def s(self, args):
        if type(args) != type(2):
            clear_output()
            print("Invalid positional argument. Please pass a single position as argument.")
            self.disp_game_state()
            return 0
        self.add_gate('s', [args])
        return
    
    def t(self, args):
        if type(args) != type(2):
            clear_output()
            print("Invalid positional argument. Please pass a single position as argument.")
            self.disp_game_state()
            return 0
        self.add_gate('t', [args])
        return
    
    def cx(self, arg1, arg2):
        if type(arg1) != type(2) or type(arg2) != type(2):
            clear_output()
            print("Invalid positional argument. Please pass a single position as argument.")
            self.disp_game_state()
            return 0
        self.add_gate('cx', [arg1, arg2])
        return
    
    def ccx(self, arg1, arg2, arg3):
        if type(arg1) != type(2) or type(arg2) != type(2) or type(arg2) != type(2):
            clear_output()
            print("Invalid positional argument. Please pass a single position as argument.")
            self.disp_game_state()
            return 0
        self.add_gate('ccx', [arg1, arg2, arg3])
        return
    
    def add_gate(self, gate, args, flag = 1):
        
        if flag and self.ready:
            if self.MultiPlayer == 1:
                if self.StartPlayer == 0 and self.move_no != self.move_no_opp: # if player 0, then should play first
                    print("Invalid move. Wait for other player to play move or try receiving move by game.get_move().")
                    return
                if self.StartPlayer == 1 and self.move_no != (self.move_no_opp - 1):
                    print("Invalid move. Wait for other player to play move or try receiving move by game.get_move().")
                    return
        
        #check if column full
        for a in range(len(args)):
            if self.coin_array[args[a]] == self.columns:
                clear_output()
                print("Column full, try different move")
                self.disp_game_state()
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
            
            if flag:
                self.pass_turn()
                self.move_no += 1
                self.make_move(gate, args)
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
    if Game.MultiPlayer == 1:
        Game.net.send('2')
    del Game
