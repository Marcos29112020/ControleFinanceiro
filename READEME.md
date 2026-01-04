Descrição
Este é um aplicativo de gerenciamento de finanças pessoais desenvolvido em Python, inicialmente como uma aplicação desktop usando Tkinter e SQLite. Agora, migrado para uma versão web/offline usando PyScript (baseado em WebAssembly), permitindo execução no navegador sem servidor backend. O app ajuda usuários a rastrear receitas, despesas, orçamentos, investimentos e gerar relatórios.

Modo Web: Acesse via navegador para uso online.
Modo Offline: Suporte como Progressive Web App (PWA), com cache para funcionamento sem internet (exceto chamadas API externas como Polygon para cotações de ações).
Banco de Dados: SQLite em memória (persistência limitada; planeje upgrades para IndexedDB).

Nota: Esta é uma versão protótipo. Funcionalidades completas do app original (autenticação, transações, relatórios) estão sendo portadas gradualmente para PyScript.
Recursos

Autenticação: Cadastro e login de usuários com hash de senhas (usando JS Crypto para web).
Transações: Adicionar, editar, deletar receitas e despesas.
Orçamentos: Definir limites mensais por categoria e monitorar status.
Investimentos: Gerenciar portfólio com cotações reais via Polygon API (requer chave API).
Relatórios: Saldo, gráficos de despesas (pizza) e portfólio (barras) usando Matplotlib.
Gráficos: Renderizados dinamicamente no navegador.
PWA: Instalável como app nativo em desktop/mobile, com suporte offline.

Instalação
Para Desenvolvimento Local

Clone o repositório:textgit clone https://github.com/seu-usuario/financas-pyscript-app.git
cd financas-pyscript-app
Abra index.html diretamente no navegador (Chrome recomendado para PWA).
Para editar: Use um editor de código como VS Code.

Para Uso Online

Acesse o link do GitHub Pages: https://seu-usuario.github.io/financas-pyscript-app/
Instale como PWA: No navegador, clique no ícone de instalação na barra de URL.

Dependências: Nenhuma instalação manual necessária! PyScript carrega pacotes via CDN (pandas, matplotlib, etc.). Para offline total, baixe assets localmente (veja docs PyScript).
Uso

Acesse o App: Abra o link ou index.html local.
Login/Cadastro: Use o form para criar uma conta ou logar.
Adicionar Transações: Preencha valor, categoria e descrição.
Gerenciar Orçamentos/Investimentos: Use os botões para definir limites ou adicionar ativos (ex: AAPL).
Relatórios: Visualize saldo, gráficos e status de orçamento.
Chave API Polygon: Insira sua chave (obtenha em polygon.io) para cotações reais.
Offline: Após primeiro acesso, o app cacheia arquivos. DB em memória perde dados ao fechar; use exportar para CSV se necessário.

Exemplo de Fluxo:

Cadastre um usuário.
Adicione uma receita de "Salário" R$5000.
Defina orçamento para "Alimentação" R$1000.
Adicione investimento em "AAPL" (quantidade e custo médio).
Gere relatório para ver gráficos.

Dependências

PyScript: Para executar Python no navegador.
Pacotes Python: pandas, matplotlib, requests, datetime (carregados via PyScript).
Outros: Service Worker para PWA offline.

Sem instalação: Tudo roda client-side.
Limitações e Melhorias Pendentes

Persistência: DB em memória; implementar IndexedDB para salvar dados localmente.
Segurança: Hash de senhas usa JS Crypto; evite dados sensíveis em produção.
API Offline: Cotações Polygon requerem internet; fallback para valores mock.
UI: Forms HTML simples; melhorar com CSS/Bootstrap.
Porte Completo: Algumas features do Tkinter original ainda em migração.
Performance: Apps PyScript podem ser lentos em dispositivos antigos.

Contribuições bem-vindas! Abra issues para bugs ou sugestões.
Contribuição

Fork o repositório.
Crie uma branch: git checkout -b feature/nova-funcionalidade.
Commit mudanças: git commit -m 'Adiciona nova funcionalidade'.
Push: git push origin feature/nova-funcionalidade.
Abra um Pull Request.

Licença
MIT License. Veja LICENSE para detalhes.
Contato

Desenvolvedor: https://github.com/Marcos29112020
Email: marcossilvamecanico2017@gmail.com

Aproveite o app e gerencie suas finanças com eficiência!