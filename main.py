from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from SpadesGame import Game, Round, Trick, HumanPlayer
import asyncio

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

game = None
current_round = None
server_phase = "lobby"
trick_winner_message = None
round_results = None
bots_before = []
bots_after = []

# multiplayer — track connected websockets and their player slots
connected_clients = {}  # websocket -> player_index
client_list = []        # ordered list of websockets


def get_state(player_index=0):
    if server_phase == "lobby":
        return {"phase": "lobby"}

    humans = [p for p in game.players if isinstance(p, HumanPlayer)]
    viewing_player = game.players[player_index]

    legal = []
    if isinstance(viewing_player, HumanPlayer) and \
       current_round.current_trick and server_phase == "playing":
        legal_cards = viewing_player.hand.legal_plays(
            current_round.current_trick.led_suit,
            current_round.current_trick.spades_broken
        )
        legal = [c.to_dict() for c in legal_cards]

    return {
        "phase": server_phase,
        "trick_winner": trick_winner_message,
        "legal_plays": legal,
        "trick_counts": {
            p.name: current_round.trick_counts[p] for p in game.players
        },
        "current_trick": [
            {
                "player": player.name,
                "card": card.to_dict()
            }
            for player, card in current_round.current_trick.played_cards
        ] if current_round.current_trick else [],
        "players": [
            {
                "name": p.name,
                "hand": p.hand.to_dict() if p.hand else [],
                "bid": p.bid,
                "type": p.__class__.__name__
            } for p in game.players
        ],
        "scores": {p.name: game.scores[p] for p in game.players},
        "bags": {p.name: game.bags[p] for p in game.players},
        "round_number": game.round_number,
        "round_results": round_results,
        "config": game.config,
        "your_player_index": player_index,
        "whose_turn": get_whose_turn()
    }


def get_whose_turn():
    if not current_round or not current_round.current_trick:
        return None
    already_played = [p for p, _ in current_round.current_trick.played_cards]
    play_order = (
        current_round.players[current_round.players.index(current_round.current_leader):] +
        current_round.players[:current_round.players.index(current_round.current_leader)]
    )
    for player in play_order:
        if player not in already_played:
            return game.players.index(player)
    return None


async def broadcast_state():
    for ws, player_index in connected_clients.items():
        try:
            await ws.send_json(get_state(player_index))
        except Exception:
            pass


def setup_game(config):
    global game, current_round, server_phase, trick_winner_message, round_results
    game = Game(config=config)
    for player in game.players:
        player._game_ref = game
        player.bid = None
    first = game.players[game.first_bidder_index % 4]
    current_round = Round(game.players, game.round_number, first, first)
    current_round.deal()
    server_phase = "bidding"
    trick_winner_message = None
    round_results = None


def collect_bids_around_human():
    global bots_before, bots_after
    humans = [p for p in game.players if isinstance(p, HumanPlayer)]
    if not humans:
        bots_before = list(game.players)
        bots_after = []
        return
    player1 = humans[0]
    bid_order = (
        current_round.players[current_round.players.index(current_round.first_bidder):] +
        current_round.players[:current_round.players.index(current_round.first_bidder)]
    )
    bots_before = [p for p in bid_order[:bid_order.index(player1)]]
    bots_after = [p for p in bid_order[bid_order.index(player1) + 1:]
                  if not isinstance(p, HumanPlayer)]


def score_current_round():
    global round_results
    results = []
    for player in game.players:
        tricks = current_round.trick_counts[player]
        bid = player.bid
        if bid == 0:
            if tricks == 0:
                game.scores[player] += 100
                results.append(f"{player.name}: nil bid successful! +100 pts")
            else:
                game.scores[player] -= 100
                results.append(f"{player.name}: nil bid failed — -100 pts")
        elif tricks == bid:
            points = bid * 10
            game.scores[player] += points
            results.append(f"{player.name}: hit bid of {bid} — +{points} pts")
        elif tricks > bid:
            bags = tricks - bid
            points = bid * 10
            game.scores[player] += points + bags
            game.bags[player] += bags
            msg = f"{player.name}: over by {bags} — +{points + bags} pts, {bags} bag(s)"
            if game.bags[player] >= 10:
                game.scores[player] -= 100
                game.bags[player] -= 10
                msg += " | 10 bags! -100 pts"
            results.append(msg)
        else:
            points = bid * 10
            game.scores[player] -= points
            results.append(f"{player.name}: missed bid of {bid} — -{points} pts")
    round_results = results


async def play_bots_until_human(websocket):
    humans = [p for p in game.players if isinstance(p, HumanPlayer)]
    if not humans:
        await play_all_bots(websocket)
        return

    play_order = (
        current_round.players[current_round.players.index(current_round.current_leader):] +
        current_round.players[:current_round.players.index(current_round.current_leader)]
    )

    already_played = [player for player, card in current_round.current_trick.played_cards]

    for player in play_order:
        if player in already_played:
            continue
        if isinstance(player, HumanPlayer):
            await broadcast_state()
            return
        card = player.choose_card(
            current_round.current_trick,
            current_round.current_trick.spades_broken,
            current_round.trick_counts
        )
        current_round.current_trick.play_card(player, card)
        current_round.spades_broken = current_round.current_trick.spades_broken
        current_round.played_cards_history.append((player.name, card.to_dict(), card))
        await broadcast_state()
        await asyncio.sleep(0.8)

    await resolve_trick(websocket)


