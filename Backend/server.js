import express from 'express'
import cors from 'cors'

const app = express()

app.use(cors())

app.use(express.json())

app.post('/submissionForm', (req, res) => {
    const {
        mode,
        location,
        season,
        soil,
        crop
    } = req.body

    console.log(location, mode, season, soil, crop)

    res.json({ message: "Hello" })
})

app.listen('8000', () => {
    console.log("server running : http://localhost:8000")
})