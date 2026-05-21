const BACKGROUND = "#35654d"
const cardW = 80
const cardH = 120
const cardY = 670
const spacing = 90
const SUITS = {
    "Spades": "♠",
    "Hearts": "♥",
    "Diamonds": "♦",
    "Clubs": "♣"
}
const SUIT_COLORS = {
    "Spades": "black",
    "Hearts": "red",
    "Diamonds": "red",
    "Clubs": "black"
}

game.width = 1200
game.height = 800

const ctx = game.getContext("2d")

let selectedIndex = null
let currentBid = 0
let gamePhase = "lobby"
let players = null
let currentTrick = []
let trickCounts = {}
let trickWinner = null
let legalPlays = []
let scores = {}
let bags = {}
let roundNumber = 1
let roundResults = null
let gameConfig = null
let myPlayerIndex = 0
let viewingPlayerIndex = 0
let whoseTurn = null
const cards = []

const PRESETS = [
    {
        label: "Solo vs Bots",
        desc: "You vs 3 Rule Based Bots",
        config: {humans: 1, rl_agents: 0, bots: 3},
        color: "#2e7d32"
    },
    {
        label: "Solo vs AI",
        desc: "You vs 3 RL Agents",
        config: {humans: 1, rl_agents: 3, bots: 0},
        color: "#1565c0"
    },
    {
        label: "Solo vs Mixed",
        desc: "You vs 1 RL Agent + 2 Bots",
        config: {humans: 1, rl_agents: 1, bots: 2},
        color: "#6a1b9a"
    },
    {
        label: "Spectator",
        desc: "Watch RL Agent vs 3 Bots",
        config: {humans: 0, rl_agents: 1, bots: 3},
        color: "#e65100"
    },
    {
        label: "AI Showdown",
        desc: "Watch 4 RL Agents",
        config: {humans: 0, rl_agents: 4, bots: 0},
        color: "#880e4f"
    },
    {
        label: "4 Player",
        desc: "Open 4 tabs to play",
        config: {humans: 4, rl_agents: 0, bots: 0},
        color: "#004d40"
    }
]

function is_human_game() {
    return gameConfig && gameConfig.humans > 0
}

function is_my_turn() {
    return whoseTurn === myPlayerIndex
}

function is_spectator() {
    return gameConfig && gameConfig.humans === 0
}

function update_viewing_hand() {
    if (!players || players.length === 0) return
    const hand = players[viewingPlayerIndex].hand
    cards.length = 0
    if (hand) {
        for (let i = 0; i < hand.length; i++) {
            cards.push({rank: hand[i].rank, suit: hand[i].suit})
        }
    }
}