async def play_all_bots(websocket):
    play_order = (
        current_round.players[current_round.players.index(current_round.current_leader):] +
        current_round.players[:current_round.players.index(current_round.current_leader)]
    )

    already_played = [player for player, card in current_round.current_trick.played_cards]

    for player in play_order:
        if player in already_played:
            continue
        card = player.choose_card(
            current_round.current_trick,
            current_round.current_trick.spades_broken,
            current_round.trick_counts
        )
        current_round.current_trick.play_card(player, card)
        current_round.spades_broken = current_round.current_trick.spades_broken
        current_round.played_cards_history.append((player.name, card.to_dict(), card))
        await broadcast_state()
        await asyncio.sleep(0.8)

    await resolve_trick(websocket)


async def resolve_trick(websocket):
    global trick_winner_message, server_phase

    current_round.current_trick.determine_winner()
    winner = current_round.current_trick.winner
    current_round.trick_counts[winner] += 1
    current_round.current_leader = winner
    current_round.tricks_played += 1
    trick_winner_message = f"{winner.name} wins the trick!"

    await broadcast_state()
    await asyncio.sleep(1.5)

    trick_winner_message = None

    if not current_round.is_complete():
        current_round.current_trick = Trick(
            current_round.spades_broken,
            current_round.tricks_played + 1
        )
        await play_bots_until_human(websocket)
    else:
        score_current_round()
        server_phase = "round_over"

    await broadcast_state()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global server_phase, trick_winner_message, current_round, round_results

    await websocket.accept()

    # assign player slot
    player_index = len(connected_clients)
    connected_clients[websocket] = player_index
    client_list.append(websocket)

    await websocket.send_json({"phase": "lobby", "your_player_index": player_index})

    try:
        while True:
            data = await websocket.receive_json()
            my_index = connected_clients[websocket]

            if data["action"] == "configure":
                setup_game(data["config"])
                collect_bids_around_human()
                for bot in bots_before:
                    bot.make_bid()
                humans = [p for p in game.players if isinstance(p, HumanPlayer)]
                if not humans:
                    for bot in game.players:
                        bot.make_bid()
                    server_phase = "playing"
                    current_round.current_trick = Trick(current_round.spades_broken, 1)
                    await broadcast_state()
                    await play_all_bots(websocket)
                else:
                    await broadcast_state()

            elif data["action"] == "bid" and server_phase == "bidding":
                player = game.players[my_index]
                if isinstance(player, HumanPlayer):
                    player.bid = data["value"]
                    # check if all humans have bid
                    humans = [p for p in game.players if isinstance(p, HumanPlayer)]
                    all_bid = all(p.bid is not None for p in humans)
                    if all_bid:
                        for bot in bots_after:
                            bot.make_bid()
                        server_phase = "playing"
                        current_round.current_trick = Trick(current_round.spades_broken, 1)
                        await broadcast_state()
                        await play_bots_until_human(websocket)
                    else:
                        await broadcast_state()

            elif data["action"] == "play_card" and server_phase == "playing":
                if "card" not in data:
                    await broadcast_state()
                    continue

                player = game.players[my_index]
                if not isinstance(player, HumanPlayer):
                    continue

                # verify it's this player's turn
                whose_turn = get_whose_turn()
                if whose_turn != my_index:
                    await broadcast_state()
                    continue

                trick_winner_message = None
                card_data = data["card"]

                legal_cards = player.hand.legal_plays(
                    current_round.current_trick.led_suit,
                    current_round.current_trick.spades_broken
                )
                selected_card = next(
                    (c for c in player.hand.cards
                     if c.rank == card_data["rank"] and c.suit == card_data["suit"]),
                    None
                )

                if selected_card is None or selected_card not in legal_cards:
                    await broadcast_state()
                    continue

                current_round.current_trick.play_card(player, selected_card)
                current_round.spades_broken = current_round.current_trick.spades_broken
                player.hand.play_card(selected_card)
                current_round.played_cards_history.append(
                    (player.name, selected_card.to_dict(), selected_card)
                )

                await broadcast_state()
                await asyncio.sleep(0.8)

                await play_bots_until_human(websocket)

            elif data["action"] == "next_round" and server_phase == "round_over":
                round_results = None
                game.rounds_history.append(current_round)
                game.round_number += 1
                game.first_bidder_index += 1

                if game.is_game_over():
                    server_phase = "game_over"
                    await broadcast_state()
                    continue

                first = game.players[game.first_bidder_index % 4]
                current_round = Round(game.players, game.round_number, first, first)
                current_round.deal()

                for player in game.players:
                    player._game_ref = game
                    player.bid = None

                server_phase = "bidding"
                collect_bids_around_human()
                for bot in bots_before:
                    bot.make_bid()

                humans = [p for p in game.players if isinstance(p, HumanPlayer)]
                if not humans:
                    for bot in game.players:
                        bot.make_bid()
                    server_phase = "playing"
                    current_round.current_trick = Trick(current_round.spades_broken, 1)
                    await broadcast_state()
                    await play_all_bots(websocket)
                else:
                    await broadcast_state()

            elif data["action"] == "play_again":
                server_phase = "lobby"
                await broadcast_state()

    except WebSocketDisconnect:
        connected_clients.pop(websocket, None)
        if websocket in client_list:
            client_list.remove(websocket)
