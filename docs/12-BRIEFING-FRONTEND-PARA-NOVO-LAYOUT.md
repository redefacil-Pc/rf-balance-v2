# Briefing funcional do frontend — RF Balance

## 1. Finalidade deste documento

Este documento descreve exclusivamente o frontend do RF Balance para servir como entrada em uma ferramenta de IA especializada em criação de layouts.

O objetivo é permitir a criação de uma interface completamente nova, sem copiar a aparência, a organização visual ou os componentes da versão existente. O novo layout pode propor outra navegação, outra hierarquia, novos componentes e uma experiência visual diferente, desde que preserve as informações, ações, permissões e regras funcionais descritas aqui.

Este documento não especifica banco de dados, infraestrutura, arquitetura do backend ou regras internas de cálculo.

## 2. Resumo do produto

O RF Balance é uma aplicação web interna para gestão comercial e financeira. Ela acompanha o ciclo completo de uma operação:

1. cadastro da proposta comercial;
2. declaração de pagamento e envio de comprovante;
3. conferência e aprovação pelo financeiro;
4. reconhecimento dos recebimentos;
5. cálculo e acompanhamento das comissões;
6. fechamento e pagamento dos beneficiários;
7. emissão de relatórios;
8. auditoria das alterações realizadas.

O sistema também centraliza cadastros de colaboradores, usuários, empresas, unidades, equipes, contas bancárias, regras de comissão e períodos financeiros.

É uma ferramenta de trabalho diário. A interface precisa favorecer velocidade, legibilidade de valores, redução de erros e clareza sobre o que requer ação.

## 3. Perfis de usuário

A interface é controlada por permissões. Um usuário não deve visualizar ações ou áreas para as quais não possui acesso.

### 3.1 Administrativo

- Mantém usuários, acessos e cadastros estruturais.
- Pode consultar auditoria e informações gerais.
- Dependendo das permissões, pode editar colaboradores, equipes, empresas e regras.

### 3.2 Comercial e operação

- Cadastra e acompanha propostas.
- Informa consultor, cliente, valor, TPS e participantes da operação.
- Pode declarar pagamentos e anexar comprovantes.
- Acompanha devoluções feitas pelo financeiro.

### 3.3 Financeiro

- Trabalha em filas de aprovação.
- Confere dados da proposta, valores e comprovantes.
- Aprova ou devolve propostas e recebimentos.
- Pode estornar recebimentos aprovados.
- Acompanha períodos, fechamentos e pagamentos.

### 3.4 Liderança e gestão

- Acompanha produção, receita, comissões, pendências e desempenho.
- Consulta relatórios por organização, unidade ou equipe.
- Pode acompanhar ranking e evolução da operação.

### 3.5 Colaborador beneficiário

- Pode ter acesso mais restrito aos próprios dados ou às áreas autorizadas.

## 4. Características gerais da experiência

O novo frontend deve ser pensado como uma aplicação desktop responsiva, também utilizável em tablets e celulares.

Características prioritárias:

- valores monetários e percentuais precisam ser fáceis de comparar;
- itens que aguardam decisão devem ter destaque claro;
- ações irreversíveis ou sensíveis devem exigir confirmação;
- filtros e contexto selecionado não podem ser confundidos com resultados;
- tabelas extensas precisam continuar compreensíveis em telas menores;
- o usuário deve perceber rapidamente o estado atual de cada operação;
- ações disponíveis devem variar conforme permissão e estado do registro;
- o sistema deve apresentar carregamento, erro, vazio e sucesso de forma explícita;
- dados pessoais devem aparecer mascarados quando o usuário não possuir permissão;
- o idioma da interface é português do Brasil.

O layout não precisa utilizar sidebar, cards ou tabelas tradicionais. Esses elementos podem ser substituídos por outras soluções, desde que a densidade de informação e a eficiência operacional sejam preservadas.

## 5. Arquitetura de informação

### 5.1 Acesso

- Login.
- Identificação do usuário autenticado.
- Troca de tema, caso o conceito ofereça modos claro e escuro.
- Menu do usuário e encerramento da sessão.