game.addEventListener("click", (e) => {
    if (gamePhase === "lobby") {
        const startX = game.width / 2 - 300
        const startY = 280
        const btnW = 260
        const btnH = 80
        const cols = 2
        const gapX = 40
        const gapY = 20

        for (let i = 0; i < PRESETS.length; i++) {
            const col = i % cols
            const row = Math.floor(i / cols)
            const x = startX + col * (btnW + gapX)
            const y = startY + row * (btnH + gapY)

            if (e.clientX > x && e.clientX < x + btnW &&
                e.clientY > y && e.clientY < y + btnH) {
                ws.send(JSON.stringify({
                    action: "configure",
                    config: PRESETS[i].config
                }))
                gameConfig = PRESETS[i].config
                viewingPlayerIndex = 0
                gamePhase = "loading"
                draw_scene()
                return
            }
        }
        return
    }

    if (gamePhase === "bidding" && is_my_turn_to_bid()) {
        const centerX = game.width / 2
        const centerY = game.height / 2

        if (e.clientX > centerX - 20 && e.clientX < centerX + 20 &&
            e.clientY > centerY - 60 && e.clientY < centerY - 20) {
            if (currentBid < 13) currentBid++
        }

        if (e.clientX > centerX - 20 && e.clientX < centerX + 20 &&
            e.clientY > centerY + 20 && e.clientY < centerY + 60) {
            if (currentBid > 0) currentBid--
        }

        if (e.clientX > centerX - 50 && e.clientX < centerX + 50 &&
            e.clientY > centerY + 60 && e.clientY < centerY + 100) {
            ws.send(JSON.stringify({action: "bid", value: currentBid}))
        }

        draw_scene()
        return
    }

    // toggle view button — show next player's hand
    if (gamePhase === "playing" || gamePhase === "bidding") {
        const btnX = game.width - 160
        const btnY = game.height - 50
        if (e.clientX > btnX && e.clientX < btnX + 140 &&
            e.clientY > btnY && e.clientY < btnY + 36) {
            viewingPlayerIndex = (viewingPlayerIndex + 1) % (players ? players.length : 4)
            update_viewing_hand()
            draw_scene()
            return
        }
    }

    if (gamePhase === "playing" && is_my_turn()) {
        if (selectedIndex !== null) {
            const btnX = game.width / 2 - 60
            const btnY = cardY - 80
            if (e.clientX > btnX && e.clientX < btnX + 120 &&
                e.clientY > btnY && e.clientY < btnY + 40) {
                ws.send(JSON.stringify({
                    action: "play_card",
                    card: cards[selectedIndex]
                }))
                selectedIndex = null
                draw_scene()
                return
            }
        }

        if (viewingPlayerIndex === myPlayerIndex) {
            for (let i = 0; i < cards.length; i++) {
                const x = 20 + i * spacing
                if (e.clientX > x && e.clientX < x + cardW &&
                    e.clientY > cardY - 20 && e.clientY < cardY + cardH) {
                    if (is_legal(cards[i])) {
                        selectedIndex = selectedIndex === i ? null : i
                    }
                }
            }
        }
        draw_scene()
    }

    if (gamePhase === "round_over" || gamePhase === "game_over") {
        const btnX = game.width / 2 - 80
        const btnY = game.height / 2 + 200
        if (e.clientX > btnX && e.clientX < btnX + 160 &&
            e.clientY > btnY && e.clientY < btnY + 50) {
            if (gamePhase === "round_over") {
                ws.send(JSON.stringify({action: "next_round"}))
            } else if (gamePhase === "game_over") {
                ws.send(JSON.stringify({action: "play_again"}))
                gamePhase = "lobby"
                selectedIndex = null
                currentBid = 0
                draw_scene()
            }
        }
        return
    }
})

function is_my_turn_to_bid() {
    if (!players) return false
    const me = players[myPlayerIndex]
    return me && me.type === "HumanPlayer" && me.bid === null
}

function is_legal(card) {
    if (viewingPlayerIndex !== myPlayerIndex) return false
    if (legalPlays.length === 0) return true
    return legalPlays.some(c => c.rank === card.rank && c.suit === card.suit)
}

function draw_card(rank, suit, x, y, elevated, legal = true) {
    const drawY = elevated ? y - 20 : y
    ctx.fillStyle = legal ? "white" : "#2d5a40"
    ctx.fillRect(x, drawY, cardW, cardH)

    if (!legal) {
        ctx.strokeStyle = "#1a3d2b"
        ctx.lineWidth = 2
        ctx.strokeRect(x, drawY, cardW, cardH)
    }

    ctx.font = "20px Arial"
    ctx.fillStyle = legal ? SUIT_COLORS[suit] : "#4a7a5a"
    ctx.fillText(rank, x + 8, drawY + 24)
    ctx.fillText(SUITS[suit], x + 8, drawY + 48)
}

function draw_lobby() {
    ctx.fillStyle = BACKGROUND
    ctx.fillRect(0, 0, game.width, game.height)

    ctx.fillStyle = "white"
    ctx.font = "bold 48px Arial"
    ctx.textAlign = "center"
    ctx.fillText("♠ SPADES ♠", game.width / 2, 120)

    ctx.font = "20px Arial"
    ctx.fillStyle = "#dddddd"
    ctx.fillText("Choose a game mode to begin", game.width / 2, 170)

    ctx.font = "16px Arial"
    ctx.fillStyle = "#aaaaaa"
    ctx.fillText("8 rounds per game — hit your bid to score", game.width / 2, 210)

    const startX = game.width / 2 - 300
    const startY = 280
    const btnW = 260
    const btnH = 80
    const cols = 2
    const gapX = 40
    const gapY = 20

    for (let i = 0; i < PRESETS.length; i++) {
        const col = i % cols
        const row = Math.floor(i / cols)
        const x = startX + col * (btnW + gapX)
        const y = startY + row * (btnH + gapY)

        ctx.fillStyle = PRESETS[i].color
        ctx.fillRect(x, y, btnW, btnH)

        ctx.strokeStyle = "rgba(255,255,255,0.3)"
        ctx.lineWidth = 1
        ctx.strokeRect(x, y, btnW, btnH)

        ctx.fillStyle = "white"
        ctx.font = "bold 18px Arial"
        ctx.textAlign = "center"
        ctx.fillText(PRESETS[i].label, x + btnW / 2, y + 30)

        ctx.font = "13px Arial"
        ctx.fillStyle = "rgba(255,255,255,0.8)"
        ctx.fillText(PRESETS[i].desc, x + btnW / 2, y + 55)
    }

    ctx.textAlign = "left"
}

