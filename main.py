from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from SpadesGame import Game, Round, Trick
import asyncio

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

game = Game()
first = game.players[game.first_bidder_index % 4]
current_round = Round(game.players, game.round_number, first, first)
current_round.deal()

server_phase = "bidding"
trick_winner_message = None
round_results = None

def get_state():
    player1 = game.players[0]
    legal = []
    if current_round.current_trick and server_phase == "playing":
        legal_cards = player1.hand.legal_plays(
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
                "hand": p.hand.to_dict(),
                "bid": p.bid
            } for p in game.players
        ],
        "scores": {p.name: game.scores[p] for p in game.players},
        "bags": {p.name: game.bags[p] for p in game.players},
        "round_number": game.round_number,
        "round_results": round_results
    }

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
    global trick_winner_message

    play_order = (
        current_round.players[current_round.players.index(current_round.current_leader):] +
        current_round.players[:current_round.players.index(current_round.current_leader)]
    )

    already_played = [player for player, card in current_round.current_trick.played_cards]

    for player in play_order:
        if player in already_played:
            continue
        if player == game.players[0]:
            return
        card = player.choose_card(
            current_round.current_trick,
            current_round.current_trick.spades_broken,
            current_round.trick_counts
        )
        current_round.current_trick.play_card(player, card)
        current_round.spades_broken = current_round.current_trick.spades_broken
        current_round.played_cards_history.append((player.name, card.to_dict()))
        await websocket.send_json(get_state())
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

    await websocket.send_json(get_state())
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

    await websocket.send_json(get_state())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global server_phase, trick_winner_message, current_round, round_results

    await websocket.accept()
    await websocket.send_json(get_state())

    while True:
        data = await websocket.receive_json()

        if data["action"] == "bid" and server_phase == "bidding":
            game.players[0].bid = data["value"]
            for bot in game.players[1:]:
                bot.make_bid()
            server_phase = "playing"
            current_round.current_trick = Trick(current_round.spades_broken, 1)
            await websocket.send_json(get_state())
            await play_bots_until_human(websocket)

        elif data["action"] == "play_card" and server_phase == "playing":
            trick_winner_message = None

            card_data = data["card"]
            player1 = game.players[0]

            legal_cards = player1.hand.legal_plays(
                current_round.current_trick.led_suit,
                current_round.current_trick.spades_broken
            )
            selected_card = next(
                (c for c in player1.hand.cards
                 if c.rank == card_data["rank"] and c.suit == card_data["suit"]),
                None
            )

            if selected_card is None or selected_card not in legal_cards:
                await websocket.send_json(get_state())
                continue

            current_round.current_trick.play_card(player1, selected_card)
            current_round.spades_broken = current_round.current_trick.spades_broken
            player1.hand.play_card(selected_card)
            current_round.played_cards_history.append((player1.name, selected_card.to_dict()))

            await websocket.send_json(get_state())
            await asyncio.sleep(0.8)

            await play_bots_until_human(websocket)

        elif data["action"] == "next_round" and server_phase == "round_over":
            round_results = None
            game.rounds_history.append(current_round)
            game.round_number += 1
            game.first_bidder_index += 1

            if game.is_game_over():
                server_phase = "game_over"
                await websocket.send_json(get_state())
                continue

            first = game.players[game.first_bidder_index % 4]
            current_round = Round(game.players, game.round_number, first, first)
            current_round.deal()
            server_phase = "bidding"
            await websocket.send_json(get_state())
