# Guia de colaboradores: regime, função e acesso

Este documento explica como cadastrar e alterar colaboradores sem confundir vínculo trabalhista, regra de comissão e permissão de acesso.

## Os três conceitos são independentes

| Conceito | Valores/exemplos | Para que serve |
|---|---|---|
| Regime | `MEI` ou `CLT` | Registra o tipo de vínculo do colaborador. |
| Função vigente | Consultor padrão, Consultor escalonado, Líder, BKO, Finalização etc. | Define o papel operacional e, para consultores, seleciona a regra de comissão. |
| Perfil de acesso | Consultor, Liderança, Operacional, Financeiro, Administrador | Autoriza telas e operações no sistema. Não calcula comissão. |

Assim, um consultor padrão ou escalonado pode ser MEI ou CLT. Alterar o regime não troca a função. Alterar a função não muda o regime nem o perfil de acesso.

## Regras dos consultores

| Função vigente | Regime permitido | Regra aplicada |
|---|---|---|
| Consultor padrão (`CONSULTOR`) | MEI ou CLT | Faixas de percentual por TPS. |
| Consultor escalonado (`CONSULTOR_MEI_ESCALONADO`) | MEI ou CLT | Percentual por produção acumulada do período. O código técnico antigo foi mantido para compatibilidade; na tela o nome é “Consultor escalonado”. |

A função vigente na data do fato é a fonte oficial do cálculo. O nome da pessoa, o regime e o perfil de acesso nunca devem ser usados para deduzir a regra.

## Cadastro

1. Cadastre os dados da pessoa e escolha `MEI` ou `CLT` em **Regime**.
2. Escolha a função operacional. Para consultores, selecione **Consultor padrão** ou **Consultor escalonado**.
3. Crie ou vincule uma conta apenas se a pessoa precisar acessar o sistema.
4. Escolha o perfil de acesso pelas permissões necessárias. O perfil Consultor não define a modalidade de comissão.

Documento identifica a pessoa e não pode ser duplicado. Colaborador e conta de usuário têm vínculo um para um, mas um colaborador pode existir sem conta de acesso.

Uma conta pode ser vinculada, trocada ou desvinculada posteriormente pela ação **Conta de acesso** na lista de colaboradores. Somente contas ativas e ainda livres são oferecidas. A tabela diferencia **Com acesso**, **Conta inativa** e **sem conta**.

## Alteração de regime

Na lista de colaboradores, abra **Editar**, mude **Regime** entre MEI e CLT e salve. A mudança preserva:

- função e regra de comissão;
- conta de acesso;
- equipe e liderança;
- propostas, recebimentos, comissões e histórico.

## Troca entre consultor padrão e escalonado

Na edição do colaborador, use **Regra de comissão (função vigente)**. A mesma troca também pode ser feita em **Funções**: selecione a outra modalidade, informe a data inicial e o motivo e clique em **Trocar**. O sistema encerra a função anterior no dia precedente e inicia a nova na data indicada, preservando o histórico.

Não podem existir funções Consultor padrão e Consultor escalonado vigentes ao mesmo tempo. A data da troca não pode estar no passado pelo fluxo de edição.

## Quando a opção de troca não aparece

A tela consulta diretamente o histórico de funções, sem depender apenas do resumo carregado na tabela.

- Se houver exatamente uma função de consultor vigente, a seleção padrão/escalonado aparece.
- Se não houver função de consultor vigente, a tela apresenta um aviso. Abra **Funções** e atribua primeiro Consultor padrão ou Consultor escalonado.
- Se a listagem acabou de ser alterada em outra aba, atualize a página para renovar todos os resumos.

Recriar o usuário ou o colaborador não é uma correção para esse caso. Isso quebraria referências históricas e poderia desvincular propostas, recebimentos e comissões.

## Exceções individuais

Exceções de comissão podem selecionar consultores ativos de ambos os regimes. A elegibilidade vem da função de consultor vigente, e não do regime MEI/CLT.

## Inativação e reativação

A inativação é efetiva na data operacional de hoje e exige motivo. Ela encerra funções vigentes e vínculos de equipe na mesma transação; funções futuras ainda não iniciadas são canceladas. O histórico anterior permanece disponível.

Um colaborador inativo pode ser reativado pela mesma ação de situação. A reativação não reabre funções antigas automaticamente: atribua as funções necessárias com uma nova vigência. A conta de acesso é administrada separadamente e não é ativada ou desativada junto com o colaborador.

As datas padrão das telas usam `America/Sao_Paulo`, inclusive depois das 21h, sem avançar indevidamente para o dia seguinte por conversão UTC.

## Edição de usuários

Nome, e-mail, perfis e situação enviados pelo modal de edição são gravados em uma única transação. Se qualquer validação falhar, nenhuma parte do formulário fica salva. Alterações de perfil ou inativação também encerram as sessões abertas.

## Diagnóstico da base de demonstração em 17/08/2026

Foram verificados os oito colaboradores e as sete contas vinculadas. Não foram encontrados usuários órfãos, vínculos duplicados ou colaboradores sem as funções esperadas. Por isso os registros e seus identificadores foram preservados.

Na data da verificação:

- Carla Consultora: regime MEI, função Consultor padrão;
- Diego: regime MEI, função Consultor padrão desde 17/08/2026; a função Consultor escalonado anterior ficou preservada no histórico;
- os demais colaboradores mantinham suas funções vigentes e vínculos de acesso.

O nome da massa de demonstração foi ajustado de “Diego MEI 2” para “Diego Consultor Escalonado” em novas instalações, evitando usar o nome antigo da modalidade como se fosse regime.

## Princípio de correção de dados

Cadastros existentes devem ser corrigidos pelos fluxos de edição, função e vínculo de conta. Uma recriação só é aceitável para um registro novo, sem propostas, recebimentos, comissões, equipe, auditoria ou outros vínculos. Em qualquer outro caso, preservar o identificador é obrigatório para manter a rastreabilidade.
