# HERMES v1.3 — Relatório de alterações

1. ECB como fonte primária de notícias: feed já presente no catálogo, confirmado na documentação oficial.
2. Criado leitor da API oficial ECB para taxas de referência diárias de USD/GBP/JPY contra EUR. Cálculo derivado de GBPUSD e USDJPY com base comum e variação em pontos/percentagem para 1D, 5D, 1M. Sem gráficos.
3. Interface aprovada preservada, com seleção do intervalo e indicação clara de que os valores não são preços em tempo real. Falta fonte autorizada para XAUUSD, NAS100, BTCUSD.
4. Melhorada a extração conservadora de afirmações para não transformar interrogações ou linguagem especulativa em afirmações categóricas. Continua sem verificação factual autónoma.
5. GitHub Pages workflow inclui ficheiro de cotações. Nenhum deployment efetuado nem endpoint testado em execução real neste ambiente.
6. Forex Factory pode servir como fonte editorial/calendário se os termos o permitirem; não foi adicionado scraper. GDELT adiado.

## Limites e riscos

O BCE publica taxas de referência, não bid/ask nem tick de mercado. A comparação de taxas derivadas pode não coincidir com um broker. Direitos de reutilização precisam de revisão antes de publicação. Os testes são unitários com fixtures; não validam API em produção, licenças, cobertura global nem modelo LLM em CPU.
