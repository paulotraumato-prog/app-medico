const express = require('express');
const path = require('path');
const app = express();

// Servir arquivos estáticos
app.use(express.static('public'));
app.use(express.json());

// Rota principal
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Health check para Render
app.get('/health', (req, res) => {
    res.json({ status: 'OK', service: 'RenovaReceitas' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`🚀 App rodando na porta ${PORT}`);
});
