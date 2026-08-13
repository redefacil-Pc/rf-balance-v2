import { zodResolver } from '@hookform/resolvers/zod';
import {
  Alert,
  Anchor,
  Box,
  Button,
  Card,
  Center,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { IconAlertTriangle } from '@tabler/icons-react';
import { useForm } from 'react-hook-form';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

import { useLogin } from '@/features/auth/mutations/useLogin';
import { useCurrentUser } from '@/features/auth/queries/useCurrentUser';
import { loginSchema, type LoginForm } from '@/features/auth/schemas/login-schema';

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { data: usuario } = useCurrentUser();
  const login = useLogin();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  });

  if (usuario) {
    const destino = (location.state as { from?: string } | null)?.from ?? '/';
    return <Navigate to={destino} replace />;
  }

  const enviar = handleSubmit((form) => {
    login.mutate(form, {
      onSuccess: () => {
        const destino = (location.state as { from?: string } | null)?.from ?? '/';
        navigate(destino, { replace: true });
      },
    });
  });

  return (
    <Center mih="100vh" bg="gray.0" p="md">
      <Box w="100%" maw={420}>
        <Stack gap="xs" mb="lg" ta="center">
          <Title order={1} size="h2">
            RF Balance
          </Title>
          <Text c="dimmed" size="sm">
            Operação comercial, recebimentos e comissionamento
          </Text>
        </Stack>

        <Card withBorder shadow="sm" padding="lg" radius="md">
          <form onSubmit={enviar} noValidate>
            <Stack gap="md">
              {login.isError && (
                <Alert
                  variant="light"
                  color="red"
                  icon={<IconAlertTriangle size={18} />}
                  title={login.error.problem.title}
                  role="alert"
                >
                  <Text size="sm">{login.error.problem.detail}</Text>
                  {login.error.correlationId && (
                    <Text size="xs" c="dimmed" mt={4}>
                      Código para o suporte: {login.error.correlationId.slice(0, 8)}
                    </Text>
                  )}
                </Alert>
              )}

              <TextInput
                label="E-mail"
                placeholder="nome@empresa.com.br"
                autoComplete="username"
                autoFocus
                withAsterisk
                error={errors.email?.message}
                {...register('email')}
              />

              <PasswordInput
                label="Senha"
                autoComplete="current-password"
                withAsterisk
                error={errors.password?.message}
                {...register('password')}
              />

              <Button type="submit" fullWidth loading={login.isPending}>
                Entrar
              </Button>

              <Text size="xs" c="dimmed" ta="center">
                Esqueceu a senha?{' '}
                <Anchor size="xs" href="mailto:suporte@rfbalance.local">
                  Fale com o administrador
                </Anchor>
              </Text>
            </Stack>
          </form>
        </Card>
      </Box>
    </Center>
  );
}
