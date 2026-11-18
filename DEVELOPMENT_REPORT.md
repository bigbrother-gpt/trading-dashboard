# HERMES v1.0 — Relatório de desenvolvimento

**17 de novembro de 2026** · Evolução da base v0.6 para a v1.0.

## Síntese

A versão 1.0 é um **marco de integração e teste**, não o lançamento público de uma plataforma de inteligência financeira plenamente autónoma. Foi preservada a interface aprovada, e foi acrescentada uma via completa de recolha de metadados RSS/Atom → triagem por regras → agrupamento conservador → revisão experimental de factos estruturados → publicação de um JSON limitado → visualização segura no website.

## Trabalhos realizados

1. **Auditoria da v0.6:** inspecionados código, catálogo de 14 fontes, testes, fluxo manual de GitHub Actions, frontend e documentação. Confirmado que a revisão factual exige observações estruturadas e que a interface apresentava acontecimentos fictícios.
2. **Novo publicador `engine/publish.py`:** recusa snapshots antigos ou recolhas sem feeds bem-sucedidos, valida URLs HTTP(S), conserva apenas referências, títulos, datas e etiquetas preliminares; aplica janela de 30 dias a datas conhecidas e limita a 180 itens/650 KB.
3. **Novo `live-data.js`:** apresenta snapshots reais de metadados, quando existem, com título, hora, fonte e instrumento potencial; não usa HTML arbitrário proveniente de RSS. Se não houver snapshot válido, regressa à demonstração com aviso visível.
4. **Proteção contra conclusões falsas:** notícias reais não recebem localização, gravidade, factos confirmados ou previsões de impacto inventadas. O mapa real fica sem pins até existir geolocalização validada.
5. **`engine/scoring.py`:** fórmula aprovada 50/30/20 com limiares provisórios, rejeitando dados incompletos e valores fora de escala. Não pontua notícias automaticamente.
6. **GitHub Actions:** testes offline e pipeline de recolha/publicação em execução **manual**, com criação de artefacto estático e diagnósticos, sem commits automáticos nem ativação de Pages.
7. **Documentação e licenciamento:** README atualizado, relatório técnico, `.gitignore` para impedir crescimento do histórico de snapshots e licença MIT para código original.
8. **Testes:** 27 testes unitários passaram offline, incluindo 7 novos testes para publicação e classificação. Não houve validação live dos feeds, nem teste end-to-end num navegador remoto.

## O que já existia e foi preservado

- Frontend aprovado com mapa monocromático, fronteiras realçadas, caduceu transparente, favicon e pins acessíveis; secções Map, Live, News e Markets.
- Recolha inicial de 14 feeds propostos, triagem lexical multilingue, agrupamento conservador de títulos e comparação experimental de observações estruturadas.
- Watchlist de sete instrumentos e regra de saturação experimental de três fontes redundantes, condicionada a independência confirmada externamente.

## O que NÃO foi implementado ou validado

- Motor de IA aberto em produção; extração autónoma de factos e verificação de independência; geolocalização real; severidade automática confiável; cotações financeiras; players de vídeo embutidos; atualizações automáticas públicas; publicação efetiva no GitHub Pages; direitos e funcionamento real dos feeds; testes de browser completos.

## Decisões técnicas tomadas sem pedir nova aprovação

- **Segurança factual acima da aparência de completude:** o mapa não coloca notícias reais em países inferidos a partir do título.
- **Publicação em modo não verificado:** permite inspecionar fontes reais sem apresentar rumores como factos confirmados.
- **Execução manual por omissão:** evita automatizar recolha e publicação de fontes cujas permissões ainda não foram confirmadas.
- **Sem modelos externos por enquanto:** não seria rigoroso prometer inferência gratuita e eficiente sem testes de CPU e limites.
- **Licença MIT para código do projeto:** sujeita a confirmação antes de publicação pública, se preferires outra licença.

## Riscos e prioridades

**Prioridade alta:** legalidade das fontes, verificação factual e proveniência, deteção de eventos distintos, precisão geográfica, viabilidade da IA no plano gratuito, publicação com limites rígidos.

**Prioridade média:** dados de mercados com direitos de reutilização, integração de broadcasts, testes de acessibilidade e browser, ampliação geográfica e linguística.

## Resultado e decisão pedida ao utilizador

A base v1.0 pode ser revista e testada offline; **não deve ser apresentada ao público como serviço de inteligência financeira verificado**. Após revisão, a decisão mais importante será escolher entre lançar primeiro uma beta claramente identificada como agregador de títulos não verificados ou adiar o lançamento até existir validação factual autónoma.