function draw_loading() {
    ctx.fillStyle = BACKGROUND
    ctx.fillRect(0, 0, game.width, game.height)
    ctx.fillStyle = "white"
    ctx.font = "bold 28px Arial"
    ctx.textAlign = "center"
    ctx.fillText("Loading...", game.width / 2, game.height / 2)
    ctx.textAlign = "left"
}

function draw_bid_selector() {
    if (!is_my_turn_to_bid()) {
        // show waiting message
        const centerX = game.width / 2
        const centerY = game.height / 2
        ctx.fillStyle = "rgba(0,0,0,0.6)"
        ctx.fillRect(centerX - 150, centerY - 40, 300, 60)
        ctx.fillStyle = "#dddddd"
        ctx.font = "20px Arial"
        ctx.textAlign = "center"
        ctx.fillText("Waiting for your turn to bid...", centerX, centerY)
        ctx.textAlign = "left"
        return
    }

    const centerX = game.width / 2
    const centerY = game.height / 2

    ctx.fillStyle = "rgba(0, 0, 0, 0.75)"
    ctx.fillRect(centerX - 110, centerY - 130, 220, 240)

    ctx.fillStyle = "white"
    ctx.font = "24px Arial"
    ctx.fillText("Your Bid:", centerX - 50, centerY - 88)

    ctx.fillText("▲", centerX - 10, centerY - 44)

    ctx.font = "48px Arial"
    ctx.fillText(currentBid, centerX - 14, centerY + 10)

    ctx.font = "24px Arial"
    ctx.fillText("▼", centerX - 10, centerY + 40)

    ctx.fillStyle = "#4caf50"
    ctx.fillRect(centerX - 50, centerY + 60, 100, 40)
    ctx.fillStyle = "white"
    ctx.font = "20px Arial"
    ctx.fillText("Confirm", centerX - 35, centerY + 86)
}

function draw_player_info() {
    if (!players) return
    for (let i = 0; i < players.length; i++) {
        const tricks = trickCounts[players[i].name] !== undefined
            ? trickCounts[players[i].name] : 0
        const bid_num = players[i].bid !== null ? players[i].bid : 0
        const score = scores[players[i].name] !== undefined
            ? scores[players[i].name] : 0
        const bag = bags[players[i].name] !== undefined
            ? bags[players[i].name] : 0

        const bidDisplay = players[i].bid !== null ? players[i].bid : "?"

        let typeLabel = ""
        if (players[i].type === "RLAgent") typeLabel = " 🤖"
        else if (players[i].type === "RuleBasedBot") typeLabel = " 🎲"
        else if (players[i].type === "HumanPlayer") typeLabel = " 👤"

        // highlight viewing player with gold border
        const isViewing = i === viewingPlayerIndex
        const isMe = i === myPlayerIndex

        ctx.fillStyle = isViewing
            ? "rgba(180, 140, 0, 0.6)"
            : "rgba(0, 0, 0, 0.45)"
        ctx.fillRect(14 + i * 280, 8, 260, 66)

        if (isViewing) {
            ctx.strokeStyle = "#ffd700"
            ctx.lineWidth = 2
            ctx.strokeRect(14 + i * 280, 8, 260, 66)
        }

        if (isMe && players[i].type === "HumanPlayer") {
            ctx.strokeStyle = "#44ff88"
            ctx.lineWidth = 2
            ctx.strokeRect(14 + i * 280, 8, 260, 66)
        }

        ctx.font = "bold 16px Arial"
        ctx.fillStyle = "#ffffff"
        ctx.fillText(`${players[i].name}${typeLabel}${isMe && players[i].type === "HumanPlayer" ? " (You)" : ""}`, 20 + i * 280, 24)

        ctx.font = "14px Arial"
        ctx.fillStyle = "#dddddd"
        ctx.fillText(`Bid: ${bidDisplay} | Score: ${score} | Bags: ${bag}`, 20 + i * 280, 44)

        ctx.fillStyle = tricks > bid_num ? "#ff4444" : "#44ff88"
        ctx.font = "bold 14px Arial"
        ctx.fillText(`Tricks: ${tricks}`, 20 + i * 280, 64)
    }
}

