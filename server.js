const express = require('express');
const { MongoClient } = require('mongodb');

const app = express();
const port = process.env.PORT || 3000;
const uri = "YOUR_MONGODB_URI";
const client = new MongoClient(uri);

app.use(express.json());

app.get('/api/leads', async (req, res) => {
    try {
        const page = parseInt(req.query.page) || 1;
        const limit = parseInt(req.query.limit) || 20;
        const skip = (page - 1) * limit;

        await client.connect();
        const db = client.db("b2b_database");
        const collection = db.collection("yc_leads");

        const leads = await collection.find({}).skip(skip).limit(limit).toArray();
        const total = await collection.countDocuments();

        res.json({
            status: "success",
            metadata: {
                total_records: total,
                current_page: page,
                records_per_page: limit
            },
            data: leads
        });
    } catch (error) {
        res.status(500).json({ error: "Internal server error" });
    }
});

app.listen(port, () => {
    console.log(`API running on http://localhost:${port}`);
});