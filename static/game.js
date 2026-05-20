const BACKGROUND = "#101010"
const FOREGROUND = "#50FF50"

console.log(game)
game.width = 1200
game.height = 800
const ctx = game.getContext("2d")
console.log(ctx)
ctx.fillStyle = BACKGROUND
ctx.fillRect(0, 0, game.width, game.height)

const cardW = 80
const cardH = 120
const cardY = 670
const spacing = 90
let selectedIndex = null

// build array of card x positions
const cards = []
for (let i = 0; i < 13; i++) {
    cards.push(20 + i * spacing)
}

function draw_hand() {
    ctx.fillStyle = BACKGROUND
    ctx.fillRect(0, 0, game.width, game.height)
    ctx.fillStyle = "white"
    for (let i = 0; i < cards.length; i++) {
        const x = cards[i]
	
	//if card has been selected, draw 20 higher than normal
        const y = selectedIndex === i ? cardY - 20 : cardY
        ctx.fillRect(x, y, cardW, cardH)
    }
}

game.addEventListener("click", (e) => {
    for (let i = 0; i < cards.length; i++) {
        const x = cards[i]
        if (e.clientX > x && e.clientX < x + cardW &&
            e.clientY > cardY - 20 && e.clientY < cardY + cardH) {
            selectedIndex = selectedIndex === i ? null : i
        }
    }
    draw_hand()
})

draw_hand()
