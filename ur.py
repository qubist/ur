import random
import time
import adafruit_trellism4

trellis = adafruit_trellism4.TrellisM4Express()

trellis.pixels.brightness = .1 # FOR TESTING ON THE TRAIN

DEBUGGING = False

TOKEN_COLORS = [(0,10,255),(100,100,100)]
TOKEN_PULSE_SPEED = 100
TOKEN_PULSE_DEPTH = 10

PREVIEW_PULSE_SPEED = 100
PREVIEW_PULSE_DEPTH = 20

PATH_COLOR = (30, 10, 10)
ROSETTE_COLOR = (35, 5, 5)

DICE_ROLL_BUTTON = (0,3)
DICE_ROLL_BUTTON_COLOR = (0, 55, 10)
DIE_WAITING_COLOR = (0, 40, 0)
DIE_ON_COLOR = (0, 200, 0)
DIE_OFF_COLOR = (0, 15, 0)
FLOP_LOW_BOUND = 5
FLOP_HIGH_BOUND = 20
# FLOP_TIME = .15
FLOP_TIME = .05 # FOR TESTING

ZERO_ROLL_DELAY = 1

# Helper functions
# ----------------
def dim(color, factor):
    r, g, b = color
    dimmedColor = int(r/factor), int(g/factor), int(b/factor)
    return dimmedColor

