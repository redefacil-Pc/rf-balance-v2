import { zodResolver } from '@hookform/resolvers/zod';
import { Alert, Button, Group, Modal, Stack, Text, Textarea } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconAlertTriangle } from '@tabler/icons-react';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';

import { useCancelProposal } from '@/features/proposals/mutations/useCancelProposal';
import {
  cancelProposalSchema,
  type CancelProposalForm,
} from '@/features/proposals/schemas/proposal-schema';
import type { Proposal } from '@/shared/types/commercial';

interface Props {
  proposta: Proposal | null;
  onFechar: () => void;
}

/** Cancelamento é terminal e exige motivo — a proposta não é apagada. */
export function CancelProposalModal({ proposta, onFechar }: Props) {
  const cancelar = useCancelProposal();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CancelProposalForm>({
    resolver: zodResolver(cancelProposalSchema),
    defaultValues: { reason: '' },
  });

  useEffect(() => {
    reset({ reason: '' });
  }, [proposta, reset]);

  const enviar = handleSubmit((form) => {
    if (!proposta) {
      return;
    }
    cancelar.mutate(
      { id: proposta.id, version: proposta.version, reason: form.reason },
      {
        onSuccess: () => {
          notifications.show({
            color: 'positivo',
            title: 'Proposta cancelada',
            message: `A proposta de ${proposta.customer_name} não produz mais efeito.`,
          });
          onFechar();
        },
      },
    );
  });

  return (
    <Modal
      opened={proposta !== null}
      onClose={onFechar}
      title="Cancelar proposta"
      size="md"
      centered
    >
      <form onSubmit={enviar} noValidate>
        <Stack gap="md">
          {cancelar.isError && (
            <Alert
              variant="light"
              color="red"
              icon={<IconAlertTriangle size={18} />}
              title={cancelar.error.problem.title}
              role="alert"
            >
              <Text size="sm">{cancelar.error.problem.detail}</Text>
            </Alert>
          )}

          <Text size="sm">
            {proposta
              ? `Cancelar a proposta de ${proposta.customer_name}? O cancelamento é definitivo e fica registrado na auditoria.`
              : ''}
          </Text>

          <Textarea
            label="Motivo"
            placeholder="Ex.: cliente desistiu da operação"
            withAsterisk
            autosize
            minRows={2}
            error={errors.reason?.message}
            {...register('reason')}
          />

          <Group justify="flex-end">
            <Button variant="default" onClick={onFechar}>
              Voltar
            </Button>
            <Button type="submit" color="red" loading={cancelar.isPending}>
              Cancelar proposta
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