### 5.2 Operação

- Dashboard.
- Propostas.
- Aprovação de propostas.
- Recebimentos.

### 5.3 Cadastros

- Colaboradores.
- Equipes.
- Empresas e unidades.
- Contas bancárias de recebimento.

### 5.4 Comissionamento

- Regras de comissão.
- Períodos de comissão.
- Fechamentos.

### 5.5 Análise

- Relatório financeiro.
- Auditoria.

### 5.6 Administração

- Usuários e acessos.
- Operações administrativas futuras.

## 6. Estrutura global esperada

A IA de layout deve propor uma estrutura global contendo:

- identificação clara do produto;
- navegação entre os módulos permitidos para o usuário;
- indicação da página atual;
- acesso ao perfil e à saída do sistema;
- área principal de conteúdo;
- suporte a notificações temporárias de sucesso e erro;
- indicação de propostas pendentes de aprovação junto ao acesso da fila financeira;
- navegação móvel equivalente à experiência desktop.

A navegação não deve exibir módulos sem permissão. A proteção visual não substitui a autorização do servidor, mas evita apresentar ações impossíveis ao usuário.

## 7. Telas e conteúdos

### 7.1 Login

Objetivo: autenticar o usuário com e-mail e senha.

Elementos necessários:

- identidade do RF Balance;
- campo de e-mail;
- campo de senha;
- ação principal para entrar;
- acesso ao suporte ou administrador;
- mensagem detalhada em caso de credenciais inválidas;
- código de correlação para suporte quando fornecido pelo servidor;
- estado de envio e bloqueio contra múltiplos cliques.

### 7.2 Dashboard

Objetivo: oferecer uma visão consolidada da operação em determinado período.

Controles:

- atalhos de período, como semana e mês;
- período personalizado com data inicial e final.

Indicadores principais:

- produção aprovada;
- faturamento reconhecido;
- total de comissões;
- faturamento líquido;
- comissão da empresa;
- pendência financeira;
- TPS médio;
- quantidade total de propostas;
- propostas abertas;
- propostas parcialmente pagas;
- propostas quitadas;
- propostas canceladas;
- quantidade aguardando aprovação.

Visualizações complementares:

- evolução diária da produção aprovada;
- faturamento reconhecido por dia;
- ranking de consultores por produção;
- quantidade de propostas por consultor;
- acessos rápidos para propostas, recebimentos, fechamentos e relatório financeiro.

O painel deve priorizar leitura e decisão, evitando uma grade de números sem hierarquia.

### 7.3 Propostas

Objetivo: cadastrar e acompanhar operações comerciais que ainda não estão na fila de decisão do financeiro.

Regra essencial: uma proposta com aprovação no estado “Aguardando financeiro” não deve aparecer nesta tela. Ela deve aparecer exclusivamente na fila de aprovação.

Filtros:

- nome do cliente;
- identificador externo/Redmine;
- consultor;
- situação financeira;
- data inicial;
- data final;
- limpar filtros.

Informações de cada proposta:

- data do negócio;
- identificador externo;
- cliente;
- CPF ou CNPJ, completo ou parcialmente mascarado conforme permissão;
- consultor;
- valor da operação;
- TPS;
- comissão da empresa;
- valor em aberto;
- situação financeira;
- situação da aprovação.

Ações condicionais:

- cadastrar nova proposta;
- editar valor e TPS;
- cancelar proposta;
- abrir detalhes, comprovantes e fluxo de aprovação;
- carregar mais resultados.

Estados financeiros da proposta:

- Em aberto;
- Parcialmente paga;
- Quitada;
- Cancelada.

Estados de aprovação da proposta:

- Rascunho;
- Aguardando financeiro;
- Aprovada;
- Devolvida.

Os dois grupos de estado são independentes e precisam ser visualmente diferenciados.

### 7.4 Cadastro de proposta

O cadastro pode ser apresentado como modal, painel lateral, página dedicada ou fluxo em etapas.

