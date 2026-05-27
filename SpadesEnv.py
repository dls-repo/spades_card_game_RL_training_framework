import gymnasium as gym
import numpy as np
from gymnasium import spaces
from SpadesGame import Game, Round, Trick, Card, Hand

SUIT_ORDER = ["Spades", "Clubs", "Diamonds", "Hearts"]
RANK_ORDER = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]


def card_to_index(card):
    return SUIT_ORDER.index(card.suit) * 13 + RANK_ORDER.index(card.rank)


def index_to_card(index):
    suit = SUIT_ORDER[index // 13]
    rank = RANK_ORDER[index % 13]
    return Card(suit, rank)


class SpadesEnv(gym.Env):
    def __init__(self):
        super().__init__()

        self.action_space = spaces.Discrete(52)

        self.observation_space = spaces.Box(
            low=0,
            high=1,
            shape=(167,),
            dtype=np.float32
        )

        self.game = None
        self.current_round = None
        self.is_bidding = True
        self.agent = None

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.game = Game(config={"humans": 0, "rl_agents": 0, "bots": 4})
        first = self.game.players[self.game.first_bidder_index % 4]
        self.current_round = Round(
            self.game.players,
            self.game.round_number,
            first,
            first
        )
        self.current_round.deal()
        self.agent = self.game.players[0]
        self.is_bidding = True
        obs = self._get_observation()
        return obs, {"action_mask": self._get_action_mask()}

    def _get_observation(self):
        obs = np.zeros(167, dtype=np.float32)

        # own hand — indices 0-51
        for card in self.agent.hand.cards:
            obs[card_to_index(card)] = 1.0

        # cards played this trick — indices 52-103
        if self.current_round.current_trick:
            for _, card in self.current_round.current_trick.played_cards:
                obs[52 + card_to_index(card)] = 1.0

        # cards played this round — indices 104-155
        for _, _, card in self.current_round.played_cards_history:
            obs[104 + card_to_index(card)] = 1.0

        # bids — indices 156-159
        for i, player in enumerate(self.game.players):
            if player.bid is not None:
                obs[156 + i] = player.bid / 13.0

        # trick counts — indices 160-163
        for i, player in enumerate(self.game.players):
            obs[160 + i] = self.current_round.trick_counts[player] / 13.0

        # spades broken — index 164
        obs[164] = 1.0 if self.current_round.spades_broken else 0.0

        # own bid — index 165
        if self.agent.bid is not None:
            obs[165] = self.agent.bid / 13.0

        # is bidding phase — index 166
        obs[166] = 1.0 if self.is_bidding else 0.0

        return obs

    def _get_action_mask(self):
        mask = np.zeros(52, dtype=bool)
        if self.is_bidding:
            for i in range(14):
                mask[i] = True
        else:
            legal = self.agent.hand.legal_plays(
                self.current_round.current_trick.led_suit,
                self.current_round.current_trick.spades_broken
            )
            for card in legal:
                mask[card_to_index(card)] = True
        return mask

    def step(self, action):
        reward = 0.0
        done = False

        if self.is_bidding:
            self.agent.bid = min(action, 13)
            for bot in self.game.players[1:]:
                bot.make_bid()
            self.is_bidding = False
            self.current_round.current_trick = Trick(
                self.current_round.spades_broken, 1
            )
            self._play_bots_until_agent()

        else:
            card = index_to_card(action)

            matching = next(
                (c for c in self.agent.hand.cards
                 if c.rank == card.rank and c.suit == card.suit),
                None
            )
            if matching is None:
                obs = self._get_observation()
                return obs, -1.0, False, False, {"action_mask": self._get_action_mask()}

            self.current_round.current_trick.play_card(self.agent, matching)
            self.current_round.spades_broken = self.current_round.current_trick.spades_broken
            self.agent.hand.play_card(matching)
            self.current_round.played_cards_history.append(
                (self.agent.name, matching.to_dict(), matching)
            )

            self._play_bots_until_agent()

            if self.current_round.current_trick.is_complete():
                self.current_round.current_trick.determine_winner()
                winner = self.current_round.current_trick.winner
                self.current_round.trick_counts[winner] += 1
                self.current_round.current_leader = winner
                self.current_round.tricks_played += 1

                if self.current_round.is_complete():
                    reward = self._calculate_reward()
                    done = True
                else:
                    self.current_round.current_trick = Trick(
                        self.current_round.spades_broken,
                        self.current_round.tricks_played + 1
                    )
                    self._play_bots_until_agent()

        obs = self._get_observation()
        return obs, reward, done, False, {"action_mask": self._get_action_mask()}

    def _play_bots_until_agent(self):
        play_order = (
            self.current_round.players[
                self.current_round.players.index(self.current_round.current_leader):
            ] +
            self.current_round.players[
                :self.current_round.players.index(self.current_round.current_leader)
            ]
        )
        already_played = [p for p, _ in self.current_round.current_trick.played_cards]
        for player in play_order:
            if player in already_played:
                continue
            if player == self.agent:
                return
            card = player.choose_card(
                self.current_round.current_trick,
                self.current_round.current_trick.spades_broken,
                self.current_round.trick_counts
            )
            self.current_round.current_trick.play_card(player, card)
            self.current_round.spades_broken = self.current_round.current_trick.spades_broken
            self.current_round.played_cards_history.append(
                (player.name, card.to_dict(), card)
            )

    def _calculate_reward(self):
        tricks = self.current_round.trick_counts[self.agent]
        bid = self.agent.bid
        if bid == 0:
            return 10.0 if tricks == 0 else -10.0
        elif tricks == bid:
            return 5.0 + bid * 0.5
        elif tricks > bid:
            bags = tricks - bid
            return 2.0 - bags * 0.5
        else:
            missed = bid - tricks
            return -5.0 - missed * 0.5
