import { navegacao } from '@/app/layouts/navegacao';
import { preloadRoute, routeModules } from '@/app/router/route-modules';

describe('routeModules', () => {
  it('mantém um módulo carregável para cada item do menu', () => {
    const caminhos = navegacao.flatMap((grupo) => grupo.itens.map((item) => item.caminho));

    expect(Object.keys(routeModules).sort()).toEqual(caminhos.sort());
  });

  it('inicia o carregamento antecipado de uma rota conhecida', () => {
    const carregamentoPendente = new Promise<
      Awaited<ReturnType<(typeof routeModules)['/']>>
    >(() => undefined);
    const load = vi.spyOn(routeModules, '/').mockReturnValue(carregamentoPendente);

    preloadRoute('/');

    expect(load).toHaveBeenCalledOnce();
  });

  it('ignora caminhos que não possuem módulo local', () => {
    expect(() => preloadRoute('/rota-inexistente')).not.toThrow();
  });
});
