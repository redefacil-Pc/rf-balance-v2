# 0013 — Papéis de colaborador em tabela associativa e intervalos de vigência fechados

- **Status:** aceito
- **Data:** 2026-08-11
- **Decisores:** Orlean
- **Fase afetada:** F2 (colaboradores e vínculos), consumido pela F4

## Contexto

O sistema atual guarda a função do colaborador em um único campo de texto. Isso cria um enum combinatório (`CONSULTOR_LIDER` para quem acumula dois papéis) e impossibilita saber qual papel valia numa data passada — informação de que o motor de comissão da F4 depende.

Além disso, o blueprint (7.3) exige que a convenção de inclusividade dos intervalos de vigência seja **única e testada**, mas não escolhe qual.

## Decisão

**Papéis em `collaborator_roles`**, uma linha por papel, cada uma com `valid_from` e `valid_to`. Uma pessoa acumula funções sem enum combinatório, e o papel vigente numa data é uma consulta, não uma interpretação de string.

**Intervalos fechados em ambas as pontas** (`[valid_from, valid_to]`), com `valid_to IS NULL` significando "vigente, sem fim previsto". A consulta canônica, idêntica à da seção 7.3:

```sql
valid_from <= :data_de_referencia
AND (valid_to IS NULL OR valid_to >= :data_de_referencia)
```

Consequência direta: **transferência fecha o vínculo anterior em `novo_inicio - 1 dia`**. Não existe intervalo de duração zero; `valid_from > valid_to` é rejeitado no domínio.

A mesma convenção vale para `team_assignments`, `commission_rule_assignments` e qualquer vigência futura. Uma convenção, um lugar: `DateRange` em `platform`.

**Sobreposição** é proibida por papel/tipo e verificada em duas camadas: no domínio, antes de gravar, e por rotina periódica em `data_integrity_checks` — o MySQL não tem constraint de exclusão por intervalo, então não há garantia declarativa possível.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Campo de texto único (como hoje) | Simples | Enum combinatório; sem histórico; quebra a F4 | É justamente o defeito que a reconstrução corrige |
| Intervalo semiaberto `[início, fim)` | Aritmética de datas mais limpa; padrão em muitos sistemas | O usuário informa "vigente até 31/08" e o banco guardaria 01/09 — divergência entre tela e dado, em sistema operado por humanos | O fechado espelha o que o operador diz e o que o blueprint escreveu em 7.3 |
| Sem `valid_to`, inferindo o fim pelo registro seguinte | Menos campo para manter | Toda consulta histórica passa a depender de subconsulta ordenada; lacuna fica indistinguível de vigência | Consulta histórica é caminho crítico da F4 |

## Consequências

**Obrigatório:**

- `DateRange` é o único lugar que interpreta vigência; nenhuma comparação de data solta em query de negócio.
- Toda criação ou alteração de vínculo verifica sobreposição no domínio.
- Transferência é uma operação atômica: fecha o anterior e abre o novo na mesma transação.
- Colaborador inativo não recebe vínculo novo (7.2).

**Proibido:**

- Alterar vigência que já sustenta snapshot de cálculo fechado — nesse caso, a correção é compensatória (7.2: "alterações não mudam snapshots históricos já fechados").

**A revisitar:** se o banco migrar para PostgreSQL (ADR-0002), a proibição de sobreposição passa a ter garantia declarativa por `EXCLUDE USING gist`, e a verificação periódica deixa de ser necessária.

## Impacto financeiro ou de dados

Alto e indireto: a atribuição de líder e o papel vigente na data determinam **quem recebe comissão**. Erro de um dia na fronteira do intervalo troca o beneficiário. Por isso a convenção é testada explicitamente nos casos de fronteira de data exigidos pela seção 16.2.