Campos da proposta:

- consultor;
- data do negócio;
- nome do cliente;
- CPF ou CNPJ do cliente;
- valor da operação;
- TPS em percentual;
- identificador Redmine;
- colaborador de BKO opcional;
- colaborador de finalização opcional.

O backend calcula a comissão. O frontend apenas coleta e apresenta os dados, sem calcular valores financeiros por conta própria.

Quando permitido, o cadastro pode incluir um bloco opcional de pagamento inicial:

- valor pago;
- data do pagamento;
- hora efetiva;
- forma de pagamento;
- conta que recebeu;
- comprovante obrigatório quando houver valor informado;
- pré-visualização do arquivo selecionado quando possível.

O usuário deve poder criar somente a proposta ou criar proposta e pagamento na mesma operação. Ao cancelar o formulário, os dados temporários e o comprovante selecionado devem ser descartados.

### 7.5 Fila de aprovação de propostas

Objetivo: apresentar ao financeiro somente propostas enviadas e ainda não decididas.

Informações da fila:

- quantidade pendente;
- data;
- proposta e cliente;
- identificador externo;
- consultor;
- valor da operação;
- comissão da empresa;
- situação;
- ação “Analisar”.

Recursos:

- atualizar fila;
- carregar mais;
- avançar para a próxima proposta após uma decisão;
- estado vazio informando que não existem propostas aguardando aprovação.

### 7.6 Análise e aprovação de proposta

Objetivo: fornecer contexto suficiente para o financeiro decidir sem navegar por várias telas.

Conteúdo da análise:

- dados do cliente e da proposta;
- participantes: consultor, BKO e finalização;
- valor da operação;
- TPS;
- comissão da empresa;
- total pago e saldo em aberto;
- indicação de valor excedente quando aplicável;
- recebimentos vinculados;
- data, valor, forma de pagamento e conta de cada recebimento;
- comprovantes;
- histórico cronológico da proposta;
- autor e horário dos eventos;
- motivo de devolução anterior, quando existir.

Comprovantes:

- devem ser visualizados dentro do sistema;
- imagens devem aparecer em pré-visualização;
- PDFs devem ser exibidos em visualizador incorporado quando o navegador permitir;
- arquivos não visualizáveis devem apresentar informações e opção de download;
- o download deve continuar disponível mesmo quando houver pré-visualização.

Ações:

- enviar ao financeiro, quando ainda estiver em rascunho e existir valor declarado;
- aprovar;
- devolver para correção com motivo obrigatório;
- cancelar e voltar;
- confirmar explicitamente antes da aprovação final.

### 7.7 Recebimentos

Objetivo: acompanhar todos os pagamentos declarados e suas decisões financeiras.

Filtro:

- situação do recebimento.

Informações:

- data;
- proposta e cliente;
- referência;
- pessoa que lançou;
- forma de pagamento;
- conta que recebeu;
- valor;
- situação;
- motivo de devolução ou estorno;
- comprovante.

Estados:

- Aguardando financeiro;
- Aprovado;
- Devolvido;
- Estornado.

Ações condicionais:

- visualizar comprovante sem download obrigatório;
- baixar comprovante;
- analisar recebimento pendente;
- aprovar ou devolver;
- visualizar memória de cálculo da comissão;
- estornar recebimento aprovado, com confirmação e motivo.

O financeiro não deve aprovar o próprio lançamento quando essa restrição estiver ativa.

### 7.8 Colaboradores

Objetivo: manter as pessoas que participam operacionalmente das propostas e comissões.

Filtros principais:

- busca por nome ou documento;
- função;
- regime tributário;
- situação;
- empresa e unidade, quando aplicável.

Informações:

- nome;
- documento completo ou mascarado;
- funções vigentes;
- regime CLT ou MEI;
- existência e situação da conta de acesso;
- situação ativa ou inativa.

Ações:

- cadastrar colaborador;
- editar cadastro;
- gerenciar funções e suas vigências;
- vincular ou trocar conta de acesso;
- inativar ou reativar.

