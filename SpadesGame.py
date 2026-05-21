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

    def to_dict(self):
        return {"rank": self.rank, "suit": self.suit}


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
        if led_suit and self.has_suit(led_suit):
            return [c for c in self.cards if c.suit == led_suit]
        if led_suit:
            return self.cards
        if not spades_broken:
            non_spades = [c for c in self.cards if c.suit != "Spades"]
            if non_spades:
                return non_spades
        return self.cards

    def to_dict(self):
        return [card.to_dict() for card in self.cards]


class Trick:
    def __init__(self, spades_broken, trick_number):
        self.played_cards = []
        self.led_suit = None
        self.spades_broken = spades_broken
        self.winner = None
        self.trick_number = trick_number

    def play_card(self, player, card):
        self.played_cards.append((player, card))
        if self.led_suit is None:
            self.led_suit = card.suit
        if card.suit == "Spades":
            self.spades_broken = True

    def is_complete(self):
        return len(self.played_cards) == 4

    def determine_winner(self):
        spades_played = [(player, card) for player, card in self.played_cards if card.suit == "Spades"]
        if spades_played:
            self.winner = max(spades_played, key=lambda x: x[1].rank_value())[0]
        else:
            led_suit_cards = [(player, card) for player, card in self.played_cards if card.suit == self.led_suit]
            self.winner = max(led_suit_cards, key=lambda x: x[1].rank_value())[0]
        return self.winner

    def to_dict(self):
        return {
            "trick_number": self.trick_number,
            "led_suit": self.led_suit,
            "spades_broken": self.spades_broken,
            "winner": self.winner.name if self.winner else None,
            "played_cards": [
                {"player": player.name, "card": card.to_dict()}
                for player, card in self.played_cards
            ]
        }


class Player:
    def __init__(self, name):
        self.name = name
        self.hand = None
        self.bid = None
        self.tricks_won = 0
        self._game_ref = None
        self._round_ref = None

    def make_bid(self):
        raise NotImplementedError

    def choose_card(self, trick, spades_broken, trick_counts):
        raise NotImplementedError

    def to_dict(self):
        return {
            "name": self.name,
            "bid": self.bid,
            "tricks_won": self.tricks_won,
            "hand": self.hand.to_dict() if self.hand else [],
            "type": self.__class__.__name__
        }


class HumanPlayer(Player):
    def __init__(self, name):
        super().__init__(name)

    def make_bid(self):
        pass

    def choose_card(self, trick, spades_broken, trick_counts):
        pass


class RuleBasedBot(Player):
    def __init__(self, name):
        super().__init__(name)

    def make_bid(self):
        temporary_bid = 0
        for card in self.hand.cards:
            if card.rank_value() == 12:
                temporary_bid += 1
            if card.suit == "Spades" and card.rank_value() > 6:
                temporary_bid += 1
        self.bid = temporary_bid

    def choose_card(self, trick, spades_broken, trick_counts):
        legal = self.hand.legal_plays(trick.led_suit, spades_broken)

        tricks_needed = self.bid - trick_counts[self]

        spade_already_played = (
            trick.led_suit != "Spades" and
            any(card.suit == "Spades" for _, card in trick.played_cards)
        )

        if self.bid == 0:
            selected = min(legal, key=lambda c: c.rank_value())

        elif tricks_needed <= 0:
            if trick.led_suit and self.hand.has_suit(trick.led_suit):
                led_cards = [c for c in legal if c.suit == trick.led_suit]
                selected = min(led_cards, key=lambda c: c.rank_value())
            else:
                non_spades = [c for c in legal if c.suit != "Spades"]
                if non_spades:
                    selected = max(non_spades, key=lambda c: c.rank_value())
                else:
                    selected = min(legal, key=lambda c: c.rank_value())

        else:
            if spade_already_played:
                selected = min(legal, key=lambda c: c.rank_value())
            elif trick.led_suit is None:
                non_spades = [c for c in legal if c.suit != "Spades"]
                if non_spades:
                    selected = max(non_spades, key=lambda c: c.rank_value())
                else:
                    selected = max(legal, key=lambda c: c.rank_value())
            elif not self.hand.has_suit(trick.led_suit) and not spades_broken:
                spades = [c for c in legal if c.suit == "Spades"]
                if spades:
                    selected = min(spades, key=lambda c: c.rank_value())
                else:
                    selected = max(legal, key=lambda c: c.rank_value())
            else:
                selected = max(legal, key=lambda c: c.rank_value())

        self.hand.play_card(selected)
        return selected


