import path from "path";
import { config } from "dotenv";
import fetch from "node-fetch";
import { fileURLToPath } from "url";

// Corrige o caminho do arquivo atual
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Carrega variáveis do .env
config({ path: path.resolve(__dirname, ".env") });

console.log(
  "DEBUG: Valor da variável OPENAI_API_KEY:",
  process.env.OPENAI_API_KEY
);

if (!process.env.OPENAI_API_KEY) {
  console.error(
    "ERRO: Chave da OpenAI não configurada. Adicione sua chave no arquivo .env"
  );
} else {
  console.log("Chave da OpenAI carregada com sucesso!");
}

// Função assíncrona para chamada à API
async function testOpenAI() {
  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
    },
    body: JSON.stringify({
      model: "gpt-3.5-turbo", // Corrija aqui!
      messages: [{ role: "user", content: "Olá!" }],
    }),
  });

  const data = await response.json();
  console.log("Resposta da OpenAI:", data);
}

testOpenAI();
