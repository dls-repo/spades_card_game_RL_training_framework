import random

card_ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
card_suits = ["Spades", "Clubs", "Diamonds", "Hearts"]


class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank

    def rank_value(self):
        return card_ranks.index(self.rank)

    def is_trump(self):
        return self.suit == "Spades"

    def __str__(self):
        return f"{self.rank} of {self.suit}"


class Hand:
    def __init__(self, cards):
        self.cards = cards

    def has_suit(self, suit):
        return any(c.suit == suit for c in self.cards)

    def play_card(self, card):
        self.cards.remove(card)

    def __len__(self):
        return len(self.cards)

    def __str__(self):
        return ", ".join(str(card) for card in self.cards)

    def legal_plays(self, led_suit, spades_broken):
        if self.has_suit(led_suit):
            return [c for c in self.cards if c.suit == led_suit]
        if not spades_broken:
            non_spades = [c for c in self.cards if c.suit != "Spades"]
            if non_spades:
                return non_spades
        return self.cards


class Trick:
    def __init__(self, spades_broken):
        self.played_cards = []
        self.led_suit = None
        self.spades_broken = spades_broken
        self.winner = None

    def play_card(self, player, card):
        self.played_cards.append((player, card))
        if self.led_suit is None:
            self.led_suit = card.suit
        if card.suit == "Spades":
            self.spades_broken = True

    def is_complete(self):
        return len(self.played_cards) == 4

    def determine_winner(self):
        # check if any spades were played since the highest of those cards would be the winner
        # lambda function is there to pull just the card from the (player, card) combined data
        # when applying the max() function for comparison
        # the [0] at the end says to only store the player in the winner variable
        spades_played = [(player, card) for player, card in self.played_cards if card.suit == "Spades"]
        if spades_played:
            self.winner = max(spades_played, key=lambda x: x[1].rank_value())[0]
        else:
            led_suit_cards = [(player, card) for player, card in self.played_cards if card.suit == self.led_suit]
            self.winner = max(led_suit_cards, key=lambda x: x[1].rank_value())[0]
        return self.winner


class Player:
    def __init__(self, name):
        self.name = name
        self.hand = None
        self.bid = None
        self.tricks_won = 0

    def make_bid(self):
        raise NotImplementedError

    def choose_card(self, trick, spades_broken):
        raise NotImplementedError


class HumanPlayer(Player):
    def __init__(self, name):
        super().__init__(name)

    def make_bid(self):
        print(f"\n{self.name}, your hand is:")
        for card in self.hand.cards:
            print(f"  {card}")
        while True:
            bid = int(input(f"\n{self.name}, enter your bid (0-13): "))
            if 0 <= bid <= 13:
                self.bid = bid
                break
            print("Invalid bid. Must be between 0 and 13.")

    def choose_card(self, trick, spades_broken):
        legal = self.hand.legal_plays(trick.led_suit, spades_broken)
        print(f"\n{self.name}'s turn")
        print("Your hand:")
        for card in self.hand.cards:
            print(f"  {card}")
        print("\nLegal plays:")
        for i, card in enumerate(legal):
            print(f"  {i}: {card}")
        while True:
            choice = int(input("Choose a card by number: "))
            if 0 <= choice < len(legal):
                selected = legal[choice]
                self.hand.play_card(selected)
                return selected
            print(f"Invalid choice. Please enter a number between 0 and {len(legal) - 1}.")

class RuleBasedBot(Player):
    def __init__(self, name):
        super().__init__(name)

    def make_bid(self):
        self.bid = random.randint(0, 13)
        print(f"\n{self.name} bids {self.bid}")

    def choose_card(self, trick, spades_broken):
        legal = self.hand.legal_plays(trick.led_suit, spades_broken)
        print(f"\n{self.name}'s turn")
        selected = random.choice(legal)
        print(f"{self.name} plays: {selected}")
        return selected

