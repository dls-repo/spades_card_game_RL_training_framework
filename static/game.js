const BACKGROUND = "#101010"
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
let gamePhase = "bidding"
let players = null
let currentTrick = []
let trickCounts = {}
let trickWinner = null
let legalPlays = []
let scores = {}
let bags = {}
let roundNumber = 1
let roundResults = null
const cards = []

function is_legal(card) {
    if (legalPlays.length === 0) return true
    return legalPlays.some(c => c.rank === card.rank && c.suit === card.suit)
}

game.addEventListener("click", (e) => {
    if (gamePhase === "bidding") {
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
            gamePhase = "playing"
        }

        draw_scene()
        return
    }

    if (gamePhase === "playing") {
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

        for (let i = 0; i < cards.length; i++) {
            const x = 20 + i * spacing
            if (e.clientX > x && e.clientX < x + cardW &&
                e.clientY > cardY - 20 && e.clientY < cardY + cardH) {
                if (is_legal(cards[i])) {
                    selectedIndex = selectedIndex === i ? null : i
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
            }
        }
        return
    }
})

function draw_card(rank, suit, x, y, elevated, legal = true) {
    const drawY = elevated ? y - 20 : y
    ctx.fillStyle = legal ? "white" : "#555555"
    ctx.fillRect(x, drawY, cardW, cardH)
    ctx.font = "20px Arial"
    ctx.fillStyle = legal ? SUIT_COLORS[suit] : "#888888"
    ctx.fillText(rank, x + 8, drawY + 24)
    ctx.fillText(SUITS[suit], x + 8, drawY + 48)
}

function draw_bid_selector() {
    const centerX = game.width / 2
    const centerY = game.height / 2

    ctx.fillStyle = "rgba(0, 0, 0, 0.7)"
    ctx.fillRect(centerX - 100, centerY - 120, 200, 220)

    ctx.fillStyle = "white"
    ctx.font = "24px Arial"
    ctx.fillText("Your Bid:", centerX - 50, centerY - 80)

    ctx.fillText("▲", centerX - 10, centerY - 40)

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
    ctx.font = "16px Arial"
    for (let i = 0; i < players.length; i++) {
        const bid = players[i].bid !== null ? players[i].bid : "?"
        const tricks = trickCounts[players[i].name] !== undefined
            ? trickCounts[players[i].name] : 0
        const bid_num = players[i].bid !== null ? players[i].bid : 0
        const score = scores[players[i].name] !== undefined
            ? scores[players[i].name] : 0
        const bag = bags[players[i].name] !== undefined
            ? bags[players[i].name] : 0

        ctx.fillStyle = "white"
        ctx.fillText(`${players[i].name}`, 20 + i * 280, 24)
        ctx.fillStyle = "#aaaaaa"
        ctx.fillText(`Bid: ${bid} | Score: ${score} | Bags: ${bag}`, 20 + i * 280, 44)
        ctx.fillStyle = tricks > bid_num ? "#e94560" : "#4caf50"
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
        ctx.fillStyle = "#aaaaaa"
        ctx.font = "12px Arial"
        ctx.fillText(currentTrick[i].player, pos.x, pos.y - 4)
    }
}

function draw_trick_winner() {
    if (!trickWinner) return
    ctx.fillStyle = "rgba(0, 0, 0, 0.6)"
    ctx.fillRect(game.width / 2 - 200, game.height / 2 - 30, 400, 60)
    ctx.fillStyle = "#4caf50"
    ctx.font = "32px Arial"
    ctx.fillText(trickWinner, game.width / 2 - 180, game.height / 2 + 14)
}

function draw_play_button() {
    if (selectedIndex === null) return
    const btnX = game.width / 2 - 60
    const btnY = cardY - 80
    ctx.fillStyle = "#e94560"
    ctx.fillRect(btnX, btnY, 120, 40)
    ctx.fillStyle = "white"
    ctx.font = "20px Arial"
    ctx.fillText("Play Card", btnX + 10, btnY + 26)
}

function draw_round_over() {
    const centerX = game.width / 2
    const centerY = game.height / 2

    ctx.fillStyle = "rgba(0, 0, 0, 0.85)"
    ctx.fillRect(centerX - 300, centerY - 220, 600, 480)

    ctx.fillStyle = "white"
    ctx.font = "28px Arial"
    ctx.fillText(`Round ${roundNumber} Results`, centerX - 120, centerY - 180)

    if (roundResults) {
        ctx.font = "18px Arial"
        for (let i = 0; i < roundResults.length; i++) {
            ctx.fillStyle = "#aaaaaa"
            ctx.fillText(roundResults[i], centerX - 270, centerY - 130 + i * 36)
        }
    }

    // scores summary
    ctx.font = "18px Arial"
    let y = centerY + 60
    ctx.fillStyle = "white"
    ctx.fillText("Current Scores:", centerX - 270, y)
    y += 30
    if (players) {
        for (let i = 0; i < players.length; i++) {
            const score = scores[players[i].name] || 0
            const bag = bags[players[i].name] || 0
            ctx.fillStyle = "#4caf50"
            ctx.fillText(`${players[i].name}: ${score} pts | ${bag} bags`, centerX - 270, y)
            y += 28
        }
    }

    // next round button
    const btnLabel = gamePhase === "game_over" ? "Game Over" : "Next Round"
    ctx.fillStyle = gamePhase === "game_over" ? "#555555" : "#4caf50"
    ctx.fillRect(centerX - 80, centerY + 200, 160, 50)
    ctx.fillStyle = "white"
    ctx.font = "20px Arial"
    ctx.fillText(btnLabel, centerX - 50, centerY + 232)
}

function draw_hand() {
    for (let i = 0; i < cards.length; i++) {
        const x = 20 + i * spacing
        const legal = is_legal(cards[i])
        draw_card(cards[i].rank, cards[i].suit, x, cardY, selectedIndex === i, legal)
    }
}

function draw_scene() {
    ctx.fillStyle = BACKGROUND
    ctx.fillRect(0, 0, game.width, game.height)

    draw_player_info()
    draw_trick()
    draw_trick_winner()
    draw_hand()
    draw_play_button()

    if (gamePhase === "bidding") {
        draw_bid_selector()
    }

    if (gamePhase === "round_over" || gamePhase === "game_over") {
        draw_round_over()
    }
}

const ws = new WebSocket("ws://localhost:8000/ws")

ws.onmessage = (event) => {
    const state = JSON.parse(event.data)
    players = state.players
    currentTrick = state.current_trick || []
    trickCounts = state.trick_counts || {}
    trickWinner = state.trick_winner || null
    legalPlays = state.legal_plays || []
    scores = state.scores || {}
    bags = state.bags || {}
    roundNumber = state.round_number || 1
    roundResults = state.round_results || null

    const hand = state.players[0].hand
    cards.length = 0
    for (let i = 0; i < hand.length; i++) {
        cards.push({rank: hand[i].rank, suit: hand[i].suit})
    }

    if (state.phase) {
        gamePhase = state.phase
    }

    if (gamePhase === "bidding") {
        currentBid = 0
        selectedIndex = null
    }

    draw_scene()
}

ctx.fillStyle = BACKGROUND
ctx.fillRect(0, 0, game.width, game.height)