class RLAgent(Player):
    def __init__(self, name, model_path="spades_agent"):
        super().__init__(name)
        from sb3_contrib import MaskablePPO
        from SpadesEnv import SpadesEnv
        self.model = MaskablePPO.load(model_path)
        self.env = SpadesEnv()

    def _build_bidding_obs(self):
        import numpy as np
        from SpadesEnv import card_to_index
        obs = np.zeros(167, dtype=np.float32)
        for card in self.hand.cards:
            obs[card_to_index(card)] = 1.0
        obs[166] = 1.0
        return obs

    def _build_bidding_mask(self):
        import numpy as np
        mask = np.zeros(52, dtype=bool)
        for i in range(14):
            mask[i] = True
        return mask

    def make_bid(self):
        if self._round_ref is None or self._round_ref.current_trick is None:
            obs = self._build_bidding_obs()
            mask = self._build_bidding_mask()
        else:
            self.env.game = self._game_ref
            self.env.current_round = self._round_ref
            self.env.agent = self
            self.env.is_bidding = True
            obs = self.env._get_observation()
            mask = self.env._get_action_mask()
        action, _ = self.model.predict(obs, action_masks=mask, deterministic=True)
        self.bid = min(int(action), 13)

    def choose_card(self, trick, spades_broken, trick_counts):
        from SpadesEnv import index_to_card
        self.env.game = self._game_ref
        self.env.current_round = self._round_ref
        self.env.agent = self
        self.env.is_bidding = False
        obs = self.env._get_observation()
        mask = self.env._get_action_mask()
        action, _ = self.model.predict(obs, action_masks=mask, deterministic=True)
        card = index_to_card(int(action))
        matching = next(
            (c for c in self.hand.cards
             if c.rank == card.rank and c.suit == card.suit),
            None
        )
        if matching is None:
            legal = self.hand.legal_plays(trick.led_suit, spades_broken)
            matching = random.choice(legal)
        self.hand.play_card(matching)
        return matching


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
        self.tricks_history = []
        self.trick_counts = {player: 0 for player in players}
        self.bids = {}

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
        for player in self.players:
            player._round_ref = self

    def collect_bids(self):
        bid_order = self.players[self.players.index(self.first_bidder):] + \
                    self.players[:self.players.index(self.first_bidder)]
        for player in bid_order:
            player.make_bid()
            self.bids[player.name] = player.bid

    def play_trick(self):
        for player in self.players:
            player._round_ref = self

        self.current_trick = Trick(self.spades_broken, self.tricks_played + 1)
        leader = self.current_leader
        play_order = self.players[self.players.index(leader):] + \
                     self.players[:self.players.index(leader)]
        for player in play_order:
            card = player.choose_card(
                self.current_trick,
                self.current_trick.spades_broken,
                self.trick_counts
            )
            self.current_trick.play_card(player, card)
            self.spades_broken = self.current_trick.spades_broken
            self.played_cards_history.append((player.name, card.to_dict(), card))
        self.current_trick.determine_winner()
        winner = self.current_trick.winner
        winning_card = max(
            [card for _, card in self.current_trick.played_cards
             if card.suit == "Spades"] or
            [card for _, card in self.current_trick.played_cards
             if card.suit == self.current_trick.led_suit],
            key=lambda c: c.rank_value()
        )
        print(f"\n--- {winner.name} wins trick {self.tricks_played + 1} with {winning_card} ---")
        self.current_leader = winner
        self.trick_counts[winner] += 1
        self.tricks_history.append(self.current_trick)
        self.tricks_played += 1

    def is_complete(self):
        return self.tricks_played == 13

    def play_round(self):
        self.deal()
        self.collect_bids()
        while not self.is_complete():
            self.play_trick()

    def to_dict(self):
        return {
            "round_number": self.round_number,
            "bids": self.bids,
            "trick_counts": {p.name: self.trick_counts[p] for p in self.players},
            "spades_broken": self.spades_broken,
            "tricks_history": [t.to_dict() for t in self.tricks_history],
            "played_cards_history": [
                (name, card_dict) for name, card_dict, _ in self.played_cards_history
            ]
        }


class Game:
    def __init__(self, config=None):
        if config is None:
            config = {"humans": 1, "rl_agents": 1, "bots": 2}

        assert config["humans"] + config["rl_agents"] + config["bots"] == 4, \
            "Must have exactly 4 players"

        self.players = []
        player_num = 1

        for _ in range(config["humans"]):
            self.players.append(HumanPlayer(f"Player {player_num}"))
            player_num += 1

        for _ in range(config["rl_agents"]):
            self.players.append(RLAgent(f"RL Agent {player_num}"))
            player_num += 1

        for _ in range(config["bots"]):
            self.players.append(RuleBasedBot(f"Bot {player_num}"))
            player_num += 1

        self.config = config
        self.scores = {player: 0 for player in self.players}
        self.bags = {player: 0 for player in self.players}
        self.round_number = 1
        self.first_bidder_index = 0
        self.rounds_history = []

    def start_round(self):
        for player in self.players:
            player._game_ref = self

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

    def to_dict(self):
        return {
            "scores": {p.name: self.scores[p] for p in self.players},
            "bags": {p.name: self.bags[p] for p in self.players},
            "round_number": self.round_number,
            "players": [p.to_dict() for p in self.players],
            "rounds_history": [r.to_dict() for r in self.rounds_history]
        }

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


if __name__ == "__main__":
    game = Game(config={"humans": 1, "rl_agents": 0, "bots": 3})
    game.play_game()