Um colaborador pode acumular funções. A interface não deve tratar função como um único valor fixo.

### 7.9 Equipes

Objetivo: representar relações entre líderes e integrantes ao longo do tempo.

Conteúdos:

- equipes e líderes ativos;
- integrantes vinculados;
- consulta do líder vigente em determinada data;
- histórico de atribuições;
- início e fim da vigência.

Ações:

- atribuir líder;
- encerrar atribuição;
- consultar histórico.

A vigência temporal é importante porque relatórios e comissões consideram a equipe existente na data da operação.

### 7.10 Empresas e unidades

Objetivo: manter a estrutura organizacional.

Empresas:

- razão social;
- nome fantasia;
- CNPJ;
- situação;
- cadastrar, editar, inativar ou reativar.

Unidades:

- empresa vinculada;
- código;
- nome;
- situação;
- cadastrar, editar, inativar ou reativar.

O layout deve deixar clara a relação hierárquica “empresa contém unidades”.

### 7.11 Contas bancárias de recebimento

Objetivo: manter as contas que podem ser selecionadas ao declarar um pagamento.

Informações:

- nome ou identificação da conta;
- ordem de exibição;
- situação ativa ou inativa.

Ações:

- cadastrar nova conta;
- editar identificação e ordem;
- ativar ou inativar;
- salvar apenas as linhas alteradas.

### 7.12 Regras de comissão

Objetivo: consultar e versionar as regras utilizadas nos cálculos.

Conteúdos:

- versão;
- nome;
- período de vigência;
- estado da versão: rascunho, agendada, ativa ou encerrada;
- faixas de TPS;
- percentual correspondente;
- configurações por função e estratégia;
- políticas dos beneficiários.

Ações:

- criar versão;
- copiar uma versão existente;
- editar rascunho;
- ativar versão com confirmação e motivo.

Uma versão anterior não deve ser sobrescrita. O histórico precisa permanecer compreensível.

### 7.13 Períodos de comissão

Objetivo: controlar intervalos, cutoff e congelamento de cálculos.

Informações:

- data inicial e final;
- data e hora de cutoff;
- estado aberto ou fechado;
- motivo;
- indicação de reabertura.

Ações:

- criar período;
- fechar período com confirmação;
- reabrir período com justificativa detalhada.

O fechamento congela cálculos e ajustes. A reabertura é excepcional e precisa ser comunicada visualmente como ação sensível e auditada.

### 7.14 Fechamentos

Objetivo: consolidar e pagar valores devidos aos colaboradores em determinado período.

Filtros:

- data inicial;
- data final.

Resumo por beneficiário:

- nome;
- função ou funções;
- valor bruto;
- acumulado anterior;
- bônus;
- desconto;
- valor adiado;
- valor pago;
- valor a pagar;
- situação.

Os beneficiários são agrupados em setores:

- consultores;
- finalização;
- BKO;
- lideranças;
- outros, quando necessário.

Ações:

- gerar ou atualizar fechamentos;
- lançar comissão manual de BKO;
- lançar bônus de finalização;
- ajustar bônus, desconto ou adiamento;
- registrar pagamento.

A interface deve explicar de maneira acessível como o saldo final é formado.

### 7.15 Relatório financeiro

Objetivo: oferecer análise consolidada e detalhada dos valores reconhecidos e das comissões.

Filtros:

- data inicial;
- data final;
- escopo organizacional;
- unidade;
- líder de equipe vigente na data final.

Indicadores principais:

- faturamento reconhecido;
- produção reconhecida;
- comissões calculadas;
- faturamento líquido.

Indicadores por categoria:

- consultores;
- liderança;
- finalização;
- líder de finalização;
- BKO;
- bônus;
- descontos;
- valores adiados;
- valores pagos;
- valores a pagar.

Tabela por beneficiário:

- beneficiário;
- função e regra;
- valor automático;
- valor manual;
- valor calculado;
- acumulado anterior;
- desconto;
- adiado;
- pago;
- a pagar;
- estado do fechamento;
- ação para detalhar a origem.