class Round:
    def __init__(self, players, round_number, first_leader, first_bidder):
        self.players = players
        self.round_number = round_number
        self.first_leader = first_leader
        self.first_bidder = first_bidder
        self.current_leader = first_leader
        self.tricks_played = 0
        self.current_trick = None
        self.spades_broken = False
        self.played_cards_history = []
        self.trick_counts = {player: 0 for player in players}

    def deal(self):
        deck = []
        for suit in card_suits:
            for rank in card_ranks:
                deck.append(Card(suit, rank))
        random.shuffle(deck)
        self.players[0].hand = Hand(deck[0:13])
        self.players[1].hand = Hand(deck[13:26])
        self.players[2].hand = Hand(deck[26:39])
        self.players[3].hand = Hand(deck[39:52])

    def collect_bids(self):
        bid_order = self.players[self.players.index(self.first_bidder):] + \
                    self.players[:self.players.index(self.first_bidder)]
        for player in bid_order:
            player.make_bid()

    def play_trick(self):
        self.current_trick = Trick(self.spades_broken)
        leader = self.current_leader
        play_order = self.players[self.players.index(leader):] + \
                     self.players[:self.players.index(leader)]
        for player in play_order:
            card = player.choose_card(self.current_trick, self.spades_broken)
            self.current_trick.play_card(player, card)
            self.played_cards_history.append(card)
        self.current_trick.determine_winner()
        self.current_leader = self.current_trick.winner
        self.trick_counts[self.current_trick.winner] += 1
        self.spades_broken = self.current_trick.spades_broken
        self.tricks_played += 1

    def is_complete(self):
        return self.tricks_played == 13

    def play_round(self):
        self.deal()
        self.collect_bids()
        while not self.is_complete():
            self.play_trick()


class Game:
    def __init__(self):
        self.players = [
            HumanPlayer("Player 1"),
            RuleBasedBot("Player 2"),
            RuleBasedBot("Player 3"),
            RuleBasedBot("Player 4")
        ]
        self.scores = {player: 0 for player in self.players}
        self.bags = {player: 0 for player in self.players}
        self.round_number = 1
        self.first_bidder_index = 0
        self.rounds_history = []

    def start_round(self):
        first = self.players[self.first_bidder_index % 4]
        current_round = Round(self.players, self.round_number, first, first)
        current_round.play_round()
        self.score_round(current_round)
        self.rounds_history.append(current_round)
        self.round_number += 1
        self.first_bidder_index += 1

    def score_round(self, current_round):
        print(f"\n--- Round {self.round_number} Results ---")
        for player in self.players:
            tricks = current_round.trick_counts[player]
            bid = player.bid
            if bid == 0:
                if tricks == 0:
                    self.scores[player] += 100
                    print(f"{player.name}: nil bid successful! +100 points")
                else:
                    self.scores[player] -= 100
                    print(f"{player.name}: nil bid failed with {tricks} trick(s) — -100 points")
            elif tricks == bid:
                points = bid * 10
                self.scores[player] += points
                print(f"{player.name}: hit bid of {bid} — +{points} points")
            elif tricks > bid:
                bags = tricks - bid
                points = bid * 10
                self.scores[player] += points + bags
                self.bags[player] += bags
                print(f"{player.name}: over bid by {bags} — +{points + bags} points, {bags} bag(s)")
                if self.bags[player] >= 10:
                    self.scores[player] -= 100
                    self.bags[player] -= 10
                    print(f"{player.name}: 10 bags! -100 point penalty, bag count reset")
            else:
                points = bid * 10
                self.scores[player] -= points
                print(f"{player.name}: missed bid of {bid} — -{points} points")

    def print_scores(self):
        print("\n--- Current Scores ---")
        for player in self.players:
            print(f"{player.name}: {self.scores[player]} points, {self.bags[player]} bags")

    def is_game_over(self):
        return self.round_number > 8

    def play_game(self):
        print("Welcome to Spades!")
        while not self.is_game_over():
            print(f"\n=== Round {self.round_number} ===")
            self.start_round()
            self.print_scores()
        print("\n=== Game Over ===")
        self.print_scores()
        winner = max(self.players, key=lambda p: self.scores[p])
        print(f"\n{winner.name} wins with {self.scores[winner]} points!")


game = Game()
game.play_game()
