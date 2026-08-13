import { TextInput } from '@mantine/core';
import { Controller, type Control, type FieldValues, type Path } from 'react-hook-form';

/**
 * Campo de texto que reformata o valor a cada tecla.
 *
 * O formulário guarda o valor **mascarado**, que é o que o operador vê e confere.
 * A conversão para o formato da API (string decimal, dígitos do documento) é
 * responsabilidade do schema Zod, num `transform` — assim existe um único ponto
 * de tradução entre a tela e o contrato, e nenhuma máscara vaza para o payload.
 */
interface Props<T extends FieldValues> {
  control: Control<T>;
  name: Path<T>;
  label: string;
  mascarar: (valor: string) => string;
  error?: string;
  placeholder?: string;
  withAsterisk?: boolean;
  disabled?: boolean;
  inputMode?: 'numeric' | 'decimal' | 'text';
  leftSection?: React.ReactNode;
}

export function CampoMascarado<T extends FieldValues>({
  control,
  name,
  label,
  mascarar,
  error,
  placeholder,
  withAsterisk,
  disabled,
  inputMode = 'numeric',
  leftSection,
}: Props<T>) {
  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => (
        <TextInput
          label={label}
          placeholder={placeholder}
          withAsterisk={withAsterisk}
          disabled={disabled}
          inputMode={inputMode}
          leftSection={leftSection}
          error={error}
          name={field.name}
          ref={field.ref}
          value={typeof field.value === 'string' ? field.value : ''}
          onBlur={field.onBlur}
          onChange={(evento) => field.onChange(mascarar(evento.currentTarget.value))}
        />
      )}
    />
  );
}