Recursos:

- agrupamento por setores;
- detalhamento da composição de cada valor;
- exportação em PDF;
- exportação em planilha;
- indicação de processamento ou disponibilidade dos documentos.

### 7.16 Usuários e acessos

Objetivo: administrar contas e perfis do sistema.

Filtros:

- nome ou e-mail;
- perfil;
- situação ativa ou inativa.

Informações:

- nome;
- e-mail;
- perfis de acesso;
- situação;
- último acesso;
- vínculo opcional com colaborador.

Ações:

- criar conta, perfil e função operacional em um fluxo integrado;
- editar usuário;
- alterar perfis;
- inativar ou reativar;
- redefinir senha;
- encerrar sessões ao inativar ou redefinir senha.

A senha temporária gerada deve ser exibida uma única vez, com alerta para envio por canal seguro.

### 7.17 Auditoria

Objetivo: consultar a trilha imutável de alterações realizadas no sistema.

Filtros:

- data inicial e final;
- módulo;
- ação;
- ator;
- tipo de entidade;
- identificador da entidade;
- código de correlação.

Informações da lista:

- data e hora;
- ator;
- módulo;
- ação;
- entidade;
- código de correlação;
- ação para detalhar.

Detalhes:

- ator;
- data e hora;
- ação;
- entidade;
- correlação completa;
- contexto registrado no evento.

O conteúdo técnico pode ser apresentado em bloco monoespaçado, mas deve continuar legível e copiável.

## 8. Fluxos críticos

### 8.1 Proposta sem pagamento inicial

Cadastro da proposta → proposta em rascunho/aberta → declaração posterior de recebimento → envio ao financeiro → análise → aprovação ou devolução.

### 8.2 Proposta com pagamento inicial

Cadastro da proposta e do pagamento no mesmo fluxo → comprovante obrigatório → envio para análise → aprovação ou devolução.

### 8.3 Aprovação financeira

Abrir fila → selecionar proposta → conferir operação, recebimentos e comprovantes → confirmar aprovação ou informar motivo da devolução → avançar para o próximo item.

### 8.4 Recebimento posterior

Abrir proposta → declarar recebimento → anexar comprovante → aguardar financeiro → aprovação → geração das comissões correspondentes.

### 8.5 Fechamento

Selecionar período → gerar fechamentos → conferir setores e beneficiários → realizar ajustes → registrar pagamentos → consultar no relatório.

## 9. Padrões de interação necessários

### 9.1 Listagens

- filtros visíveis ou facilmente acessíveis;
- contagem de resultados;
- paginação ou carregamento incremental;
- ordenação visualmente compreensível quando disponível;
- ações da linha próximas do item relacionado;
- cabeçalhos persistentes em tabelas longas, se o conceito permitir;
- alternativa responsiva para dispositivos estreitos.

### 9.2 Formulários

- rótulos sempre visíveis;
- indicação de obrigatoriedade;
- máscaras brasileiras para moeda, percentual, CPF, CNPJ e PIX;
- validação próxima ao campo;
- resumo de erro do servidor quando necessário;
- ação principal claramente diferenciada da ação de cancelar;
- bloqueio e indicador durante envio.

### 9.3 Confirmações

Devem ser usadas para:

- aprovação financeira;
- devolução;
- cancelamento;
- estorno;
- inativação;
- fechamento e reabertura de período;
- ativação de regra;
- pagamento de fechamento.

A confirmação deve mostrar o item afetado, o efeito da ação e, quando aplicável, solicitar um motivo.

### 9.4 Estados de tela

Toda consulta deve prever:

- carregando;
- carregado com dados;
- vazio com orientação útil;
- erro com opção de tentar novamente;
- sem permissão;
- atualização em segundo plano.

Toda mutação deve prever:

- estado inicial;
- envio;
- sucesso;
- erro de validação;
- conflito por dado desatualizado;
- erro inesperado com código de correlação.

## 10. Regras de apresentação de dados