function draw_trick() {
    if (!currentTrick || currentTrick.length === 0) return

    const centerX = game.width / 2
    const centerY = game.height / 2

    const positions = [
        {x: centerX - 40, y: centerY + 20},
        {x: centerX + 60, y: centerY - 60},
        {x: centerX - 40, y: centerY - 140},
        {x: centerX - 140, y: centerY - 60},
    ]

    for (let i = 0; i < currentTrick.length; i++) {
        const card = currentTrick[i].card
        const pos = positions[i]
        draw_card(card.rank, card.suit, pos.x, pos.y, false, true)
        ctx.fillStyle = "rgba(0, 0, 0, 0.6)"
        ctx.fillRect(pos.x, pos.y - 18, 80, 18)
        ctx.fillStyle = "#ffffff"
        ctx.font = "12px Arial"
        ctx.fillText(currentTrick[i].player, pos.x + 4, pos.y - 4)
    }
}

function draw_trick_winner() {
    if (!trickWinner) return
    ctx.fillStyle = "rgba(0, 0, 0, 0.7)"
    ctx.fillRect(game.width / 2 - 200, game.height / 2 - 30, 400, 60)
    ctx.fillStyle = "#44ff88"
    ctx.font = "bold 32px Arial"
    ctx.fillText(trickWinner, game.width / 2 - 180, game.height / 2 + 14)
}

function draw_play_button() {
    if (!is_my_turn()) return
    if (selectedIndex === null) return
    if (viewingPlayerIndex !== myPlayerIndex) return
    const btnX = game.width / 2 - 60
    const btnY = cardY - 80
    ctx.fillStyle = "#c0392b"
    ctx.fillRect(btnX, btnY, 120, 40)
    ctx.fillStyle = "white"
    ctx.font = "bold 20px Arial"
    ctx.fillText("Play Card", btnX + 8, btnY + 26)
}

function draw_toggle_button() {
    if (gamePhase !== "playing" && gamePhase !== "bidding") return
    if (!players) return
    const btnX = game.width - 160
    const btnY = game.height - 50
    ctx.fillStyle = "rgba(0,0,0,0.6)"
    ctx.fillRect(btnX, btnY, 140, 36)
    ctx.strokeStyle = "#ffd700"
    ctx.lineWidth = 1
    ctx.strokeRect(btnX, btnY, 140, 36)
    ctx.fillStyle = "#ffd700"
    ctx.font = "13px Arial"
    ctx.fillText(`👁 View: ${players[viewingPlayerIndex].name}`, btnX + 8, btnY + 22)
}

function draw_turn_indicator() {
    if (!is_human_game()) return
    if (gamePhase !== "playing") return
    const centerX = game.width / 2
    if (is_my_turn()) {
        ctx.fillStyle = "rgba(0,0,0,0.6)"
        ctx.fillRect(centerX - 80, cardY - 120, 160, 30)
        ctx.fillStyle = "#44ff88"
        ctx.font = "bold 16px Arial"
        ctx.textAlign = "center"
        ctx.fillText("Your turn!", centerX, cardY - 100)
        ctx.textAlign = "left"
    } else if (whoseTurn !== null && players) {
        ctx.fillStyle = "rgba(0,0,0,0.6)"
        ctx.fillRect(centerX - 120, cardY - 120, 240, 30)
        ctx.fillStyle = "#dddddd"
        ctx.font = "16px Arial"
        ctx.textAlign = "center"
        ctx.fillText(`Waiting for ${players[whoseTurn].name}...`, centerX, cardY - 100)
        ctx.textAlign = "left"
    }
}