# pulses the input color's brightness according to the device time
# speed: the speed at which the pulse pulses. 100 is medium, 300 is very slow.
# depth: how dim the pulse gets at its dimmest. higher values are less
#        dim. 10 is medium, 2 is very deep, 30 is very shallow.
def pulse(color, speed, depth):
    milliseconds = int(time.monotonic()*100)
    # print("time:",time.monotonic())
    timeValue = abs(milliseconds % speed - speed//2)
    # print(timeValue)
    dimAmount = timeValue/depth + 1
    # print(dimAmount)
    return dim(color, dimAmount)

# a node has a number and a token value which is None if no token, 0 if player
# 0's token, 1 if player 1's token, and 2 if both players' tokens
class Tile:
    def __init__(self, number):
        self.number = number
        self.token = None

    def __str__(self):
        return "{tile #" + str(self.number) + " " + "token: " + str(self.token) + "}"

    def getToken(self):
        return self.token

    # set this tile's token to either 1, 0, 2, or None
    def setToken(self, p):
        assert p is None or p == 0 or p == 1 or p == 2
        self.token = p

    # add the specified token p (1 or 0) to the tile
    def addToken(self, p):
        currentToken = self.getToken()
        if currentToken == 2:
            # both tokens are already there, can't add more
            return
        if currentToken == p:
            # token we're trying to add already there, can't add
            return
        # if no token, just set the token to add. Simple.
        if currentToken == None:
            self.setToken(p)
        # if the token is the opposite of what we're adding (only other option at this point?), set token to 2 (both)
        elif currentToken == (not p):
            self.setToken(2)

    # remove token p (0 or 1) from the tile
    def removeToken(self, p):
        currentToken = self.getToken()
        # if the tile has no tokens at all
        if currentToken == None:
        # if not self.hasToken():
            # no tokens here; can't remove one
            return
        # if the tile doesn't have the token we're trying to remove
        if not self.hasToken(p):
            # it's not here; can't remove it
            return
        # now we know this token has the tile we're trying to remove
        # if both tokens are present
        if currentToken == 2:
            # set the token to be the opposite as the one we're trying to remove
            if p == 1:
                self.setToken(0)
            else: self.setToken(1)
        # otherwise, the only token should be the one we're trying to remove
        elif currentToken == p:
            # so set there to be no tokens
            self.setToken(None)

    def hasToken(self, player=None):
        tokenValue = self.getToken()
        if player == None:
            return tokenValue != None
        elif player == 0:
            return tokenValue == 0 or tokenValue == 2
        elif player == 1:
            return tokenValue == 1 or tokenValue == 2
        elif player == 2:
            return tokenValue == 2

    # return the number of this tile
    def getNumber(self):
        return self.number

    # returns bool: whether the tile is a rosette
    def isRosette(self):
        rosetteNumbers = [3, 7, 13]
        for n in rosetteNumbers:
            if self.getNumber() == n:
                return True
        return False

    def isShared(self):
        return self.number >= 4 and self.number <=11

    def getXCoord(self):
        n = self.getNumber()
        # if the spot is in the middle row
        if n >= 4 and n <= 11:
            x = n - 4
        # if the spot is in the top or bottom row
        else:
            if n >= 0 and n <= 3:
                x = 3 - n
            else:
                x = 19 - n
        return x

    # MAYBE NOT USED
    def getYCoord(self, player):
        if n.isShared():
            return 1
        # if player is 0, row is 0, if player is 1, row is 2
        else: return player * 2

class Path:
    def __init__(self):
        self.data = [Tile(n) for n in range(14)]

    def toArray(self):
        out = []
        for item in self.data:
            out.append(item)
        return out

    def __str__(self):
        out = []
        for item in self.toArray():
            out.append(str(item))
        return str(out)

    # gets the the tile on the board by its number
    def getTile(self, tileNumber):
        # assert self.data[tileNumber].number == tileNumber
        return self.data[tileNumber]

    # can we move the specified token n spots forward?
    # player must be specified if tileNumber is not shared
    def canMoveToken(self, tileNumber, n, player=None):
        # make sure player is specified if needed
        if not self.getTile(tileNumber).isShared():
            # assert player is not None

        ## GENERAL REQUIREMENTS:

        # can only move between one and four tiles
        if n > 4 or n <= 0:
            # if DEBUGGING: print(f"\nInvalid move of tile #{tileNumber} forward {n} spaces: can only move between one and four tiles!")
            return False
        # can't move beyond end of path
        if tileNumber + n > 14:
            # if DEBUGGING: print(f"\nInvalid move of tile #{tileNumber} forward {n} spaces: can't move beyond end of path!")
            return False
        # CAN move out if exact
        if tileNumber + n == 14:
            # # if DEBUGGING: print(f"\n{tileNumber},{n}, CAN move out if exact!")
            return True
        # at this point we know that the destination tile is a real tile

        # get the specified tile so we can check it out
        tile = self.getTile(tileNumber)

        ## IF TILE IS SHARED (SIMPLE CASE):
        if tile.isShared():
            # can't move a token that doesn't exist
            if not tile.hasToken():
                # if DEBUGGING: print(f"\nInvalid move of tile #{tileNumber} forward {n} spaces: can't move a token that doesn't exist!")
                return False
            # at this point, the tile has a token
            # calculate the number of the tile to which we're trying to move
            destinationTileNumber = tileNumber + n
            destinationTile = self.getTile(destinationTileNumber)
            tilePlayer = tile.getToken()

            # can't move onto own piece
            # if the destination tile has a token of the same type as we're trying to move
            if destinationTile.hasToken(tilePlayer):
                # if DEBUGGING: print(f"\nInvalid move of tile #{tileNumber} forward {n} spaces: can't move onto own piece!")
                return False
            # if we're moving to another shared tile
            if destinationTile.isShared():
                # if that shared tile has the opposite player on it
                if destinationTile.hasToken(not tilePlayer):
                    # we can't move there if it's safe
                    if destinationTile.isRosette():
                        # if DEBUGGING: print(f"\nInvalid move of tile #{tileNumber} forward {n} spaces: can't move onto safe enemy piece!")
                        return False
            # if we're moving to a private tile, we don't need to check if the
            # enemy is there, because they can't be

        # otherwise IF WE'RE MOVING FROM A SPLIT TILE:
        elif not tile.isShared():
            # can't move a token that doesn't exist
            if not tile.hasToken(player):
                # if DEBUGGING: print(f"\nInvalid move of tile #{tileNumber} forward {n} spaces: can't move a token on private tile that doesn't exist!")
                return False
            # at this point, the tile has our token and may also have the other
            # calculate the number of the tile to which we're trying to move
            destinationTileNumber = tileNumber + n
            destinationTile = self.getTile(destinationTileNumber)
            tilePlayer = player

            # if the destination tile has a token of the same type as we're trying to move
            if destinationTile.hasToken(tilePlayer):
                # if DEBUGGING: print(f"\nInvalid move of tile #{tileNumber} forward {n} spaces: can't move onto own piece from private tile!")
                return False
            # rosette check
            # if we're moving onto a shared tile
            if destinationTile.isShared():
                # if that shared tile has the opposite player on it
                if destinationTile.hasToken(not tilePlayer):
                    # we can't move there if it's safe
                    if destinationTile.isRosette():
                        # if DEBUGGING: print(f"\nInvalid move of tile #{tileNumber} forward {n} spaces: can't move onto safe enemy piece from private tile!")
                        return False

            # if we're moving from a split tile, the tile exists, and the tile
            # we're trying to move to isn't occupied by our own piece or by a
            # safe enemy piece, we can move

        # if we made it through that gauntlet of tests, then we can move
        return True

    # move the token of specified tile n spots forward, if possible
    def moveToken(self, tileNumber, n, player=None):
        # make sure player is specified if needed
        if not self.getTile(tileNumber).isShared():
            # assert player is not None

        if self.canMoveToken(tileNumber, n, player):
            tile = self.getTile(tileNumber)
            if tile.isShared():
                tokenPlayer = tile.getToken()
            else:
                tokenPlayer = player
            destinationTileNumber = tileNumber + n
            # if the token is moving off the board
            if destinationTileNumber == 14:
                tile.removeToken(tokenPlayer)
                # exitToken(tokenPlayer) # FIXME
            else:
                destinationTile = self.getTile(destinationTileNumber)
                destinationTile.addToken(tokenPlayer)
                tile.removeToken(tokenPlayer)

    # returns a tile. Also returns a player if a split tile was pressed
    # returns none if the button wasn't on the path
    def getTileByCoordinate(self, coordinate):
        x = coordinate[0]
        y = coordinate[1]
        player = None
        # if a split tile was pressed
        if y == 0 or y == 2:
            # set the player
            player = y // 2
            if x >= 0 and x <= 3:
                n = abs(x - 3)
                return self.getTile(n), player
            elif x >= 6 and x <= 7:
                n = 19 - x
                return self.getTile(n), player
            else:
                # raise Exception("Coordinate isn't a tile on the board; in a notch")
                print("Coordinate isn't a tile on the board; in a notch")
                return None
        # if a shared tile was pressed
        elif y == 1:
            n = x + 4
            return self.getTile(n), player
        else:
            # raise Exception("Coordinate isn't a tile on the board; not in first three rows")
            print("Coordinate isn't a tile on the board; not in first three rows")
            return None

    # returns list of instructions to print tokens in format:
    # ((x,y of token), player of token)
    def generateTokenPrintInstructions(self):
        toDisplay = []
        for tile in self.data:
            if tile.hasToken():
                # print(tile)
                # get the x coord
                x = tile.getXCoord()
                token = tile.getToken()
                # if it's a shared tile, we know the x and y, and there can only
                # be one token on it
                if tile.isShared():
                    y = 1
                    p = token
                    toDisplay.append( ((x,y),p) )
                # if it's a split tile, we have to check for both p0 and p1 case
                else:
                    if tile.hasToken(0):
                        y = 0
                        p = 0
                        toDisplay.append( ((x,y),p) )

                    if tile.hasToken(1):
                        y = 2
                        p = 1
                        toDisplay.append( ((x,y),p) )
        return toDisplay

class Dice():
    def __init__(self):
        self.values = [None for i in range(4)]

    def __str__(self):
        return "Dice: " + str(self.values)

    def hasValues(self):
        return self.values[0] != None

    # animates a roll landing on the current values of the dice. Use roll()
    # before animateRoll() so that they match up.
    def animateRoll(self):
        # randomly generate how many times each die should flip before settling
        flops = [random.randint(FLOP_LOW_BOUND,FLOP_HIGH_BOUND) for i in self.values]

        # set up the temporary position array for the dice such that the
        # generated flops will land each die on their current actual position
        positions = []
        for i, value in enumerate(self.values):
            change = flops[i] % 2
            if change:
                positions.append(int(not self.values[i]))
            else:
                positions.append(self.values[i])

        # as long as we're not out of flops, flop each die with flops left and
        # display each time
        while max(flops) > 0:
            self.displayFromSource(positions)
            for i, die in enumerate(self.values):
                if flops[i] == 0:
                    continue
                flops[i] -= 1
                positions[i] = int(not positions[i])
            time.sleep(FLOP_TIME)
        # display again so the last positions update is shown
        self.displayFromSource(positions)

        # assert positions == self.values

    def roll(self):
        for i in range(len(self.values)):
            self.values[i] = random.randint(0,1)
        self.animateRoll()

    # displays the dice from a given source (array of 4 bool values). Usually
    # takes self.values
    def displayFromSource(self, source):
        y = 3
        for i, value in enumerate(source):
            x = i+1
            if value == 1:
                color = DIE_ON_COLOR
            else:
                color = DIE_OFF_COLOR
            trellis.pixels[(x,y)] = color

    def getSum(self):
        return sum(self.values)

    def clear(self):
        self.values = [None for i in range(4)]


class Board():
    def __init__(self):
        self.path = Path()
        self.dice = Dice()
        self.turn = 0
        self.stage = "roll"
        self.selected = None
        self.preview = None

    # checks whether a given button pressed is on the path (not in the dice row)
    # or in the notches
    def isButtonOnPath(self, button):
        t = self.path.getTileByCoordinate(button)
        return t != None

    # checks whether a given coordinate has a token of the given player on it
    def coordinateHasToken(self, coordinate, player):
        tile, tilePlayer = self.path.getTileByCoordinate(coordinate)
        return tile.hasToken(player) and (tilePlayer == player or tilePlayer == None)

    # sets the previewed tile
    def setPreview(self, tile, player):
        self.preview = tile, player

    # attempts to set the selected tile field to a given coordinate
    # doesn't do anything if there's no tile there, or if the tile doesn't
    # belong to the person whose turn it is
    def setSelected(self, coord):
        tile, player = self.path.getTileByCoordinate(coord)
        # if trying to select the wrong player's token on a turn
        # first checks if the wrong row was pressed, then checks if the tile
        # has a token belonging to the player whose turn it is
        if player == (not self.turn) or (not tile.hasToken(self.turn)):
            # don't do anything
            return

        if tile.hasToken(self.turn):
            self.selected = coord

    def isSelected(self, coord):
        return self.selected == coord

    def paintTokens(self):
        for token in self.path.generateTokenPrintInstructions():
            p = token[1]
            coord = token[0]
            tileOfToken, playerOfToken = self.path.getTileByCoordinate(coord)

            isSelected = coord == self.selected
            if self.preview == None:
                isPreview = False
            elif tileOfToken.isShared():
                isPreview = tileOfToken == self.preview[0]
            else:
                isPreview = self.path.getTileByCoordinate(coord) == self.preview

            if isSelected:
                trellis.pixels[coord] = pulse(TOKEN_COLORS[p], TOKEN_PULSE_SPEED, TOKEN_PULSE_DEPTH)
            elif isPreview:
                trellis.pixels[coord] = pulse(TOKEN_COLORS[p], PREVIEW_PULSE_SPEED, PREVIEW_PULSE_DEPTH)
            else:
                trellis.pixels[coord] = TOKEN_COLORS[p]

    def paintPath(self): # TODO: refactor
        for tile in self.path.data:
            # in the case that it's in the middle row
            if tile.isShared():
                if not tile.hasToken():

                    if self.preview == None:
                        isPreview = False
                    else:
                        isPreview = tile == self.preview[0]

                    y = 1
                    x = tile.getXCoord()
                    if tile.isRosette():
                        color = ROSETTE_COLOR
                    else:
                        color = PATH_COLOR
                    if isPreview:
                        trellis.pixels[(x,y)] = pulse(color, TOKEN_PULSE_SPEED, TOKEN_PULSE_DEPTH)
                    else:
                        trellis.pixels[(x,y)] = color
            # in the case that it's in a split tile
            else:
                x = tile.getXCoord()
                # if we're drawing a path on the top pixel of this tile
                if not tile.hasToken(0):

                    if self.preview == None:
                        isPreview = False
                    else:
                        prevTile, prevPlayer = self.preview
                        isPreview = (tile == prevTile and prevPlayer == 0)

                    y = 0
                    if tile.isRosette():
                        color = ROSETTE_COLOR
                    else:
                        color = PATH_COLOR
                    if isPreview:
                        trellis.pixels[(x,y)] = pulse(color, TOKEN_PULSE_SPEED, TOKEN_PULSE_DEPTH)
                    else:
                        trellis.pixels[(x,y)] = color

                # if we're drawing a path on the bottom pixel of this tile
                if not tile.hasToken(1):

                    if self.preview == None:
                        isPreview = False
                    else:
                        prevTile, prevPlayer = self.preview
                        isPreview = (tile == prevTile and prevPlayer == 1)

                    y = 2
                    # p = 1 # I think this is leftover and doesn't matter !! FIXME
                    if tile.isRosette():
                        color = ROSETTE_COLOR
                    else:
                        color = PATH_COLOR
                    if isPreview:
                        trellis.pixels[(x,y)] = pulse(color, TOKEN_PULSE_SPEED, TOKEN_PULSE_DEPTH)
                    else:
                        trellis.pixels[(x,y)] = color

    def paintDice(self):
        if self.stage == "roll":
            trellis.pixels[DICE_ROLL_BUTTON] = pulse(DICE_ROLL_BUTTON_COLOR, TOKEN_PULSE_SPEED, TOKEN_PULSE_DEPTH)
        else:
            trellis.pixels[DICE_ROLL_BUTTON] = DICE_ROLL_BUTTON_COLOR

        dice = self.dice
        # if there's no roll, paint the waiting color
        if not dice.hasValues():
            y = 3
            for i in range(4):
                x = i+1
                trellis.pixels[(x,y)] = DIE_WAITING_COLOR
        # if there is a roll value, paint it
        else:
            self.dice.displayFromSource(dice.values)

    def paintBoard(self):
        self.paintPath()
        self.paintTokens()
        self.paintDice()

# Test board
board = Board()
board.path.getTile(0).setToken(2) # tile 0 has both p0 and p1 tokens
board.path.getTile(2).setToken(1) # tile 2 has p1 token
board.path.getTile(3).setToken(0) # tile 3 has p0 token
board.path.getTile(6).setToken(0)
board.path.getTile(6).setToken(1)
board.path.getTile(7).setToken(0)
board.path.getTile(10).setToken(1)
board.path.getTile(12).setToken(0)
board.path.getTile(13).setToken(1)

path = board.path

current_press = []
while True:
    # detect new keys pressed down
    pressed = trellis.pressed_keys
    new_buttons = [x for x in pressed if x not in current_press]

    # if a button's been pressed this time around the loop
    if new_buttons != []:
        # only care about the first button
        button = new_buttons[0]

        # MOVE STAGE
        if board.stage == "move":
            # if a button on the path was pressed
            if board.isButtonOnPath(button):
                rollValue = board.dice.getSum()
                tile, player = path.getTileByCoordinate(button)
                if tile.hasToken(board.turn):
                    tileNumber = tile.getNumber()
                    print("tile:", tile, "\nplayer if split:", player)

                    # if the button that was pressed is already selected,
                    if board.isSelected(button):
                        if path.canMoveToken(tileNumber, rollValue, player):
                            # move it
                            path.moveToken(tileNumber, rollValue, player)
                            # and then, unless it landed on a rosette, pass the turn
                            destinationTileNumber = tileNumber + rollValue
                            if destinationTileNumber <= 13:
                                if not path.getTile(destinationTileNumber).isRosette():
                                    # toggles value between 0 and 1
                                    board.turn ^= 1
                            else:
                                board.turn ^= 1
                            # also change the stage to "roll" for the next player's turn
                            board.stage = "roll"
                            board.preview = None

                    # if it's a new button that wasn't selected before
                    # and it's a tile and the current player controls that tile
                    else:
                        if board.coordinateHasToken(button, board.turn):
                            board.setSelected(button)
                            destinationTileNumber = tileNumber + rollValue
                            if destinationTileNumber <= 13:
                                destinationTile = path.getTile(destinationTileNumber)
                                board.setPreview(destinationTile, board.turn)
                                print(board.preview)

        # ROLL STAGE
        elif board.stage == "roll":
            if button == DICE_ROLL_BUTTON:
                # paint the button its original color in case it was pulsing
                trellis.pixels[DICE_ROLL_BUTTON] = DICE_ROLL_BUTTON_COLOR

                board.dice.roll()
                # if they roll a 0
                if board.dice.getSum() == 0:
                    time.sleep(ZERO_ROLL_DELAY)
                    board.turn ^= 1
                else:
                    board.stage = "move"

    # actually paint the board every loop
    board.paintBoard()

    # eliminate held down buttons
    current_press = pressed