- Moeda: formato brasileiro, como `R$ 12.345,67`.
- Percentual: vírgula decimal, como `31,50%`.
- Data de negócio: `DD/MM/AAAA`, sem conversão indevida de fuso horário.
- Data e hora de eventos: horário de São Paulo.
- Valores financeiros vêm prontos do backend como strings decimais.
- O frontend não recalcula comissão, saldo, faturamento ou fechamento.
- Números financeiros devem usar algarismos tabulares quando possível.
- CPF, CNPJ e outros dados pessoais devem respeitar a permissão de visualização.
- Estados devem combinar texto e sinal visual; não depender somente de cor.
- Motivos de devolução, cancelamento e estorno devem permanecer próximos do estado correspondente.

## 11. Requisitos de acessibilidade e responsividade

- Contraste adequado entre texto, fundo, bordas e estados.
- Navegação utilizável por teclado.
- Foco visível.
- Campos associados aos seus rótulos.
- Botões de ícone com nome acessível ou tooltip.
- Modais com foco controlado e fechamento previsível.
- Erros anunciados de forma acessível.
- Não comunicar estado somente por cor.
- Áreas de toque adequadas em dispositivos móveis.
- Tabelas largas podem usar rolagem horizontal, cartões responsivos ou visualização detalhada.
- A navegação deve possuir uma versão móvel real, não apenas reduzir a largura do desktop.

## 12. Liberdade criativa para a nova proposta

A IA pode explorar livremente:

- sidebar, navegação superior, launcher, command palette ou combinação desses padrões;
- dashboard editorial, operacional, modular ou orientado por filas;
- visualização em tabela, cartões, linhas expansíveis ou painéis mestre-detalhe;
- página dedicada, painel lateral, modal ou etapas para cadastros complexos;
- modo claro, escuro ou ambos;
- linguagem visual, tipografia, iconografia, cores, espaçamento e movimento;
- reorganização das áreas desde que as permissões e fluxos sejam preservados.

Evitar:

- transformar todas as informações em cartões iguais;
- esconder ações frequentes em muitos níveis de menu;
- usar gráficos decorativos sem apoiar uma decisão;
- reduzir densidade a ponto de exigir navegação excessiva;
- misturar fila de aprovação com propostas comuns;
- exigir download para analisar um comprovante;
- inventar métricas ou cálculos inexistentes;
- apresentar ações que o perfil não pode executar.

## 13. Entregáveis desejados da IA de layout

Solicitar, preferencialmente:

1. conceito visual e justificativa;
2. mapa de navegação desktop e mobile;
3. design system básico com cores, tipografia, espaçamento, estados e componentes;
4. login;
5. dashboard;
6. listagem de propostas;
7. cadastro de proposta completo;
8. fila e análise financeira com pré-visualização de comprovante;
9. recebimentos;
10. fechamentos e relatório financeiro;
11. uma tela de cadastro administrativo;
12. estados de carregamento, vazio, erro, sucesso e sem permissão;
13. versões desktop, tablet e mobile das telas críticas;
14. protótipo navegável ou especificação suficiente para implementação em React.

## 14. Resumo curto para usar como prompt

Crie um novo frontend para o RF Balance, uma aplicação interna de gestão comercial, recebimentos, aprovação financeira e comissões. O produto acompanha propostas desde o cadastro até o pagamento dos beneficiários. Ele possui dashboard, propostas, fila financeira, recebimentos, colaboradores, equipes, empresas, unidades, contas bancárias, regras versionadas de comissão, períodos, fechamentos, relatório financeiro, usuários e auditoria. A interface deve ser responsiva, densa sem ser confusa, orientada a tarefas e permissões, adequada para valores financeiros e totalmente diferente do layout existente. Preserve os dois estados independentes da proposta, mantenha itens enviados ao financeiro exclusivamente na fila de aprovação e permita analisar imagens e PDFs de comprovantes dentro do sistema. Não calcule valores no frontend e não invente métricas. Produza uma arquitetura de navegação, design system e layouts desktop/mobile para os fluxos críticos.