function draw_round_over() {
    const centerX = game.width / 2
    const centerY = game.height / 2

    ctx.fillStyle = "rgba(0, 0, 0, 0.88)"
    ctx.fillRect(centerX - 300, centerY - 220, 600, 480)

    ctx.fillStyle = "white"
    ctx.font = "bold 28px Arial"

    if (gamePhase === "game_over") {
        ctx.fillText("Game Over!", centerX - 80, centerY - 180)
        if (players && Object.keys(scores).length > 0) {
            const winner = players.reduce((a, b) =>
                (scores[a.name] || 0) > (scores[b.name] || 0) ? a : b
            )
            ctx.fillStyle = "#44ff88"
            ctx.font = "22px Arial"
            ctx.fillText(
                `${winner.name} wins with ${scores[winner.name]} pts!`,
                centerX - 180, centerY - 140
            )
        }
    } else {
        ctx.fillText(`Round ${roundNumber} Results`, centerX - 130, centerY - 180)
    }

    if (roundResults) {
        ctx.font = "17px Arial"
        for (let i = 0; i < roundResults.length; i++) {
            ctx.fillStyle = "#cccccc"
            ctx.fillText(roundResults[i], centerX - 270, centerY - 130 + i * 36)
        }
    }

    ctx.font = "18px Arial"
    let y = centerY + 60
    ctx.fillStyle = "white"
    ctx.fillText("Current Scores:", centerX - 270, y)
    y += 30
    if (players) {
        for (let i = 0; i < players.length; i++) {
            const score = scores[players[i].name] || 0
            const bag = bags[players[i].name] || 0
            ctx.fillStyle = "#44ff88"
            ctx.fillText(
                `${players[i].name}: ${score} pts | ${bag} bags`,
                centerX - 270, y
            )
            y += 28
        }
    }

    const btnLabel = gamePhase === "game_over" ? "Back to Lobby" : "Next Round"
    ctx.fillStyle = "#2e7d32"
    ctx.fillRect(centerX - 80, centerY + 200, 160, 50)
    ctx.strokeStyle = "#44ff88"
    ctx.lineWidth = 2
    ctx.strokeRect(centerX - 80, centerY + 200, 160, 50)
    ctx.fillStyle = "white"
    ctx.font = "bold 20px Arial"
    ctx.fillText(btnLabel, centerX - 60, centerY + 232)
}

function draw_hand() {
    for (let i = 0; i < cards.length; i++) {
        const x = 20 + i * spacing
        const legal = viewingPlayerIndex === myPlayerIndex ? is_legal(cards[i]) : true
        draw_card(cards[i].rank, cards[i].suit, x, cardY, selectedIndex === i && viewingPlayerIndex === myPlayerIndex, legal)
    }
}

function draw_spectator_label() {
    if (is_human_game()) return
    ctx.fillStyle = "rgba(0,0,0,0.5)"
    ctx.fillRect(game.width / 2 - 80, game.height - 40, 160, 30)
    ctx.fillStyle = "#44ff88"
    ctx.font = "bold 16px Arial"
    ctx.textAlign = "center"
    ctx.fillText("SPECTATOR MODE", game.width / 2, game.height - 20)
    ctx.textAlign = "left"
}

function draw_scene() {
    if (gamePhase === "lobby") {
        draw_lobby()
        return
    }

    if (gamePhase === "loading") {
        draw_loading()
        return
    }

    ctx.fillStyle = BACKGROUND
    ctx.fillRect(0, 0, game.width, game.height)

    draw_player_info()
    draw_trick()
    draw_trick_winner()
    draw_hand()
    draw_play_button()
    draw_toggle_button()
    draw_turn_indicator()
    draw_spectator_label()

    if (gamePhase === "bidding" && is_human_game()) {
        draw_bid_selector()
    }

    if (gamePhase === "round_over" || gamePhase === "game_over") {
        draw_round_over()
    }
}

const ws = new WebSocket("ws://localhost:8000/ws")

ws.onmessage = (event) => {
    const state = JSON.parse(event.data)

    if (state.phase === "lobby") {
        gamePhase = "lobby"
        if (state.your_player_index !== undefined) {
            myPlayerIndex = state.your_player_index
            viewingPlayerIndex = myPlayerIndex
        }
        draw_scene()
        return
    }

    if (state.your_player_index !== undefined) {
        myPlayerIndex = state.your_player_index
    }

    if (state.players) {
        players = state.players
    }

    currentTrick = state.current_trick || []
    trickCounts = state.trick_counts || {}
    trickWinner = state.trick_winner || null
    legalPlays = state.legal_plays || []
    scores = state.scores || {}
    bags = state.bags || {}
    roundNumber = state.round_number || 1
    roundResults = state.round_results || null
    whoseTurn = state.whose_turn !== undefined ? state.whose_turn : null

    if (state.config) {
        gameConfig = state.config
    }

    if (state.players) {
        update_viewing_hand()
    }

    if (state.phase) {
        gamePhase = state.phase
    }

    if (gamePhase === "round_over" || gamePhase === "game_over") {
        selectedIndex = null
    }

    if (gamePhase === "bidding") {
        currentBid = 0
        selectedIndex = null
    }

    draw_scene()
}

ctx.fillStyle = BACKGROUND
ctx.fillRect(0, 0, game.width, game.height)
draw_scene()
